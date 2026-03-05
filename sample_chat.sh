#!/bin/bash
# chat.sh - 自律応答スクリプト

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/fire.log"
SETTING_FILE="$SCRIPT_DIR/setting.txt"
MY_NAME="alice"

# OpenClaw Gateway設定
GW_URL="http://127.0.0.1:18789/v1/chat/completions"
GW_TOKEN="your_token_here"

while true; do
    # 消火チェック
    BURNING=$(cat "$SCRIPT_DIR/burning.txt" 2>/dev/null | tr -d '\n')
    if [ "$BURNING" != "1" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Alice退場（消火検知）" >> /tmp/alice.log
        exit 0
    fi

    # 火力値を取得
    INTERVAL=$(grep INTERVAL "$SETTING_FILE" 2>/dev/null | cut -d= -f2)
    INTERVAL=${INTERVAL:-10}

    # 次回まで待つ
    sleep "$INTERVAL"

    # 最後の発言者チェック
    LAST=$(tail -1 "$LOG_FILE" 2>/dev/null)
    if echo "$LAST" | grep -q "\[$MY_NAME\]"; then
        continue
    fi

    # コンテキスト取得（最新15行）
    CONTEXT=$(tail -15 "$LOG_FILE" 2>/dev/null)

    # 応答生成（--argでシングルクォート等の特殊文字を安全に渡す）
    SYSTEM_PROMPT="あなたはEC2 Alice🐇。焚き火チャット中。短く自然に応答（1〜2文、絵文字OK）。"
    PAYLOAD=$(jq -n \
        --arg sys "$SYSTEM_PROMPT" \
        --arg ctx "$CONTEXT" \
        '{model:"claude-sonnet-4-6",max_tokens:200,messages:[{role:"user",content:($sys + "\n\nログ:\n" + $ctx)}]}')

    RESPONSE=$(curl -s -X POST "$GW_URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $GW_TOKEN" \
        -d "$PAYLOAD" \
        2>/dev/null)

    # 応答抽出
    MSG=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // empty' 2>/dev/null | head -3 | tr '\n' ' ')

    if [ -n "$MSG" ]; then
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$TIMESTAMP] [$MY_NAME] $MSG" >> "$LOG_FILE"
    fi
done
