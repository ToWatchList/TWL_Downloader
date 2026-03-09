#!/bin/sh
# this is a script to repair/rebuild the Music Video database in Kodi as provided by Jellyfin
# The web interface for Kodi is at http://10.0.3.252/ with username "osmc" and password "osmc"

VERBOSE=0
if [ "$1" = "-v" ]; then
  VERBOSE=1
fi

KODI_HOST="10.0.3.252"
KODI_USER="osmc"
KODI_PASS="osmc"

# Music Video library ID from Jellyfin. To update:
# scp osmc@10.0.3.252:/home/osmc/.kodi/userdata/Database/jellyfin.db /tmp/ && sqlite3 /tmp/jellyfin.db "SELECT view_id FROM view WHERE media_type='musicvideos';"
LIBRARY_ID="e2c00f297a5f80af390f52f72e782147"

log() {
  [ "$VERBOSE" -eq 1 ] && echo "$1"
}

# Function to send a jsonrpc message to Kodi
send_jsonrpc() {
  method="$1"
  params="$2"

  curl -s -X POST \
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
  exit 1
fi

log "Music Video library contains: $MUSIC_VIDEO_COUNT items"

# Only run repair if library has less than 10 items
if [ "$MUSIC_VIDEO_COUNT" -ge 10 ]; then
  echo "Kodi rebuild skipped: $MUSIC_VIDEO_COUNT items (>= 10)"
  exit 0
fi

echo "REPAIRED Music Video library ($MUSIC_VIDEO_COUNT items)"
log "Starting repair for library ID: $LIBRARY_ID"

# Trigger the RepairLibrary action
log "Sending repair command to Jellyfin addon..."
send_jsonrpc "Addons.ExecuteAddon" "{\"addonid\":\"plugin.video.jellyfin\",\"params\":{\"mode\":\"repairlib\",\"id\":\"$LIBRARY_ID\"}}" > /dev/null

sleep 10

# Return to home screen
log "Returning to home screen"
send_jsonrpc "Input.Home" "{}" > /dev/null
