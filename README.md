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

This project uses a `Makefile` to simplify common tasks like building and running the application.

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

### Using YouTube Cookies

To download age-restricted or private videos that require a login, you can provide a cookies file. This allows `yt-dlp` to make requests as if you were logged into YouTube in your browser.

1.  **Install a Browser Extension**: Use an extension that can export cookies in the `Netscape cookie file` format (a plain text file). The user recommended [cookies.txt](https://github.com/hrdl-github/cookies-txt), which is available for [Chrome](https://chrome.google.com/webstore/detail/cookiestxt/njabckikapfpffapmjgojcnbfjonfjfg) and [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/).
2.  **Export Your Cookies**: Go to `youtube.com` in your browser. Click the extension's icon and then the "Export" or "Download" button to save the `cookies.txt` file.
3.  **Place the Cookies File**: Move the downloaded `cookies.txt` file into your application's config directory. Using the example path, this would be `/exos/docker-data/config/appdata/twl_downloader/cookies.txt`.
4.  **Update Your Configuration**: In your `.env` file, set the `YOUTUBE_COOKIES_FILE` variable to point to the location of the file *inside the container*:
    ```
    YOUTUBE_COOKIES_FILE=/config/cookies.txt
    ```

Now, when you run the application, it will automatically use these cookies for YouTube downloads.

### Advanced `docker run` Example

If you prefer to use the `docker run` command directly, you can customize the volume mounts to match your system's paths. Here is an example using the specific paths you provided:

```bash
docker run --rm \
  --env-file .env \
  -v "/exos/video/Other/ToWatchList/":/downloads \
  -v "/exos/docker-data/config/appdata/twl_downloader/":/config \
  --name twl-downloader \
  twl-downloader
```

In this example:
-   Your video download folder `/exos/video/Other/ToWatchList/` is mapped to the `/downloads` directory inside the container.
-   Your application data folder `/exos/docker-data/config/appdata/twl_downloader/` is mapped to the `/config` directory inside the container. This is where `yt-dlp`'s cache and your `cookies.txt` file will be stored.

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

The recommended way to run tests is inside a clean Docker container:

```bash
make test
```

You can also run the tests directly on your local machine:

```bash
make test-local
```

**Note**: The `test-local` command includes an integration test that requires `ffmpeg` to be installed on your system.

### Linting & Formatting

To check the code for style issues and automatically format it, run:

```bash
make lint
make format
```