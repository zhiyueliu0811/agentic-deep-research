"""FastAPI 应用入口。

启动命令：
    uv run uvicorn backend.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.research import router as research_router
from backend.routes.observability import router as obs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时清理残留状态，关闭时清理资源。"""
    import os
    os.makedirs("data", exist_ok=True)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)
app.include_router(obs_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
