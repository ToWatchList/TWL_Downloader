#!/bin/bash

IMAGE_NAME="twl-downloader"
ENV_FILE="/home/nick/TWL_Downloader/.env"

# Source .env so SLACK_WEBHOOK_URL is available for the pre-flight check below.
# The same file is passed to the container via --env-file.
# shellcheck disable=SC1090
[ -f "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a

if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo "ERROR: Docker image '$IMAGE_NAME' not found. Run 'make build' in /home/nick/TWL_Downloader/" >&2
    curl -s -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"TWL Downloader cron skipped: Docker image '$IMAGE_NAME' is missing. Run \`make build\` on the NAS.\"}" \
        "$SLACK_WEBHOOK_URL"
    exit 1
fi

exec /usr/bin/docker run --rm \
    --env-file /home/nick/TWL_Downloader/.env \
    -v "/exos/video/Other/ToWatchList/":/downloads \
    -v "/exos/docker-data/config/appdata/twl_downloader/":/config \
    -v "/exos/tmp/":/tmp \
    --name "$IMAGE_NAME" \
    "$IMAGE_NAME"
