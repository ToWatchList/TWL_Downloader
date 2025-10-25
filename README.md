# ToWatchList Downloader

ToWatchList Downloader or `twl-downloader` is a Python script to automate downloading videos from [ToWatchList.com](https://towatchlist.com) using yt-dlp.

This project is designed to be run as a Docker container. It syncs your local video library with your ToWatchList account, downloading new videos and removing ones that have been marked as watched or deleted.

## Key Features

-   **Best Quality Downloads**: Automatically downloads the best available video and audio streams and packages them in a high-quality MKV container.
-   **DRM/SABR Protection Handling**: Automatically detects when YouTube applies DRM protection or SABR streaming restrictions (which can limit quality) and retries the download without cookies to obtain the best available quality. If the best quality still cannot be obtained, the download is skipped rather than downloading a degraded version.
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

### Handling DRM and SABR Protection

YouTube sometimes applies DRM (Digital Rights Management) protection or forces SABR (Streaming Audio/Video Bitrate Reduction) streaming on certain videos, especially when using cookies or certain client types. This can prevent access to the highest quality formats (like 4K).

The downloader automatically handles this situation:

1.  **Detection**: When DRM/SABR warnings are detected during the initial metadata fetch, the script recognizes that the best quality may not be available.
2.  **Automatic Retry**: The script automatically retries the download *without* cookies, which often bypasses these restrictions and allows access to higher quality formats.
3.  **Quality Guarantee**: If the best quality still cannot be obtained after the retry, the download is **skipped entirely** rather than downloading a degraded version. This ensures your library only contains the highest quality videos available.

You'll see log messages like this when DRM/SABR protection is detected and handled:

```
WARNING: [youtube] Some tv client https formats have been skipped as they are DRM protected
INFO: Retrying download without cookies to bypass DRM/SABR restrictions...
INFO: Successfully downloaded without cookies
```

If the video cannot be downloaded in acceptable quality even without cookies, you'll see:

```
ERROR: Skipping video due to DRM/SABR protection: Cannot guarantee best quality download
```

This feature ensures you never unknowingly download a low-quality version when a high-quality version should be available.

#### Disabling DRM Protection (Advanced)

In some cases, you may want to bypass the DRM protection checks and attempt to download videos even when protection is detected. This can be useful for testing or when you're willing to accept potentially lower quality downloads. To allow SABR/DRM downloads:

```bash
SKIP_SABR_DRM_DOWNLOADS=false
```

**Note**: The Docker image allows SABR/DRM downloads by default (`SKIP_SABR_DRM_DOWNLOADS=false`) to allow downloads to proceed. You can re-enable protection by setting `SKIP_SABR_DRM_DOWNLOADS=true` in your environment or rebuilding the image with the default changed.

### SponsorBlock Audio Sync Fix

By default, the downloader preserves audio synchronization by marking sponsor segments as chapters instead of physically removing them. This prevents audio sync issues that can occur in media players like Kodi, especially when custom audio delays are configured.

```bash
REMOVE_SPONSOR_SEGMENTS=false  # Default: preserve audio sync
```

**Recommended (Default)**: Keep `REMOVE_SPONSOR_SEGMENTS=false`
-   **Preserves Timeline**: The video timeline remains intact, preventing audio sync issues
-   **Chapter Navigation**: Sponsor segments are marked as chapters for easy skipping
-   **Kodi Compatible**: Works perfectly with Kodi's audio delay settings

**Alternative**: Set `REMOVE_SPONSOR_SEGMENTS=true` for the old behavior
-   **Physically Removes**: Sponsor segments are cut out of the video file
-   **Smaller Files**: Results in slightly smaller file sizes
-   **Sync Issues**: May cause audio desynchronization in some players, especially Kodi

If you experience audio sync problems after sponsor segments in Kodi (where you need to stop and restart playback to fix sync), use the default setting (`false`) to resolve this issue.

### Filtering Tallscreen Videos

By default, the downloader will process all videos regardless of their aspect ratio. However, if you want to skip portrait/vertical videos (where the height is greater than the width), you can enable the tallscreen filter:

```bash
SKIP_TALLSCREEN_VIDEOS=true
```

When enabled, the downloader will:

1.  **Check Dimensions**: Examine the video's width and height from the metadata.
2.  **Skip Tallscreen Videos**: If height > width, the video will be skipped and not downloaded.
3.  **Log the Action**: You'll see a message like: `Skipping tallscreen video: 'Video Title' (height > width)`

This is useful if you primarily watch videos on landscape displays and want to automatically filter out portrait-oriented content like TikTok videos, Instagram Reels, or YouTube Shorts that were filmed vertically.

### Fixing Malformed NFO Files

If you have existing NFO files that are malformed (causing XML parsing errors in Jellyfin, Kodi, or other media centers), you can regenerate them by setting:

```bash
OVERWRITE_NFO_FILES=true
```

When enabled:

1.  **Overwrites Existing Files**: The downloader will regenerate `.nfo` files even if they already exist.
2.  **Proper XML Escaping**: All special characters (`&`, `<`, `>`, `'`, `"`) will be properly escaped to ensure valid XML.
3.  **Jellyfin-Compliant**: The new NFO files will be fully compliant with Jellyfin's NFO specification.

This is particularly useful if you have older NFO files created before XML escaping was properly implemented. Simply run the downloader with this option enabled, and it will recreate all NFO files with proper formatting.

**Tip**: You can combine this with `REPROCESS_EXISTING=true` to only update NFO files without re-downloading any videos.

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
| `OVERWRITE_NFO_FILES`       | Set to `true` to overwrite existing `.nfo` files (useful for fixing malformed files). | `false`                                            |
| `SKIP_TALLSCREEN_VIDEOS`    | Set to `true` to skip downloading videos where height > width (portrait).      | `false`                                                  |
| `SPONSORBLOCK_CATEGORIES`   | Comma-separated list of SponsorBlock categories to mark as chapters.           | `sponsor,intro,outro,selfpromo,preview,music_offtopic`   |
| `SKIP_SABR_DRM_DOWNLOADS`   | Set to `false` to bypass DRM/SABR protection and attempt downloads anyway.     | `false` (Docker), `true` (local)                        |
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
