# ToWatchList Downloader

ToWatchList Downloader or `twl-downloader` is a Python script to automate downloading videos from [ToWatchList.com](https://towatchlist.com) using yt-dlp.

This project is designed to be run as a Docker container. It syncs your local video library with your ToWatchList account, downloading new videos and removing ones that have been marked as watched or deleted.

## Key Features

- **Best Quality Downloads**: Automatically downloads the best available video and audio streams and packages them in a high-quality MP4 container.
- **EJS (External JavaScript) Support**: Uses yt-dlp's External JavaScript system with Deno to solve YouTube's JavaScript challenges, ensuring reliable access to video streams even when YouTube's protection mechanisms evolve.
- **DRM/SABR Protection Handling**: Automatically detects when YouTube applies DRM protection or SABR streaming restrictions (which can limit quality) and retries the download without cookies to obtain the best available quality. If the best quality still cannot be obtained, the download is skipped rather than downloading a degraded version.
- **Embedded Chapters**: Automatically embeds chapters into the video file from both YouTube's native chapters and from SponsorBlock data.
- **Rich Metadata**: Creates detailed, Jellyfin-compliant `.nfo` files for media centers like Kodi, including the video description, upload date, and your personal ToWatchList comments.
- **Correct Timestamps**: Sets the final video file's modification date to the video's original upload date, making it easy to sort your library chronologically.
- **Cookie Support**: Can use your YouTube cookies to download age-restricted, private, or members-only videos.

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

1. **Install a Browser Extension**: Use an extension that can export cookies in the `Netscape cookie file` format (a plain text file). The user recommended [cookies.txt](https://github.com/hrdl-github/cookies-txt), which is available for [Chrome](https://chrome.google.com/webstore/detail/cookiestxt/njabckikapfpffapmjgojcnbfjonfjfg) and [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/).
2. **Export Your Cookies**: Go to `youtube.com` in your browser. Click the extension's icon and then the "Export" or "Download" button to save the `cookies.txt` file.
3. **Place the Cookies File**: Move the downloaded `cookies.txt` file into your application's config directory. Using the example path, this would be `/exos/docker-data/config/appdata/twl_downloader/cookies.txt`.
4. **Update Your Configuration**: In your `.env` file, set the `YOUTUBE_COOKIES_FILE` variable to point to the location of the file _inside the container_:

   ```sh
   YOUTUBE_COOKIES_FILE=/config/cookies.txt
   ```

Now, when you run the application, it will automatically use these cookies for YouTube downloads.

### External JavaScript (EJS) Support

The downloader uses yt-dlp's **External JavaScript (EJS)** system to solve YouTube's JavaScript challenges. This ensures reliable video downloads even as YouTube's protection mechanisms evolve.

**What is EJS?**

EJS allows yt-dlp to run JavaScript challenge solver scripts using an external JavaScript runtime. The Docker image includes **Deno**, a secure JavaScript runtime that executes these scripts in a sandboxed environment.

**Configuration:**

```bash
JS_RUNTIMES=deno              # JavaScript runtime (default: Deno)
REMOTE_COMPONENTS=ejs:github  # Where to download EJS scripts
```

See the environment variables table below for more details. For comprehensive EJS troubleshooting, visit the [yt-dlp EJS Wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

### Handling YouTube Protection Mechanisms

YouTube frequently changes its protection mechanisms (DRM, SABR, nsig extraction), which can cause temporary download issues. The downloader implements multiple automatic strategies to handle these:

**Automatic Handling:**

1. **SABR/DRM Detection**: Automatically detects when YouTube forces SABR or DRM streaming
2. **Retry Without Cookies**: Retries downloads without cookies, which often bypasses these restrictions
3. **TV Client Fallback**: If n-parameter extraction fails, automatically retries with the `tv` client
4. **Quality Guarantee**: If best quality can't be obtained, the download is skipped (not degraded)

**Typical Recovery Messages:**

```txt
WARNING: DRM/SABR detected with cookies, retrying without cookies...
INFO: Successfully bypassed DRM/SABR by removing cookies
```

**If Issues Persist:**

- **Update yt-dlp**: The most important step - YouTube protection changes are fixed in new yt-dlp releases
- **Use PO Tokens** (advanced): When SABR blocks all clients, a PO Token can unlock the `mweb` client

**Advanced: PO Token Configuration**

For videos where YouTube forces SABR on all clients, you can use a **PO Token** (Proof of Origin token) to access the `mweb` client:

```bash
YOUTUBE_PO_TOKEN=your_token_here  # Get from browser or plugin
USE_MWEB_CLIENT=true
```

See the [PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) for details on obtaining tokens.

**Advanced: Allow Low-Quality Downloads**

By default, videos with DRM/SABR protection are skipped. To attempt downloads anyway:

```bash
SKIP_SABR_DRM_DOWNLOADS=false
```

**For Detailed Troubleshooting:** See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

### SponsorBlock Audio Sync Fix

By default, the downloader preserves audio synchronization by marking sponsor segments as chapters instead of physically removing them. This prevents audio sync issues that can occur in media players like Kodi, especially when custom audio delays are configured.

```bash
REMOVE_SPONSOR_SEGMENTS=false  # Default: preserve audio sync
```

**Recommended (Default)**: Keep `REMOVE_SPONSOR_SEGMENTS=false`

- **Preserves Timeline**: The video timeline remains intact, preventing audio sync issues
- **Chapter Navigation**: Sponsor segments are marked as chapters for easy skipping
- **Kodi Compatible**: Works perfectly with Kodi's audio delay settings

**Alternative**: Set `REMOVE_SPONSOR_SEGMENTS=true` for the old behavior

- **Physically Removes**: Sponsor segments are cut out of the video file
- **Smaller Files**: Results in slightly smaller file sizes
- **Sync Issues**: May cause audio desynchronization in some players, especially Kodi

If you experience audio sync problems after sponsor segments in Kodi (where you need to stop and restart playback to fix sync), use the default setting (`false`) to resolve this issue.

### Filtering Tallscreen Videos

By default, the downloader will process all videos regardless of their aspect ratio. However, if you want to skip portrait/vertical videos (where the height is greater than the width), you can enable the tallscreen filter:

```bash
SKIP_TALLSCREEN_VIDEOS=true
```

When enabled, the downloader will:

1. **Check Dimensions**: Examine the video's width and height from the metadata.
2. **Skip Tallscreen Videos**: If height > width, the video will be skipped and not downloaded.
3. **Log the Action**: You'll see a message like: `Skipping tallscreen video: 'Video Title' (height > width)`

This is useful if you primarily watch videos on landscape displays and want to automatically filter out portrait-oriented content like TikTok videos, Instagram Reels, or YouTube Shorts that were filmed vertically.

### Fixing Malformed NFO Files

If you have existing NFO files that are malformed (causing XML parsing errors in Jellyfin, Kodi, or other media centers), you can regenerate them by setting:

```bash
OVERWRITE_NFO_FILES=true
```

When enabled:

1. **Overwrites Existing Files**: The downloader will regenerate `.nfo` files even if they already exist.
2. **Proper XML Escaping**: All special characters (`&`, `<`, `>`, `'`, `"`) will be properly escaped to ensure valid XML.
3. **Jellyfin-Compliant**: The new NFO files will be fully compliant with Jellyfin's NFO specification.

This is particularly useful if you have older NFO files created before XML escaping was properly implemented. Simply run the downloader with this option enabled, and it will recreate all NFO files with proper formatting.

**Tip**: You can combine this with `REPROCESS_EXISTING=true` to only update NFO files without re-downloading any videos.

### Path Management

The application uses two important directories inside the container:

- `/downloads`: Where your final video files are stored.
- `/tmp`: A temporary directory for in-progress downloads.

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

| Variable                  | Description                                                                           | Default                                                |
| ------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `TWL_API_KEY`             | **Required.** Your ToWatchList.com API key.                                           | (none)                                                 |
| `TWL_LOOKBACK_DAYS`       | Number of days to look back for new videos.                                           | `28`                                                   |
| `YOUTUBE_COOKIES_FILE`    | Optional. Path inside the container to a YouTube cookies file.                        | (none)                                                 |
| `YOUTUBE_PO_TOKEN`        | Optional. PO Token for mweb client to bypass SABR/GVS restrictions. Requires cookies. | (none)                                                 |
| `USE_MWEB_CLIENT`         | Set to `true` to force the mweb client (requires `YOUTUBE_PO_TOKEN`).                 | `false`                                                |
| `TWL_WRITE_NFO_FILES`     | Set to `true` to generate `.nfo` metadata files for Kodi.                             | `true`                                                 |
| `OVERWRITE_NFO_FILES`     | Set to `true` to overwrite existing `.nfo` files (useful for fixing malformed files). | `false`                                                |
| `SKIP_TALLSCREEN_VIDEOS`  | Set to `true` to skip downloading videos where height > width (portrait).             | `false`                                                |
| `SPONSORBLOCK_CATEGORIES` | Comma-separated list of SponsorBlock categories to mark as chapters.                  | `sponsor,intro,outro,selfpromo,preview,music_offtopic` |
| `SKIP_SABR_DRM_DOWNLOADS` | Set to `false` to bypass DRM/SABR protection and attempt downloads anyway.            | `false` (Docker), `true` (local)                       |
| `JS_RUNTIMES`             | JavaScript runtime for EJS (deno, bun, node, quickjs).                                | `deno`                                                 |
| `REMOTE_COMPONENTS`       | How to download EJS scripts (ejs:github, ejs:npm).                                    | `ejs:github`                                           |
| `TWL_KODI_HOSTNAME`       | The hostname or IP address of your Kodi instance.                                     | (none)                                                 |
| `TWL_KODI_PORT`           | The port for Kodi's web interface.                                                    | `8080`                                                 |
| `TWL_KODI_USER`           | The username for Kodi's web interface.                                                | (none)                                                 |
| `TWL_KODI_PASSWORD`       | The password for Kodi's web interface.                                                | (none)                                                 |

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

## Documentation

- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Comprehensive troubleshooting guide for common issues
- **[yt-dlp EJS Wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS)** - External JavaScript support details
- **[yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)** - Proof of Origin token documentation
- **[SABR Issue #12482](https://github.com/yt-dlp/yt-dlp/issues/12482)** - YouTube SABR/nsig protection discussion

## Logging & Debugging

The downloader provides clean, minimal logging by default. To see detailed debug information:

```bash
LOG_LEVEL=DEBUG make run
```

Debug mode will show:

- EJS script loading and execution
- HTTP client selection details
- PO token generation attempts
- Full yt-dlp warning messages
- Metadata extraction details
