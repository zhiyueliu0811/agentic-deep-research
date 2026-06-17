"""API 请求模型。"""

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """提交研究任务的请求。"""
    query: str = Field(..., min_length=1, max_length=5000, description="研究主题/问题")


class ReviewAction(BaseModel):
    """Human Review 审查决定。"""
    action: str = Field(..., pattern="^(approve|revise|reject)$", description="审查动作")
    feedback: str = Field(default="", description="修改反馈（action=revise 时必填）")
