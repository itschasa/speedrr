import httpx
import threading
from typing import Union, List
import time
import traceback
import ipaddress

from helpers.config import SpeedrrConfig, MediaServerConfig
from helpers.log_loader import logger
from helpers.bit_convert import bit_conv



class MediaServerModule:
    def __init__(self, config: SpeedrrConfig, module_config: List[MediaServerConfig], update_event: threading.Event) -> None:
        self.reduction_value_dict: dict[MediaServerConfig, float] = {}

        self._config = config
        self._module_config = module_config
        self._update_event = update_event

        self.servers: list[Union[PlexServer, TautulliServer, JellyfinServer]] = []
        
        for server in self._module_config:
            if server.type == "plex":
                self.servers.append(PlexServer(config, server, self))
            
            elif server.type == "tautulli":
                self.servers.append(TautulliServer(config, server, self))
            
            elif server.type == "jellyfin":
                self.servers.append(JellyfinServer(config, server, self))
            
            else:
                logger.error(f"Unknown media server type in config: {server.type}")
                exit()

            self.servers[-1].get_bandwidth()


    def get_reduction_value(self) -> float:
        "How much to reduce the upload speed by, in the config's units."

        logger.info(f"<media_servers> Reduction values = {'; '.join(f'{server.url}: {reduction}' for server, reduction in self.reduction_value_dict.items())}")
        return sum(self.reduction_value_dict.values())


    def run(self):
        for server in self.servers:
            server.daemon = True
            server.start()



class BaseServer(threading.Thread):
    def __init__(self, config: SpeedrrConfig, server_config: MediaServerConfig, module: MediaServerModule) -> None:
        threading.Thread.__init__(self)
        
        self._config = config
        self._server_config = server_config
        self._module = module

        self._client = httpx.Client(
            base_url=self._server_config.url,
            verify=self._server_config.https_verify
        )

        self._paused_since: dict[str, int] = {}

        self._logger_prefix = f"<{self._server_config.type}|{self._server_config.url}>"

        # Prevents a duplicate event running at the beginning, if the bandwidth for this server is 0 (and thus will not affect the upload speed).
        self._module.reduction_value_dict[self._server_config] = 0
    

    def get_bandwidth(self) -> int:
        "Get the current bandwidth usage from the server, in kbit/s."
        raise NotImplementedError("get_bandwidth must be implemented in a subclass")
    

    def set_reduction(self, reduction) -> None:
        "Set the upload speed reduction for the server, in config units. Accepts kbit/s as input."
        reduction = bit_conv(reduction, "kbit", self._config.units)

        old_reduction = self._module.reduction_value_dict.get(self._server_config)

        if old_reduction == reduction:
            return

        self._module.reduction_value_dict[self._server_config] = reduction
        self._module._update_event.set()
    

    def process_session(self, bandwidth: int, paused: bool, ip_address: str, session_id: str, title: str) -> int:
        "Process a session and return the bandwidth usage. Returns 0 if the session should be ignored."

        if paused and self._server_config.ignore_paused_after != -1:
            
            if session_id not in self._paused_since:
                self._paused_since[session_id] = int(time.time())
                logger.debug(f"{self._logger_prefix} {title}:{session_id} is paused, noted time")
            
            elif int(time.time()) - self._paused_since[session_id] > self._server_config.ignore_paused_after:
                logger.debug(f"{self._logger_prefix} Removing {title}:{session_id} from count, paused for too long")
                return 0
        
        elif self._server_config.ignore_paused_after != -1:
            if session_id in self._paused_since:
                logger.debug(f"{self._logger_prefix} {title}:{session_id} is no longer paused, removing from paused dict")
                del self._paused_since[session_id]
        
        
        if ip_address == "lan":
            local_ip = True
        
        elif ip_address == "wan":
            local_ip = False
        
        elif ipaddress.ip_address(ip_address).is_private:
            local_ip = True
        
        else:
            local_ip = False


        if local_ip and self._server_config.ignore_local_streams:
            logger.debug(f"{self._logger_prefix} Ignoring local stream {title}:{session_id} ({ip_address})")
            return 0
        
        logger.debug(f"{self._logger_prefix} Adding {bandwidth} to count for {title}:{session_id}")
        
        return bandwidth


    def remove_old_paused(self, active_session_ids: list[str]) -> None:
        for session_id in self._paused_since.copy(): # Copy to prevent RuntimeError: dictionary changed size during iteration
            if session_id not in active_session_ids:
                logger.debug(f"{self._logger_prefix} Removing {session_id} from paused_since, no longer in session list")
                del self._paused_since[session_id]


    def run(self) -> None:
        while True:
            try:
                bandwidth = int(self.get_bandwidth() * self._server_config.bandwidth_multiplier)
            except Exception:
                logger.error(f"{self._logger_prefix} Error getting bandwidth:\n" + traceback.format_exc())
            else:
                self.set_reduction(bandwidth)
            
            time.sleep(self._server_config.update_interval)



class PlexServer(BaseServer):
    def get_bandwidth(self) -> int:
        "Get the current bandwidth usage from Plex, in kbit/s."

        logger.debug(f"{self._logger_prefix} Getting bandwidth")
        
        res = self._client.get("/status/sessions", params={"X-Plex-Token": self._server_config.token, "X-Plex-Language": "en"}, headers={"Accept": "application/json"})
        
        logger.debug(f"{self._logger_prefix} Got {res.status_code} response from Plex")
        
        res.raise_for_status()

        res_json: dict = res.json()
        if "MediaContainer" not in res_json:
            raise Exception(f"Error from Plex: {res_json}")
        
        if res_json["MediaContainer"]["size"] == 0:
            logger.debug(f"{self._logger_prefix} No sessions found")
            return 0
        
        count = 0
        session_ids: list[str] = []

        for session in res_json["MediaContainer"]["Metadata"]:
            session_ids.append(session["Session"]["id"])
            
            count += self.process_session(
                bandwidth   = int(session["Session"]["bandwidth"]),
                paused      = session["Player"]["state"] == "paused",
                ip_address  = session["Session"]["location"],
                session_id  = session["Session"]["id"],
                title       = session["title"]
            )
        
        self.remove_old_paused(session_ids)

        return count



class TautulliServer(BaseServer):
    def get_bandwidth(self) -> int:
        "Get the current bandwidth usage from Tautulli, in kbit/s."

        logger.debug(f"{self._logger_prefix} Getting bandwidth")
        
        res = self._client.get("/api/v2", params={"apikey": self._server_config.api_key, "cmd": "get_activity"})

        logger.debug(f"{self._logger_prefix} Got {res.status_code} response from Tautulli")

        res.raise_for_status()

        res_json: dict = res.json()
        if res_json["response"]["result"] != "success":
            raise Exception(f"Error from Tautulli: {res_json['response']['message']}")
        
        count = 0
        session_ids: list[str] = []

        for session in res_json["response"]["data"]["sessions"]:
            session_ids.append(session["session_id"])

            count += self.process_session(
                bandwidth   = int(session["bandwidth"]),
                paused      = session["state"] == "paused",
                ip_address  = session["ip_address"],
                session_id  = session["session_id"],
                title       = session["full_title"]
            )
        
        self.remove_old_paused(session_ids)

        return count



class JellyfinServer(BaseServer):
    def get_bandwidth(self) -> int:
        "Get the current bandwidth usage from Jellyfin, in kbit/s."

        logger.debug(f"{self._logger_prefix} Getting bandwidth")
        
        res = self._client.get("/Sessions", headers={"Authorization": f'MediaBrowser Token="{self._server_config.api_key}"'})

        logger.debug(f"{self._logger_prefix} Got {res.status_code} response from Jellyfin")

        res.raise_for_status()

        res_json: list[dict] = res.json()
        
        count = 0
        session_ids: list[str] = []

        for session in res_json:
            if session.get("NowPlayingItem"): # Ignore sessions that aren't playing anything
                session_ids.append(session["Id"])

                if session["PlayState"]["PlayMethod"] == "DirectPlay":
                    logger.debug(f"{self._logger_prefix} {session['Id']} is direct play, calculating estimated bandwidth from MediaStreams")
                    
                    bandwidth = 0
                    for stream in session["NowPlayingItem"]["MediaStreams"]:
                        bandwidth += int(stream.get("BitRate", 0))
                
                else:
                    bandwidth = int(session["TranscodingInfo"]["Bitrate"])

                count += self.process_session(
                    bandwidth   = bandwidth,
                    paused      = session["PlayState"]["IsPaused"],
                    ip_address  = session["RemoteEndPoint"],
                    session_id  = session["Id"],
                    title       = session["NowPlayingItem"]["Name"]
                )

        self.remove_old_paused(session_ids)

        return int(round(bit_conv(count, 'bit', 'kbit'), 0))

