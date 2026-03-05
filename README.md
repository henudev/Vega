# Vega-TTS 文本转语音服务

Vega-TTS 是一个基于 `Flask + edge-tts` 的中文文本转语音服务，提供：

- Web 页面交互使用
- HTTP API 调用
- 一键启动 / 停止 / 重启 / 状态查看脚本
- 生成文件列表、试听、下载
- 页面按钮直接“打开文件位置”（打开输出目录或定位到具体音频文件）

## 1. 功能概览

- 文本转语音（支持中文声音、语速、音调）
- 音频文件默认保存到本地目录
- `manage_tts.sh` 脚本支持自定义端口
- 状态检测可显示 TTS 进程详情（PID、命令、执行文件、工作目录、监听端口）
- 页面可查看历史生成文件并直接操作

## 2. 目录结构

```text
Vega/
├── tts_server.py      # Flask 服务（页面 + API）
├── manage_tts.sh      # 一键管理脚本
├── test_tts.py        # 示例测试脚本（并发生成示例音频）
├── requirements.txt   # Python 依赖
└── README.md
```

## 3. 环境要求

- macOS / Linux / Windows（已做打开文件管理器的系统兼容）
- Python 3.9 及以上（建议 3.10+）
- 可访问互联网（`edge-tts` 生成语音时需要网络）

## 4. 安装依赖

建议使用虚拟环境：

```bash
cd /Users/shu/github/Vega
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 5. 一键管理脚本用法

脚本文件：`/Users/shu/github/Vega/manage_tts.sh`

### 5.1 基本命令

```bash
./manage_tts.sh start
./manage_tts.sh stop
./manage_tts.sh restart
./manage_tts.sh status
```

### 5.2 指定端口启动

支持两种写法：

```bash
./manage_tts.sh start --port 16931
./manage_tts.sh start 16931
```

`stop/restart/status` 同样支持 `--port` 或位置参数端口。

### 5.3 常用环境变量

- `PYTHON_BIN`：指定解释器路径
- `TTS_PORT`：默认端口（未传参数时使用）
- `OUTPUT_DIR`：音频输出目录

示例：

```bash
PYTHON_BIN=./.venv/bin/python OUTPUT_DIR="$PWD" ./manage_tts.sh start --port 16931
```

### 5.4 PID 和日志文件

脚本按端口区分 PID/日志：

- PID：`.tts_server.<port>.pid`
- 日志：`.tts_server.<port>.log`

### 5.5 推荐启动方式（本机与局域网访问）

推荐使用项目虚拟环境并指定输出目录到当前项目目录：

```bash
cd /Users/shu/github/Vega
PYTHON_BIN="$PWD/.venv/bin/python" OUTPUT_DIR="$PWD" ./manage_tts.sh start --port 16931
```

停止服务：

```bash
cd /Users/shu/github/Vega
PYTHON_BIN="$PWD/.venv/bin/python" ./manage_tts.sh stop --port 16931
```

启动后可访问：

- 本机：`http://127.0.0.1:16931/`
- Host IP（示例）：`http://10.14.56.138:16931/`

快速验证：

```bash
curl -I http://127.0.0.1:16931/
curl http://127.0.0.1:16931/health
```

## 6. Web 页面使用

服务启动后访问：

- `http://127.0.0.1:16928`（或你指定的端口）

页面功能：

- 输入文本并选择声音生成语音
- 设置语速（如 `+0%`）和音调（如 `+0Hz`）
- 播放刚生成的音频
- 下载音频
- 打开输出目录
- 在历史列表中打开某个文件位置

## 7. API 说明

### 7.1 健康检查

```bash
curl http://127.0.0.1:16928/health
```

### 7.2 获取可用声音

```bash
curl http://127.0.0.1:16928/voices
```

### 7.3 文本转语音

```bash
curl -X POST http://127.0.0.1:16928/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"hello 马德里","voice":"zh-CN-XiaoxiaoNeural","rate":"+0%","pitch":"+0Hz"}'
```

返回示例：

```json
{
  "success": true,
  "file": "d9e66f3e.mp3",
  "path": "/Users/shu/github/Vega/d9e66f3e.mp3",
  "voice": "zh-CN-XiaoxiaoNeural",
  "text": "hello 马德里",
  "size": 10800
}
```

### 7.4 下载音频

```bash
curl -O http://127.0.0.1:16928/audio/d9e66f3e.mp3
```

### 7.5 列出文件

```bash
curl http://127.0.0.1:16928/list
```

### 7.6 打开文件位置（目录或具体文件）

打开输出目录：

```bash
curl -X POST http://127.0.0.1:16928/open-location \
  -H "Content-Type: application/json" \
  -d '{}'
```

定位到某个文件：

```bash
curl -X POST http://127.0.0.1:16928/open-location \
  -H "Content-Type: application/json" \
  -d '{"filename":"d9e66f3e.mp3"}'
```

## 8. 输出目录说明

- 默认输出目录：`/Users/shu/Desktop/Vega-TTS-output`
- 可通过 `OUTPUT_DIR` 覆盖为任意目录（例如当前目录）

示例：

```bash
OUTPUT_DIR="$PWD" ./manage_tts.sh start --port 16931
```

## 9. 故障排查

- `ModuleNotFoundError: No module named edge_tts`
  - 执行 `pip install -r requirements.txt`
- 端口被占用
  - 换端口启动：`./manage_tts.sh start --port 17000`
- 启动失败看日志
  - 查看 `.tts_server.<port>.log`
- 无法生成语音
  - 检查网络连通性（`edge-tts` 依赖在线服务）

## 10. 开发与测试建议

- 语法检查：

```bash
python3 -m py_compile tts_server.py
bash -n manage_tts.sh
```

- 快速回归（生成一条音频）：

```bash
curl -X POST http://127.0.0.1:16928/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"hello 马德里"}'
```
