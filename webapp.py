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
           border: 1px solid #444; margin-bottom: 20px; white-space: pre-wrap; }
    .controls { display: flex; gap: 10px; margin-bottom: 20px; align-items: center; }
    input[type="text"] { flex: 1; padding: 10px; background: #2a2a2a; border: 1px solid #444; color: #f0f0f0; }
    button { padding: 10px 20px; background: #ff6b35; border: none; color: white; cursor: pointer; }
    button:hover { background: #ff8555; }
    .fire-control { display: flex; align-items: center; gap: 10px; }
    input[type="range"] { flex: 1; }
  </style>
</head>
<body>
  <h1>🔥 焚き火チャット</h1>
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
    
    // SSEでログをリアルタイム表示
    const es = new EventSource('/stream');
    es.onmessage = (e) => {
      log.textContent += e.data + '\\n';
      log.scrollTop = log.scrollHeight;
    };
    
    // メッセージ送信
    function send() {
      const name = document.getElementById('name').value || 'master';
      const msg = msgInput.value.trim();
      if (!msg) return;
      fetch('/send', {
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
      fetch('/setting', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({interval: val})
      });
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
    return jsonify({'ok': True})

@app.route('/setting', methods=['POST'])
def setting():
    data = request.json
    interval = data.get('interval', 10)
    with open(SETTING_FILE, 'w') as f:
        f.write(f"INTERVAL={interval}\n")
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8796, debug=False)
