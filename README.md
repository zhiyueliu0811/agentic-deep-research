# Agentic Deep Research Platform 🧠

基于 **LangGraph** 的多智能体深度研究系统，支持自动化网络搜索、报告生成、人工审查（HITL）与事实核查。

## ✨ 功能亮点

- **5 Agent 协作**：Supervisor → Researcher → Writer → Draft → Evaluator 流水线
- **HITL 人工审查**：生成草稿后暂停，人工批准或修改后继续
- **事实核查**：对报告中的关键声明进行网络验证与证据标注
- **SSE 实时进度**：前端通过 Server-Sent Events 实时展示研究进度
- **长期记忆**：基于 ChromaDB + DashScope Embedding 的向量记忆，新任务自动检索历史上下文
- **成本追踪**：每次 LLM 调用的 Token 消耗与费用自动记录

## 🏗️ 架构

```
浏览器 :3000 ──→ Next.js 前端（SSE + REST）
                      │
                      ├── POST /api/research/start       → 创建任务
                      ├── GET  /api/research/{id}/stream  → SSE 实时进度
                      ├── POST /api/research/{id}/resume  → HITL 审查决定
                      └── GET  /api/research/{id}/report  → 最终报告

FastAPI :8000 ──→ LangGraph Agent（5 Agent 协作）
                      │
                      ├── Redis      → Checkpoint 持久化 + 审查决定缓存
                      ├── SQLite     → 任务历史、最终报告
                      ├── ChromaDB   → 历史研究向量记忆
                      └── JSONL      → 执行轨迹 + Token 成本日志
```

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI + Uvicorn |
| Agent 编排 | LangGraph + LangChain |
| 前端 | Next.js 15 (React) |
| 向量存储 | ChromaDB |
| 缓存/状态 | Redis |
| 任务存储 | SQLite（可切换 MySQL） |
| AI 模型 | 兼容 OpenAI API 格式（DashScope / DeepSeek / Qwen 等） |

## 🚀 快速开始

### 前置依赖

- Python 3.12+
- Node.js 20+
- Docker Desktop（运行 Redis）

### 1. 配置

```bash
cp config.example.yml config.yml
# 编辑 config.yml，填入你的 API Key
```

### 2. 启动 Redis

```bash
docker run -d --name redis -p 6379:6379 redis:7
```

### 3. 安装依赖

```bash
# 后端
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 4. 启动服务

```bash
# 终端 1：后端
uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 终端 2：前端
cd frontend && npm run dev
```

浏览器打开 `http://localhost:3000`。

> 💡 如果不想用 Redis，在 `config.yml` 中将 `redis.enabled` 改为 `false`，后端会自动降级为内存模式。

## 📂 项目结构

```
├── backend/           FastAPI 应用层
│   ├── main.py        入口
│   ├── routes/        API 路由（research + observability）
│   ├── schemas/       请求/响应模型
│   └── services/      业务逻辑（Agent 执行、SSE、任务存储）
├── deep_research/     核心引擎
│   ├── agents/        5 个 Agent 节点
│   ├── callbacks/     回调（成本追踪、流式输出、执行轨迹）
│   ├── memory/        记忆系统（向量 + 结构化存储）
│   ├── tools/         工具（搜索、摘要、报告精炼）
│   └── verification/  事实核查
├── frontend/          Next.js 前端
└── config.example.yml  配置模板
```

## 🤝 贡献

欢迎提 Issue 和 PR！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可

MIT License — 详见 [LICENSE](LICENSE) 文件。
