# Agentic Deep Research Platform 🧠

基于 LangGraph 构建的多 Agent 深度研究系统，Supervisor 自主拆解任务、并行调度 Research Agent 检索，集成事实校验、人机审核与双层记忆复用，生成结构化研究报告。

## ✨ 功能亮点

- **多智能体自演化**：Supervisor 通过 ConductResearch 工具动态拉起并行研究，Evaluator 打分回炉 + Red Team 对抗审查形成质量闭环，含停滞检测防止无效循环
- **并行事实校验**：LLM 提取可验证主张 → 并行网络检索 → 四档判定（Supported / Partial / Unsupported / Unverifiable），输出可量化幻觉率
- **双层记忆复用**：ChromaDB 向量语义检索 + Entities / Claims / Evidence / Contradictions 四集合结构化存储，LLM 自动抽取实体与主张，Jaccard 去重后跨会话注入上下文
- **人机协同与全链路可观测**：LangGraph `interrupt()` 实现草稿阶段 HITL 审核断点，SSE 实时推送执行事件，Callback 层按模型计费成本追踪 + 阈值告警

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

LangGraph · LangChain · FastAPI · Next.js · Redis · ChromaDB · Docker

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
