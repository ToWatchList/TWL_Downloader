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

HOSTNAME=$(hostname)

# Music Video library ID from Jellyfin. To update:
# sqlite3 /home/osmc/.kodi/userdata/Database/jellyfin.db "SELECT view_id FROM view WHERE media_type='musicvideos';"
LIBRARY_ID="e2c00f297a5f80af390f52f72e782147"

KODI_DB="/home/osmc/.kodi/userdata/Database/MyVideos131.db"
JELLYFIN_DB="/home/osmc/.kodi/userdata/Database/jellyfin.db"
PLAYLIST_FILE="/home/osmc/.kodi/userdata/playlists/video/jellyfinmusicvideos${LIBRARY_ID}.xsp"
NODE_INDEX="/home/osmc/.kodi/userdata/library/video/jellyfinmusicvideos${LIBRARY_ID}/index.xml"

log() {
  [ "$VERBOSE" -eq 1 ] && echo "$1"
}

notify_slack() {
  local msg="$1"
  [ -z "${SLACK_WEBHOOK_URL:-}" ] && return 0
  curl -s --max-time 10 -X POST "$SLACK_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"attachments\":[{\"color\":\"danger\",\"title\":\"Kodi Rebuild [$HOSTNAME]\",\"text\":\"$msg\",\"footer\":\"kodi.rebuild.sh @ $HOSTNAME\"}]}" \
    > /dev/null || true
}

send_jsonrpc() {
  method="$1"
  params="$2"
  curl -s --max-time 5 -X POST \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"$method\",\"params\":$params,\"id\":1}" \
    "http://$KODI_USER:$KODI_PASS@$KODI_HOST:8080/jsonrpc"
}

# --- Database integrity checks ---
# Use musicvideo_view (what Kodi actually queries) not the raw musicvideo table.
# JSON-RPC is NOT used for health checks — it returns 0 transiently during
# Kodi's UpdateLibrary rebuild cycle and cannot be trusted.
log "Checking Music Video library health..."

DB_RESULT=$(python3 -c "
import sqlite3, sys
try:
    c = sqlite3.connect('$KODI_DB', timeout=5)
    # view count: what Kodi's JSON-RPC actually sees (joins musicvideo->files->path)
    view  = c.execute('SELECT count(*) FROM musicvideo_view').fetchone()[0]
    # raw table count: how many musicvideo rows exist regardless of join integrity
    table = c.execute('SELECT count(*) FROM musicvideo').fetchone()[0]
    # orphan count: files rows referencing a non-existent path record.
    # non-zero means the path record was deleted while files/musicvideo rows remain
    orphans = c.execute('''
        SELECT count(*) FROM files
        WHERE idFile IN (SELECT idFile FROM musicvideo)
          AND idPath NOT IN (SELECT idPath FROM path)
    ''').fetchone()[0]
    c.close()
    print(view, table, orphans)
except Exception as e:
    print(-1, -1, -1)
" 2>/dev/null)

VIEW_COUNT=$(echo "$DB_RESULT" | cut -d' ' -f1)
TABLE_COUNT=$(echo "$DB_RESULT" | cut -d' ' -f2)
ORPHAN_COUNT=$(echo "$DB_RESULT" | cut -d' ' -f3)

if [ "$VIEW_COUNT" = "-1" ] || [ -z "$VIEW_COUNT" ]; then
  echo "ERROR: Could not query Kodi database"
  notify_slack "ERROR: Could not read Kodi database at $KODI_DB"
  exit 1
fi

log "musicvideo_view=$VIEW_COUNT  musicvideo_table=$TABLE_COUNT  orphaned_files=$ORPHAN_COUNT"

# Check jellyfin.db still has this library registered (repair needs it)
JELLYFIN_REGISTERED=$(python3 -c "
import sqlite3
try:
    c = sqlite3.connect('$JELLYFIN_DB', timeout=5)
    n = c.execute(\"SELECT count(*) FROM view WHERE view_id='$LIBRARY_ID' AND media_type='musicvideos'\").fetchone()[0]
    c.close()
    print(n)
except:
    print(0)
" 2>/dev/null)

log "jellyfin.db registered=$JELLYFIN_REGISTERED"

# Accumulate any issues found
ISSUES=""

# Primary check: view count is what Kodi shows — catches missing path/files/musicvideo rows
if [ "$VIEW_COUNT" -lt 10 ]; then
  ISSUES="${ISSUES} low_view_count=${VIEW_COUNT}"
fi

# Mismatch check: if table has rows but view doesn't show all of them,
# some musicvideo entries have broken joins (missing path or files records)
if [ "$TABLE_COUNT" -gt "$VIEW_COUNT" ]; then
  ISSUES="${ISSUES} join_mismatch(view=${VIEW_COUNT},table=${TABLE_COUNT})"
fi

# Orphan check: files rows referencing a non-existent path record.
# This catches the exact failure from tonight — the path table row was deleted
# while musicvideo/files rows remained, causing musicvideo_view to return 0.
if [ "$ORPHAN_COUNT" -gt 0 ]; then
  ISSUES="${ISSUES} orphaned_files=${ORPHAN_COUNT}"
fi

# Node file checks: if these are missing the library won't appear in Kodi's UI
# even if the database is healthy
if [ ! -f "$PLAYLIST_FILE" ]; then
  ISSUES="${ISSUES} missing_playlist"
fi
if [ ! -f "$NODE_INDEX" ]; then
  ISSUES="${ISSUES} missing_node_index"
fi

# Healthy: exit cleanly without Slack noise
if [ -z "$ISSUES" ]; then
  echo "Kodi rebuild skipped: view=${VIEW_COUNT} table=${TABLE_COUNT} orphans=${ORPHAN_COUNT} (healthy)"
  exit 0
fi

# Verify library is registered before attempting repair
if [ "$JELLYFIN_REGISTERED" = "0" ]; then
  echo "ERROR: library not in jellyfin.db — cannot repair"
  notify_slack "Music Video library broken ($ISSUES) but library_id $LIBRARY_ID not in jellyfin.db — manual intervention needed"
  exit 1
fi

echo "REPAIRING Music Video library: ${ISSUES}"
notify_slack "Music Video library repair triggered: ${ISSUES}"
log "Starting repair for library ID: $LIBRARY_ID"

REPAIR_RESPONSE=$(send_jsonrpc "Addons.ExecuteAddon" \
  "{\"addonid\":\"plugin.video.jellyfin\",\"params\":{\"mode\":\"repairlib\",\"id\":\"$LIBRARY_ID\"}}")
log "Repair response: $REPAIR_RESPONSE"

if echo "$REPAIR_RESPONSE" | grep -q '"error"'; then
  echo "ERROR: repairlib command failed"
  notify_slack "repairlib command failed: $REPAIR_RESPONSE"
  exit 1
fi

sleep 10

log "Returning to home screen"
send_jsonrpc "Input.Home" "{}" > /dev/null
