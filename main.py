import threading
from typing import Union, List
import traceback

from helpers.log_loader import logger
from helpers import arguments, config, log_loader
from clients import qbittorrent
from modules import media_server, schedule



if __name__ == '__main__':
    args = arguments.load_args()

    log_loader.file_handler.setLevel(args.log_file_level)
    log_loader.stdout_handler.setLevel(args.log_level)

    logger.debug("Loading config")

    if not args.config:
        logger.error("No config file specified, use --config_path arg or SPEEDRR_CONFIG env var to specify a config file.")
        exit()

    cfg = config.load_config(args.config)
    
    logger.info("Starting Speedrr")

    
    update_event = threading.Event()
    

    clients: List[Union[qbittorrent.qBittorrentClient]] = []
    for client in cfg.clients:
        if client.type == "qbittorrent":
            torrent_client = qbittorrent.qBittorrentClient(cfg, client)
        
        else:
            logger.error(f"Unknown client type in config: {client.type}")
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
        logger.error("No modules enabled in config, exiting")
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
            new_upload_speed = max(
                cfg.min_upload,
                (cfg.max_upload - sum(module.get_reduction_value() for module in modules))
            ) # This is in the config's units

            logger.info(f"New calculated upload speed: {new_upload_speed}{cfg.units}")

            logger.info("Getting active torrent counts")

            client_active_torrent_dict = {
                client: client.get_active_torrent_count()
                for client in clients
            }

            sum_active_torrents = sum(client_active_torrent_dict.values())

            for torrent_client, active_torrent_count in client_active_torrent_dict.items():
                try:
                    if active_torrent_count == 0:
                        # if there are no active torrents, set the upload speed to the new speed
                        torrent_client.set_upload_speed(new_upload_speed)
                    else:
                        torrent_client.set_upload_speed((active_torrent_count / sum_active_torrents * new_upload_speed))
                
                except Exception:
                    logger.warn(f"An error occurred while updating {torrent_client._client_config.url}, skipping:\n" + traceback.format_exc())
                
                else:
                    logger.info(f"Set upload speed for {torrent_client._client_config.url} to {new_upload_speed}{cfg.units}")
            

            logger.info("Upload speeds updated")
        

        except Exception:
            logger.error("An error occurred while updating clients:\n" + traceback.format_exc())
        

        logger.info("Waiting for next update event")
