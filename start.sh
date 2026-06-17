#!/bin/bash
# Deep Research Platform 一键启动脚本
# 使用方法：在 Git Bash 中运行 bash start.sh

PROJECT_DIR="d:/Yuebing/PyCharm/项目3/project-Deep_Research"

echo "=== 启动 Redis ==="
docker start redis 2>/dev/null || echo "Redis 未安装或已启动，跳过"

echo "=== 启动后端 (port 8000) ==="
cd "$PROJECT_DIR"
.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
sleep 5

echo "=== 启动前端 (port 3000) ==="
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
sleep 5

echo ""
echo "==================================="
echo "  后端:  http://127.0.0.1:8000"
echo "  前端:  http://localhost:3000"
echo "  Redis: docker exec redis redis-cli ping"
echo "==================================="
echo ""
echo "按 Ctrl+C 停止前后端（Redis 继续运行）"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '前后端已停止（Redis 仍在运行）'" EXIT
wait
