# ToWatchList Downloader

ToWatchList Downloader or `twl_downloader` is a Python script to automate downloading videos from [ToWatchList.com](https://towatchlist.com) using yt-dlp.

This project is designed to be run as a Docker container. It syncs your local video library with your ToWatchList account, downloading new videos and removing ones that have been marked as watched or deleted.

## Requirements

- A [ToWatchList.com](https://towatchlist.com) account.
- [Docker](https://www.docker.com/) installed on your system.

## Getting Started

The script is configured via environment variables. You will need to provide your ToWatchList API key. The other variables are optional.

### Building the Docker Image

To build the Docker image, run the following command in the project directory:

```bash
docker build -t towatchlist-downloader .
```

### Running the Container

To run the container, you need to provide your API key and mount volumes for your downloads and for the application's configuration cache.

Here is an example `docker run` command:

```bash
docker run --rm \
  -e TWL_API_KEY="your_api_key_here" \
  -v /path/to/your/videos:/downloads \
  -v /path/to/your/appdata/twl-dl:/config \
  --name towatchlist-downloader \
  towatchlist-downloader
```

- `--rm`: Automatically removes the container when it exits.
- `-e TWL_API_KEY`: Sets your ToWatchList API key. **This is required.**
- `-v /path/to/your/videos:/downloads`: Mounts a local directory to store the downloaded videos.
- `-v /path/to/your/appdata/twl-dl:/config`: Mounts a local directory to store configuration and cache for `yt-dlp`. This helps to avoid re-downloading `yt-dlp` on every run. The user from the original request mentioned using `/exos/docker-data/config/appdata/twl-dl` for this path.
- `--name towatchlist-downloader`: Assigns a name to the container.

It is recommended to run this container on a schedule using a tool like `cron`.

### Environment Variables

The following environment variables are available for configuration:

| Variable              | Description                                                                 | Default                  |
| --------------------- | --------------------------------------------------------------------------- | ------------------------ |
| `TWL_API_KEY`         | **Required.** Your ToWatchList.com API key.                                 | (none)                   |
| `TWL_DOWNLOAD_LOCATION`| The directory inside the container to save videos to.                       | `/downloads`             |
| `TWL_WRITE_NFO_FILES` | Set to `true` to generate `.nfo` metadata files for Kodi.                   | `false`                  |
| `TWL_DOWNLOAD_TO_TMP` | Set to `true` to download to a temporary location before moving.            | `true`                   |
| `TWL_KODI_HOSTNAME`   | The hostname or IP address of your Kodi instance.                           | (none)                   |
| `TWL_KODI_PORT`       | The port for Kodi's web interface.                                          | `8080`                   |
| `TWL_KODI_USER`       | The username for Kodi's web interface.                                      | (none)                   |
| `TWL_KODI_PASSWORD`   | The password for Kodi's web interface.                                      | (none)                   |

## How it Works

The container's entrypoint script first updates `yt-dlp` to the latest version, using the `/config` volume to cache the package. Then, it runs the main Python script which:
1. Fetches the latest unwatched videos from your ToWatchList account via the API.
2. Downloads any new videos using `yt-dlp`.
3. Deletes any local video files that have been marked as watched or deleted on ToWatchList.
4. Optionally, creates `.nfo` files for metadata.
5. Optionally, sends a notification to a Kodi instance to scan or clean the library.

## Disclaimers

This script uses the private APIs from ToWatchList, which may change at any time. The original developer of this script is also the developer of ToWatchList and intended to keep it updated.
Please see the [ToWatchList API Page](http://towatchlist.com/api) for more API details.
