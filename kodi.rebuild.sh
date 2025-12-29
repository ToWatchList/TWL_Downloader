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
# send_jsonrpc "GUI.ShowNotification" '{"title":"Library Update","message":"Starting Music Video library repair...","displaytime":5000}'

echo "Starting Music Video library repair..."
echo "Library ID: $LIBRARY_ID"

# Trigger the RepairLibrary action via the Jellyfin addon plugin URL
PLUGIN_URL="plugin://plugin.video.jellyfin/?mode=repairlib&id=$LIBRARY_ID"

echo "Sending repair command to Jellyfin addon..."
send_jsonrpc "Addons.ExecuteAddon" "{\"addonid\":\"plugin.video.jellyfin\",\"params\":{\"mode\":\"repairlib\",\"id\":\"$LIBRARY_ID\"}}"

echo
echo "The Music Video library is being rebuilt. Monitor Kodi for progress."
