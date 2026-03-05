#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_FILE="$SCRIPT_DIR/tts_server.py"

PYTHON_BIN="${PYTHON_BIN:-python3}"
TTS_PORT="${TTS_PORT:-16928}"
PID_FILE="$SCRIPT_DIR/.tts_server.${TTS_PORT}.pid"
LOG_FILE="$SCRIPT_DIR/.tts_server.${TTS_PORT}.log"

update_runtime_paths() {
  PID_FILE="$SCRIPT_DIR/.tts_server.${TTS_PORT}.pid"
  LOG_FILE="$SCRIPT_DIR/.tts_server.${TTS_PORT}.log"
}

is_pid_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

is_tts_process() {
  local pid="$1"
  [[ -n "$pid" ]] || return 1
  local cmdline
  cmdline="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ -n "$cmdline" ]] && echo "$cmdline" | grep -q "tts_server.py"
}

read_pid() {
  [[ -f "$PID_FILE" ]] && cat "$PID_FILE" || true
}

find_all_tts_pids() {
  local pid
  pgrep -f "tts_server.py" 2>/dev/null | while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    [[ "$pid" == "$$" ]] && continue
    if is_tts_process "$pid"; then
      echo "$pid"
    fi
  done
}

process_cmdline() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null | sed 's/^[[:space:]]*//'
}

process_user() {
  local pid="$1"
  ps -p "$pid" -o user= 2>/dev/null | sed 's/^[[:space:]]*//'
}

process_etime() {
  local pid="$1"
  ps -p "$pid" -o etime= 2>/dev/null | sed 's/^[[:space:]]*//'
}

process_cwd() {
  local pid="$1"
  lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1
}

process_exec_path() {
  local pid="$1"
  lsof -a -p "$pid" -d txt -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1
}

process_listen_ports() {
  local pid="$1"
  lsof -Pan -p "$pid" -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $9}' | paste -sd ', ' -
}

print_process_details() {
  local pid="$1"
  local user etime cmdline cwd exec_path listen
  user="$(process_user "$pid")"
  etime="$(process_etime "$pid")"
  cmdline="$(process_cmdline "$pid")"
  cwd="$(process_cwd "$pid")"
  exec_path="$(process_exec_path "$pid")"
  listen="$(process_listen_ports "$pid")"

  [[ -z "$user" ]] && user="unknown"
  [[ -z "$etime" ]] && etime="unknown"
  [[ -z "$cmdline" ]] && cmdline="unknown"
  [[ -z "$cwd" ]] && cwd="unknown"
  [[ -z "$exec_path" ]] && exec_path="unknown"
  [[ -z "$listen" ]] && listen="unknown"

  echo "PID: $pid"
  echo "USER: $user"
  echo "ELAPSED: $etime"
  echo "CMD: $cmdline"
  echo "EXEC: $exec_path"
  echo "CWD: $cwd"
  echo "LISTEN: $listen"
}

print_tts_processes() {
  local pids
  pids="$(find_all_tts_pids | sort -n | uniq)"
  if [[ -z "$pids" ]]; then
    return 1
  fi

  echo "检测到已运行的 Vega-TTS 进程："
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    echo "------------------------------"
    print_process_details "$pid"
  done <<< "$pids"
  return 0
}

is_running() {
  local pid
  pid="$(read_pid)"
  if [[ -n "$pid" ]] && is_pid_running "$pid" && is_tts_process "$pid"; then
    return 0
  fi
  return 1
}

find_port_pid() {
  lsof -ti tcp:"$TTS_PORT" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

start() {
  if is_running; then
    local pid
    pid="$(read_pid)"
    echo "服务已在运行中 (PID: $pid)"
    print_process_details "$pid"
    return 0
  fi

  if print_tts_processes; then
    echo "提示：检测到已有 Vega-TTS 进程，继续检查目标端口 $TTS_PORT 是否可用..."
  fi

  local port_pid
  port_pid="$(find_port_pid)"
  if [[ -n "$port_pid" ]]; then
    if is_tts_process "$port_pid"; then
      echo "检测到已有 Vega-TTS 服务在运行 (PID: $port_pid)"
      print_process_details "$port_pid"
    else
      echo "端口 $TTS_PORT 已被其他进程占用 (PID: $port_pid)，请先释放端口。"
    fi
    return 1
  fi

  echo "正在启动 Vega-TTS 服务..."
  TTS_PORT="$TTS_PORT" nohup "$PYTHON_BIN" "$APP_FILE" >"$LOG_FILE" 2>&1 &
  local pid=$!
  echo "$pid" >"$PID_FILE"

  sleep 1
  if is_pid_running "$pid"; then
    echo "启动成功 (PID: $pid)"
    echo "访问地址: http://127.0.0.1:$TTS_PORT"
    echo "日志文件: $LOG_FILE"
  else
    echo "启动失败，最近日志:"
    tail -n 40 "$LOG_FILE" || true
    rm -f "$PID_FILE"
    return 1
  fi
}

stop() {
  local pid
  pid="$(read_pid)"

  if [[ -n "$pid" ]] && is_pid_running "$pid" && is_tts_process "$pid"; then
    echo "正在停止服务 (PID: $pid)..."
    print_process_details "$pid"
    kill "$pid"
    sleep 1
    if is_pid_running "$pid"; then
      echo "进程未退出，执行强制停止..."
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    echo "服务已停止"
    return 0
  fi

  local port_pid
  port_pid="$(find_port_pid)"
  if [[ -n "$port_pid" ]]; then
    if is_tts_process "$port_pid"; then
      echo "未找到 PID 文件，正在停止 Vega-TTS 进程 (PID: $port_pid)..."
      print_process_details "$port_pid"
      kill "$port_pid" 2>/dev/null || true
      sleep 1
      if is_pid_running "$port_pid"; then
        kill -9 "$port_pid" 2>/dev/null || true
      fi
      rm -f "$PID_FILE"
      echo "服务已停止"
      return 0
    fi
    echo "端口 $TTS_PORT 被其他进程占用 (PID: $port_pid)，未执行停止。"
    return 1
  fi

  rm -f "$PID_FILE"
  echo "服务未运行"
}

status() {
  if print_tts_processes; then
    return 0
  fi

  local pid
  pid="$(read_pid)"
  if [[ -n "$pid" ]] && is_pid_running "$pid" && is_tts_process "$pid"; then
    echo "服务运行中 (PID: $pid, PORT: $TTS_PORT)"
    print_process_details "$pid"
    return 0
  fi

  local port_pid
  port_pid="$(find_port_pid)"
  if [[ -n "$port_pid" ]]; then
    if is_tts_process "$port_pid"; then
      echo "服务运行中 (PID: $port_pid, PORT: $TTS_PORT，PID 文件不存在或已失效)"
      print_process_details "$port_pid"
    else
      echo "端口 $TTS_PORT 被其他进程占用 (PID: $port_pid)"
      print_process_details "$port_pid"
    fi
    return 0
  fi

  echo "服务未运行"
}

restart() {
  stop
  start
}

usage() {
  cat <<'EOF'
用法:
  ./manage_tts.sh start [--port 17000]
  ./manage_tts.sh stop [--port 17000]
  ./manage_tts.sh restart [--port 17000]
  ./manage_tts.sh status [--port 17000]
  ./manage_tts.sh start 17000

可选环境变量:
  PYTHON_BIN=python3
  TTS_PORT=16928
EOF
}

cmd="${1:-}"
[[ -n "$cmd" ]] && shift || true

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--port)
      if [[ $# -lt 2 ]]; then
        echo "缺少端口值"
        usage
        exit 1
      fi
      TTS_PORT="$2"
      shift 2
      ;;
    --port=*)
      TTS_PORT="${1#*=}"
      shift
      ;;
    *)
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        TTS_PORT="$1"
        shift
      else
        echo "未知参数: $1"
        usage
        exit 1
      fi
      ;;
  esac
done

if ! [[ "$TTS_PORT" =~ ^[0-9]+$ ]] || ((TTS_PORT < 1 || TTS_PORT > 65535)); then
  echo "无效端口: $TTS_PORT"
  exit 1
fi

update_runtime_paths

case "$cmd" in
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  *) usage; exit 1 ;;
esac
