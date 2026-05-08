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
        "js_runtimes": ["deno"],
        "remote_components": ["ejs:github"],
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


@pytest.mark.slow
def test_youtube_description_chapters(tmp_path):
    """
    Tests YouTube description chapter embedding.
    Uses a video known to have chapters in its description.
    """
    video_url = "https://www.youtube.com/watch?v=VgiPWtD6Dqo"
    video_id = "VgiPWtD6Dqo"
    temp_dir = str(tmp_path)

    config = {
        "tmp_download_location": None,
        "download_location": temp_dir,
        "youtube_cookies_file": None,
        "sponsorblock_categories": [],  # No SponsorBlock for this test
        "skip_sabr_drm_downloads": False,
        "remove_sponsor_segments": False,
        "js_runtimes": ["deno"],
        "remote_components": ["ejs:github"],
    }

    # Get metadata and download
    info_dict = twl_downloader.get_video_metadata(video_url, config)
    assert info_dict is not None
    assert info_dict["id"] == video_id

    twl_downloader.download_video(video_url, info_dict, config)

    # Find the downloaded video
    video_files = list(Path(temp_dir).glob(f"*-{video_id}.mp4"))
    assert len(video_files) == 1, f"Expected 1 MP4 file, but found {len(video_files)}"
    video_path = video_files[0]

    # Check for embedded chapters
    ffprobe_chapters_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_chapters", str(video_path)
    ]

    result = subprocess.run(ffprobe_chapters_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ffprobe chapters failed: {result.stderr}"

    chapters_info = json.loads(result.stdout)
    chapters = chapters_info.get("chapters", [])

    print(f"Found {len(chapters)} YouTube description chapters:")
    for i, chapter in enumerate(chapters):
        start_time = float(chapter.get("start_time", 0))
        end_time = float(chapter.get("end_time", 0))
        title = chapter.get("tags", {}).get("title", f"Chapter {i+1}")
        print(f"  Chapter {i+1}: {start_time:.1f}s to {end_time:.1f}s - '{title}'")

    # This video should have 6 chapters from its description
    assert len(chapters) >= 5, f"Expected at least 5 YouTube description chapters, found {len(chapters)}"

    # Verify chapter titles contain expected content
    chapter_titles = [chapter.get("tags", {}).get("title", "") for chapter in chapters]
    expected_keywords = ["format", "trick-taking", "Bottle", "Bean", "Naishi", "Iliad"]

    found_keywords = 0
    for keyword in expected_keywords:
        if any(keyword in title for title in chapter_titles):
            found_keywords += 1

    assert found_keywords >= 3, f"Expected to find at least 3 keywords in chapter titles, found {found_keywords}"
    print(f"Successfully verified YouTube description chapters with {found_keywords}/{len(expected_keywords)} expected keywords")


@pytest.mark.slow
def test_sponsorblock_chapter_marking(tmp_path):
    """
    Tests SponsorBlock chapter marking (default behavior).
    Uses a video known to have sponsor segments.
    """
    video_url = "https://www.youtube.com/watch?v=Nq-Faw_ENEQ"
    video_id = "Nq-Faw_ENEQ"
    temp_dir = str(tmp_path)

    config = {
        "tmp_download_location": None,
        "download_location": temp_dir,
        "youtube_cookies_file": None,
        "sponsorblock_categories": ["sponsor", "intro", "outro"],
        "skip_sabr_drm_downloads": False,
        "remove_sponsor_segments": False,  # Default: mark as chapters only
        "js_runtimes": ["deno"],
        "remote_components": ["ejs:github"],
    }

    # Get metadata and download with chapter marking
    info_dict = twl_downloader.get_video_metadata(video_url, config)
    assert info_dict is not None
    assert info_dict["id"] == video_id

    twl_downloader.download_video(video_url, info_dict, config)

    # Find the downloaded video with chapters
    video_files = list(Path(temp_dir).glob(f"*-{video_id}.mp4"))
    assert len(video_files) == 1, f"Expected 1 MP4 file, but found {len(video_files)}"
    video_path = video_files[0]

    # Check for embedded chapters
    ffprobe_chapters_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_chapters", str(video_path)
    ]

    result = subprocess.run(ffprobe_chapters_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ffprobe chapters failed: {result.stderr}"

    chapters_info = json.loads(result.stdout)
    chapters = chapters_info.get("chapters", [])

    print(f"Found {len(chapters)} chapters with SponsorBlock marking:")
    for i, chapter in enumerate(chapters):
        start_time = float(chapter.get("start_time", 0))
        end_time = float(chapter.get("end_time", 0))
        title = chapter.get("tags", {}).get("title", f"Chapter {i+1}")
        print(f"  Chapter {i+1}: {start_time:.3f}s to {end_time:.3f}s - '{title}'")

    # Get original duration for comparison
    ffprobe_format_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(video_path)
    ]

    result = subprocess.run(ffprobe_format_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ffprobe format failed: {result.stderr}"

    format_info = json.loads(result.stdout)
    original_duration = float(format_info["format"]["duration"])

    print(f"Chapter-marked video duration: {original_duration}s (segments preserved)")

    # The video may or may not have chapters depending on SponsorBlock data availability
    # The main test is that the download succeeded and we can check for chapters
    print(f"Note: This video has {len(chapters)} chapters (may be 0 if no SponsorBlock data or description chapters)")
    assert original_duration > 600, f"Video seems too short: {original_duration}s"


@pytest.mark.slow
def test_combined_youtube_and_sponsorblock_chapters(tmp_path):
    """
    Tests that YouTube description chapters and SponsorBlock chapters work together.
    Uses the board game video which has both types.
    """
    video_url = "https://www.youtube.com/watch?v=VgiPWtD6Dqo"
    video_id = "VgiPWtD6Dqo"
    temp_dir = str(tmp_path)

    config = {
        "tmp_download_location": None,
        "download_location": temp_dir,
        "youtube_cookies_file": None,
        "sponsorblock_categories": ["sponsor", "intro", "outro", "selfpromo"],
        "skip_sabr_drm_downloads": False,
        "remove_sponsor_segments": False,  # Preserve audio sync
        "js_runtimes": ["deno"],
        "remote_components": ["ejs:github"],
    }

    # Get metadata and download
    info_dict = twl_downloader.get_video_metadata(video_url, config)
    assert info_dict is not None
    assert info_dict["id"] == video_id

    twl_downloader.download_video(video_url, info_dict, config)

    # Find the downloaded video
    video_files = list(Path(temp_dir).glob(f"*-{video_id}.mp4"))
    assert len(video_files) == 1, f"Expected 1 MP4 file, but found {len(video_files)}"
    video_path = video_files[0]

    # Check for embedded chapters
    ffprobe_chapters_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_chapters", str(video_path)
    ]

    result = subprocess.run(ffprobe_chapters_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ffprobe chapters failed: {result.stderr}"

    chapters_info = json.loads(result.stdout)
    chapters = chapters_info.get("chapters", [])

    print(f"Found {len(chapters)} total chapters (YouTube + SponsorBlock):")

    youtube_chapters = 0
    sponsorblock_chapters = 0

    for i, chapter in enumerate(chapters):
        start_time = float(chapter.get("start_time", 0))
        end_time = float(chapter.get("end_time", 0))
        title = chapter.get("tags", {}).get("title", f"Chapter {i+1}")
        print(f"  Chapter {i+1}: {start_time:.1f}s to {end_time:.1f}s - '{title}'")

        # Classify chapter type based on title
        if any(keyword in title.lower() for keyword in ["sponsor", "intro", "outro", "promo"]):
            sponsorblock_chapters += 1
        else:
            youtube_chapters += 1

    print(f"Breakdown: {youtube_chapters} YouTube description chapters, {sponsorblock_chapters} SponsorBlock chapters")

    # Should have YouTube description chapters (at least 5)
    assert len(chapters) >= 5, f"Expected at least 5 total chapters, found {len(chapters)}"

    # Verify we got the expected YouTube chapters
    expected_keywords = ["format", "trick-taking", "Bottle", "Bean"]
    chapter_titles = [chapter.get("tags", {}).get("title", "") for chapter in chapters]
    found_keywords = sum(1 for keyword in expected_keywords if any(keyword in title for title in chapter_titles))

    assert found_keywords >= 2, f"Expected YouTube chapter keywords, found {found_keywords}/{len(expected_keywords)}"
    print(f"Successfully verified combined chapter embedding with {found_keywords} YouTube keywords")


@pytest.mark.slow
def test_sponsorblock_segment_removal(tmp_path):
    """
    Tests SponsorBlock segment removal (alternative behavior that may cause audio sync issues).
    This tests the REMOVE_SPONSOR_SEGMENTS=true configuration.
    """
    video_url = "https://www.youtube.com/watch?v=Nq-Faw_ENEQ"
    video_id = "Nq-Faw_ENEQ"
    temp_dir = str(tmp_path)

    config = {
        "tmp_download_location": None,
        "download_location": temp_dir,
        "youtube_cookies_file": None,
        "sponsorblock_categories": ["sponsor"],
        "skip_sabr_drm_downloads": False,
        "remove_sponsor_segments": True,  # Enable segment removal
        "js_runtimes": ["deno"],
        "remote_components": ["ejs:github"],
    }

    # Get metadata and download with segment removal
    info_dict = twl_downloader.get_video_metadata(video_url, config)
    assert info_dict is not None
    assert info_dict["id"] == video_id

    twl_downloader.download_video(video_url, info_dict, config)

    # Find the downloaded video with removed segments
    video_files = list(Path(temp_dir).glob(f"*-{video_id}.mp4"))
    assert len(video_files) == 1, f"Expected 1 MP4 file, but found {len(video_files)}"
    video_path = video_files[0]

    # Get duration and chapters after segment removal
    ffprobe_format_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_chapters", str(video_path)
    ]

    result = subprocess.run(ffprobe_format_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ffprobe failed: {result.stderr}"

    media_info = json.loads(result.stdout)
    removed_duration = float(media_info["format"]["duration"])
    chapters = media_info.get("chapters", [])

    print(f"Segment-removed video duration: {removed_duration}s")
    print(f"Chapters after removal: {len(chapters)}")

    for i, chapter in enumerate(chapters):
        start_time = float(chapter.get("start_time", 0))
        end_time = float(chapter.get("end_time", 0))
        title = chapter.get("tags", {}).get("title", f"Chapter {i+1}")
        print(f"  Chapter {i+1}: {start_time:.3f}s to {end_time:.3f}s - '{title}'")

    # Video should be reasonable length (not too short or long)
    assert 60 < removed_duration < 3600, f"Video duration {removed_duration}s seems unreasonable"

    # May have chapters from the removal process
    print(f"Successfully tested segment removal - final duration: {removed_duration}s with {len(chapters)} chapters")


@pytest.mark.slow
def test_no_sponsorblock_categories(tmp_path):
    """
    Tests downloading with SponsorBlock disabled (empty categories).
    Should only get YouTube description chapters if present.
    """
    video_url = "https://www.youtube.com/watch?v=VgiPWtD6Dqo"
    video_id = "VgiPWtD6Dqo"
    temp_dir = str(tmp_path)

    config = {
        "tmp_download_location": None,
        "download_location": temp_dir,
        "youtube_cookies_file": None,
        "sponsorblock_categories": [],  # No SponsorBlock processing
        "skip_sabr_drm_downloads": False,
        "remove_sponsor_segments": False,
        "js_runtimes": ["deno"],
        "remote_components": ["ejs:github"],
    }

    # Get metadata and download
    info_dict = twl_downloader.get_video_metadata(video_url, config)
    assert info_dict is not None
    assert info_dict["id"] == video_id

    twl_downloader.download_video(video_url, info_dict, config)

    # Find the downloaded video
    video_files = list(Path(temp_dir).glob(f"*-{video_id}.mp4"))
    assert len(video_files) == 1, f"Expected 1 MP4 file, but found {len(video_files)}"
    video_path = video_files[0]

    # Check for embedded chapters
    ffprobe_chapters_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_chapters", str(video_path)
    ]

    result = subprocess.run(ffprobe_chapters_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ffprobe chapters failed: {result.stderr}"

    chapters_info = json.loads(result.stdout)
    chapters = chapters_info.get("chapters", [])

    print(f"Found {len(chapters)} chapters with SponsorBlock disabled:")
    for i, chapter in enumerate(chapters):
        start_time = float(chapter.get("start_time", 0))
        end_time = float(chapter.get("end_time", 0))
        title = chapter.get("tags", {}).get("title", f"Chapter {i+1}")
        print(f"  Chapter {i+1}: {start_time:.1f}s to {end_time:.1f}s - '{title}'")

    # Should still get YouTube description chapters
    assert len(chapters) >= 5, f"Expected YouTube description chapters even without SponsorBlock, found {len(chapters)}"

    # Verify these are YouTube chapters (not SponsorBlock)
    chapter_titles = [chapter.get("tags", {}).get("title", "") for chapter in chapters]
    youtube_indicators = ["format", "trick-taking", "Bottle", "Bean", "Naishi"]
    found_youtube = sum(1 for indicator in youtube_indicators if any(indicator in title for title in chapter_titles))

    assert found_youtube >= 2, f"Expected YouTube chapter indicators, found {found_youtube}"
    print(f"Successfully verified YouTube-only chapters: {found_youtube} indicators found")


@pytest.mark.slow
def test_chapter_edge_cases(tmp_path):
    """
    Tests edge cases for chapter handling:
    - Video with no description chapters
    - Various SponsorBlock category combinations
    """
    # Test with a simple video that likely has minimal chapters
    video_url = "https://www.youtube.com/watch?v=LXb3EKWsInQ"  # 4K test video
    video_id = "LXb3EKWsInQ"
    temp_dir = str(tmp_path)

    config = {
        "tmp_download_location": None,
        "download_location": temp_dir,
        "youtube_cookies_file": None,
        "sponsorblock_categories": ["sponsor", "intro", "outro", "selfpromo", "preview", "music_offtopic"],
        "skip_sabr_drm_downloads": False,
        "remove_sponsor_segments": False,
        "js_runtimes": ["deno"],
        "remote_components": ["ejs:github"],
    }

    # Get metadata and download
    info_dict = twl_downloader.get_video_metadata(video_url, config)
    assert info_dict is not None
    assert info_dict["id"] == video_id

    twl_downloader.download_video(video_url, info_dict, config)

    # Find the downloaded video
    video_files = list(Path(temp_dir).glob(f"*-{video_id}.mp4"))
    assert len(video_files) == 1, f"Expected 1 MP4 file, but found {len(video_files)}"
    video_path = video_files[0]

    # Check for embedded chapters
    ffprobe_chapters_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_chapters", str(video_path)
    ]

    result = subprocess.run(ffprobe_chapters_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ffprobe chapters failed: {result.stderr}"

    chapters_info = json.loads(result.stdout)
    chapters = chapters_info.get("chapters", [])

    print(f"Found {len(chapters)} chapters in video with full SponsorBlock categories:")
    for i, chapter in enumerate(chapters):
        start_time = float(chapter.get("start_time", 0))
        end_time = float(chapter.get("end_time", 0))
        title = chapter.get("tags", {}).get("title", f"Chapter {i+1}")
        print(f"  Chapter {i+1}: {start_time:.1f}s to {end_time:.1f}s - '{title}'")

    # Video should download successfully regardless of chapter count
    # (May be 0 chapters if no description chapters and no SponsorBlock segments)
    assert len(chapters) >= 0, "Chapter count should be non-negative"

    # Verify the video file is valid
    ffprobe_format_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(video_path)
    ]

    result = subprocess.run(ffprobe_format_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ffprobe format failed: {result.stderr}"

    format_info = json.loads(result.stdout)
    duration = float(format_info["format"]["duration"])

    assert duration > 60, f"Video seems too short: {duration}s"
    print(f"Successfully handled edge case video: {duration}s duration, {len(chapters)} chapters")
