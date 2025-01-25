import threading
from typing import Union, List
import traceback

from helpers.log_loader import logger
from helpers import arguments, config, log_loader
from clients import qbittorrent
from modules import media_server, schedule



if __name__ == '__main__':
    args = arguments.load_args()

    logger.debug("Loading config")

    if not args.config:
        logger.critical("No config file specified, use --config_path arg or SPEEDRR_CONFIG env var to specify a config file.")
        exit()

    cfg = config.load_config(args.config)

    if cfg.logs_path:
        log_loader.set_file_handler(cfg.logs_path, args.log_file_level)
    
    log_loader.stdout_handler.setLevel(args.log_level)
    
    logger.info("Starting Speedrr")

    
    update_event = threading.Event()
    

    clients: List[Union[qbittorrent.qBittorrentClient]] = []
    for client in cfg.clients:
        if client.type == "qbittorrent":
            torrent_client = qbittorrent.qBittorrentClient(cfg, client)
        
        else:
            logger.critical(f"Unknown client type in config: {client.type}")
            exit()

        clients.append(torrent_client)


    modules: List[Union[media_server.MediaServerModule, schedule.ScheduleModule]] = []
    if cfg.modules.media_servers:
        plex_module = media_server.MediaServerModule(cfg, cfg.modules.media_servers, update_event)
        modules.append(plex_module)

    if cfg.modules.schedule:
        schedule_module = schedule.ScheduleModule(cfg, cfg.modules.schedule, update_event)
        modules.append(schedule_module)
    

    if not modules:
        logger.critical("No modules enabled in config, exiting")
        exit()
    

    for module in modules:
        module.run()
        logger.info(f"Started module: {module.__class__.__name__}")


    # Force an initial update
    update_event.set()

    while True:
        # Without a timeout, Ctrl+C won't work.
        # Polling isn't great, but it will work.
        event_triggered = update_event.wait(timeout=0.2)
        if not event_triggered:
            continue
        
        # Clear immediately, so that the next event can be set.
        update_event.clear()

        logger.info("Update event triggered")

        try:
            module_reduction_values = [
                module.get_reduction_value()
                for module in modules
            ]

            # These are in the config's units
            new_upload_speed = max(
                cfg.min_upload,
                (cfg.max_upload - sum(module[0] for module in module_reduction_values))
            )

            new_download_speed = max(
                cfg.min_download,
                (cfg.max_download - sum(module[1] for module in module_reduction_values))
            )

            logger.info(f"New calculated upload speed: {new_upload_speed}{cfg.units}")
            logger.info(f"New calculated download speed: {new_download_speed}{cfg.units}")

            logger.info("Getting active torrent counts")

            client_active_torrent_dict = {
                client: client.get_active_torrent_count()
                for client in clients
            }

            sum_active_torrents = sum(client_active_torrent_dict.values())

            for torrent_client, active_torrent_count in client_active_torrent_dict.items():
                # If there are no active torrents, set the upload speed to the new speed
                effective_upload_speed = (active_torrent_count / sum_active_torrents * new_upload_speed) if active_torrent_count > 0 else new_upload_speed
                effective_download_speed = (active_torrent_count / sum_active_torrents * new_download_speed) if active_torrent_count > 0 else new_download_speed
                
                try:
                    torrent_client.set_upload_speed(effective_upload_speed)
                    torrent_client.set_download_speed(effective_download_speed)
                
                except Exception:
                    logger.warning(f"An error occurred while updating {torrent_client._client_config.url}, skipping:\n" + traceback.format_exc())
                
                else:
                    logger.info(f"Set upload speed for {torrent_client._client_config.url} to {effective_upload_speed}{cfg.units}")
                    logger.info(f"Set download speed for {torrent_client._client_config.url} to {effective_download_speed}{cfg.units}")
            

            logger.info("Speeds updated")


        except Exception:
            logger.error("An error occurred while updating clients:\n" + traceback.format_exc())
        

        logger.info("Waiting for next update event")
