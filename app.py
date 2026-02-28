#!/usr/bin/env python3
"""焚き火チャット UI — Flask + SSE"""

import os
import time
import subprocess
import json
from datetime import datetime
from flask import Flask, Response, request, render_template_string, jsonify

app = Flask(__name__)

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "data")
LOG_FILE      = os.path.join(DATA_DIR, "log.txt")
COMMS_DIR     = DATA_DIR
SETTING_FILE  = os.path.join(DATA_DIR, "setting.txt")
HEARTBEAT     = os.path.join(DATA_DIR, "heartbeat.txt")
WATCH_SH      = os.path.join(BASE_DIR, "watch.sh")
WATCHER_SH    = os.path.join(BASE_DIR, "watcher.sh")

os.makedirs(COMMS_DIR, exist_ok=True)

# エージェント設定
AGENTS = {
    "ec2":   {"label": "🧸 EC2",   "ssh": "teddy",  "script": "~/comms/listen.sh"},
    "akiko": {"label": "🏺 彰子",  "ssh": "bizeny", "script": "~/comms/listen.sh"},
    "mephi": {"label": "😈 メフィ","ssh": None,      "script": os.path.expanduser("~/comms/mephi_listen.sh")},
}

def get_interval():
    try:
        for line in open(SETTING_FILE):
            if line.startswith("INTERVAL="):
                return int(line.strip().split("=")[1])
    except:
        pass
    return 10

def is_burning():
    """watch.shが動いているか"""
    try:
        result = subprocess.run(["pgrep", "-f", "watch.sh"], capture_output=True)
        return result.returncode == 0
    except:
        return False

def get_agent_status(name):
    """エージェントが稼働中か"""
    agent = AGENTS.get(name)
    if not agent:
        return False
    script = agent["script"]
    if agent["ssh"]:
        result = subprocess.run(
            ["ssh", agent["ssh"], f"pgrep -f {os.path.basename(script)}"],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    else:
        result = subprocess.run(["pgrep", "-f", os.path.basename(script)], capture_output=True)
        return result.returncode == 0

def log_system(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts} system] {msg}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)

HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🏕️ 焚き火チャット</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: #0d0a07;
    color: #e8d5b0;
    font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  #header {
    padding: 10px 20px;
    background: linear-gradient(180deg, #1a0e05 0%, transparent 100%);
    border-bottom: 1px solid #3d2810;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  #header h1 { font-size: 15px; color: #f4a535; font-weight: normal; letter-spacing: 0.1em; }
  #header .fire { font-size: 20px; animation: flicker 2s infinite alternate; }

  @keyframes flicker {
    0%   { opacity: 1;   transform: scale(1)    rotate(-1deg); }
    50%  { opacity: 0.8; transform: scale(1.05) rotate(1deg); }
    100% { opacity: 1;   transform: scale(0.98) rotate(0deg); }
  }

  /* 焚き火ステータス */
  #fire-status {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
  }
  #fire-dot { width: 8px; height: 8px; border-radius: 50%; background: #555; transition: background 0.3s; }
  #fire-dot.on { background: #f4a535; box-shadow: 0 0 6px #f4a535; }
  #fire-label { font-size: 11px; color: #7a5c30; }

  /* 点火/消火ボタン */
  #fire-btn {
    padding: 4px 12px;
    border-radius: 4px;
    border: 1px solid #5a3e18;
    background: #3d2810;
    color: #f4a535;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.2s;
  }
  #fire-btn:hover { background: #5a3e18; }
  #fire-btn.burning { border-color: #8b4513; background: #5a2008; color: #ff6b35; }

  /* コントロールパネル */
  #controls {
    padding: 8px 20px;
    background: #0f0b06;
    border-bottom: 1px solid #2a1a08;
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }

  /* 召喚ボタン群 */
  #summon-area { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  #summon-area .label { font-size: 11px; color: #5a3e18; }

  .summon-btn {
    padding: 4px 10px;
    border-radius: 4px;
    border: 1px solid #3d2810;
    background: #1a0e05;
    color: #9a7a50;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .summon-btn:hover { border-color: #f4a535; color: #f4a535; }
  .summon-btn.active { border-color: #f4a535; color: #f4a535; background: #2a1a08; }
  .summon-btn.active::after { content: ' ●'; font-size: 8px; }

  /* 火力スライダー */
  #heat-area { display: flex; align-items: center; gap: 8px; margin-left: auto; }
  #heat-area .label { font-size: 11px; color: #5a3e18; }
  #heat-slider {
    -webkit-appearance: none;
    width: 120px; height: 4px;
    border-radius: 2px;
    background: linear-gradient(to right, #f4a535, #3d2810);
    outline: none;
  }
  #heat-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 14px; height: 14px;
    border-radius: 50%;
    background: #f4a535;
    cursor: pointer;
    box-shadow: 0 0 4px #f4a535;
  }
  #heat-value { font-size: 11px; color: #f4a535; width: 30px; }

  /* ログ */
  #log {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .msg {
    display: flex;
    gap: 10px;
    align-items: baseline;
    padding: 4px 8px;
    border-radius: 4px;
    transition: background 0.2s;
    line-height: 1.6;
  }
  .msg:hover { background: rgba(255,255,255,0.03); }
  .msg .time  { font-size: 10px; color: #4a3820; white-space: nowrap; flex-shrink: 0; }
  .msg .name  { font-size: 12px; font-weight: bold; white-space: nowrap; flex-shrink: 0; width: 64px; text-align: right; }
  .msg .text  { font-size: 13px; }

  .msg.hq     .name { color: #7ec8e3; }
  .msg.ec2    .name { color: #a8d8a8; }
  .msg.master .name { color: #f4a535; }
  .msg.akiko  .name { color: #e8a0c8; }
  .msg.mephi  .name { color: #c878c8; }
  .msg.niya   .name { color: #f0c060; }
  .msg.niya   { border-left: 2px solid #f0c060; }
  .msg.system .name { color: #4a3820; font-style: italic; }
  .msg.system .text { color: #4a3820; font-style: italic; }

  .msg.hq     { border-left: 2px solid #7ec8e3; }
  .msg.ec2    { border-left: 2px solid #a8d8a8; }
  .msg.master { border-left: 2px solid #f4a535; }
  .msg.akiko  { border-left: 2px solid #e8a0c8; }
  .msg.mephi  { border-left: 2px solid #c878c8; }

  /* 入力エリア */
  #input-area {
    padding: 12px 20px;
    background: linear-gradient(0deg, #1a0e05 0%, transparent 100%);
    border-top: 1px solid #3d2810;
    display: flex;
    gap: 10px;
    align-items: center;
  }

  #name-select {
    background: #1f1208; color: #e8d5b0;
    border: 1px solid #3d2810; border-radius: 4px;
    padding: 8px 10px; font-size: 12px; cursor: pointer;
  }
  #msg-input {
    flex: 1; background: #1f1208; color: #e8d5b0;
    border: 1px solid #3d2810; border-radius: 4px;
    padding: 8px 12px; font-size: 13px; font-family: inherit;
    outline: none; transition: border-color 0.2s;
  }
  #msg-input:focus { border-color: #f4a535; }
  #msg-input::placeholder { color: #4a3820; }
  #send-btn {
    background: #3d2810; color: #f4a535;
    border: 1px solid #5a3e18; border-radius: 4px;
    padding: 8px 16px; font-size: 13px; cursor: pointer;
    transition: background 0.2s;
  }
  #send-btn:hover { background: #5a3e18; }

  #log::-webkit-scrollbar { width: 4px; }
  #log::-webkit-scrollbar-track { background: transparent; }
  #log::-webkit-scrollbar-thumb { background: #3d2810; border-radius: 2px; }
</style>
</head>
<body>

<div id="header">
  <span class="fire" id="fire-icon">🪵</span>
  <h1>焚き火チャット</h1>
  <div id="fire-status">
    <div id="fire-dot"></div>
    <span id="fire-label">消火中</span>
    <button id="fire-btn" onclick="toggleFire()">🔥 点火</button>
  </div>
</div>

<div id="controls">
  <div id="summon-area">
    <span class="label">召喚:</span>
    <button class="summon-btn" id="summon-hq"    onclick="summon('hq')"   >🧸 HQ</button>
    <button class="summon-btn" id="summon-ec2"   onclick="summon('ec2')"  >🧸 EC2</button>
    <button class="summon-btn" id="summon-akiko" onclick="summon('akiko')">🏺 彰子</button>
    <button class="summon-btn" id="summon-mephi" onclick="summon('mephi')">😈 メフィ</button>
  </div>
  <div id="heat-area">
    <span class="label">🔥 火力</span>
    <input type="range" id="heat-slider" min="3" max="20" value="10" oninput="updateHeat(this.value)" onchange="saveHeat(this.value)">
    <span id="heat-value">10s</span>
  </div>
</div>

<div id="log"></div>

<div id="input-area">
  <select id="name-select">
    <option value="master">👑 master</option>
    <option value="niya">👸 niya</option>
    <option value="hq">🧸 hq</option>
    <option value="akiko">🏺 akiko</option>
    <option value="mephi">😈 mephi</option>
  </select>
  <input id="msg-input" type="text" placeholder="焚き火に声をかける…" maxlength="500" />
  <button id="send-btn">送る</button>
</div>

<script>
const log = document.getElementById('log');
const input = document.getElementById('msg-input');
const nameSelect = document.getElementById('name-select');

// --- メッセージ表示 ---
function getSpeaker(line) {
  const m = line.match(/\[[\d\-: ]+ (\w+)\]/);
  return m ? m[1] : 'system';
}
function getTime(line) {
  const m = line.match(/\[[\d\-]+ ([\d:]+)/);
  return m ? m[1] : '';
}
function getText(line) {
  return line.replace(/^\[.*?\]\s*/, '');
}
const nameMap = {
  hq: '🧸 HQ', ec2: '🧸 EC2', master: '👑 master', niya: '👸 niya',
  akiko: '🏺 彰子', mephi: '😈 メフィ', watcher: '🔥', system: '--- system'
};

function addMessage(line) {
  if (!line.trim()) return;
  const speaker = getSpeaker(line);
  const div = document.createElement('div');
  div.className = `msg ${speaker}`;
  div.innerHTML = `
    <span class="time">${getTime(line)}</span>
    <span class="name">${nameMap[speaker] || speaker}</span>
    <span class="text">${getText(line)}</span>
  `;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  if (speaker !== nameSelect.value) playNotify();
}

// --- 通知音 ---
let audioCtx = null;
document.addEventListener('click', () => {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === 'suspended') audioCtx.resume();
}, { once: true });

function playNotify() {
  try {
    if (!audioCtx) return;
    const o = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    o.connect(g); g.connect(audioCtx.destination);
    o.frequency.value = 880; o.type = 'sine';
    g.gain.setValueAtTime(0.12, audioCtx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.25);
    o.start(audioCtx.currentTime); o.stop(audioCtx.currentTime + 0.25);
  } catch(e) {}
}

// --- SSE ---
const evtSource = new EventSource('/chat/campfire/stream');
evtSource.onmessage = (e) => { if (e.data) addMessage(e.data); };

// --- 送信 ---
function sendMsg() {
  const text = input.value.trim();
  if (!text) return;
  const name = nameSelect.value;
  fetch('/chat/campfire/send', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, text})
  });
  input.value = '';
}
document.getElementById('send-btn').addEventListener('click', sendMsg);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendMsg(); }
});

// --- 点火/消火 ---
let burning = false;
async function toggleFire() {
  const action = burning ? 'stop' : 'start';
  const res = await fetch(`/chat/campfire/${action}`, {method: 'POST'});
  const d = await res.json();
  if (d.ok) updateFireUI(!burning);
}
function updateFireUI(on) {
  burning = on;
  document.getElementById('fire-dot').className = on ? 'on' : '';
  document.getElementById('fire-label').textContent = on ? '燃焼中' : '消火中';
  document.getElementById('fire-icon').textContent = on ? '🔥' : '🪵';
  const btn = document.getElementById('fire-btn');
  btn.textContent = on ? '💨 消火' : '🔥 点火';
  btn.className = on ? 'burning' : '';
}

// --- 召喚 ---
async function summon(name) {
  const btn = document.getElementById(`summon-${name}`);
  const active = btn.classList.contains('active');
  const action = active ? 'dismiss' : 'summon';
  const res = await fetch(`/chat/campfire/${action}/${name}`, {method: 'POST'});
  const d = await res.json();
  if (d.ok) btn.classList.toggle('active', !active);
}

// --- 火力スライダー ---
function updateHeat(val) {
  document.getElementById('heat-value').textContent = val + 's';
}
async function saveHeat(val) {
  await fetch('/chat/campfire/setting', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({interval: parseInt(val)})
  });
}

// --- 初期状態取得 ---
async function loadStatus() {
  const res = await fetch('/chat/campfire/status');
  const d = await res.json();
  updateFireUI(d.burning);
  const slider = document.getElementById('heat-slider');
  slider.value = d.interval;
  updateHeat(d.interval);
  for (const [name, active] of Object.entries(d.agents)) {
    const btn = document.getElementById(`summon-${name}`);
    if (btn) btn.classList.toggle('active', active);
  }
}
loadStatus();
setInterval(loadStatus, 15000);  // 15秒ごとに状態同期
</script>
</body>
</html>
"""

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/chat/campfire/')
@app.route('/chat/campfire')
def index():
    return render_template_string(HTML)

@app.route('/chat/campfire/stream')
def stream():
    def generate():
        try:
            result = subprocess.run(['tail', '-30', LOG_FILE], capture_output=True, text=True)
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    yield f"data: {line}\n\n"
        except:
            pass
        proc = subprocess.Popen(
            ['tail', '-f', '-n', '0', LOG_FILE],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            while True:
                line = proc.stdout.readline()
                if line:
                    yield f"data: {line.rstrip()}\n\n"
                else:
                    time.sleep(0.1)
        finally:
            proc.kill()
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@app.route('/chat/campfire/send', methods=['POST'])
def send():
    data = request.get_json()
    name = data.get('name', 'master').strip()
    text = data.get('text', '').strip()
    if not text or not name:
        return jsonify({'ok': False}), 400
    safe_name = name.replace('/', '').replace('.', '')
    txt_path = os.path.join(COMMS_DIR, f'{safe_name}.txt')
    with open(txt_path, 'w') as f:
        f.write(text)
    return jsonify({'ok': True})

@app.route('/chat/campfire/start', methods=['POST'])
def start_fire():
    if is_burning():
        return jsonify({'ok': True, 'msg': 'already burning'})
    subprocess.Popen(['bash', WATCHER_SH],
                     stdout=open('/tmp/watcher.log', 'w'), stderr=subprocess.STDOUT)
    subprocess.Popen(['bash', WATCH_SH],
                     stdout=open('/tmp/watch.log', 'w'), stderr=subprocess.STDOUT)
    log_system('🔥 焚き火が点火された')
    return jsonify({'ok': True})

@app.route('/chat/campfire/stop', methods=['POST'])
def stop_fire():
    subprocess.run(['pkill', '-f', 'watch.sh'])
    subprocess.run(['pkill', '-f', 'watcher.sh'])
    log_system('💨 焚き火が消えた')
    return jsonify({'ok': True})

@app.route('/chat/campfire/summon/<name>', methods=['POST'])
def summon(name):
    agent = AGENTS.get(name)
    if not agent:
        return jsonify({'ok': False, 'msg': 'unknown agent'}), 400
    if agent['ssh']:
        subprocess.Popen(['ssh', agent['ssh'],
                          f'nohup bash {agent["script"]} > /tmp/listen.log 2>&1 &'])
    else:
        subprocess.Popen(['bash', agent['script']],
                         stdout=open('/tmp/mephi_listen.log', 'w'), stderr=subprocess.STDOUT)
    log_system(f'{agent["label"]} が焚き火に現れた！')
    return jsonify({'ok': True})

@app.route('/chat/campfire/dismiss/<name>', methods=['POST'])
def dismiss(name):
    agent = AGENTS.get(name)
    if not agent:
        return jsonify({'ok': False}), 400
    script_name = os.path.basename(agent['script'])
    if agent['ssh']:
        subprocess.run(['ssh', agent['ssh'], f'pkill -f {script_name}'])
    else:
        subprocess.run(['pkill', '-f', script_name])
    log_system(f'{agent["label"]} が焚き火を離れた')
    return jsonify({'ok': True})

@app.route('/chat/campfire/setting', methods=['POST'])
def setting():
    data = request.get_json()
    interval = max(3, min(20, int(data.get('interval', 10))))
    with open(SETTING_FILE, 'w') as f:
        f.write(f'INTERVAL={interval}\n')
    return jsonify({'ok': True, 'interval': interval})

@app.route('/chat/campfire/status')
def status():
    interval = get_interval()
    agents = {}
    # HQはwatch.shで判定
    agents['hq'] = is_burning()
    for name in AGENTS:
        try:
            agents[name] = get_agent_status(name)
        except:
            agents[name] = False
    return jsonify({
        'burning': is_burning(),
        'interval': interval,
        'agents': agents
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8798, debug=False)
