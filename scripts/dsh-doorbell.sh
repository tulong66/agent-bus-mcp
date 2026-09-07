#!/bin/bash
# DSH (DeepSeek Harness) Doorbell Listener
# Monitors ~/.agent-bus/doorbells/deepseek.bell and triggers DSH wake event
set -euo pipefail

AGENT_ID="${1:-deepseek-coder}"
BELL_FILE="$HOME/.agent-bus/doorbells/${AGENT_ID}.bell"
mkdir -p "$(dirname "$BELL_FILE")"

echo "[dsh-doorbell] Listening for doorbell on ${AGENT_ID}..."
LAST_MTIME=0
if [ -f "$BELL_FILE" ]; then
  LAST_MTIME=$(stat -f %m "$BELL_FILE" 2>/dev/null || stat -c %Y "$BELL_FILE" 2>/dev/null || echo 0)
fi

while true; do
  if [ -f "$BELL_FILE" ]; then
    CUR_MTIME=$(stat -f %m "$BELL_FILE" 2>/dev/null || stat -c %Y "$BELL_FILE" 2>/dev/null || echo 0)
    if [ "$CUR_MTIME" -gt "$LAST_MTIME" ]; then
      echo "[dsh-doorbell] Bell rung at $(date)!"
      # Echo latest message from inbox
      INBOX_FILE="$HOME/.agent-bus/inbox/${AGENT_ID}.msg"
      if [ -f "$INBOX_FILE" ]; then
        echo "--- New Message ---"
        cat "$INBOX_FILE"
      fi
      LAST_MTIME="$CUR_MTIME"
    fi
  fi
  sleep 0.2
done
