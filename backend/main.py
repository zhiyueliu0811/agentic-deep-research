"""FastAPI 应用入口。

启动命令：
    uv run uvicorn backend.main:app --reload --port 8000
"""

import json
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.routes.research import router as research_router
from backend.routes.observability import router as obs_router

# ---- Rate Limiter ----
_RATE_LIMIT_WINDOW = 60  # 秒
_RATE_LIMIT_MAX = 30     # 每窗口最大请求数
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


async def _rate_limit_middleware(request: Request, call_next):
    """简单的滑动窗口速率限制。"""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # 清理过期记录
    window_start = now - _RATE_LIMIT_WINDOW
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if t > window_start
    ]

    if len(_rate_limit_store[client_ip]) >= _RATE_LIMIT_MAX:
        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试", "retry_after": _RATE_LIMIT_WINDOW},
        )

    _rate_limit_store[client_ip].append(now)
    response = await call_next(request)
    return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时清理残留状态，关闭时清理资源。"""
    import os
    os.makedirs("data", exist_ok=True)

    # 预热 LLM 模型 + 预编译 Agent 图（避免首次请求时阻塞 SSE 流）
    try:
        from deep_research.llm import get_chat_model
        for role in ["supervisor", "writer", "evaluator", "red_team", "researcher_main", "researcher_compressor", "researcher_summarizer", "draft"]:
            try:
                get_chat_model(role)
            except Exception:
                pass
        # 预编译 agent 图
        from backend.services.agent_service import _build_agent
        _build_agent()
    except Exception:
        pass

    # 启动时将残留的 running/pending 任务标记为失败（仅 InMemory 模式）
    try:
        from backend.services import task_store
        from backend.services.agent_service import _get_checkpointer, init_checkpointer

        # 初始化 checkpointer（优先 Redis）
        _get_checkpointer()
        await init_checkpointer()

        # Redis 模式下不标记失败（checkpoint 可恢复）
        from langgraph.checkpoint.memory import InMemorySaver
        if isinstance(_get_checkpointer(), InMemorySaver):
            for t in task_store.list_tasks():
                if t["status"] in ("running", "pending"):
                    task_store.update_task(t["thread_id"], status="failed",
                                           error="后端重启导致任务中断，请重新提交")
    except Exception:
        pass

    yield


app = FastAPI(
    title="Agentic Deep Research Platform",
    description="基于 LangGraph 的多智能体深度研究系统 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.middleware("http")(_rate_limit_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)
app.include_router(obs_router)


@app.get("/api/test-sse")
async def test_sse():
    """极简 SSE 测试——排除 FastAPI StreamingResponse 问题。"""
    import asyncio
    from fastapi.responses import StreamingResponse

    async def gen():
        for i in range(5):
            yield f"data: {json.dumps({'event': 'ping', 'data': {'i': i}})}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/health")
async def health():
    # 增强健康检查：报告关键组件状态
    import os
    status = {"status": "ok", "components": {}}

    # Redis check
    try:
        from backend.services.agent_service import _get_checkpointer
        cp = _get_checkpointer()
        from langgraph.checkpoint.memory import InMemorySaver
        status["components"]["checkpoint"] = "redis" if not isinstance(cp, InMemorySaver) else "inmemory"
    except Exception as e:
        status["components"]["checkpoint"] = f"error: {e}"

    # ChromaDB check
    try:
        persist_dir = os.path.join(os.getcwd(), "data", "chroma")
        if os.path.exists(persist_dir):
            status["components"]["chromadb"] = f"ok (persist_dir: {persist_dir})"
        else:
            status["components"]["chromadb"] = "not_initialized"
    except Exception as e:
        status["components"]["chromadb"] = f"error: {e}"

    # SQLite check
    try:
        db_path = os.path.join(os.getcwd(), "data", "tasks.db")
        status["components"]["sqlite"] = "ok" if os.path.exists(db_path) else "not_initialized"
    except Exception as e:
        status["components"]["sqlite"] = f"error: {e}"

    return status
