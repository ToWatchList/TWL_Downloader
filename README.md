# ToWatchList Downloader

ToWatchList Downloader or `twl_downloader` is a Python script to automate downloading videos from [ToWatchList.com](https://towatchlist.com) using yt-dlp.

This project is designed to be run as a Docker container. It syncs your local video library with your ToWatchList account, downloading new videos and removing ones that have been marked as watched or deleted.

## Getting Started

This project uses a `Makefile` to simplify common tasks like building and running the application.

### 1. Create a Configuration File

First, copy the example environment file and fill in your details:

```bash
cp .env.example .env
```

Now, edit the `.env` file to add your `TWL_API_KEY`.

### 2. Build and Run with Docker

You can build and run the application using the following `make` commands:

```bash
# Build the Docker image
make build

# Run the application in a container
make run
```

The `make run` command will mount the `./videos` directory for downloads and the `./config` directory for caching `yt-dlp` updates.

It is recommended to run this container on a schedule using a tool like `cron`.

### Environment Variables

The application is configured via environment variables, which are loaded from the `.env` file by the `Makefile`.

| Variable              | Description                                                                 | Default                  |
| --------------------- | --------------------------------------------------------------------------- | ------------------------ |
| `TWL_API_KEY`         | **Required.** Your ToWatchList.com API key.                                 | (none)                   |
| `TWL_DOWNLOAD_LOCATION`| The directory to save videos to.                                            | `./videos`               |
| `TWL_WRITE_NFO_FILES` | Set to `true` to generate `.nfo` metadata files for Kodi.                   | `false`                  |
| `TWL_DOWNLOAD_TO_TMP` | Set to `true` to download to a temporary location before moving.            | `true`                   |
| `TWL_KODI_HOSTNAME`   | The hostname or IP address of your Kodi instance.                           | (none)                   |
| `TWL_KODI_PORT`       | The port for Kodi's web interface.                                          | `8080`                   |
| `TWL_KODI_USER`       | The username for Kodi's web interface.                                      | (none)                   |
| `TWL_KODI_PASSWORD`   | The password for Kodi's web interface.                                      | (none)                   |


## Development

### Running Locally

To run the script outside of Docker for development purposes:

```bash
make run-local
```

This requires Python 3 and the dependencies from `requirements.txt`.

### Running Tests

The project includes a test suite using `pytest`. To run the tests:

```bash
make test
```

### Linting

To check the code for style issues, run the linter:

```bash
make lint
```

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
