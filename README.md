# ToWatchList Downloader

ToWatchList Downloader or `twl_downloader` is a Python script to automate downloading videos from [ToWatchList.com](https://towatchlist.com) using yt-dlp.

This project is designed to be run as a Docker container. It syncs your local video library with your ToWatchList account, downloading new videos and removing ones that have been marked as watched or deleted.

## Key Features

-   **Best Quality Downloads**: Automatically downloads the best available video and audio streams and packages them in a high-quality MKV container.
-   **Embedded Chapters**: Automatically embeds chapters into the video file from both YouTube's native chapters and from SponsorBlock data.
-   **Rich Metadata**: Creates detailed `.nfo` files for media centers like Kodi, including the video description, upload date, and your personal ToWatchList comments.
-   **Correct Timestamps**: Sets the final video file's modification date to the video's original upload date, making it easy to sort your library chronologically.
-   **Cookie Support**: Can use your YouTube cookies to download age-restricted, private, or members-only videos.

## Getting Started

This project uses a `Makefile` to simplify common tasks like building and running the application.

### 1. Create a Configuration File

First, copy the example environment file and fill in your details:

```bash
cp .env.example .env
```

Now, edit the `.env` file to add your `TWL_API_KEY`. You can also customize other settings, such as the SponsorBlock categories.

### 2. Build and Run with Docker

You can build and run the application using the following `make` commands:

```bash
# Build the Docker image
make build

# Run the application in a container
make run
```

The `make run` command will mount the `./videos` directory for downloads and the `./config` directory for caching `yt-dlp` updates.

### Using YouTube Cookies

To download age-restricted or private videos that require a login, you can provide a cookies file.

1.  Export your YouTube cookies using a browser extension like [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc).
2.  Save the cookies file as `cookies.txt` in your config directory (the same one you mount to `/config` in the container).
3.  In your `.env` file, set the `YOUTUBE_COOKIES_FILE` variable to the path *inside the container*:
    ```
    YOUTUBE_COOKIES_FILE=/config/cookies.txt
    ```
The `make run` command will automatically mount this file into the container.

### Environment Variables

| Variable                    | Description                                                                    | Default                                                  |
| --------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------- |
| `TWL_API_KEY`               | **Required.** Your ToWatchList.com API key.                                    | (none)                                                   |
| `TWL_DOWNLOAD_LOCATION`     | The directory to save videos to.                                               | `./videos`                                               |
| `YOUTUBE_COOKIES_FILE`      | Optional. Path inside the container to a YouTube cookies file.                 | (none)                                                   |
| `TWL_WRITE_NFO_FILES`       | Set to `true` to generate `.nfo` metadata files for Kodi.                      | `true`                                                   |
| `SPONSORBLOCK_CATEGORIES`   | Comma-separated list of SponsorBlock categories to mark as chapters.           | `sponsor,intro,outro,selfpromo,preview,music_offtopic`   |
| `TWL_DOWNLOAD_TO_TMP`       | Set to `true` to download to a temporary location before moving.               | `true`                                                   |
| `TWL_KODI_HOSTNAME`         | The hostname or IP address of your Kodi instance.                              | (none)                                                   |
| `TWL_KODI_PORT`             | The port for Kodi's web interface.                                             | `8080`                                                   |
| `TWL_KODI_USER`             | The username for Kodi's web interface.                                         | (none)                                                   |
| `TWL_KODI_PASSWORD`         | The password for Kodi's web interface.                                         | (none)                                                   |

## Development

### Running Locally

To run the script outside of Docker for development purposes:

```bash
make run-local
```

### Running Tests

The project includes a test suite using `pytest`. To run the tests:

```bash
make test
```

### Linting & Formatting

To check the code for style issues and automatically format it, run:

```bash
make lint
make format
```