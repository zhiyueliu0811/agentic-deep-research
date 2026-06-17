# Deep Research Platform 启动指南

## 前置依赖

- **Docker Desktop**（运行 Redis）
- **Python 3.12+** + venv
- **Node.js 20+**

---

## 启动步骤

### 1. 启动 Redis

```bash
docker start redis
```

验证：`docker exec redis redis-cli ping` → 返回 `PONG`

> 如果 Redis 不可用，把 `config.yml` 中 `redis.enabled` 改为 `false`，后端会自动降级为内存模式。

### 2. 启动后端

```bash
cd ~/project-Deep_Research
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

启动日志中出现 `RedisSaver connected` 表示 Redis 模式，`Using InMemorySaver` 表示降级模式。

### 3. 启动前端

```bash
cd ~/project-Deep_Research/frontend
npm run dev
```

然后浏览器打开 `http://localhost:3000`。

---

## 一键启动

在项目根目录打开 Git Bash：

```bash
docker start redis
bash start.sh
```

按 `Ctrl+C` 停止前后端，Redis 继续运行。

---

## 端口被占用

```bash
netstat -ano | grep ":8000"
taskkill //F //PID <PID>
```

---

## 重新安装依赖

```bash
# 后端
cd ~/project-Deep_Research
.venv/bin/pip install -r requirements.txt

# 前端
cd ~/project-Deep_Research/frontend
npm install
```

---

## 架构简图

```
浏览器 :3000  ──→  Next.js 前端（SSE + REST）
                        │
                        ├── GET  /api/research/{id}/stream  →  SSE 实时进度
                        ├── POST /api/research/start        →  创建任务
                        ├── POST /api/research/{id}/resume  →  HITL 审查决定
                        ├── GET  /api/research/{id}/report  →  最终报告
                        └── GET  /api/obs/trace/{id}        →  执行轨迹

FastAPI :8000  ──→  LangGraph Agent（5 Agent 协作）
                        │
                        ├── Redis      → Checkpoint 持久化 + 审查决定缓存
                        ├── SQLite     → 任务历史、最终报告
                        ├── ChromaDB   → 历史研究向量记忆
                        └── JSONL      → 执行轨迹 + Token 成本日志
```

