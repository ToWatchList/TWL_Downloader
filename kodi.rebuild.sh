#!/bin/sh
# this is a script to repair/rebuild the Music Video database in Kodi as provided by Jellyfin
# Intended to run directly on the kodi host (osmc-az.local) so all requests hit 127.0.0.1.
# Deploy with: make deploy-kodi
# Set up cron on the kodi host: 10 * * * * /home/osmc/kodi.rebuild.sh

VERBOSE=0
if [ "$1" = "-v" ]; then
  VERBOSE=1
fi

# Source local env file for SLACK_WEBHOOK_URL (create on kodi host if needed:
#   echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/..." > ~/.kodi_rebuild.env)
[ -f "$HOME/.kodi_rebuild.env" ] && . "$HOME/.kodi_rebuild.env"

KODI_HOST="127.0.0.1"
KODI_USER="osmc"
KODI_PASS="osmc"

# Music Video library ID from Jellyfin. To update:
# sqlite3 /home/osmc/.kodi/userdata/Database/jellyfin.db "SELECT view_id FROM view WHERE media_type='musicvideos';"
LIBRARY_ID="e2c00f297a5f80af390f52f72e782147"

log() {
  [ "$VERBOSE" -eq 1 ] && echo "$1"
}

notify_slack() {
  local msg="$1"
  [ -z "${SLACK_WEBHOOK_URL:-}" ] && return 0
  curl -s --max-time 10 -X POST "$SLACK_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"attachments\":[{\"color\":\"danger\",\"title\":\"Kodi Rebuild\",\"text\":\"$msg\",\"footer\":\"kodi.rebuild.sh\"}]}" \
    > /dev/null || true
}

# Function to send a jsonrpc message to Kodi
send_jsonrpc() {
  method="$1"
  params="$2"

  curl -s --max-time 5 -X POST \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"$method\",\"params\":$params,\"id\":1}" \
    "http://$KODI_USER:$KODI_PASS@$KODI_HOST/jsonrpc"
}

# Check the number of music videos in the library
log "Checking Music Video library count..."
RESPONSE=$(send_jsonrpc "VideoLibrary.GetMusicVideos" "{\"properties\":[]}")

MUSIC_VIDEO_COUNT=$(echo "$RESPONSE" | grep -o '"total":[0-9]*' | cut -d':' -f2 | head -1)

if [ -z "$MUSIC_VIDEO_COUNT" ]; then
  echo "ERROR: Could not parse music video count"
  [ "$VERBOSE" -eq 1 ] && echo "Response: $RESPONSE"
  notify_slack "Could not reach Kodi or parse music video count (response: $RESPONSE)"
  exit 1
fi

log "Music Video library contains: $MUSIC_VIDEO_COUNT items"

# Only run repair if library has less than 10 items
if [ "$MUSIC_VIDEO_COUNT" -ge 10 ]; then
  echo "Kodi rebuild skipped: $MUSIC_VIDEO_COUNT items (>= 10)"
  exit 0
fi

echo "REPAIRED Music Video library ($MUSIC_VIDEO_COUNT items)"
notify_slack "Music Video library had $MUSIC_VIDEO_COUNT items — repair triggered"
log "Starting repair for library ID: $LIBRARY_ID"

# Trigger the RepairLibrary action
log "Sending repair command to Jellyfin addon..."
REPAIR_RESPONSE=$(send_jsonrpc "Addons.ExecuteAddon" "{\"addonid\":\"plugin.video.jellyfin\",\"params\":{\"mode\":\"repairlib\",\"id\":\"$LIBRARY_ID\"}}")
log "Repair response: $REPAIR_RESPONSE"

if echo "$REPAIR_RESPONSE" | grep -q '"error"'; then
  echo "ERROR: repairlib command failed"
  notify_slack "repairlib command failed: $REPAIR_RESPONSE"
  exit 1
fi

sleep 10

# Return to home screen
log "Returning to home screen"
send_jsonrpc "Input.Home" "{}" > /dev/null
