<p align="center">
    <img src="https://raw.githubusercontent.com/itschasa/speedrr/master/images/speedrr_text.png" alt="speedrr" width="336" height="84">
    <br/>
    <h1>speedrr - Dynamic Upload Speed Manager for Torrenting</h1>
</p>

Change your torrent client's upload speed dynamically, on certain events such as:
- When a Plex/Jellyfin stream starts
- Time of day and day of the week
- <i>More coming soon!</i>

This script is ideal for users with limited upload speed, however anyone can use it to maximise their upload speed, whilst keeping their Plex/Jellyfin streams buffer-free!


## Features
- Multi-server support for Plex, Jellyfin, and Tautulli.
- Supports qBittorrent (more clients soon, maybe).
- Multi-torrent-client support.
    - Bandwidth is split between them, by number of downloading/uploading torrents.
- Schedule a time/day when upload speed should be lowered.


## Setup

### Docker
Pull the image with:
```cmd
docker pull itschasa/speedrr
```

Your config file should be stored outside of the container, for easy editing.

You can then add a volume to the container (like /data/), which points to a folder where your config is stored.

Example `docker run` command:
```
docker run -d
    -e SPEEDRR_CONFIG=/data/config.yaml
    -v /folder_with_config/:/data/
    --name speedrr
    --network host
    itschasa/speedrr
```

### Unraid
1. Open your console and run the following command:
```
cd /boot/config/plugins/dockerMan/templates-user && touch my-speedrr.xml && nano my-speedrr.xml
```
2. Go to <a href="https://raw.githubusercontent.com/itschasa/speedrr/main/speedrr-unraid.xml">speedrr-unraid.xml</a>, and copy and paste it into your console.
3. Press Ctrl+O, then Enter, then Ctrl+X (to save the file and exit).
4. Open your WebUI > `Docker` > `Add Container`.
5. Click `Select a template`, and select `speedrr`.
6. The options should be fine as they are defaulted. Apply changes.
7. Using the <a href="https://github.com/itschasa/speedrr/blob/main/config.yaml">template</a>, create config.yaml in your /appdata/speedrr/ folder, and fill out the config.
8. Start/Restart the container in the WebUI.
9. Check everything is working in the logs (Docker Logs).

### Source
1. Download the source code.
2. Install Python 3.10 (other versions should work).
3. Install the required modules with `python -m pip install -r requirements.txt`.
4. Edit the config to your liking.
5. Run `python main.py --config_path config.yaml` to start.


## Contributing
Anyone is welcome to contribute! Feel free to open pull requests.

## Issues and Bugs
Please report any bugs in the <a href="https://github.com/itschasa/speedrr/issues">Issues</a> section.

## Feature Suggestions
Got an idea for the project? Sugges it <a href="https://github.com/itschasa/speedrr/issues">here</a>!