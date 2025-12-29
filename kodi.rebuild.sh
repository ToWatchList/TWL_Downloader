#!/bin/sh
# this is a script to repair/rebuild the Music Video database in Kodi as provided by Jellyfin
# The web interface for Kodi is at http://10.0.3.252/ with username "osmc" and password "osmc"

KODI_HOST="10.0.3.252"
KODI_USER="osmc"
KODI_PASS="osmc"

# Music Video library ID from Jellyfin. To update:
# scp osmc@10.0.3.252:/home/osmc/.kodi/userdata/Database/jellyfin.db /tmp/ && sqlite3 /tmp/jellyfin.db "SELECT view_id FROM view WHERE media_type='musicvideos';"
LIBRARY_ID="e2c00f297a5f80af390f52f72e782147"

# Function to send a jsonrpc message to Kodi
send_jsonrpc() {
  local method=$1
  local params=$2

  curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"$method\",\"params\":$params,\"id\":1}" \
    http://$KODI_USER:$KODI_PASS@$KODI_HOST/jsonrpc
}

# First send an alert to the user that we are starting the rebuild
send_jsonrpc "GUI.ShowNotification" '{"title":"Library Update","message":"Starting Music Video library repair...","displaytime":5000}'

echo "Starting Music Video library repair..."
echo "Library ID: $LIBRARY_ID"

# Send the RepairLibrary notification to the Jellyfin addon
# The Jellyfin addon listens for NotifyAll messages with method "RepairLibrary"
DATA=$(echo "{\"Id\": \"$LIBRARY_ID\"}" | sed 's/"/\\"/g')
NOTIFY_CMD="NotifyAll(plugin.video.jellyfin, RepairLibrary, \"[$DATA]\")"

echo "Sending repair command to Jellyfin addon..."
send_jsonrpc "XBMC.ExecuteBuiltin" "{\"command\":\"$NOTIFY_CMD\"}"

# Give it a moment to start
sleep 2

# Send a notification that the repair has been initiated
send_jsonrpc "GUI.ShowNotification" '{"title":"Library Update","message":"Music Video library repair initiated. This may take several minutes.","displaytime":10000}'

echo "Repair command sent successfully!"
echo "The Music Video library is being rebuilt. Monitor Kodi for progress."
