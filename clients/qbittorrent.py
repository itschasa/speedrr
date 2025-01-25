import qbittorrentapi
from typing import Union

from helpers.config import SpeedrrConfig, ClientConfig
from helpers.log_loader import logger
from helpers.bit_convert import bit_conv



class qBittorrentClient:
    def __init__(self, config: SpeedrrConfig, config_client: ClientConfig) -> None:
        self._client = qbittorrentapi.Client(
            host = config_client.url,
            username = config_client.username,
            password = config_client.password,
            FORCE_SCHEME_FROM_HOST = True,
            VERIFY_WEBUI_CERTIFICATE = config_client.https_verify
        )
        self._client_config = config_client
        self._config = config

        logger.debug(f"<qbit|{self._client_config.url}> Connecting to qBittorrent at {config_client.url}")

        try:
            self._client.auth_log_in()
        
        except qbittorrentapi.LoginFailed:
            raise Exception(f"<qbit|{self._client_config.url}> Failed to login to qBittorrent, check your credentials")
        
        except qbittorrentapi.Forbidden403Error:
            raise Exception(f"<qbit|{self._client_config.url}> Failed to login to qBittorrent, temporarily banned, try again later")
        
        logger.debug(f"<qbit|{self._client_config.url}> Connected to qBittorrent")


    def get_active_torrent_count(self) -> int:
        "Get the number of torrents that are currently downloading or uploading."

        logger.debug(f"<qbit|{self._client_config.url}> Getting active torrent count")

        return sum(
            1 for torrent in self._client.torrents_info()
            if torrent.state_enum.is_downloading or torrent.state_enum.is_uploading
        )
    

    def set_upload_speed(self, speed: Union[int, float]) -> None:
        "Set the upload speed limit for the client, in config units."
        
        logger.debug(f"<qbit|{self._client_config.url}> Setting upload speed to {speed}{self._config.units}")
        self._client.transfer_set_upload_limit(
            max(1, int(bit_conv(speed, self._config.units, 'B')))
        )


    def set_download_speed(self, speed: Union[int, float]) -> None:
        "Set the download speed limit for the client, in config units."
        
        logger.debug(f"<qbit|{self._client_config.url}> Setting dowload speed to {speed}{self._config.units}")
        self._client.transfer_set_download_limit(
            max(1, int(bit_conv(speed, self._config.units, 'B')))
        )
