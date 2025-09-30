#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Update yt-dlp to the latest version using uv.
# We use a cache directory inside /config to persist downloads between runs.
echo "Checking for yt-dlp updates..."
uv pip install --cache-dir /config/pip-cache --upgrade yt-dlp

# Run the main application
echo "Starting ToWatchList Downloader sync..."
python3 twl_downloader.py
