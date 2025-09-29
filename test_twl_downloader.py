from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

import twl_downloader


@pytest.fixture
def mock_env(monkeypatch):
    """Fixture to mock environment variables."""
    monkeypatch.setenv("TWL_API_KEY", "test_api_key")
    monkeypatch.setenv("TWL_LOOKBACK_DAYS", "10")
    return monkeypatch


def test_get_config(mock_env):
    """Test that configuration is read correctly from environment variables."""
    config = twl_downloader.get_config()
    assert config["api_key"] == "test_api_key"
    assert config["lookback_days"] == 10


def test_get_videos_from_api_success(mocker):
    """Test successful API call to fetch videos with custom lookback."""
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {"marks": ["video1", "video2"]}
    mock_response.raise_for_status.return_value = None
    mocker.patch("requests.get", return_value=mock_response)

    twl_downloader.get_videos_from_api("fake_key", 15)

    requests.get.assert_called_once_with(
        "https://towatchlist.com/api/v1/marks?since=-15days&uid=fake_key"
    )


@patch("twl_downloader.yt_dlp.YoutubeDL")
def test_download_uses_hardcoded_tmp_path(mock_yt_dlp):
    """Test that the download function uses the hardcoded /tmp path."""
    config = {
        "youtube_cookies_file": None,
        "sponsorblock_categories": [],
    }
    info_dict = {"title": "Test Video", "id": "test_id"}
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance

    twl_downloader.download_video("http://example.com/video", info_dict, config)

    mock_yt_dlp.assert_called_once()
    args, _ = mock_yt_dlp.call_args
    ydl_opts_passed = args[0]
    assert "/tmp" in ydl_opts_passed["outtmpl"]


@patch("os.path.exists", return_value=True)
@patch("os.utime")
def test_set_file_modification_time(mock_utime, mock_exists):
    """Test that file modification time is set correctly."""
    info_dict = {"upload_date": "20230115"}
    video_path = "/downloads/video.mkv"
    twl_downloader.set_file_modification_time(video_path, info_dict)
    expected_datetime = datetime(2023, 1, 15)
    expected_timestamp = expected_datetime.timestamp()
    mock_utime.assert_called_once_with(
        video_path, (expected_timestamp, expected_timestamp)
    )


@patch(
    "twl_downloader.find_video_file_for_id", return_value="/downloads/test-video.mkv"
)
def test_create_nfo_file(mock_find_video, mocker):
    """Test Jellyfin-compliant NFO file creation."""

    def mock_path_exists(path):
        return path.endswith(".mkv")

    mocker.patch("os.path.exists", side_effect=mock_path_exists)
    mock_open_file = mocker.patch("builtins.open", mocker.mock_open())
    twl_video_info = {"Mark": {"comment": "A TWL comment."}}
    yt_video_info = {
        "id": "test_id_123",
        "title": "NFO Test",
        "channel": "Test Channel",
        "uploader": "Test Uploader",
        "upload_date": "20230115",
        "description": "The main description.",
        "duration": 360,
        "thumbnail": "http://thumb.url/img.jpg",
        "webpage_url": "http://example.com/nfo_video",
        "categories": ["Science & Technology"],
        "tags": ["testing", "python"],
    }
    twl_downloader.create_nfo_file(
        "/downloads/test-video.mkv", twl_video_info, yt_video_info
    )
    handle = mock_open_file()
    written_content = "".join(call.args[0] for call in handle.write.call_args_list)
    assert '<?xml version="1.0" encoding="utf-8" standalone="yes"?>' in written_content
    assert "<title>NFO Test</title>" in written_content
    assert '<uniqueid type="youtube" default="true">test_id_123</uniqueid>' in written_content
    assert "<releasedate>2023-01-15</releasedate>" in written_content
    assert "<dateadded>" in written_content


@patch("twl_downloader.Kodi")
def test_notify_kodi_is_skipped(mock_kodi):
    """Test that Kodi notification is skipped if hostname is not set."""
    config = {"kodi_hostname": None}
    twl_downloader.notify_kodi(config, scan=True)
    mock_kodi.assert_not_called()