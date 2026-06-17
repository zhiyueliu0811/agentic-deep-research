# 项目开发指南

## 快速开始

1. `cp config.example.yml config.yml` 并填入 API Key
2. `docker start redis` (或禁用 config.yml 中 `redis.enabled`)
3. `pip install -r requirements.txt`
4. `uvicorn backend.main:app --reload --port 8000`
5. `cd frontend && npm install && npm run dev`

## 架构原则

- 核心引擎在 `deep_research/`，不依赖 FastAPI，可独立使用
- Web 层在 `backend/`，薄封装，只做路由和 SSE 适配
- 前端通过 SSE 实时消费 Agent 执行事件

## 添加新 Agent

1. 在 `deep_research/agents/` 创建节点文件
2. 在 `deep_research/agent_builder.py` 注册节点

## 代码规范

- 修改前先说明计划
- 不提交 `.env`、API Key、数据库文件
- 修改后更新相关文档
