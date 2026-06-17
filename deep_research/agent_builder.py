#***********************************************
#      Filename: agent_builder.py
#   Description: 多智能体深度研究Builder
#   Features:    HITL 人工审查 + 记忆注入 + 持久化 Checkpoint
#***********************************************


import os
import sqlite3
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from deep_research.utils import get_today_str
from deep_research.states import AgentState, AgentInputState
from deep_research.prompts import FINAL_REPORT_PROMPT, RESEARCH_BRIEF_PROMPT
from deep_research.agents import supervisor_agent
from deep_research.agents.draft_agent import write_draft_report
from deep_research.memory.manager import MemoryManager
from deep_research.llm import get_chat_model, get_chat_model_auto
from deep_research import logging as dr_logging

logger = dr_logging.get_logger(__name__)

# ===== Config =====

writer_model = get_chat_model("writer")
memory_manager: MemoryManager | None = None


def _get_memory_manager() -> MemoryManager:
    global memory_manager
    if memory_manager is None:
        memory_manager = MemoryManager(persist_dir=os.path.join(os.getcwd(), "data", "chroma"))
    return memory_manager


# ===== RESEARCH BRIEF (with Memory Injection) =====

async def write_research_brief(state: AgentState) -> Command[str]:
    """生成研究简报，同时注入历史记忆作为上下文参考。"""

    messages = state.get("messages", [])
    # 提取用户最新 query 用于记忆检索和智能路由
    user_query = messages[-1].content if messages else ""

    # 检索历史记忆
    memory_context = ""
    try:
        mgr = _get_memory_manager()
        memory_context = mgr.retrieve_context(user_query)
        if memory_context:
            logger.info("Injected memory context into research_brief")
    except Exception as e:
        logger.warning("Memory retrieval failed: %s", e)

    # 智能路由选择模型
    draft_model = get_chat_model_auto("draft", query_text=user_query)

    prompt = RESEARCH_BRIEF_PROMPT.format(
        messages=messages,
        date=get_today_str()
    )

    # 注入记忆上下文
    if memory_context:
        prompt = memory_context + "\n\n" + prompt

    response = await draft_model.ainvoke([HumanMessage(content=prompt)])
    research_brief = response.content

    return Command(
        goto="write_draft_report",
        update={"research_brief": research_brief}
    )


# ===== HUMAN REVIEW (HITL) =====

async def human_review(state: AgentState) -> Command[str]:
    """HITL 节点：展示报告草稿，等待人工审查。

    用户可以通过 resume 传入 {'action': 'approve'} 或 {'action': 'revise', 'feedback': '...'}
    """
    draft = state.get("draft_report", "")
    research_brief = state.get("research_brief", "")

    # 触发中断，等待人工输入
    review = interrupt({
        "message": "报告草稿已生成，请审查",
        "draft_report_preview": draft[:1000] + ("..." if len(draft) > 1000 else ""),
        "research_brief": research_brief[:500],
        "options": ["approve", "revise"],
    })

    action = review if isinstance(review, str) else review.get("action", "approve")

    if action == "revise":
        feedback = review.get("feedback", "") if isinstance(review, dict) else ""
        revision_prompt = f"请根据以下反馈修改报告草稿：\n{feedback}\n\n当前草稿：\n{draft}"
        response = await writer_model.ainvoke([HumanMessage(content=revision_prompt)])
        logger.info("HITL: report revised based on user feedback")
        return Command(
            goto="human_review",
            update={"draft_report": response.content}
        )
    else:
        logger.info("HITL: user approved draft, proceeding to research")
        return Command(goto="supervisor_subgraph")


# ===== CLAIM VERIFICATION =====

async def claim_verification(state: AgentState) -> dict:
    """报告草稿的事实核查：提取关键 Claim → 搜索验证 → 生成核查报告。

    完全容错：任何步骤失败都优雅跳过，不影响主流程。
    """
    try:
        from deep_research.verification.claim_extractor import ClaimExtractor
        from deep_research.verification.claim_verifier import ClaimVerifier
        from deep_research.verification.schemas import VerificationReport

        draft = state.get("draft_report", "")
        if not draft or len(draft) < 100:
            logger.info("Skipping claim verification: draft too short")
            return {"verification_report": None, "claim_verification_warning": ""}

        extractor = ClaimExtractor()
        verifier = ClaimVerifier()

        claims = extractor.extract(draft)
        if not claims:
            logger.info("No claims extracted from draft")
            return {"verification_report": None, "claim_verification_warning": ""}

        verdicts = await verifier.verify(claims)
        report = VerificationReport.from_verdicts(verdicts)
        logger.info(
            "Verification complete: %d/%d supported, hallucination_rate=%.1f%%",
            report.supported, report.total_claims, report.hallucination_rate * 100,
        )

        warning = ""
        if report.unsupported > 0:
            unsupported_texts = [v.claim_text[:100] for v in verdicts if v.verdict == "UNSUPPORTED"]
            warning = f"\n[事实核查警告] 以下 {report.unsupported} 条断言缺乏证据支持，请在最终报告中标注或移除：\n" + \
                      "\n".join(f"- {t}" for t in unsupported_texts)

        return {
            "verification_report": report.model_dump() if report else None,
            "claim_verification_warning": warning,
        }
    except Exception as e:
        logger.warning("Claim verification failed (skipping): %s", e)
        return {"verification_report": None, "claim_verification_warning": ""}


# ===== FINAL REPORT GENERATION =====

async def final_report_generation(state: AgentState):
    """最终报告的生成: 用户query，研究简报，findings, 报告初稿 => 报告"""

    notes = state.get("notes", [])
    findings = "\n".join(notes)

    warning = state.get("claim_verification_warning", "")
    report_context = FINAL_REPORT_PROMPT.format(
        research_brief=state.get("research_brief", ""),
        findings=findings,
        date=get_today_str(),
        draft_report=state.get("draft_report", "")
    )
    final_report_prompt = report_context + warning

    final_report = await writer_model.ainvoke([HumanMessage(content=final_report_prompt)])
    report_content = final_report.content

    # 存储到记忆库
    try:
        user_query = ""
        msgs = state.get("messages", [])
        if msgs:
            user_query = msgs[0].content if isinstance(msgs[0].content, str) else str(msgs[0])
        mgr = _get_memory_manager()
        mgr.store_from_report(user_query, report_content)
        logger.info("Final report stored to memory")
    except Exception as e:
        logger.warning("Failed to store memory: %s", e)

    return {
        "final_report": report_content,
        "messages": ["最终的报告: " + report_content],
    }


# ===== BUILD GRAPH =====

async def build_agent_async(with_hitl: bool = True, checkpoint_db: str | None = None) -> Any:
    """异步构建 Deep Research Agent（支持 astream_events）。

    流式场景使用 InMemorySaver（已验证兼容 astream_events），
    持久化由 build_agent() 同步版的 SqliteSaver 负责。

    Args:
        with_hitl: 是否启用 HITL 中断审查
        checkpoint_db: 忽略（保留参数兼容性），流式场景统一用 InMemorySaver

    Returns:
        编译后的 LangGraph agent（带 InMemorySaver）
    """
    builder = _create_builder(with_hitl)
    checkpointer = InMemorySaver()
    logger.info("Agent built with InMemorySaver for streaming")
    return builder.compile(checkpointer=checkpointer)


def build_agent(with_hitl: bool = True, checkpoint_db: str | None = None) -> Any:
    """同步构建 Agent（用于 get_graph 或非流式 ainvoke）。

    流式场景请使用 build_agent_async。
    """
    builder = _create_builder(with_hitl)

    checkpointer = None
    if checkpoint_db:
        os.makedirs(os.path.dirname(checkpoint_db) or ".", exist_ok=True)
        conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        logger.info("Agent built with SqliteSaver at %s", checkpoint_db)
    else:
        logger.info("Agent built without persistent checkpointer")

    return builder.compile(checkpointer=checkpointer)


def _create_builder(with_hitl: bool = True) -> StateGraph:
    """创建 StateGraph 并添加节点和边（公共逻辑）。

    工作流:
      START → write_research_brief → write_draft_report → [human_review] → supervisor_subgraph
          → claim_verification → final_report_generation → END
    """
    builder = StateGraph(AgentState, input_schema=AgentInputState)

    builder.add_node("write_research_brief", write_research_brief)
    builder.add_node("write_draft_report", write_draft_report)
    builder.add_node("supervisor_subgraph", supervisor_agent)
    builder.add_node("claim_verification", claim_verification)
    builder.add_node("final_report_generation", final_report_generation)

    builder.add_edge(START, "write_research_brief")

    if with_hitl:
        builder.add_node("human_review", human_review)
        builder.add_edge("write_research_brief", "write_draft_report")
        builder.add_edge("write_draft_report", "human_review")
    else:
        builder.add_edge("write_research_brief", "write_draft_report")
        builder.add_edge("write_draft_report", "supervisor_subgraph")

    # supervisor 之后走 claim_verification → final_report
    builder.add_edge("supervisor_subgraph", "claim_verification")
    builder.add_edge("claim_verification", "final_report_generation")
    builder.add_edge("final_report_generation", END)
    return builder


# ===== MODULE-LEVEL INSTANCES =====

_checkpoint_path = os.path.join(os.getcwd(), "data", "checkpoints.db")

# 流式兼容的模块级 agent（InMemorySaver，支持 astream_events）
_streaming_agent = _create_builder(with_hitl=True).compile(checkpointer=InMemorySaver())
agent = _streaming_agent

# 流式场景使用 agent_async（同一套 InMemorySaver 逻辑）
# 用法: agent = await build_agent_async(with_hitl=True)

# 兼容旧引用
deep_researcher_builder = _create_builder(with_hitl=True)
