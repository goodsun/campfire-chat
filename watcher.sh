#!/bin/bash
# watcher.sh — HQ焚き火ウォッチャー

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMMS_DIR="$SCRIPT_DIR/data"
MEMBERS=(master niya hq ec2 akiko mephi)
POLL=1

touch "$COMMS_DIR/log.txt"
echo "[watcher] 焚き火チャット開始 🏕️" >> "$COMMS_DIR/log.txt"

while true; do
    # heartbeatを更新（listen.sh の生存確認用）
    touch "$COMMS_DIR/heartbeat.txt"

    # 火力チェック（INTERVAL < 3 で緊急鎮火）
    INTERVAL=$(grep INTERVAL "$COMMS_DIR/setting.txt" 2>/dev/null | cut -d= -f2)
    if [[ -n "$INTERVAL" && "$INTERVAL" -lt 3 ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S') system] 🚒 緊急鎮火（INTERVAL=$INTERVAL）" >> "$COMMS_DIR/log.txt"
        pkill -f watch.sh
        exit 0
    fi

    for NAME in "${MEMBERS[@]}"; do
        FILE="$COMMS_DIR/${NAME}.txt"
        if [ -s "$FILE" ]; then
            TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
            CONTENT=$(cat "$FILE")
            echo "[$TIMESTAMP $NAME] $CONTENT" >> "$COMMS_DIR/log.txt"
            > "$FILE"
        fi
    done
    sleep "$POLL"
done
