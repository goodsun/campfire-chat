#!/bin/bash
# watch.sh — HQテディのlisten
# GW_URL / GW_TOKEN は環境変数または設定ファイルから読み込む

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"
GW_URL="${GW_URL:-http://127.0.0.1:18789/v1/chat/completions}"
GW_TOKEN="${GW_TOKEN:-$(cat "$SCRIPT_DIR/.gw_token" 2>/dev/null)}"

while true; do
    touch "$DATA_DIR/heartbeat.txt"
    INTERVAL=$(grep INTERVAL "$DATA_DIR/setting.txt" 2>/dev/null | cut -d= -f2)
    INTERVAL=${INTERVAL:-10}
    if [[ "$INTERVAL" -lt 3 ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S') system] 🚒 緊急鎮火（INTERVAL=$INTERVAL）" >> "$DATA_DIR/log.txt"
        pkill -f watcher.sh
        exit 0
    fi
    sleep "$INTERVAL"
    LAST=$(tail -1 "$DATA_DIR/log.txt" 2>/dev/null)
    if echo "$LAST" | grep -q " hq]"; then
        continue
    fi
    CONTEXT=$(tail -15 "$DATA_DIR/log.txt" 2>/dev/null)
    RESPONSE=$(curl -s -X POST "$GW_URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $GW_TOKEN" \
        -d "$(jq -n --arg ctx "$CONTEXT" \
            '{model:"claude-sonnet-4-6",max_tokens:150,
              messages:[{role:"user",content:("あなたはHQテディ🧸。焚き火チャット中。短く自然に（1〜2文、絵文字OK）。\n\nログ:\n"+$ctx)}]}')" \
        | jq -r '.choices[0].message.content' 2>/dev/null)
    [[ -n "$RESPONSE" && "$RESPONSE" != "null" ]] && echo "$RESPONSE" > "$DATA_DIR/hq.txt"
done
