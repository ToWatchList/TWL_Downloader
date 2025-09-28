import glob
import os
import shutil
import sys
from datetime import datetime
from html.parser import HTMLParser

import requests
import yt_dlp
from kodijson import Kodi


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


def get_config():
    """Reads configuration from environment variables."""
    sponsorblock_default = "sponsor,intro,outro,selfpromo,preview,music_offtopic"
    config = {
        "api_key": os.getenv("TWL_API_KEY"),
        "download_location": os.getenv("TWL_DOWNLOAD_LOCATION", "/downloads"),
        "write_nfo_files": os.getenv("TWL_WRITE_NFO_FILES", "true").lower()
        in ("true", "1", "t"),
        "kodi_hostname": os.getenv("TWL_KODI_HOSTNAME"),
        "kodi_port": int(os.getenv("TWL_KODI_PORT", "8080")),
        "kodi_user": os.getenv("TWL_KODI_USER"),
        "kodi_password": os.getenv("TWL_KODI_PASSWORD"),
        "download_to_tmp": os.getenv("TWL_DOWNLOAD_TO_TMP", "true").lower()
        in ("true", "1", "t"),
        "youtube_cookies_file": os.getenv("YOUTUBE_COOKIES_FILE"),
        "sponsorblock_categories": os.getenv(
            "SPONSORBLOCK_CATEGORIES", sponsorblock_default
        ).split(","),
    }
    if not config["api_key"]:
        sys.exit("ERROR: TWL_API_KEY environment variable not set.")
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


def get_videos_from_api(api_key):
    """Fetches the list of videos from the ToWatchList API."""
    api_url = f"https://towatchlist.com/api/v1/marks?since=-28days&uid={api_key}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json().get("marks", [])
    except requests.exceptions.RequestException as e:
        sys.exit(f"ERROR: Failed to fetch data from ToWatchList API: {e}")
    except ValueError:
        sys.exit("ERROR: Failed to parse JSON response from ToWatchList API.")


def get_video_metadata(url, config):
    """Fetches video metadata using yt-dlp without downloading."""
    ydl_opts = {"quiet": True, "skip_download": True}
    if config["youtube_cookies_file"] and os.path.isfile(
        config["youtube_cookies_file"]
    ):
        ydl_opts["cookiefile"] = config["youtube_cookies_file"]
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"WARNING: Could not fetch metadata for {url}. Reason: {e}")
        return None


def download_video(url, info_dict, config):
    """Downloads a single video using yt-dlp."""
    title = info_dict.get("title", "Unknown Title")
    video_id = info_dict.get("id", "UnknownID")
    print(f"Downloading: '{title}' ({url})")

    output_path = "/tmp" if config["download_to_tmp"] else config["download_location"]
    safe_title = "".join(
        c for c in title if c.isalnum() or c in (" ", "-", "_")
    ).rstrip()
    output_template = os.path.join(output_path, f"{safe_title}-{video_id}.%(ext)s")

    postprocessors = [
        {"key": "FFmpegMetadata", "add_metadata": True},
        {"key": "SponsorBlock", "when": "pre_process", "categories": config["sponsorblock_categories"]},
        {"key": "ModifyChapters", "remove_sponsor_segments": config["sponsorblock_categories"]},
    ]

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

    if config["youtube_cookies_file"] and os.path.isfile(
        config["youtube_cookies_file"]
    ):
        ydl_opts["cookiefile"] = config["youtube_cookies_file"]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"ERROR: Failed to download '{title}'. Reason: {e}")


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
            print(f"Set modification date for '{os.path.basename(video_path)}' to {upload_datetime.date()}")
        except (ValueError, TypeError):
            print(f"WARNING: Could not parse upload date '{upload_date_str}'")


def create_nfo_file(video_file_path, twl_video_info, yt_video_info):
    """Creates an NFO file with rich metadata."""
    if not yt_video_info or not os.path.exists(video_file_path):
        return

    nfo_file_path = os.path.splitext(video_file_path)[0] + ".nfo"
    if os.path.exists(nfo_file_path):
        return

    print(f"Creating NFO file for: {yt_video_info.get('title')}")

    upload_date = yt_video_info.get("upload_date")
    aired_date = ""
    if upload_date:
        try:
            aired_date = datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    download_date = datetime.now().strftime("%Y-%m-%d")

    plot = f"""{yt_video_info.get('description', '')}

---
ToWatchList Comment: {strip_tags(twl_video_info['Mark'].get('comment', ''))}
Downloaded on: {download_date}
"""

    nfo_content = f"""
<episodedetails>
  <title>{yt_video_info.get('title', '')}</title>
  <showtitle>{yt_video_info.get('channel', '')}</showtitle>
  <aired>{aired_date}</aired>
  <plot>{plot}</plot>
  <runtime>{round(yt_video_info.get('duration', 0) / 60.0)}</runtime>
  <thumb>{yt_video_info.get('thumbnail', '')}</thumb>
  <videourl>{yt_video_info.get('webpage_url', '')}</videourl>
</episodedetails>
"""
    with open(nfo_file_path, "w", encoding="utf-8") as nfo_file:
        nfo_file.write(nfo_content)


def remove_watched_video(video_id, config):
    """Removes local files for a watched or deleted video."""
    files_to_remove = get_all_files_for_video_id(video_id, config["download_location"])
    for f in files_to_remove:
        try:
            os.remove(f)
            print(f"Removed watched/deleted file: {os.path.basename(f)}")
        except OSError as e:
            print(f"ERROR: Could not remove file {f}. Reason: {e}")


def notify_kodi(config, scan=False, clean=False):
    """Sends notifications to Kodi to scan or clean the library."""
    if not config["kodi_hostname"]:
        return

    print(f"Contacting Kodi at {config['kodi_hostname']}...")
    try:
        kodi = Kodi(
            f"http://{config['kodi_hostname']}:{config['kodi_port']}/jsonrpc",
            config["kodi_user"],
            config["kodi_password"],
        )
        if kodi.JSONRPC.Ping()["result"] != "pong":
            print("ERROR: Bad response from Kodi.")
            return

        if scan or clean:
            kodi.GUI.ShowNotification(
                {"title": "ToWatchList Downloader", "message": "Updating Kodi library..."}
            )
        if scan:
            print("Scanning Kodi video library...")
            kodi.VideoLibrary.Scan()
        if clean:
            print("Cleaning Kodi video library...")
            kodi.VideoLibrary.Clean()
        if not scan and not clean:
            print("No Scan or Clean of Kodi needed.")

    except Exception as e:
        print(f"ERROR: Could not connect to Kodi. Reason: {e}")


def main():
    """Main function to run the sync process."""
    config = get_config()
    os.makedirs(config["download_location"], exist_ok=True)
    if config["download_to_tmp"]:
        os.makedirs("/tmp", exist_ok=True)

    videos = get_videos_from_api(config["api_key"])
    print(f"Syncing ToWatchList with '{config['download_location']}'")
    print(f"Found {len(videos)} videos to process.")
    print("---------------------------------")

    should_scan_kodi = False
    should_clean_kodi = False

    for twl_video_info in videos:
        mark = twl_video_info["Mark"]
        video_id = mark["video_id"]
        video_url = mark["source_url"]

        if mark.get("watched") or mark.get("delflag"):
            remove_watched_video(video_id, config)
            should_clean_kodi = True
            continue

        video_file = find_video_file_for_id(video_id, config["download_location"])
        if video_file:
            print(f"Already downloaded: '{mark['title']}'")
        else:
            yt_video_info = get_video_metadata(video_url, config)
            if not yt_video_info:
                continue

            download_video(video_url, yt_video_info, config)

            if config["download_to_tmp"]:
                temp_video_file = find_video_file_for_id(video_id, "/tmp")
                if temp_video_file:
                    downloaded_files = get_all_files_for_video_id(video_id, "/tmp")
                    for f in downloaded_files:
                        try:
                            shutil.move(f, config["download_location"])
                        except shutil.Error as e:
                            print(f"WARN: Could not move file {f}. It may already exist. Details: {e}")

            final_video_path = find_video_file_for_id(video_id, config["download_location"])
            set_file_modification_time(final_video_path, yt_video_info)

            if config["write_nfo_files"]:
                create_nfo_file(final_video_path, twl_video_info, yt_video_info)

            should_scan_kodi = True

        print("---------------------------------")

    notify_kodi(config, scan=should_scan_kodi, clean=should_clean_kodi)
    print("Sync complete.")


if __name__ == "__main__":
    main()