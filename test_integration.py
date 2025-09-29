import json
import os
import subprocess
from pathlib import Path

import pytest

import twl_downloader


@pytest.mark.slow
def test_download_rick_astley(tmp_path):
    """
    Tests a real download of a known video to verify its properties.
    This test is slow and requires network access.
    """
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = "dQw4w9WgXcQ"
    temp_dir = str(tmp_path)

    # Minimal config for the download function
    config = {
        "download_to_tmp": False,
        "download_location": temp_dir,
        "youtube_cookies_file": None,
        "sponsorblock_categories": [],
    }

    # First, get the metadata, as the main script does
    info_dict = twl_downloader.get_video_metadata(video_url, config)
    assert info_dict is not None
    assert info_dict["id"] == video_id

    # Now, download the video
    twl_downloader.download_video(video_url, info_dict, config)

    # Find the downloaded video file
    downloaded_files = list(Path(temp_dir).glob(f"*-{video_id}.mkv"))
    assert len(downloaded_files) == 1, f"Expected 1 MKV file, but found {len(downloaded_files)}"
    video_path = downloaded_files[0]

    # Use ffprobe to check the video properties
    ffprobe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,duration",
        "-of",
        "json",
        str(video_path),
    ]

    result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ffprobe failed with error: {result.stderr}"

    media_info = json.loads(result.stdout)["streams"][0]

    # Check duration (3m 33s = 213s). Allow a small tolerance.
    duration = float(media_info["duration"])
    assert 212 < duration < 214, f"Expected duration to be ~213s, but got {duration}s"

    # Check resolution (4K is 3840x2160)
    height = int(media_info["height"])
    assert height == 2160, f"Expected height to be 2160 (4K), but got {height}"

    print(f"Successfully verified '{video_path.name}' has duration {duration}s and height {height}p.")