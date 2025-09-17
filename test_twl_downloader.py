from unittest.mock import MagicMock, patch

import pytest
import requests

import twl_downloader


@pytest.fixture
def mock_env(monkeypatch):
    """Fixture to mock environment variables."""
    monkeypatch.setenv("TWL_API_KEY", "test_api_key")
    monkeypatch.setenv("TWL_DOWNLOAD_LOCATION", "/test/downloads")
    monkeypatch.setenv("TWL_WRITE_NFO_FILES", "true")
    monkeypatch.setenv("TWL_KODI_HOSTNAME", "kodi_host")
    return monkeypatch


def test_get_config(mock_env):
    """Test that configuration is read correctly from environment variables."""
    config = twl_downloader.get_config()
    assert config["api_key"] == "test_api_key"
    assert config["download_location"] == "/test/downloads"
    assert config["write_nfo_files"] is True
    assert config["kodi_hostname"] == "kodi_host"


def test_get_config_missing_api_key(mock_env):
    """Test that the script exits if the API key is not set."""
    mock_env.delenv("TWL_API_KEY")
    with pytest.raises(SystemExit):
        twl_downloader.get_config()


def test_get_videos_from_api_success(mocker):
    """Test successful API call to fetch videos."""
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {"marks": ["video1", "video2"]}
    mock_response.raise_for_status.return_value = None
    mocker.patch("requests.get", return_value=mock_response)

    videos = twl_downloader.get_videos_from_api("fake_key")

    assert videos == ["video1", "video2"]
    requests.get.assert_called_once_with(
        "https://towatchlist.com/api/v1/marks?since=-28days&uid=fake_key"
    )


def test_get_videos_from_api_failure(mocker):
    """Test API call failure."""
    mocker.patch(
        "requests.get", side_effect=requests.exceptions.RequestException("API is down")
    )
    with pytest.raises(SystemExit):
        twl_downloader.get_videos_from_api("fake_key")


@patch("twl_downloader.yt_dlp.YoutubeDL")
def test_download_video(mock_yt_dlp, tmp_path):
    """Test the video download function."""
    config = {"download_to_tmp": False, "download_location": str(tmp_path)}
    video_info = {
        "Mark": {
            "title": "Test Video",
            "source_url": "http://example.com/video",
            "video_id": "test_id",
        }
    }

    # Mock the context manager
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance

    twl_downloader.download_video(video_info, config)

    # Check that YoutubeDL was initialized with correct options
    mock_yt_dlp.assert_called_once()
    args, kwargs = mock_yt_dlp.call_args
    # The options dictionary is the first positional argument
    ydl_opts_passed = args[0]
    assert "outtmpl" in ydl_opts_passed
    assert "Test Video-test_id" in ydl_opts_passed["outtmpl"]

    # Check that download was called
    mock_ydl_instance.download.assert_called_with(["http://example.com/video"])


@patch("os.remove")
@patch("glob.glob")
def test_remove_watched_video(mock_glob, mock_remove):
    """Test removal of watched video files."""
    config = {"download_location": "/downloads"}
    video_id = "watched_video_id"

    mock_glob.return_value = [
        "/downloads/video1-watched_video_id.mp4",
        "/downloads/video1-watched_video_id.nfo",
    ]

    twl_downloader.remove_watched_video(video_id, config)

    mock_glob.assert_called_once_with("/downloads/*-watched_video_id.*")
    assert mock_remove.call_count == 2
    mock_remove.assert_any_call("/downloads/video1-watched_video_id.mp4")
    mock_remove.assert_any_call("/downloads/video1-watched_video_id.nfo")


@patch(
    "twl_downloader.find_video_file_for_id", return_value="/downloads/test-video.mp4"
)
@patch("twl_downloader.yt_dlp.YoutubeDL")
def test_create_nfo_file(mock_yt_dlp, mock_find_video, mocker):
    """Test NFO file creation."""
    # Mock 'open' inside the test function
    mock_open_file = mocker.patch("builtins.open", mocker.mock_open())

    # Mock yt-dlp to return a thumbnail
    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = {
        "thumbnail": "http://thumb.url/img.jpg"
    }
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance

    config = {"download_location": "/downloads"}
    video_info = {
        "Mark": {
            "video_id": "test_id",
            "title": "NFO Test",
            "channel_title": "Test Channel",
            "created": "2023-01-01",
            "comment": "<p>A description</p>",
            "duration": "360",
            "source_url": "http://example.com/nfo_video",
        }
    }

    twl_downloader.create_nfo_file(video_info, config)

    mock_find_video.assert_called_once_with("test_id", "/downloads")
    mock_open_file.assert_called_once_with(
        "/downloads/test-video.nfo", "w", encoding="utf-8"
    )

    # Check that the content written to the file is correct
    handle = mock_open_file()
    written_content = "".join(call.args[0] for call in handle.write.call_args_list)
    assert "<title>NFO Test</title>" in written_content
    assert "<plot>A description</plot>" in written_content
    assert "<thumb>http://thumb.url/img.jpg</thumb>" in written_content
