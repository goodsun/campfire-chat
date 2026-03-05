#!/usr/bin/env python3
"""
焚き火チャット - シンプルWebUI
ログ表示 + 投稿 + 火力調整のみ
"""
from flask import Flask, request, Response, jsonify
import time
from datetime import datetime
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, 'fire.log')
SETTING_FILE = os.path.join(BASE_DIR, 'setting.txt')
BURNING_FILE = os.path.join(BASE_DIR, 'burning.txt')

LOG_THRESHOLD = 1000  # これを超えたらトリム
LOG_KEEP = 500        # 後半何行を残すか

def trim_log_if_needed():
    """ログが LOG_THRESHOLD 行を超えたら後半 LOG_KEEP 行だけ残す"""
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
        if len(lines) > LOG_THRESHOLD:
            with open(LOG_FILE, 'w') as f:
                f.writelines(lines[-LOG_KEEP:])
    except Exception:
        pass

HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🔥 焚き火チャット</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: monospace; background: #1a1a1a; color: #f0f0f0; padding: 20px; }
    h1 { color: #ff6b35; margin-bottom: 20px; }
    #log { background: #2a2a2a; padding: 15px; height: 60vh; overflow-y: auto; 
           border: 1px solid #444; margin-bottom: 20px; font-family: monospace; line-height: 1.6; }
    .log-line { margin-bottom: 4px; }
    .log-time { color: #888; }
    .log-name { font-weight: bold; }
    .log-msg { opacity: 0.8; }
    .msg-master { color: #ff00ff; }
    .msg-alice { color: #7ec8e3; }
    .msg-akiko { color: #90ee90; }
    .msg-teddy { color: #ffa500; }
    .msg-mephi { color: #da70d6; }
    .msg-system { color: #888; font-style: italic; }
    .msg-flow { color: #90ee90; }
    .controls { display: flex; gap: 10px; margin-bottom: 20px; align-items: center; }
    input[type="text"] { padding: 10px; background: #2a2a2a; border: 1px solid #444; color: #f0f0f0; }
    #name { width: 120px; flex-shrink: 0; }
    #msg { flex: 1; }
    button { padding: 10px 20px; background: #ff6b35; border: none; color: white; cursor: pointer; }
    button:hover { background: #ff8555; }
    .fire-buttons { display: flex; gap: 10px; margin-bottom: 20px; }
    .fire-btn { padding: 12px 24px; font-size: 1.1em; border: none; cursor: pointer; color: white; }
    .fire-btn.on { background: #ff6b35; }
    .fire-btn.off { background: #666; }
    .fire-control { display: flex; align-items: center; gap: 10px; }
    input[type="range"] { flex: 1; }
  </style>
</head>
<body>
  <h1>🔥 焚き火チャット</h1>
  <div class="fire-buttons">
    <button class="fire-btn on" onclick="ignite()">🔥 点火</button>
    <button class="fire-btn off" onclick="extinguish()">💨 消火</button>
  </div>
  <div id="log"></div>
  <div class="controls">
    <input type="text" id="name" placeholder="名前" value="master">
    <input type="text" id="msg" placeholder="メッセージ">
    <button onclick="send()">送信</button>
  </div>
  <div class="fire-control">
    <label>🔥 火力:</label>
    <input type="range" id="interval" min="3" max="20" value="10" oninput="updateInterval()">
    <span id="intervalValue">10</span>秒
  </div>
  <script>
    const log = document.getElementById('log');
    const msgInput = document.getElementById('msg');
    
    // ログ行をパースして整形
    function formatLogLine(line) {
      // [2026-03-05 12:34:56] [name] message 形式
      const match = line.match(/^\[([^\]]+)\] \[([^\]]+)\] (.*)$/);
      if (!match) return line;
      
      const [, timestamp, name, message] = match;
      
      // UTC → JST変換（表示用）
      const utcDate = new Date(timestamp.replace(' ', 'T') + 'Z');
      const jstTime = utcDate.toLocaleTimeString('ja-JP', { 
        timeZone: 'Asia/Tokyo', 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
      });
      
      const className = 'msg-' + name.toLowerCase();
      return `<div class="log-line ${className}">` +
             `<span class="log-time">[${jstTime}]</span> ` +
             `<span class="log-name">[${name}]</span> ` +
             `<span class="log-msg">${message}</span>` +
             `</div>`;
    }
    
    // SSEでログをリアルタイム表示
    const es = new EventSource('./stream');
    es.onmessage = (e) => {
      log.innerHTML += formatLogLine(e.data);
      log.scrollTop = log.scrollHeight;
    };
    
    // メッセージ送信
    function send() {
      const name = document.getElementById('name').value || 'master';
      const msg = msgInput.value.trim();
      if (!msg) return;
      fetch('./send', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, message: msg})
      });
      msgInput.value = '';
    }
    
    // Enter送信
    msgInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') send();
    });
    
    // 火力調整
    function updateInterval() {
      const val = document.getElementById('interval').value;
      document.getElementById('intervalValue').textContent = val;
      fetch('./setting', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({interval: val})
      });
    }
    
    // 点火
    function ignite() {
      fetch('./ignite', {method: 'POST'});
    }
    
    // 消火
    function extinguish() {
      fetch('./extinguish', {method: 'POST'});
    }
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML

@app.route('/stream')
def stream():
    def generate():
        with open(LOG_FILE, 'r') as f:
            # 既存ログを送信
            for line in f:
                yield f"data: {line.rstrip()}\n\n"
            # 新規行を監視
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.rstrip()}\n\n"
                else:
                    time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')

@app.route('/send', methods=['POST'])
def send():
    data = request.json
    name = data.get('name', 'master')
    message = data.get('message', '')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] [{name}] {message}\n")
    trim_log_if_needed()
    return jsonify({'ok': True})

@app.route('/setting', methods=['POST'])
def setting():
    data = request.json
    interval = data.get('interval', 10)
    with open(SETTING_FILE, 'w') as f:
        f.write(f"INTERVAL={interval}\n")
    return jsonify({'ok': True})

@app.route('/ignite', methods=['POST'])
def ignite():
    with open(BURNING_FILE, 'w') as f:
        f.write('1\n')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] [system] 🔥 焚き火が点火された\n")
    trim_log_if_needed()
    return jsonify({'ok': True})

@app.route('/extinguish', methods=['POST'])
def extinguish():
    with open(BURNING_FILE, 'w') as f:
        f.write('0\n')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] [system] 💨 焚き火が消えた\n")
    trim_log_if_needed()
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8796, debug=False)
