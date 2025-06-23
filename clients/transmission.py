import transmission_rpc
from transmission_rpc.error import (
    TransmissionAuthError,
    TransmissionConnectError,
    TransmissionTimeoutError,
)
from typing import Union, Literal

from helpers.config import SpeedrrConfig, ClientConfig
from helpers.log_loader import logger
from helpers.bit_convert import bit_conv

class transmissionClient:
    def __init__(self, config: SpeedrrConfig, config_client: ClientConfig) -> None:
        # Get protocol and host adress from the url
        if "http" in config_client.url:
            protocol, url_adress = config_client.url.split("://")
            if protocol not in ("http", "https"):
                raise ValueError(f"<trans|{self._client_config.url}> Url protocol has to be http or https, not {protocol}")
            url_protocol: Literal['http', 'https'] = protocol
        else:
            url_protocol = "http"
            url_adress = config_client.url

        self._client_config = config_client
        self._config = config

        logger.debug(f"<trans|{self._client_config.url}> Connecting to Transmission at {config_client.url}")

        try:
            self._client = transmission_rpc.Client(
                protocol = url_protocol,
                username = config_client.url,
                password = config_client.password,
                host = url_adress,
                port = 9091, # TODO allow custom port
                path = '/transmission/rpc', # TODO Check if this has to be customisable
            )
        
        except TransmissionTimeoutError:
            raise Exception(f"<trans|{self._client_config.url}> Connection to Transmission timed out")
        
        except TransmissionAuthError:
            raise Exception(f"<trans|{self._client_config.url}> Failed to login to Transmission, check your credentials")

        except TransmissionConnectError:
            raise Exception(f"<trans|{self._client_config.url}> Failed to connect to Transmission, check your url")

        logger.debug(f"<trans|{self._client_config.url}> Connected to Transmission")
