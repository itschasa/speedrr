import transmission_rpc
from transmission_rpc.error import (
    TransmissionAuthError,
    TransmissionConnectError,
    TransmissionTimeoutError,
)
from typing import Union, Literal
import urllib.parse

from helpers.config import SpeedrrConfig, ClientConfig
from helpers.log_loader import logger
from helpers.bit_convert import bit_conv

class TransmissionClient:
    def __init__(self, config: SpeedrrConfig, config_client: ClientConfig) -> None:
        self._client_config = config_client
        self._config = config

        u = urllib.parse.urlparse(config_client.url)

        protocol = u.scheme
        if protocol == "http":
            default_port = 80
        elif protocol == "https":
            default_port = 443
        else:
            raise ValueError(f"<trans|{self._client_config.url}> Unknown url scheme {u.scheme}")
        
        if u.hostname is None:
            raise ValueError(f"<trans|{self._client_config.url}> Missing hostname")

        logger.debug(f"<trans|{self._client_config.url}> Connecting to Transmission at {config_client.url}")

        try:
            self._client = transmission_rpc.Client(
                protocol = protocol,
                username = config_client.username,
                password = config_client.password,
                host = u.hostname,
                port = u.port or default_port, # TODO allow custom port
                path = u.path or "/transmission/rpc", # TODO Check if this has to be customisable
            )
        
        except TransmissionTimeoutError:
            raise Exception(f"<trans|{self._client_config.url}> Connection to Transmission timed out")
        
        except TransmissionAuthError:
            raise Exception(f"<trans|{self._client_config.url}> Failed to login to Transmission, check your credentials")

        except TransmissionConnectError:
            raise Exception(f"<trans|{self._client_config.url}> Failed to connect to Transmission, check your url")

        logger.debug(f"<trans|{self._client_config.url}> Connected to Transmission")

    def get_active_torrent_count(self) -> int:
        "Get the number of torrents that are currently downloading or uploading."

        logger.debug(f"<trans|{self._client_config.url}> Getting active torrent count")

        sessionStats = self._client.session_stats()
        return sessionStats.active_torrent_count

    def set_upload_speed(self, speed: Union[int, float]) -> None:
        "Set the upload speed limit for the client, in config units."

        logger.debug(f"<trans|{self._client_config.url}> Setting upload speed to {speed}{self._config.units}")

        speed_limit_up = max(1, int(bit_conv(speed, self._config.units, 'KB')))
        self._client.set_session(speed_limit_up=speed_limit_up)

    def set_download_speed(self, speed: Union[int, float]) -> None:
        "Set the download speed limit for the client, in config units."

        logger.debug(f"<trans|{self._client_config.url}> Setting dowload speed to {speed}{self._config.units}")

        speed_limit_down = max(1, int(bit_conv(speed, self._config.units, "KB")))
        self._client.set_session(speed_limit_down=speed_limit_down)
