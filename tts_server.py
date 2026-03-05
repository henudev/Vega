#!/usr/bin/env python3
"""
Vega-TTS 文本转语音服务
提供简单的 Web API 接口
"""

import asyncio
import edge_tts
import uuid
import os
import platform
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 配置
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/Users/shu/Desktop/Vega-TTS-output")
OUTPUT_PATH = Path(OUTPUT_DIR).resolve()
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

# 支持的中文声音
CHINESE_VOICES = [
    'zh-CN-XiaoxiaoNeural',  # 女声（温柔）
    'zh-CN-YunyangNeural',   # 男声
    'zh-CN-XiaoyiNeural',    # 女声（活泼）
    'zh-CN-YunjianNeural',   # 男声（专业）
    'zh-CN-XiaohanNeural',   # 女声（成熟）
]

PAGE_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Vega-TTS 文本转语音</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --card: #ffffff;
      --line: #d7deea;
      --text: #1f2430;
      --muted: #5b6475;
      --brand: #1f6feb;
      --ok: #1a7f37;
      --danger: #cf222e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
      background: radial-gradient(circle at top right, #deebff 0, var(--bg) 45%);
      color: var(--text);
    }
    .wrap {
      max-width: 980px;
      margin: 32px auto;
      padding: 0 16px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 16px;
      box-shadow: 0 6px 22px rgba(31, 36, 48, 0.06);
    }
    h1 {
      margin: 0 0 8px;
      font-size: 26px;
    }
    .sub {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    textarea, select, input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      font-size: 14px;
      background: #fff;
      color: var(--text);
    }
    textarea { min-height: 138px; resize: vertical; }
    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 12px;
    }
    button {
      border: 1px solid transparent;
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 14px;
      cursor: pointer;
    }
    .primary { background: var(--brand); color: #fff; }
    .secondary { background: #eef3ff; color: #1d4d99; border-color: #cad8ff; }
    .danger { background: #fff0f0; color: var(--danger); border-color: #ffd0d4; }
    .status {
      margin-top: 10px;
      font-size: 13px;
      color: var(--muted);
      min-height: 20px;
      white-space: pre-wrap;
    }
    .ok { color: var(--ok); }
    .error { color: var(--danger); }
    .result {
      margin-top: 12px;
      border: 1px dashed var(--line);
      border-radius: 10px;
      padding: 12px;
      display: none;
    }
    .result p { margin: 0 0 8px; font-size: 13px; }
    .files {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }
    .file {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      display: grid;
      gap: 8px;
    }
    .file-top {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      font-size: 13px;
      color: var(--muted);
    }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      word-break: break-all;
    }
    @media (max-width: 720px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Vega-TTS 文本转语音</h1>
      <p class="sub">输出目录：<span class="mono">{{ output_dir }}</span></p>
      <div class="actions">
        <button class="secondary" type="button" onclick="openLocation()">打开输出目录</button>
      </div>
    </div>

    <div class="card">
      <div class="grid">
        <div>
          <label for="text">文本</label>
          <textarea id="text" placeholder="请输入要转换的文本"></textarea>
        </div>
        <div>
          <label for="voice">声音</label>
          <select id="voice"></select>
          <div style="height: 8px;"></div>
          <label for="rate">语速</label>
          <input id="rate" value="+0%" />
          <div style="height: 8px;"></div>
          <label for="pitch">音调</label>
          <input id="pitch" value="+0Hz" />
        </div>
      </div>
      <div class="actions">
        <button class="primary" id="generateBtn" type="button">生成语音</button>
      </div>
      <div class="status" id="status"></div>
      <div class="result" id="result">
        <p id="resultPath"></p>
        <audio id="resultAudio" controls style="width:100%;"></audio>
        <div class="actions">
          <button class="secondary" type="button" id="resultLocateBtn">打开文件位置</button>
          <a id="resultDownload" href="#" download><button class="secondary" type="button">下载</button></a>
        </div>
      </div>
    </div>

    <div class="card">
      <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;">
        <strong>历史文件</strong>
        <button class="secondary" type="button" onclick="loadFiles()">刷新列表</button>
      </div>
      <div class="files" id="files"></div>
    </div>
  </div>

  <script>
    const statusEl = document.getElementById('status');
    const filesEl = document.getElementById('files');
    const resultEl = document.getElementById('result');
    const resultPathEl = document.getElementById('resultPath');
    const resultAudioEl = document.getElementById('resultAudio');
    const resultLocateBtn = document.getElementById('resultLocateBtn');
    const resultDownload = document.getElementById('resultDownload');

    function setStatus(message, isError = false) {
      statusEl.textContent = message || '';
      statusEl.className = 'status ' + (message ? (isError ? 'error' : 'ok') : '');
    }

    function escapeHtml(text) {
      return text.replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
      })[ch]);
    }

    async function loadVoices() {
      const res = await fetch('/voices');
      const data = await res.json();
      const select = document.getElementById('voice');
      const voices = data.chinese || [];
      select.innerHTML = voices.map(v => `<option value="${v}">${v}</option>`).join('');
    }

    async function openLocation(filename = null) {
      try {
        const payload = filename ? { filename } : {};
        const res = await fetch('/open-location', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!data.success) {
          throw new Error(data.error || '打开失败');
        }
      } catch (err) {
        setStatus('打开文件位置失败：' + err.message, true);
      }
    }

    function bytesToText(size) {
      if (size < 1024) return `${size} B`;
      if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
      return `${(size / (1024 * 1024)).toFixed(2)} MB`;
    }

    async function loadFiles() {
      try {
        const res = await fetch('/list');
        const data = await res.json();
        if (!data.success) throw new Error(data.error || '获取失败');
        if (!data.files.length) {
          filesEl.innerHTML = '<div class="sub">暂无文件</div>';
          return;
        }
        filesEl.innerHTML = data.files.map(file => {
          const time = new Date(file.created * 1000).toLocaleString();
          return `
            <div class="file">
              <div class="file-top">
                <span class="mono">${escapeHtml(file.name)}</span>
                <span>${time}</span>
              </div>
              <div class="file-top">
                <span>${bytesToText(file.size)}</span>
                <span></span>
              </div>
              <audio controls src="/audio/${encodeURIComponent(file.name)}" style="width:100%;"></audio>
              <div class="actions">
                <button class="secondary" type="button" onclick="openLocation(decodeURIComponent('${encodeURIComponent(file.name)}'))">打开文件位置</button>
                <a href="/audio/${encodeURIComponent(file.name)}" download="${escapeHtml(file.name)}"><button class="secondary" type="button">下载</button></a>
              </div>
            </div>
          `;
        }).join('');
      } catch (err) {
        filesEl.innerHTML = '<div class="error">加载失败：' + escapeHtml(err.message) + '</div>';
      }
    }

    document.getElementById('generateBtn').addEventListener('click', async () => {
      const text = document.getElementById('text').value.trim();
      const voice = document.getElementById('voice').value;
      const rate = document.getElementById('rate').value.trim() || '+0%';
      const pitch = document.getElementById('pitch').value.trim() || '+0Hz';

      if (!text) {
        setStatus('请输入文本', true);
        return;
      }

      setStatus('正在生成，请稍候...');
      resultEl.style.display = 'none';

      try {
        const res = await fetch('/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, voice, rate, pitch })
        });
        const data = await res.json();
        if (!data.success) {
          throw new Error(data.error || '生成失败');
        }

        const audioUrl = '/audio/' + encodeURIComponent(data.file);
        resultPathEl.textContent = '文件：' + data.path;
        resultAudioEl.src = audioUrl;
        resultLocateBtn.onclick = () => openLocation(data.file);
        resultDownload.href = audioUrl;
        resultDownload.download = data.file;
        resultEl.style.display = 'block';
        setStatus('生成成功');
        await loadFiles();
      } catch (err) {
        setStatus('生成失败：' + err.message, true);
      }
    });

    (async () => {
      try {
        await loadVoices();
        await loadFiles();
      } catch (err) {
        setStatus('初始化失败：' + err.message, true);
      }
    })();
  </script>
</body>
</html>
"""


def safe_audio_path(filename):
    """返回输出目录内的安全文件路径"""
    target_path = (OUTPUT_PATH / filename).resolve()
    if OUTPUT_PATH not in target_path.parents:
        return None
    return target_path


def open_in_file_manager(target_path):
    """在系统文件管理器中打开目录或定位文件"""
    system = platform.system()
    if system == 'Darwin':
        cmd = ['open', '-R', str(target_path)] if target_path.is_file() else ['open', str(target_path)]
    elif system == 'Windows':
        cmd = ['explorer', '/select,', str(target_path)] if target_path.is_file() else ['explorer', str(target_path)]
    else:
        browse_path = target_path.parent if target_path.is_file() else target_path
        cmd = ['xdg-open', str(browse_path)]
    subprocess.run(cmd, check=True)

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'service': 'vega-tts',
        'version': '7.2.7'
    })

@app.route('/voices', methods=['GET'])
def get_voices():
    """获取可用声音列表"""
    return jsonify({
        'chinese': CHINESE_VOICES
    })

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """文本转语音"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': '请提供 text 字段'
        }), 400
    
    text = data['text']
    voice = data.get('voice', 'zh-CN-XiaoxiaoNeural')
    rate = data.get('rate', '+0%')  # 语速
    pitch = data.get('pitch', '+0Hz')  # 音调
    
    # 生成文件名
    filename = f"{uuid.uuid4().hex[:8]}.mp3"
    output_path = OUTPUT_PATH / filename
    
    # 异步执行 TTS
    try:
        import traceback
        async def generate_audio():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    with open(output_path, "ab") as f:
                        f.write(chunk["data"])
                elif chunk["type"] == "error":
                    raise Exception(f"TTS Error: {chunk.get('message', 'Unknown error')}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate_audio())
        loop.close()
        
        # 验证文件
        if not output_path.exists() or output_path.stat().st_size == 0:
            return jsonify({
                'success': False,
                'error': '文件生成失败或文件为空'
            }), 500
        
        return jsonify({
            'success': True,
            'file': filename,
            'path': f"{OUTPUT_DIR}/{filename}",
            'voice': voice,
            'text': text,
            'size': output_path.stat().st_size
        })
    except Exception as e:
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f"{type(e).__name__}: {str(e)}"
        }), 500

@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    """获取生成的音频文件"""
    file_path = safe_audio_path(filename)
    if file_path is None:
        return jsonify({
            'success': False,
            'error': '非法文件名'
        }), 400
    
    if not file_path.exists():
        return jsonify({
            'success': False,
            'error': '文件不存在'
        }), 404
    
    return send_file(str(file_path), mimetype='audio/mpeg')

@app.route('/list', methods=['GET'])
def list_files():
    """列出所有生成的音频文件"""
    files = []
    for f in OUTPUT_PATH.glob('*.mp3'):
        files.append({
            'name': f.name,
            'size': f.stat().st_size,
            'created': f.stat().st_ctime
        })
    
    return jsonify({
        'success': True,
        'files': sorted(files, key=lambda x: x['created'], reverse=True)
    })

@app.route('/open-location', methods=['POST'])
def open_location():
    """打开输出目录或文件在系统中的位置"""
    data = request.get_json(silent=True) or {}
    filename = data.get('filename')

    target_path = OUTPUT_PATH
    if filename:
        target_path = safe_audio_path(filename)
        if target_path is None:
            return jsonify({
                'success': False,
                'error': '非法文件名'
            }), 400
        if not target_path.exists():
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404

    try:
        open_in_file_manager(target_path)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'打开失败: {type(e).__name__}: {str(e)}'
        }), 500

    return jsonify({
        'success': True,
        'path': str(target_path)
    })


@app.route('/', methods=['GET'])
def ui_page():
    """Web 页面"""
    return render_template_string(PAGE_HTML, output_dir=OUTPUT_DIR)


@app.route('/api', methods=['GET'])
def api_info():
    """API 说明"""
    return jsonify({
        'service': 'Vega-TTS 文本转语音服务',
        'version': '1.0.0',
        'endpoints': {
            'GET /': 'Web 页面',
            'GET /api': 'API 说明',
            'GET /health': '健康检查',
            'GET /voices': '获取可用声音列表',
            'POST /tts': '文本转语音（需要 JSON: {"text": "...", "voice": "zh-CN-XiaoxiaoNeural"}）',
            'GET /audio/<filename>': '下载音频文件',
            'GET /list': '列出所有音频文件',
            'POST /open-location': '打开输出目录或定位文件（可选 JSON: {"filename":"xxx.mp3"}）'
        },
        'example': {
            "curl": 'curl -X POST http://localhost:16928/tts -H "Content-Type: application/json" -d \'{"text": "你好，世界！"}\''
        }
    })

def run_server(port=None):
    """启动服务器"""
    if port is None:
        port = int(os.getenv('TTS_PORT', '16928'))

    print(f"🚀 Vega-TTS 服务启动")
    print(f"📍 地址: http://localhost:{port}")
    print(f"📂 输出目录: {OUTPUT_DIR}")
    print(f"\n可用声音: {', '.join(CHINESE_VOICES[:3])}...")
    print(f"\n示例命令:")
    print(f'  curl -X POST http://localhost:{port}/tts \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"text": "你好，世界！"}}\'')
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    run_server()
