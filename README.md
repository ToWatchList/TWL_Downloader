# ToWatchList Downloader

ToWatchList Downloader or `twl-downloader` is a Python script to automate downloading videos from [ToWatchList.com](https://towatchlist.com) using yt-dlp.

This project is designed to be run as a Docker container. It syncs your local video library with your ToWatchList account, downloading new videos and removing ones that have been marked as watched or deleted.

## Key Features

-   **Best Quality Downloads**: Automatically downloads the best available video and audio streams and packages them in a high-quality MKV container.
-   **Embedded Chapters**: Automatically embeds chapters into the video file from both YouTube's native chapters and from SponsorBlock data.
-   **Rich Metadata**: Creates detailed, Jellyfin-compliant `.nfo` files for media centers like Kodi, including the video description, upload date, and your personal ToWatchList comments.
-   **Correct Timestamps**: Sets the final video file's modification date to the video's original upload date, making it easy to sort your library chronologically.
-   **Cookie Support**: Can use your YouTube cookies to download age-restricted, private, or members-only videos.

## Getting Started

### 1. Create a Configuration File

First, copy the example environment file and fill in your details:

```bash
cp .env.example .env
```

Now, edit the `.env` file to add your `TWL_API_KEY`. You can also customize other settings, such as the SponsorBlock categories.

### 2. Build and Run with Docker

The easiest way to run the application is with the `make` commands:

```bash
# Build the Docker image
make build

# Run the application in a container
make run
```

The `make run` command uses the configuration from your `.env` file and mounts local directories for downloads (`./videos`) and configuration (`./config`).

### Path Management

The application uses two important directories inside the container:
-   `/downloads`: Where your final video files are stored.
-   `/tmp`: A temporary directory for in-progress downloads.

You should map local directories on your host machine to these container paths using Docker volumes. The `make run` command handles this for you by default, mapping `./videos` and `./config` from your project folder.

### Advanced `docker run` Example

If you prefer to use the `docker run` command directly instead of `make run`, you can customize the volume mounts to match your system's paths. Here is an example using the specific paths you provided:

```bash
docker run --rm \
  --env-file .env \
  -v "/exos/video/Other/ToWatchList/":/downloads \
  -v "/exos/docker-data/config/appdata/twl_downloader/":/config \
  --name twl-downloader \
  twl-downloader
```

### Environment Variables

| Variable                    | Description                                                                    | Default                                                  |
| --------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------- |
| `TWL_API_KEY`               | **Required.** Your ToWatchList.com API key.                                    | (none)                                                   |
| `TWL_LOOKBACK_DAYS`         | Number of days to look back for new videos.                                    | `28`                                                     |
| `YOUTUBE_COOKIES_FILE`      | Optional. Path inside the container to a YouTube cookies file.                 | (none)                                                   |
| `TWL_WRITE_NFO_FILES`       | Set to `true` to generate `.nfo` metadata files for Kodi.                      | `true`                                                   |
| `SPONSORBLOCK_CATEGORIES`   | Comma-separated list of SponsorBlock categories to mark as chapters.           | `sponsor,intro,outro,selfpromo,preview,music_offtopic`   |
| `TWL_KODI_HOSTNAME`         | The hostname or IP address of your Kodi instance.                              | (none)                                                   |
| `TWL_KODI_PORT`             | The port for Kodi's web interface.                                             | `8080`                                                   |
| `TWL_KODI_USER`             | The username for Kodi's web interface.                                         | (none)                                                   |
| `TWL_KODI_PASSWORD`         | The password for Kodi's web interface.                                         | (none)                                                   |

## Development

### Running Tests

The recommended way to run tests is inside a clean Docker container:

```bash
# Run unit tests (fast)
make test

# Run integration tests (slower, requires network)
make test-integration

# Run all tests
make test-all
```

You can also run the tests directly on your local machine if you have the dependencies (including `ffmpeg`) installed:

```bash
make test-local
```

### Linting & Formatting

To check the code for style issues and automatically format it, run:

```bash
make lint
make format
```