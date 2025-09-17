#!/usr/bin/env python3
# coding=utf-8
"""
This script downloads a user's latest ToWatchList unwatched videos using yt-dlp.
"""

import os
import sys
import glob
import requests
import yt_dlp
import shutil
from html.parser import HTMLParser
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
        return ''.join(self.fed)

def strip_tags(html):
    """Strips HTML tags from a string."""
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def get_config():
    """Reads configuration from environment variables."""
    config = {
        'api_key': os.getenv('TWL_API_KEY'),
        'download_location': os.getenv('TWL_DOWNLOAD_LOCATION', '/downloads'),
        'write_nfo_files': os.getenv('TWL_WRITE_NFO_FILES', 'false').lower() in ('true', '1', 't'),
        'kodi_hostname': os.getenv('TWL_KODI_HOSTNAME'),
        'kodi_port': int(os.getenv('TWL_KODI_PORT', '8080')),
        'kodi_user': os.getenv('TWL_KODI_USER'),
        'kodi_password': os.getenv('TWL_KODI_PASSWORD'),
        'download_to_tmp': os.getenv('TWL_DOWNLOAD_TO_TMP', 'true').lower() in ('true', '1', 't'),
    }
    if not config['api_key']:
        sys.exit("ERROR: TWL_API_KEY environment variable not set.")
    return config

def get_all_files_for_video_id(video_id, download_dir):
    """Finds all files (video, thumbnail, subs, etc.) for a given video_id."""
    pattern = os.path.join(download_dir, f'*-{video_id}.*')
    return glob.glob(pattern)

def find_video_file_for_id(video_id, download_dir):
    """Finds the main video file for a given video_id."""
    # Common video extensions that yt-dlp might output.
    video_extensions = ['mp4', 'mkv', 'webm', 'mov', 'flv', 'avi']
    for ext in video_extensions:
        files = glob.glob(os.path.join(download_dir, f'*-{video_id}.{ext}'))
        if files:
            return files[0]
    # Fallback if the extension is not in our list
    all_files = get_all_files_for_video_id(video_id, download_dir)
    return all_files[0] if all_files else None


def get_videos_from_api(api_key):
    """Fetches the list of videos from the ToWatchList API."""
    api_url = f"https://towatchlist.com/api/v1/marks?since=-28days&uid={api_key}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json().get('marks', [])
    except requests.exceptions.RequestException as e:
        sys.exit(f"ERROR: Failed to fetch data from ToWatchList API: {e}")
    except ValueError:
        sys.exit("ERROR: Failed to parse JSON response from ToWatchList API.")

def download_video(video_info, config):
    """Downloads a single video using yt-dlp."""
    title = video_info['Mark']['title']
    video_url = video_info['Mark']['source_url']
    video_id = video_info['Mark']['video_id']

    print(f"Downloading: '{title}' ({video_url})")

    output_path = '/tmp' if config['download_to_tmp'] else config['download_location']
    # Ensure filename is sanitized and doesn't contain path traversal characters
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    output_template = os.path.join(output_path, f'{safe_title}-{video_id}.%(ext)s')

    ydl_opts = {
        'format': 'bestvideo[height<=1080][vcodec*=avc]+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_template,
        'writethumbnail': True,
        'writesubtitles': True,
        'embedsubtitles': True,
        'addmetadata': True,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        print(f"ERROR: Failed to download '{title}'. Reason: {e}")
        return

    if config['download_to_tmp']:
        downloaded_files = get_all_files_for_video_id(video_id, '/tmp')
        for f in downloaded_files:
            try:
                print(f"Moving {os.path.basename(f)} to {config['download_location']}")
                shutil.move(f, config['download_location'])
            except shutil.Error as e:
                print(f"WARN: Could not move file {f}. It may already exist. Details: {e}")


def create_nfo_file(video_info, config):
    """Creates an NFO file for Kodi."""
    video_id = video_info['Mark']['video_id']
    video_file = find_video_file_for_id(video_id, config['download_location'])
    if not video_file:
        print(f"WARNING: Video file for '{video_id}' not found. Cannot create NFO file.")
        return

    nfo_file_path = os.path.splitext(video_file)[0] + '.nfo'
    if os.path.exists(nfo_file_path):
        return

    print(f"Creating NFO file for: {video_info['Mark']['title']}")

    thumb_url = ''
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            info_dict = ydl.extract_info(video_info['Mark']['source_url'], download=False)
            thumb_url = info_dict.get('thumbnail', '')
    except Exception as e:
        print(f"WARNING: Could not fetch thumbnail for {video_info['Mark']['title']}. Reason: {e}")

    nfo_content = f"""
<episodedetails>
  <title>{video_info['Mark']['title']}</title>
  <showtitle>{video_info['Mark']['channel_title']}</showtitle>
  <aired>{video_info['Mark']['created']}</aired>
  <plot>{strip_tags(video_info['Mark'].get('comment', ''))}</plot>
  <runtime>{round(int(video_info['Mark']['duration']) / 60.0)}</runtime>
  <thumb>{thumb_url}</thumb>
  <videourl>{video_info['Mark']['source_url']}</videourl>
</episodedetails>
"""
    with open(nfo_file_path, "w", encoding="utf-8") as nfo_file:
        nfo_file.write(nfo_content)

def remove_watched_video(video_id, config):
    """Removes local files for a watched or deleted video."""
    files_to_remove = get_all_files_for_video_id(video_id, config['download_location'])
    for f in files_to_remove:
        try:
            os.remove(f)
            print(f"Removed watched/deleted file: {os.path.basename(f)}")
        except OSError as e:
            print(f"ERROR: Could not remove file {f}. Reason: {e}")

def notify_kodi(config, scan=False, clean=False):
    """Sends notifications to Kodi to scan or clean the library."""
    if not config['kodi_hostname']:
        return

    print(f"Contacting Kodi at {config['kodi_hostname']}...")
    try:
        kodi = Kodi(f"http://{config['kodi_hostname']}:{config['kodi_port']}/jsonrpc", config['kodi_user'], config['kodi_password'])
        if kodi.JSONRPC.Ping()['result'] != 'pong':
            print("ERROR: Bad response from Kodi.")
            return

        if scan or clean:
            kodi.GUI.ShowNotification({"title": "ToWatchList Downloader", "message": "Updating Kodi library..."})
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

    os.makedirs(config['download_location'], exist_ok=True)
    if config['download_to_tmp']:
        os.makedirs('/tmp', exist_ok=True)

    videos = get_videos_from_api(config['api_key'])

    print(f"Syncing ToWatchList with '{config['download_location']}'")
    print(f"Found {len(videos)} videos to process.")
    print("---------------------------------")

    should_scan_kodi = False
    should_clean_kodi = False

    for video__info in videos:
        mark = video_info['Mark']
        video_id = mark['video_id']

        if mark.get('watched') or mark.get('delflag'):
            remove_watched_video(video_id, config)
            should_clean_kodi = True
            continue

        video_file = find_video_file_for_id(video_id, config['download_location'])
        if video_file:
            print(f"Already downloaded: '{mark['title']}'")
        else:
            download_video(video_info, config)
            should_scan_kodi = True

        if config['write_nfo_files']:
            create_nfo_file(video_info, config)

        print("---------------------------------")

    notify_kodi(config, scan=should_scan_kodi, clean=should_clean_kodi)
    print("Sync complete.")

if __name__ == '__main__':
    main()
