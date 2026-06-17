"""研究任务 API 端点：提交、SSE 流、状态、审查、报告、历史。"""

from __future__ import annotations

import json
import time

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.schemas.requests import ResearchRequest, ReviewAction
from backend.services import agent_service as svc
from backend.services import task_store
from backend.services.sse_adapter import sse_event_stream

router = APIRouter(prefix="/api/research", tags=["research"])

# ===== 审查决定存储（Redis 优先，内存降级）=====

_review_ttl: int = 600  # 默认 10 分钟过期
_redis_client: Any = None
_memory_reviews: dict[str, dict] = {}


def _get_redis():
    """获取 Redis 客户端（延迟连接，失败返回 None）。"""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as redis_lib

        with open("config.yml", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        redis_cfg = cfg.get("stages", {}).get("prod", {}).get("redis", {})
        if not redis_cfg or not redis_cfg.get("enabled"):
            return None

        global _review_ttl
        _review_ttl = redis_cfg.get("review_ttl_seconds", 600)
        _redis_client = redis_lib.from_url(redis_cfg.get("url", "redis://localhost:6379"))
        _redis_client.ping()
        return _redis_client
    except Exception:
        return None


def _store_review(thread_id: str, action: str, feedback: str):
    r = _get_redis()
    if r:
        val = json.dumps({"action": action, "feedback": feedback}, ensure_ascii=False)
        r.setex(f"review:{thread_id}", _review_ttl, val)
    else:
        _memory_reviews[thread_id] = {"action": action, "feedback": feedback}


def _pop_review(thread_id: str) -> dict | None:
    r = _get_redis()
    if r:
        key = f"review:{thread_id}"
        raw = r.getdel(key)
        if raw:
            return json.loads(raw)
        return None
    return _memory_reviews.pop(thread_id, None)


@router.post("/start")
async def start_research(req: ResearchRequest):
    """提交研究任务，返回 thread_id。"""
    result = svc.create_task(req.query)
    return result


def _is_waiting_review(agent, thread_config: dict) -> bool:
    try:
        state = agent.get_state(thread_config)
        return bool(state.next and "human_review" in state.next)
    except Exception:
        return False


@router.get("/{thread_id}/stream")
async def stream_research(thread_id: str):
    """SSE 实时进度推送。

    首次调用：启动完整研究流程。
    审查后重连：自动从 HITL 中断处恢复执行。
    """
    task = svc.get_task_status(thread_id)
    if task["status"] == "unknown":
        raise HTTPException(status_code=404, detail="Task not found")

    query = task["query"]
    thread_config = svc.get_thread_config(thread_id)

    async def event_generator():
        start_time = time.time()
        agent = svc._build_agent()

        # 检查是否有待处理的审查决定
        review = _pop_review(thread_id)
        # 或者检查 agent 是否停在 human_review
        if not review and _is_waiting_review(agent, thread_config):
            # 还没收到审查决定，等待（让前端通过 resume 提交后再重连）
            state = agent.get_state(thread_config)
            draft = (state.values.get("draft_report", "") or "") if state.values else ""
            svc.update_task(thread_id, status="waiting_review", stage="human_review", draft_report=draft)
            yield f"data: {json.dumps({'event': 'human_review_required', 'data': {'draft_preview': draft[:2000], 'message': '报告草稿已生成，请审查'}}, ensure_ascii=False)}\n\n"
            return

        if review:
            # 有审查决定：用 resume command 恢复执行
            svc.set_task_stage(thread_id, "supervisor_subgraph")
            user_input = svc.build_resume_command(review["action"], review.get("feedback", ""))
        else:
            # 首次启动：用原始 query 开始
            svc.set_task_stage(thread_id, "write_research_brief")
            user_input = svc.build_input(query)

        async for sse_msg in sse_event_stream(agent, user_input, thread_config, thread_id=thread_id):
            yield sse_msg

        # SSE 流结束后检查最终状态
        final = svc.extract_final_state(agent, thread_config)
        if final.get("final_report"):
            svc.mark_task_completed(thread_id, final["final_report"], final.get("verification"))
            yield f"data: {json.dumps({'event': 'complete', 'data': {'duration_seconds': round(time.time() - start_time, 1)}}, ensure_ascii=False)}\n\n"
        elif _is_waiting_review(agent, thread_config):
            state = agent.get_state(thread_config)
            draft = (state.values.get("draft_report", "") or "") if state.values else ""
            svc.update_task(thread_id, status="waiting_review", stage="human_review", draft_report=draft)
            yield f"data: {json.dumps({'event': 'human_review_required', 'data': {'draft_preview': draft[:2000], 'message': '报告草稿已生成，请审查'}}, ensure_ascii=False)}\n\n"
        else:
            # 既没有 final_report 也不在 waiting_review → 流程异常终止
            svc.mark_task_failed(thread_id, "工作流异常终止，未生成最终报告")
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': '工作流异常终止，未生成最终报告'}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{thread_id}/resume")
async def resume_research(thread_id: str, review: ReviewAction):
    """提交 HITL 审查决定。

    审查决定存入 _pending_reviews，前端随后重连 /stream 即可自动恢复。
    """
    task = svc.get_task_status(thread_id)
    if task["status"] == "unknown":
        raise HTTPException(status_code=404, detail="Task not found")

    _store_review(thread_id, review.action, review.feedback)
    svc.update_task(thread_id, status="running", stage="supervisor_subgraph")
    return {"ok": True, "thread_id": thread_id}


@router.get("/{thread_id}/status")
async def get_research_status(thread_id: str):
    """查询任务当前状态。"""
    status = svc.get_task_status(thread_id)
    if status["status"] == "unknown":
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@router.delete("/{thread_id}")
async def delete_research_task(thread_id: str):
    """删除历史任务。"""
    task_store.update_task(thread_id, status="deleted")
    return {"deleted": True}


@router.get("/{thread_id}/report")
async def get_research_report(thread_id: str):
    """获取最终报告。"""
    report = svc.get_report(thread_id)
    if not report.get("final_report"):
        raise HTTPException(status_code=404, detail="Report not found or task not completed")
    return report


@router.get("/history/list")
async def get_history():
    """获取历史任务列表。"""
    return svc.list_tasks()
