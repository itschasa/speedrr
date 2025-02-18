from dataclasses import dataclass, field
from typing import List, Optional, Union, Literal
from dataclass_wizard import YAMLWizard # type: ignore


@dataclass(frozen=True)
class ClientConfig(YAMLWizard):
    type: Literal['qbittorrent', 'deluge', 'transmission']
    url: str
    username: str
    password: str
    https_verify: bool

@dataclass(frozen=True)
class MediaServerConfig(YAMLWizard):
    type: Literal['plex', 'tautulli', 'jellyfin', 'emby']
    url: str
    https_verify: bool
    bandwidth_multiplier: float
    update_interval: int
    ignore_local_streams: bool
    ignore_paused_after: int
    token: Optional[str] = None
    api_key: Optional[str] = None

    def __hash__(self) -> int:
        return super().__hash__()

@dataclass(frozen=True)
class ScheduleConfig(YAMLWizard):
    start: str
    end: str
    days: tuple[Literal['all', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']]
    upload: Union[int, str]
    download: Union[int, str]

@dataclass(frozen=True)
class ModulesConfig(YAMLWizard):
    media_servers: Optional[List[MediaServerConfig]]
    schedule: Optional[List[ScheduleConfig]]

@dataclass(frozen=True)
class SpeedrrConfig(YAMLWizard):
    logs_path: Optional[str]
    units: Literal[
        'bit',
        'B',
        'byte',
        'Kbit',
        'kilobit',
        'Kibit',
        'kibibit',
        'KB',
        'kilobyte',
        'KiB',
        'kibibyte',
        'Mbit',
        'megabit',
        'Mibit',
        'mebibit',
        'MB',
        'megabyte',
        'MiB',
        'mebibyte',
        'Gbit',
        'gigabit',
        'Gibit',
        'gibibit',
        'GB',
        'gigabyte',
        'GiB',
        'gibibyte',
    ]
    min_upload: int
    max_upload: int
    min_download: int
    max_download: int
    clients: List[ClientConfig]
    modules: ModulesConfig


def load_config(config_file: str) -> SpeedrrConfig:
    config = SpeedrrConfig.from_yaml_file(config_file)
    if isinstance(config, list):
        raise ValueError("Config can't be a list")
    return config
