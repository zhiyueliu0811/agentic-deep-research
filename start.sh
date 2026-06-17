#!/bin/bash
# Deep Research Platform 一键启动脚本
set -e

# 自动检测项目根目录（兼容 Linux / macOS / Windows Git Bash）
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 检测虚拟环境的 Python 路径
if [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
elif [ -f "$PROJECT_DIR/.venv/Scripts/python.exe" ]; then
    PYTHON="$PROJECT_DIR/.venv/Scripts/python.exe"
else
    echo "未找到虚拟环境，请先运行: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "=== 启动 Redis ==="
docker start redis 2>/dev/null || echo "Redis 未启动，如不需要可忽略（config.yml 中 redis.enabled 设为 false）"

echo "=== 启动后端 (port 8000) ==="
cd "$PROJECT_DIR"
"$PYTHON" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
sleep 3

echo "=== 启动前端 (port 3000) ==="
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
sleep 3

echo ""
echo "==================================="
echo "  后端 API: http://127.0.0.1:8000"
echo "  接口文档: http://127.0.0.1:8000/docs"
echo "  前端页面: http://localhost:3000"
echo "==================================="
echo ""
echo "按 Ctrl+C 停止前后端"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '前后端已停止'" EXIT
wait
