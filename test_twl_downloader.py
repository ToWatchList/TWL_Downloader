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
    # Accept both single and double quotes in XML declaration (both are valid)
    assert ('<?xml version="1.0" encoding="utf-8"?>' in written_content or 
            "<?xml version='1.0' encoding='utf-8'?>" in written_content)
    assert "<title>NFO Test</title>" in written_content
    assert '<id>test_id_123</id>' in written_content
    assert "<releasedate>2023-01-15</releasedate>" in written_content
    assert "<added>" in written_content


@patch("twl_downloader.Kodi")
def test_notify_kodi_is_skipped(mock_kodi):
    """Test that Kodi notification is skipped if hostname is not set."""
    config = {"kodi_hostname": None}
    twl_downloader.notify_kodi(config, scan=True)
    mock_kodi.assert_not_called()


@patch("twl_downloader.yt_dlp.YoutubeDL")
@patch("os.path.isfile")
def test_drm_sabr_retry_without_cookies(mock_isfile, mock_yt_dlp):
    """Test that DRM/SABR protection triggers retry without cookies."""
    # Mock that cookies file exists
    mock_isfile.return_value = True

    config = {
        "youtube_cookies_file": "/config/cookies.txt",
        "sponsorblock_categories": [],
        "tmp_download_location": "/tmp",
    }

    drm_warning = "[youtube] test_id: Some tv client https formats have been skipped as they are DRM protected"
    sabr_warning = "[youtube] test_id: Some web client https formats have been skipped as they are missing a url. YouTube is forcing SABR streaming"

    call_count = 0

    def create_mock_ydl(opts):
        nonlocal call_count
        call_count += 1

        mock_instance = MagicMock()
        mock_context = MagicMock()

        # First call with cookies - trigger DRM/SABR warnings
        if call_count == 1 and 'cookiefile' in opts:
            if 'logger' in opts:
                opts['logger'].warning(drm_warning)
                opts['logger'].warning(sabr_warning)
            mock_context.extract_info.return_value = {
                "title": "Test Video",
                "id": "test_id",
                "upload_date": "20230115"
            }
        # Second call without cookies - succeeds
        else:
            mock_context.extract_info.return_value = {
                "title": "Test Video",
                "id": "test_id",
                "upload_date": "20230115",
                "_no_cookies": True
            }

        mock_instance.__enter__.return_value = mock_context
        mock_instance.__exit__.return_value = None
        return mock_instance

    mock_yt_dlp.side_effect = create_mock_ydl

    # Test get_video_metadata which should retry without cookies
    result = twl_downloader.get_video_metadata("http://example.com/video", config)

    # Should have been called twice (once with cookies, once without)
    assert mock_yt_dlp.call_count == 2

    # First call should have cookies
    first_call_opts = mock_yt_dlp.call_args_list[0][0][0]
    assert 'cookiefile' in first_call_opts

    # Second call should NOT have cookies
    second_call_opts = mock_yt_dlp.call_args_list[1][0][0]
    assert 'cookiefile' not in second_call_opts

    # Result should indicate no cookies were used
    assert result is not None
    assert result.get('_no_cookies') == True
