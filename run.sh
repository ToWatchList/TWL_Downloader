#!/bin/bash

IMAGE_NAME="twl-downloader"
PROJECT_DIR="/home/nick/TWL_Downloader"
ENV_FILE="$PROJECT_DIR/.env"
LOCK_FILE="/tmp/twl-build.lock"

# Source .env so SLACK_WEBHOOK_URL is available for notifications below.
# The same file is passed to the container via --env-file.
# shellcheck disable=SC1090
[ -f "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a

notify() {
    [ -n "$SLACK_WEBHOOK_URL" ] || return 0
    # jq-free JSON escaping via python
    local payload
    payload=$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}))' "$1")
    curl -s -X POST -H 'Content-type: application/json' --data "$payload" "$SLACK_WEBHOOK_URL" > /dev/null
}

if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo "Docker image '$IMAGE_NAME' not found; rebuilding..." >&2
    BUILD_LOG=$(mktemp)
    # flock serializes builds so overlapping cron runs don't double-build;
    # a waiting run re-checks the image once it gets the lock.
    if ! flock "$LOCK_FILE" bash -c \
        "docker image inspect '$IMAGE_NAME' > /dev/null 2>&1 || docker build -t '$IMAGE_NAME' '$PROJECT_DIR'" \
        > "$BUILD_LOG" 2>&1; then
        tail -n 15 "$BUILD_LOG" >&2
        notify "TWL Downloader cron: image '$IMAGE_NAME' was missing and auto-rebuild FAILED. Last log lines:
$(tail -n 8 "$BUILD_LOG")"
        rm -f "$BUILD_LOG"
        exit 1
    fi
    rm -f "$BUILD_LOG"
    echo "Rebuild complete." >&2
fi

# timeout turns a hung run into a failed run (fail ping) instead of silence.
exec timeout --foreground -k 30 2h /usr/bin/docker run --rm \
    --env-file "$ENV_FILE" \
    -v "/exos/video/Other/ToWatchList/":/downloads \
    -v "/exos/docker-data/config/appdata/twl_downloader/":/config \
    -v "/exos/tmp/":/tmp \
    --name "$IMAGE_NAME" \
    "$IMAGE_NAME"
