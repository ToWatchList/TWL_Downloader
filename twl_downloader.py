import glob
import os
import shutil
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import requests
import yt_dlp
from kodijson import Kodi
import logging

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Verify logging is configured correctly
logging.debug(f"Logging configured with level: {LOG_LEVEL}")


# Custom exceptions
class DownloadError(Exception):
    """Custom exception for download errors"""
    pass


class DRMProtectionError(DownloadError):
    """Raised when DRM protection prevents downloading best quality"""
    pass


class MLStripper(HTMLParser):
    """A simple HTML parser to strip tags from a string."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return "".join(self.fed)


def strip_tags(html):
    """Strips HTML tags from a string."""
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def load_tallscreen_cache(download_location):
    """Loads the set of tallscreen video IDs from the cache file."""
    cache_file = os.path.join(download_location, ".yttallscreen")
    if not os.path.exists(cache_file):
        return set()

    try:
        with open(cache_file, "r") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        logging.warning(f"Could not read tallscreen cache: {e}")
        return set()


def save_tallscreen_cache(download_location, video_ids):
    """Saves the set of tallscreen video IDs to the cache file."""
    cache_file = os.path.join(download_location, ".yttallscreen")
    try:
        with open(cache_file, "w") as f:
            for video_id in sorted(video_ids):
                f.write(f"{video_id}\n")
        logging.debug(f"Saved {len(video_ids)} tallscreen video IDs to cache")
    except Exception as e:
        logging.error(f"Could not write tallscreen cache: {e}")


def add_to_tallscreen_cache(download_location, video_id):
    """Adds a video ID to the tallscreen cache."""
    cache = load_tallscreen_cache(download_location)
    if video_id not in cache:
        cache.add(video_id)
        save_tallscreen_cache(download_location, cache)
        logging.debug(f"Added {video_id} to tallscreen cache")


def get_config():
    """Reads configuration from environment variables."""
    sponsorblock_default = "sponsor,intro,outro,selfpromo,preview,music_offtopic"
    config = {
        "api_key": os.getenv("TWL_API_KEY"),
        "lookback_days": int(os.getenv("TWL_LOOKBACK_DAYS", "28")),
        "write_nfo_files": os.getenv("TWL_WRITE_NFO_FILES", "true").lower() in ("true", "1", "t"),
        "kodi_hostname": os.getenv("TWL_KODI_HOSTNAME"),
        "kodi_port": int(os.getenv("TWL_KODI_PORT", "8080")),
        "kodi_user": os.getenv("TWL_KODI_USER"),
        "kodi_password": os.getenv("TWL_KODI_PASSWORD"),
        "youtube_cookies_file": os.getenv("YOUTUBE_COOKIES_FILE"),
        "sponsorblock_categories": os.getenv(
            "SPONSORBLOCK_CATEGORIES", sponsorblock_default
        ).split(","),
        "download_location": os.getenv("TWL_DOWNLOAD_LOCATION", "/downloads"),
        "tmp_download_location": os.getenv("TWL_TMP_DOWNLOAD_LOCATION", "/tmp"),
        # New: whether to just reprocess existing files (update/create NFOs) instead of re-downloading
        "reprocess_existing": os.getenv("REPROCESS_EXISTING", "false").lower() in ("true", "1", "t"),
        # New: whether to skip tallscreen videos (height > width)
        "skip_tallscreen_videos": os.getenv("SKIP_TALLSCREEN_VIDEOS", "false").lower() in ("true", "1", "t"),
        # New: whether to overwrite existing NFO files (useful for fixing malformed NFO files)
        "overwrite_nfo_files": os.getenv("OVERWRITE_NFO_FILES", "false").lower() in ("true", "1", "t"),
        # New: whether to skip downloads when SABR/DRM protection is detected
        "skip_sabr_drm_downloads": os.getenv("SKIP_SABR_DRM_DOWNLOADS", "true").lower() in ("true", "1", "t"),
    }
    if not config["api_key"]:
        logging.error("TWL_API_KEY environment variable not set.")
        sys.exit(1)
    return config


def get_all_files_for_video_id(video_id, download_dir):
    """Finds all files (video, thumbnail, subs, etc.) for a given video_id."""
    pattern = os.path.join(download_dir, f"*-{video_id}.*")
    return glob.glob(pattern)


def find_video_file_for_id(video_id, download_dir):
    """Finds the main video file for a given video_id."""
    video_extensions = ["mkv", "mp4", "webm", "mov", "flv", "avi"]
    for ext in video_extensions:
        files = glob.glob(os.path.join(download_dir, f"*-{video_id}.{ext}"))
        if files:
            return files[0]
    all_files = get_all_files_for_video_id(video_id, download_dir)
    return all_files[0] if all_files else None


def get_videos_from_api(api_key, lookback_days):
    """Fetches the list of videos from the ToWatchList API."""
    api_url = (
        f"https://towatchlist.com/api/v1/marks?since=-{lookback_days}days&uid={api_key}"
    )
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json().get("marks", [])
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch data from ToWatchList API: {e}")
        return []
    except ValueError:
        logging.error("Failed to parse JSON response from ToWatchList API.")
        return []


def get_video_metadata(url, config):
    """Fetches video metadata using yt-dlp without downloading."""
    warning_messages = []

    class WarningLogger:
        def debug(self, msg):
            logging.debug(msg)
        def warning(self, msg):
            warning_messages.append(msg)
            logging.warning(msg)
        def error(self, msg):
            warning_messages.append(msg)
            logging.error(msg)
        def info(self, msg):
            logging.info(msg)

    ydl_opts = {
        "quiet": False,
        "skip_download": True,
        "logger": WarningLogger(),
    }

    # Try with cookies first
    use_cookies = config["youtube_cookies_file"] and os.path.isfile(config["youtube_cookies_file"])
    if use_cookies:
        ydl_opts["cookiefile"] = config["youtube_cookies_file"]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Check for DRM/SABR warnings
        drm_sabr_detected = any(
            'DRM protected' in msg or 'SABR streaming' in msg or 'missing a url' in msg
            for msg in warning_messages
        )

        if drm_sabr_detected:
            if use_cookies:
                # Retry without cookies
                logging.warning(f"DRM/SABR detected with cookies, retrying without cookies for {url}")
                warning_messages.clear()
                ydl_opts_no_cookies = {
                    "quiet": False,
                    "skip_download": True,
                    "logger": WarningLogger(),
                }
                with yt_dlp.YoutubeDL(ydl_opts_no_cookies) as ydl:
                    info = ydl.extract_info(url, download=False)

                # Check again for DRM/SABR
                drm_sabr_still_detected = any(
                    'DRM protected' in msg or 'SABR streaming' in msg or 'missing a url' in msg
                    for msg in warning_messages
                )

                if drm_sabr_still_detected:
                    # Instead of raising an exception, log warning and return metadata with flag
                    logging.warning(f"DRM/SABR protection detected for {url} even without cookies. Cannot guarantee best quality download.")
                    for msg in warning_messages:
                        if 'DRM protected' in msg or 'SABR streaming' in msg or 'missing a url' in msg:
                            logging.warning(f"  - {msg}")
                    # Mark that DRM/SABR was detected but still return the metadata
                    info['_drm_sabr_detected'] = True
                    return info
                else:
                    logging.info(f"Successfully bypassed DRM/SABR by removing cookies for {url}")
                    # Mark that we should download without cookies
                    info['_no_cookies'] = True
                    return info
            else:
                # Instead of raising an exception, log warning and return metadata with flag
                logging.warning(f"DRM/SABR protection detected for {url}. Cannot guarantee best quality download.")
                for msg in warning_messages:
                    if 'DRM protected' in msg or 'SABR streaming' in msg or 'missing a url' in msg:
                        logging.warning(f"  - {msg}")
                # Mark that DRM/SABR was detected but still return the metadata
                info['_drm_sabr_detected'] = True
                return info

        return info
    except DRMProtectionError:
        raise  # Re-raise DRM errors (though we shouldn't hit this anymore)
    except Exception as e:
        logging.warning(f"Could not fetch metadata for {url}. Reason: {e}")
        return None


def is_tallscreen_video(info_dict):
    """Checks if a video is tallscreen (height > width)."""
    if not info_dict:
        return False

    height = info_dict.get("height")
    width = info_dict.get("width")

    if height and width:
        is_tallscreen = height > width
        if is_tallscreen:
            logging.debug(f"Video dimensions: {width}x{height} (tallscreen)")
        else:
            logging.debug(f"Video dimensions: {width}x{height}")
        return is_tallscreen

    logging.debug("Video dimensions not available in metadata")
    return False


def download_video(url, info_dict, config):
    """Downloads a single video using yt-dlp with DRM/SABR protection detection."""
    title = info_dict.get("title", "Unknown Title")
    video_id = info_dict.get("id", "UnknownID")

    # Check if DRM/SABR was detected during metadata fetch and if we should skip such downloads
    if info_dict.get('_drm_sabr_detected') and config.get("skip_sabr_drm_downloads", True):
        logging.error(f"Skipping download of '{title}' due to DRM/SABR protection. Metadata was captured but download cannot proceed.")
        raise DRMProtectionError(f"DRM/SABR protection prevents downloading: {title}")
    elif info_dict.get('_drm_sabr_detected'):
        logging.warning(f"DRM/SABR protection detected for '{title}' but skipping is disabled. Attempting download anyway.")

    logging.info(f"Downloading: '{title}' ({url})")

    # Check if we should skip cookies (set by get_video_metadata when DRM/SABR was bypassed)
    skip_cookies = info_dict.get('_no_cookies', False)

    # Use tmp_download_location if specified, otherwise use download_location directly
    if config.get("tmp_download_location"):
        output_path = config["tmp_download_location"]
    else:
        output_path = config.get("download_location", "/tmp")

    safe_title = "".join(
        c for c in title if c.isalnum() or c in (" ", "-", "_")
    ).rstrip()
    output_template = os.path.join(output_path, f"{safe_title}-{video_id}.%(ext)s")

    postprocessors = [
        {"key": "FFmpegMetadata", "add_metadata": True},
        {
            "key": "SponsorBlock",
            "when": "pre_process",
            "categories": config["sponsorblock_categories"],
        },
        {
            "key": "ModifyChapters",
            "remove_sponsor_segments": ["sponsor"],  # Only remove sponsor segments
        },
    ]

    # Accept webm format if needed to bypass DRM/SABR
    ydl_format = "bestvideo+bestaudio/best"

    ydl_opts = {
        "format": ydl_format,
        "merge_output_format": "mkv",
        "outtmpl": output_template,
        "writethumbnail": True,
        "writesubtitles": True,
        "embedsubtitles": True,
        "addmetadata": True,
        "quiet": True,
        "postprocessors": postprocessors,
    }

    # Only use cookies if we didn't detect DRM/SABR issues
    if not skip_cookies and config["youtube_cookies_file"] and os.path.isfile(config["youtube_cookies_file"]):
        ydl_opts["cookiefile"] = config["youtube_cookies_file"]
        logging.debug(f"Using cookies for download: {config['youtube_cookies_file']}")
    elif skip_cookies:
        logging.info(f"Downloading without cookies to bypass DRM/SABR protection")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logging.error(f"Failed to download '{title}'. Reason: {e}")
        raise DownloadError(f"Failed to download: {e}")


def set_file_modification_time(video_path, info_dict):
    """Sets the file's modification time to the video's upload date."""
    if not video_path or not os.path.exists(video_path):
        return
    upload_date_str = info_dict.get("upload_date")
    if upload_date_str:
        try:
            upload_datetime = datetime.strptime(upload_date_str, "%Y%m%d")
            mod_time = upload_datetime.timestamp()
            os.utime(video_path, (mod_time, mod_time))
            logging.debug(
                f"Set modification date for '{os.path.basename(video_path)}' to {upload_datetime.date()}"
            )
        except (ValueError, TypeError):
            logging.warning(f"Could not parse upload date '{upload_date_str}'")


def create_nfo_file(video_file_path, twl_video_info, yt_video_info, config=None):
    """Creates a Jellyfin-compliant NFO file with rich metadata."""
    if not yt_video_info or not os.path.exists(video_file_path):
        return

    nfo_file_path = os.path.splitext(video_file_path)[0] + ".nfo"
    overwrite = config.get("overwrite_nfo_files", False) if config else False

    if os.path.exists(nfo_file_path) and not overwrite:
        return

    if os.path.exists(nfo_file_path) and overwrite:
        logging.info(f"Overwriting existing NFO file for: {yt_video_info.get('title')}")
    else:
        logging.debug(f"Creating NFO file for: {yt_video_info.get('title')}")

    # --- Prepare metadata fields ---
    video_id = yt_video_info.get('id', '')
    upload_date = yt_video_info.get("upload_date")
    release_date_str = ""
    year_str = ""
    if upload_date:
        try:
            dt_upload = datetime.strptime(upload_date, "%Y%m%d")
            release_date_str = dt_upload.strftime("%Y-%m-%d")
            year_str = dt_upload.strftime("%Y")
        except (ValueError, TypeError):
            pass

    download_timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Get current date in Pacific timezone for the ToWatchList comment
    pacific_tz = ZoneInfo("America/Los_Angeles")
    downloaded_date = datetime.now(pacific_tz).strftime("%Y-%m-%d")

    # Only include ToWatchList comment, not YouTube description
    twl_comment = strip_tags(twl_video_info['Mark'].get('comment', ''))
    plot = f"{twl_comment}\n\nDownloaded on: {downloaded_date}"

    # --- Build the NFO XML structure using ElementTree for proper escaping ---
    movie = ET.Element("movie")

    # Helper function to add text elements safely
    def add_element(parent, tag, text):
        if text is not None:
            elem = ET.SubElement(parent, tag)
            elem.text = str(text)
            return elem
        return None

    add_element(movie, "title", yt_video_info.get("title", ""))
    add_element(movie, "originaltitle", yt_video_info.get("title", ""))
    add_element(movie, "sorttitle", yt_video_info.get("title", ""))
    add_element(movie, "year", year_str)
    if release_date_str:
        add_element(movie, "premiered", f"{release_date_str}T00:00:00")
    add_element(movie, "filename", os.path.basename(video_file_path))
    add_element(movie, "path", video_file_path)
    add_element(movie, "plot", plot)
    add_element(movie, "rating", twl_video_info.get("Mark", {}).get("rating", "0"))
    add_element(movie, "votes", twl_video_info.get("Mark", {}).get("votes", "0"))
    add_element(movie, "mpaa", "NR")
    add_element(movie, "studio", yt_video_info.get("uploader", ""))
    add_element(movie, "director", yt_video_info.get("uploader", ""))
    add_element(movie, "writer", yt_video_info.get("uploader", ""))

    # Add actor
    if yt_video_info.get("uploader"):
        actor = ET.SubElement(movie, "actor")
        add_element(actor, "name", yt_video_info.get("uploader"))

    # Add tags
    for tag in yt_video_info.get("tags", []):
        if tag:  # Only add non-empty tags
            add_element(movie, "tag", tag)

    add_element(movie, "country", "US")
    add_element(movie, "language", "English")
    add_element(movie, "script", "UTF-8")
    if release_date_str:
        add_element(movie, "releasedate", release_date_str)
    add_element(movie, "added", downloaded_date)
    add_element(movie, "lastmodified", downloaded_date)
    add_element(movie, "playcount", "0")
    add_element(movie, "id", video_id)

    # --- Write the NFO file ---
    try:
        # Create XML tree and write with proper formatting
        tree = ET.ElementTree(movie)
        ET.indent(tree, space="  ")  # Pretty print with 2-space indentation
        tree.write(nfo_file_path, encoding="utf-8", xml_declaration=True)

        # Set permissions to 664 (rw-rw-r--) so Jellyfin can write to it
        try:
            os.chmod(nfo_file_path, 0o664)
        except Exception as perm_error:
            logging.warning(f"Could not set permissions on NFO file: {perm_error}")

        logging.info(f"NFO file created: {nfo_file_path}")
    except Exception as e:
        logging.error(f"Failed to create NFO file. Reason: {e}")


def remove_watched_video(video_id, download_location="/downloads"):
    """Removes local files for a watched or deleted video."""
    files_to_remove = get_all_files_for_video_id(video_id, download_location)
    for f in files_to_remove:
        try:
            os.remove(f)
            logging.info(f"Removed watched/deleted file: {os.path.basename(f)}")
        except OSError as e:
            logging.error(f"Could not remove file {f}. Reason: {e}")


def notify_kodi(config, scan=False, clean=False):
    """Sends notifications to Kodi to scan or clean the library."""
    if not config["kodi_hostname"]:
        return

    logging.info(f"Contacting Kodi at {config['kodi_hostname']}...")
    try:
        kodi = Kodi(
            f"http://{config['kodi_hostname']}:{config['kodi_port']}/jsonrpc",
            config["kodi_user"],
            config["kodi_password"],
        )
        if kodi.JSONRPC.Ping()["result"] != "pong":
            logging.error("Bad response from Kodi.")
            return

        if scan or clean:
            kodi.GUI.ShowNotification(
                {
                    "title": "ToWatchList Downloader",
                    "message": "Updating Kodi library...",
                }
            )
        if scan:
            logging.info("Scanning Kodi video library...")
            kodi.VideoLibrary.Scan()
        if clean:
            logging.info("Cleaning Kodi video library...")
            kodi.VideoLibrary.Clean()
        if not scan and not clean:
            logging.info("No Scan or Clean of Kodi needed.")

    except Exception as e:
        logging.error(f"Could not connect to Kodi. Reason: {e}")


def get_files_matching_video_id(video_id, download_dir):
    """Finds any files in download_dir that contain the video_id in their filename (glob '*video_id*')."""
    pattern = os.path.join(download_dir, f"*{video_id}*")
    return glob.glob(pattern)


def process_video(url, config):
    """Main processing function for each video."""
    video_id = url.split("v=")[-1]
    video_files = get_all_files_for_video_id(video_id, config["download_location"])

    # Check if video is already downloaded
    video_file = find_video_file_for_id(video_id, config["download_location"])
    if video_file:
        logging.info(f"Video already downloaded: {video_file}")
        return

    # Fetch video metadata from API
    video_info = None
    twl_video_info = None
    try:
        video_info = get_video_metadata(url, config)
        twl_video_info = next(
            (item for item in get_videos_from_api(config["api_key"], config["lookback_days"]) if item["video_id"] == video_id),
            None
        )
    except Exception as e:
        logging.error(f"Failed to fetch video info. Reason: {e}")
        return

    # Download the video
    if video_info:
        download_video(url, video_info, config)

    # Post-processing: Set file modification time and create NFO file
    if video_file and video_info:
        set_file_modification_time(video_file, video_info)
        if config["write_nfo_files"]:
            create_nfo_file(video_file, twl_video_info, video_info, config)


def main():
    config = get_config()
    logging.debug(f"Configuration loaded. Download location: {config['download_location']}")
    logging.debug(f"Lookback days: {config['lookback_days']}")

    download_location = config["download_location"]
    tmp_download_location = config["tmp_download_location"]

    os.makedirs(download_location, exist_ok=True)
    os.makedirs(tmp_download_location, exist_ok=True)

    # Load tallscreen cache
    tallscreen_cache = load_tallscreen_cache(download_location)
    if tallscreen_cache:
        logging.debug(f"Loaded {len(tallscreen_cache)} tallscreen video IDs from cache")

    logging.debug("Calling get_videos_from_api...")
    videos = get_videos_from_api(config["api_key"], config["lookback_days"])
    logging.debug(f"get_videos_from_api returned. Found {len(videos)} videos to process.")
    logging.info(f"Syncing ToWatchList with '{download_location}'")
    logging.info(f"Found {len(videos)} videos to process.")
    logging.info("---------------------------------")

    should_scan_kodi = False
    should_clean_kodi = False

    for twl_video_info in videos:
        logging.debug(f"Processing video: {twl_video_info['Mark']['title']}")
        mark = twl_video_info["Mark"]
        video_id = mark["video_id"]
        video_url = mark["source_url"]
        logging.debug(f"Video ID: {video_id}, URL: {video_url}")

        # Check tallscreen cache early if skip_tallscreen_videos is enabled
        if config["skip_tallscreen_videos"] and video_id in tallscreen_cache:
            logging.info(f"Skipping cached tallscreen video: '{mark['title']}' (from cache)")
            logging.info("---------------------------------")
            continue

        # New preprocessing: if configured, look for any files matching '*{video_id}*' and update/create NFOs
        if config.get("reprocess_existing"):
            logging.debug(f"REPROCESS_EXISTING enabled: looking for files matching '*{video_id}*' in {download_location}")
            try:
                yt_video_info = get_video_metadata(video_url, config)
            except DRMProtectionError as e:
                logging.error(f"Skipping video {video_id} due to DRM/SABR protection during metadata fetch: {e}")
                logging.info("---------------------------------")
                continue

            if not yt_video_info:
                logging.debug(f"Could not get metadata for {video_id}; skipping reprocess step.")
            else:
                # Check if it's tallscreen and add to cache if needed
                if config["skip_tallscreen_videos"] and is_tallscreen_video(yt_video_info):
                    if video_id not in tallscreen_cache:
                        add_to_tallscreen_cache(download_location, video_id)
                        tallscreen_cache.add(video_id)
                    logging.info(f"Skipping tallscreen video: '{mark['title']}' (height > width, added to cache)")
                    logging.info("---------------------------------")
                    continue

                matching_files = get_files_matching_video_id(video_id, download_location)
                if matching_files:
                    logging.info(f"Found {len(matching_files)} existing file(s) for {video_id}; updating NFOs if needed.")
                    video_exts = {"mkv", "mp4", "webm", "mov", "flv", "avi"}
                    nfo_updated = False
                    for f in matching_files:
                        ext = os.path.splitext(f)[1].lstrip('.').lower()
                        # Only treat likely video files for NFO creation
                        if ext in video_exts:
                            if config["write_nfo_files"]:
                                create_nfo_file(f, twl_video_info, yt_video_info, config)
                                nfo_updated = True
                    if nfo_updated:
                        should_scan_kodi = True
                    # We've handled existing files; skip download step for this video
                    logging.info(f"Reprocess complete for {video_id}; skipping download.")
                    logging.info("---------------------------------")
                    continue

        if mark.get("watched") or mark.get("delflag"):
            logging.debug(f"Video {video_id} is marked as watched or deleted. Removing...")
            remove_watched_video(video_id, download_location)
            should_clean_kodi = True
            continue

        video_file = find_video_file_for_id(video_id, download_location)
        if video_file:
            logging.debug(f"Video {video_id} already downloaded: {video_file}")
            logging.info(f"Already downloaded: '{mark['title']}'")

            # Check if NFO file exists, create it if missing
            if config["write_nfo_files"]:
                nfo_file_path = os.path.splitext(video_file)[0] + ".nfo"
                if not os.path.exists(nfo_file_path) or config.get("overwrite_nfo_files", False):
                    logging.debug(f"NFO file missing for {video_id}, creating it now")
                    try:
                        yt_video_info = get_video_metadata(video_url, config)
                    except DRMProtectionError as e:
                        logging.warning(f"Cannot create NFO for {video_id} due to DRM/SABR protection: {e}")
                        yt_video_info = None

                    if yt_video_info:
                        create_nfo_file(video_file, twl_video_info, yt_video_info, config)
        else:
            logging.debug(f"Video {video_id} needs to be downloaded")
            try:
                yt_video_info = get_video_metadata(video_url, config)
            except DRMProtectionError as e:
                logging.error(f"Skipping video {video_id} due to DRM/SABR protection: {e}")
                logging.info("---------------------------------")
                continue

            if not yt_video_info:
                logging.debug(f"Could not get metadata for {video_id}, skipping")
                continue

            # Check if video is tallscreen and should be skipped
            if config["skip_tallscreen_videos"] and is_tallscreen_video(yt_video_info):
                if video_id not in tallscreen_cache:
                    add_to_tallscreen_cache(download_location, video_id)
                    tallscreen_cache.add(video_id)
                logging.info(f"Skipping tallscreen video: '{mark['title']}' (height > width, added to cache)")
                logging.info("---------------------------------")
                continue

            try:
                download_video(video_url, yt_video_info, config)
            except DRMProtectionError as e:
                logging.error(f"Skipping video {video_id} due to DRM/SABR protection: {e}")
                logging.info("---------------------------------")
                continue
            except DownloadError as e:
                logging.error(f"Failed to download video {video_id}: {e}")
                logging.info("---------------------------------")
                continue

            # Move downloaded files from tmp to final location
            downloaded_files = get_all_files_for_video_id(video_id, tmp_download_location)
            for f in downloaded_files:
                try:
                    shutil.move(f, download_location)
                except shutil.Error as e:
                    logging.warning(f"Could not move file {f}. It may already exist. Details: {e}")

            final_video_path = find_video_file_for_id(video_id, download_location)
            set_file_modification_time(final_video_path, yt_video_info)

            if config["write_nfo_files"]:
                create_nfo_file(final_video_path, twl_video_info, yt_video_info, config)

            should_scan_kodi = True

        logging.info("---------------------------------")

    notify_kodi(config, scan=should_scan_kodi, clean=should_clean_kodi)
    logging.info("Sync complete.")


if __name__ == "__main__":
    main()
