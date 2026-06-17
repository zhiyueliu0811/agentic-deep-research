"""可观测性 API：Agent 执行轨迹、成本统计。"""

from __future__ import annotations

import json
import os
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/obs", tags=["observability"])

DATA_DIR = os.path.join(os.getcwd(), "data")
TRACE_PATH = os.path.join(DATA_DIR, "agent_trace.jsonl")
COST_PATH = os.path.join(DATA_DIR, "cost_log.jsonl")


def _read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


@router.get("/trace/{thread_id}")
async def get_trace(thread_id: str):
    """返回指定任务的 Agent 执行轨迹（节点树 + 工具调用）。"""
    events = _read_jsonl(TRACE_PATH)
    # 按 thread_id 过滤
    filtered = [e for e in events if e.get("thread_id") == thread_id]
    return _build_trace_tree(filtered)


@router.get("/cost/{thread_id}")
async def get_cost(thread_id: str):
    """返回指定任务的 Token 消耗和成本。"""
    records = _read_jsonl(COST_PATH)
    # 按 thread_id 过滤
    filtered = [r for r in records if r.get("thread_id") == thread_id]
    total_input = sum(r.get("input_tokens", 0) for r in filtered)
    total_output = sum(r.get("output_tokens", 0) for r in filtered)
    total_cost = sum(r.get("cost_rmb", 0) for r in filtered)

    model_stats: dict[str, dict] = {}
    for r in filtered:
        model = r.get("model", "unknown")
        if model not in model_stats:
            model_stats[model] = {"input_tokens": 0, "output_tokens": 0, "cost_rmb": 0.0, "calls": 0}
        model_stats[model]["input_tokens"] += r.get("input_tokens", 0)
        model_stats[model]["output_tokens"] += r.get("output_tokens", 0)
        model_stats[model]["cost_rmb"] += r.get("cost_rmb", 0)
        model_stats[model]["calls"] += 1

    return {
        "thread_id": thread_id,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "total_cost_rmb": round(total_cost, 4),
        "model_stats": model_stats,
        "records": filtered[-50:],  # 最近 50 条
    }


@router.get("/stats")
async def get_stats():
    """返回全局统计摘要。"""
    records = _read_jsonl(COST_PATH)
    trace_events = _read_jsonl(TRACE_PATH)

    total_input = sum(r.get("input_tokens", 0) for r in records)
    total_output = sum(r.get("output_tokens", 0) for r in records)
    total_cost = sum(r.get("cost_rmb", 0) for r in records)

    return {
        "total_tasks": 0,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "total_cost_rmb": round(total_cost, 4),
        "total_llm_calls": len(records),
        "total_trace_events": len(trace_events),
    }


def _build_trace_tree(events: list[dict]) -> dict:
    """将平铺的 trace 事件转为树形结构。"""
    nodes = []
    edges = []
    # 追踪每个 agent 最新的 decision 节点，用于 tool_call 连边
    current_node: dict[str, str] = {}
    counter = [0]

    def new_id() -> str:
        nid = f"n{counter[0]}"
        counter[0] += 1
        return nid

    for evt in events:
        agent = evt.get("agent", "unknown")
        event_type = evt.get("event_type", "")
        data = evt.get("data", {})

        if event_type == "decision":
            nid = new_id()
            current_node[agent] = nid
            nodes.append({
                "id": nid,
                "type": "agent",
                "label": agent,
                "detail": data.get("decision", ""),
            })
        elif event_type == "tool_call":
            tool_name = data.get("tool", "unknown")
            nid = new_id()
            parent_nid = current_node.get(agent)
            nodes.append({
                "id": nid,
                "type": "tool",
                "label": tool_name,
                "detail": data.get("input", "")[:100],
            })
            if parent_nid:
                edges.append({"source": parent_nid, "target": nid})
        elif event_type == "quality_score":
            nodes.append({
                "id": new_id(),
                "type": "quality",
                "label": f"Quality: {data.get('score', '?')}/10",
                "detail": data.get("feedback", ""),
            })

    return {"nodes": nodes, "edges": edges}
