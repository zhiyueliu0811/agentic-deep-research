"""Agent 生命周期管理：任务注册、状态查询、HITL 审查、最终结果提取。"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime
from typing import Any

import yaml
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver

from deep_research.agent_builder import _create_builder
from backend.services import task_store
from deep_research import logging as dr_logging

logger = dr_logging.get_logger(__name__)

_DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(_DATA_DIR, exist_ok=True)

# 模块级共享 checkpointer —— 优先 Redis，不可用时降级 InMemorySaver
_checkpointer: Any = None


def _load_redis_config() -> dict | None:
    try:
        with open("config.yml", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        return config.get("stages", {}).get("prod", {}).get("redis")
    except Exception:
        return None


def _create_redis_saver():
    """尝试创建 AsyncRedisSaver（同步创建，异步 setup 需要后续调用 init_checkpointer）。"""
    try:
        import redis.asyncio as aioredis
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver

        redis_cfg = _load_redis_config()
        if not redis_cfg or not redis_cfg.get("enabled"):
            return None

        url = redis_cfg.get("url", "redis://localhost:6379")
        client = aioredis.from_url(url)
        saver = AsyncRedisSaver(redis_client=client)
        logger.info("RedisSaver created (%s), setup pending", url)
        return saver
    except Exception as e:
        logger.warning("Redis unavailable, falling back to InMemorySaver: %s", e)
        return None


async def init_checkpointer():
    """在 FastAPI lifespan 中异步完成 RedisSaver 的 setup。"""
    global _checkpointer
    try:
        if _checkpointer is not None and hasattr(_checkpointer, "asetup"):
            await _checkpointer.asetup()
            logger.info("RedisSaver setup complete")
    except Exception as e:
        logger.warning("RedisSaver setup failed, falling back to InMemorySaver: %s", e)
        _checkpointer = InMemorySaver()


def _get_checkpointer():
    """获取 checkpointer：优先 Redis，降级 InMemorySaver。"""
    global _checkpointer
    if _checkpointer is None:
        redis_saver = _create_redis_saver()
        if redis_saver:
            _checkpointer = redis_saver
        else:
            _checkpointer = InMemorySaver()
            logger.info("Using InMemorySaver (checkpoints lost on restart)")
    return _checkpointer


_agent_cache: Any = None


def _build_agent():
    """构建 agent 实例（缓存复用，避免每次请求重编译 3-8 秒）。"""
    global _agent_cache
    if _agent_cache is not None:
        return _agent_cache
    builder = _create_builder(with_hitl=True)
    _agent_cache = builder.compile(checkpointer=_get_checkpointer())
    return _agent_cache


# ===== 任务 CRUD =====

def create_task(query: str) -> dict:
    """创建新研究任务，持久化到 SQLite。"""
    thread_id = uuid.uuid4().hex[:12]
    return task_store.create_task(thread_id, query)


def get_task_status(thread_id: str) -> dict:
    """获取任务状态快照。"""
    task = task_store.get_task(thread_id)
    if not task:
        return {"thread_id": thread_id, "status": "unknown"}
    return {
        "thread_id": task["thread_id"],
        "status": task["status"],
        "stage": task["stage"],
        "query": task["query"],
        "draft_report": task.get("draft_report", ""),
        "final_report": task.get("final_report", ""),
        "verification": task.get("verification"),
        "error": task.get("error", ""),
    }


def update_task(thread_id: str, **kwargs):
    """更新任务字段（持久化到 SQLite）。"""
    task_store.update_task(thread_id, **kwargs)


def set_task_stage(thread_id: str, stage: str):
    """更新当前阶段，自动推导状态。"""
    status_map = {
        "human_review": "waiting_review",
        "final_report_generation": "completed",
    }
    status = status_map.get(stage, "running")
    update_task(thread_id, stage=stage, status=status)


def mark_task_failed(thread_id: str, error: str):
    update_task(thread_id, status="failed", error=error)


def mark_task_completed(thread_id: str, final_report: str, verification: dict | None):
    update_task(
        thread_id,
        status="completed",
        stage="final_report_generation",
        final_report=final_report,
        verification=verification,
    )


def list_tasks() -> list[dict]:
    """列出所有历史任务（按创建时间倒序）。"""
    return task_store.list_tasks()


# ===== Agent 输入/输出工具 =====

def get_thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def build_input(query: str) -> dict:
    return {"messages": [HumanMessage(content=query)]}


def build_resume_command(action: str, feedback: str = "") -> Command:
    if action == "revise":
        return Command(resume={"action": "revise", "feedback": feedback})
    return Command(resume={"action": "approve"})


async def extract_final_state(agent, thread_config: dict) -> dict:
    """从 agent checkpointer 中提取最终状态。"""
    try:
        state = await agent.aget_state(thread_config)
        if state and state.values:
            return {
                "final_report": state.values.get("final_report", ""),
                "verification": state.values.get("verification_report"),
                "draft_report": state.values.get("draft_report", ""),
                "research_brief": state.values.get("research_brief", ""),
            }
    except Exception:
        pass
    return {}


async def get_report(thread_id: str) -> dict:
    """获取最终报告（优先 agent state，回退到 task_store）。"""
    agent = _build_agent()
    config = get_thread_config(thread_id)
    state_values = await extract_final_state(agent, config)

    task = task_store.get_task(thread_id) or {}

    final_report = state_values.get("final_report") or task.get("final_report", "")
    verification = state_values.get("verification") or task.get("verification")

    return {
        "thread_id": thread_id,
        "query": task.get("query", ""),
        "final_report": final_report,
        "verification": verification,
        "draft_report": state_values.get("draft_report") or task.get("draft_report", ""),
    }
