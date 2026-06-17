"""API 响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreated(BaseModel):
    """研究任务创建成功响应。"""
    thread_id: str
    status: str = "pending"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TaskStatus(BaseModel):
    """任务状态快照。"""
    thread_id: str
    status: str  # pending | running | waiting_review | completed | failed
    stage: str = ""  # 当前阶段名称
    query: str = ""
    draft_report: str = ""
    final_report: str = ""
    verification: dict[str, Any] | None = None
    error: str = ""


class SSEEvent(BaseModel):
    """SSE 推送事件。"""
    event: str
    data: dict[str, Any]


class TaskListItem(BaseModel):
    """历史任务列表项。"""
    thread_id: str
    query: str
    status: str
    created_at: str
    updated_at: str
