#!/bin/bash
# campfire_ssh.sh — SSH forced command ラッパー
# authorized_keysのforced commandとして設定する
# 許可するコマンドのみ実行、それ以外は拒否

DATA_DIR="$(cd "$(dirname "$0")/data" && pwd)"

case "$SSH_ORIGINAL_COMMAND" in
    "read_last")
        tail -1 "$DATA_DIR/log.txt"
        ;;
    "read_context")
        tail -15 "$DATA_DIR/log.txt"
        ;;
    "check_heartbeat")
        find "$DATA_DIR/heartbeat.txt" -mmin +0.5 2>/dev/null | wc -l
        ;;
    "read_interval")
        grep INTERVAL "$DATA_DIR/setting.txt" 2>/dev/null | cut -d= -f2
        ;;
    write_*)
        NAME="${SSH_ORIGINAL_COMMAND#write_}"
        # 名前のバリデーション（英数字のみ）
        if [[ "$NAME" =~ ^[a-zA-Z0-9]+$ ]]; then
            cat > "$DATA_DIR/${NAME}.txt"
        else
            echo "denied: invalid name" >&2
            exit 1
        fi
        ;;
    *)
        echo "denied: unknown command" >&2
        exit 1
        ;;
esac
