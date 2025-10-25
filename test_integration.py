import json
import os
import subprocess
from pathlib import Path

import pytest

import twl_downloader


@pytest.mark.slow
def test_download_4k60fps_video(tmp_path):
    """
    Tests a real download of a known 4K60fps video to verify its properties.
    This test is slow and requires network access.
    """
    video_url = "https://www.youtube.com/watch?v=LXb3EKWsInQ"
    video_id = "LXb3EKWsInQ"
    temp_dir = str(tmp_path)

    # Minimal config for the download function
    config = {
        "tmp_download_location": None,  # Test direct download
        "download_location": temp_dir,
        "youtube_cookies_file": None,
        "sponsorblock_categories": [],
        "skip_sabr_drm_downloads": False,  # Allow SABR/DRM downloads for testing
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

    # Use ffprobe to check the video properties for exact values
    ffprobe_cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ffprobe failed with error: {result.stderr}"

    media_info = json.loads(result.stdout)

    # Check for the exact duration from the format info
    duration = media_info["format"]["duration"]
    assert duration == "313.808000", f"Expected duration to be '313.808000', but got {duration}"

    # Check for the exact resolution from the stream info (4K)
    height = int(media_info["streams"][0]["height"])
    width = int(media_info["streams"][0]["width"])
    assert height == 2160, f"Expected height to be 2160 (4K), but got {height}"
    assert width == 3840, f"Expected width to be 3840 (4K), but got {width}"

    # Check for 60fps (or 59.94fps which is commonly reported as 60fps)
    fps = media_info["streams"][0].get("r_frame_rate", "").split("/")
    if len(fps) == 2 and fps[1] != "0":
        actual_fps = int(fps[0]) / int(fps[1])
        assert 59.9 <= actual_fps <= 60.1, f"Expected ~60fps, but got {actual_fps}fps"

    # Verify we got a high-quality format (HDR content should have high bitrate)
    bitrate = int(media_info["format"].get("bit_rate", "0"))
    assert bitrate > 10000000, f"Expected high bitrate (>10Mbps) for 4K60HDR, but got {bitrate}bps"

    print(f"Successfully verified '{video_path.name}' has duration {duration}s, resolution {width}x{height}@{actual_fps}fps, and bitrate {bitrate}bps.")
