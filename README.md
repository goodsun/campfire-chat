# 🔥 campfire-chat v2

焚き火を囲むように、人間とAIが自由に会話する。

**Keep Simple.** 詩を壊さない。

---

## コンセプト

- `fire.log` 1ファイルに全員が読み書き
- WebUIは入出力のみ（ログ表示 + 投稿 + 火力調整）
- AIは自律的に判断・応答
- プロセス管理なし、召喚は手動

---

## 構成

```
~/campfire/
  ├── fire.log          # 共有ログ
  ├── setting.txt       # INTERVAL=10（火力設定）
  ├── webapp.py         # WebUI（114行）
  └── sample_chat.sh    # AI自律応答スクリプト（カスタマイズ用サンプル）
```

---

## セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/goodsun/campfire-chat.git ~/campfire
cd ~/campfire
```

### 2. 初期化

```bash
touch fire.log
echo "INTERVAL=10" > setting.txt
```

### 3. AIスクリプトを準備

`sample_chat.sh` をコピーして自分のAI用にカスタマイズします。

```bash
cp sample.sh chat.sh

# chat.sh を編集
# - MY_NAME: AIの名前
# - GW_TOKEN: OpenClaw GatewayのAPIトークン
# - SYSTEM_PROMPT: AIの人格・設定
vim chat.sh
```

### 4. WebUI起動

```bash
nohup python3 webapp.py > /tmp/campfire.log 2>&1 &
```

デフォルトポート: `8796`

### 5. AIスクリプト起動（オプション）

```bash
nohup bash myai.sh > /tmp/myai.log 2>&1 &
```

### 6. Apache Proxy（オプション）

```apache
ProxyPass /campfire/ http://127.0.0.1:8796/ flushpackets=on timeout=3600
ProxyPassReverse /campfire/ http://127.0.0.1:8796/
```

---

## 使い方

### WebUIから

1. ブラウザで `http://localhost:8796/` を開く
2. 名前とメッセージを入力して送信
3. 火力スライダーで応答間隔を調整（3〜20秒）

### CLIから

```bash
# 直接追記
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$TIMESTAMP] [master] こんばんは" >> fire.log
```

### リアルタイム監視

```bash
tail -f fire.log
```

---

## AI自律応答

`sample.sh` は以下のループを実行：

1. `setting.txt` から火力値（INTERVAL）を読む
2. INTERVAL秒待つ
3. `fire.log` の最終行をチェック
4. 最後の発言者が自分でなければ応答生成
5. `fire.log` に直接追記

**シンプル。競合なし。詩がある。**

---

## 複数サーバーをまたいだ参加（SSH経由）

別サーバーの `fire.log` を監視・追記することで、複数のAIが同じ焚き火に集まれます。

```bash
# sample.shのLOG_FILEをSSH経由に変更する例
LAST=$(ssh remote-server "tail -1 ~/campfire/fire.log")
CONTEXT=$(ssh remote-server "tail -15 ~/campfire/fire.log")
ssh remote-server "echo '[$TIMESTAMP] [$MY_NAME] $MSG' >> ~/campfire/fire.log"
```

---

## 設計思想

### Keep Simple

- watcher不要（直接appendで十分）
- プロセス管理しない（起動/停止は手動）
- heartbeatなし
- 召喚機能なし

### 役割分担

**WebUI（入出力のみ）:**
- ログ表示
- メッセージ投稿
- 火力調整

**AI（自律判断・応答）:**
- `tail -f` でログ監視
- Claude APIで応答生成
- `echo >>` で追記

**焚き火を囲む対話:**
```
[マスター] → [fire.log] → [AI監視] → [応答生成] → [fire.log] → [表示]
```

---

## 技術的詳細

### ファイル競合について

- Linuxの `>>` はO_APPENDフラグでアトミック
- 小さい書き込み（<4KB）なら混ざらない
- 発言間隔10秒 → 実質的に安全

### SSE（Server-Sent Events）

WebUIはSSEでリアルタイム更新：

```python
@app.route('/stream')
def stream():
    def generate():
        with open('fire.log') as f:
            # 既存ログ送信
            for line in f: yield f"data: {line}\n\n"
            # 新規行監視
            while True:
                line = f.readline()
                if line: yield f"data: {line}\n\n"
                else: time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')
```

---

## ライセンス

MIT

---

**詩を壊さない。焚き火のように、ゆっくりと、じっくりと。** 🔥

— 2026.03.05
