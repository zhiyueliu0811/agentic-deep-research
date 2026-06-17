"""逐条核查 Claim 的事实依据。"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from deep_research.llm import get_chat_model_for_task
from deep_research.tools.tool import tavily_search
from deep_research.verification.schemas import ClaimVerdict
from deep_research.utils import parse_json_response
from deep_research import logging as dr_logging

logger = dr_logging.get_logger(__name__)

CLAIM_VERIFY_PROMPT = """你是一名严格的事实核查员。请判断以下断言是否能从搜索结果中找到可靠依据。

断言：{claim_text}

搜索结果：
{search_results}

判断标准：
- SUPPORTED：搜索结果中有明确证据，能直接佐证该断言的核心事实
- PARTIAL：搜索结果部分相关，能找到间接证据或部分讨论，但不足以完全确认
- UNSUPPORTED：搜索结果与断言明显矛盾，或搜索到了相关信息但无法找到任何支撑
- UNVERIFIABLE：仅当断言涉及未公开的内部数据、尚未发生的事件、或无法通过公开信息判断的个人主观感受时使用

关键原则：
- 如果搜索结果中找不到相关证据，且该断言理应可被公开信息验证，应判为 UNSUPPORTED 而非 UNVERIFIABLE
- 不要因为 PARTIAL 也能接受就放宽标准——只有真正存在支撑证据时才判 PARTIAL
- UNVERIFIABLE 是狭窄的例外类别，不应作为默认选项

返回 JSON：
```json
{{"verdict": "SUPPORTED|PARTIAL|UNSUPPORTED|UNVERIFIABLE", "evidence": "关键证据摘要（1-2句话）", "confidence": 0.0-1.0}}
```
"""


class ClaimVerifier:
    """逐条核查 Claim，返回核查结果。"""

    MAX_CLAIMS = 10
    SEARCH_RESULTS_PER_CLAIM = 3

    def __init__(self) -> None:
        self._model = get_chat_model_for_task("verifying")

    async def verify(self, claims: list) -> list[ClaimVerdict]:
        """逐条核查 Claim，兼容字符串和字典格式。"""
        verdicts: list[ClaimVerdict] = []
        for claim in claims[: self.MAX_CLAIMS]:
            if isinstance(claim, str):
                text = claim
            elif isinstance(claim, dict):
                text = claim.get("text") or claim.get("claim") or str(claim)
            else:
                text = str(claim)
            verdict = await self._verify_one(text)
            verdicts.append(verdict)

        supported = sum(1 for v in verdicts if v.verdict == "SUPPORTED")
        partial = sum(1 for v in verdicts if v.verdict == "PARTIAL")
        total = len(verdicts)
        # 验证通过率 = (SUPPORTED + PARTIAL) / total，即至少能找到部分依据的比例
        verified_rate = (supported + partial) / total * 100 if total > 0 else 0
        logger.info(
            "Verification: %d supported + %d partial = %.0f%% verified (%d total)",
            supported, partial, verified_rate, total,
        )
        return verdicts

    async def _verify_one(self, claim_text: str) -> ClaimVerdict:
        """核查单条 Claim。"""
        if not claim_text.strip():
            return ClaimVerdict(claim_text=claim_text, verdict="UNVERIFIABLE")

        # 搜索验证：提取前 100 字作为搜索关键词，去掉引号和 verify 前缀
        search_query = claim_text[:120].strip().strip('"').strip("'")
        # 去掉常见的连接词让搜索更精准
        for word in ["此外", "同时", "值得注意", "综上"]:
            search_query = search_query.replace(word, "")

        try:
            search_results = tavily_search(search_query, max_results=self.SEARCH_RESULTS_PER_CLAIM)
        except Exception as e:
            logger.warning("Search failed for claim verification: %s", e)
            return ClaimVerdict(claim_text=claim_text, verdict="UNVERIFIABLE", evidence=str(e))

        # LLM 判断
        prompt = CLAIM_VERIFY_PROMPT.format(
            claim_text=claim_text,
            search_results=str(search_results)[:3000],
        )
        response = self._model.invoke([HumanMessage(content=prompt)])

        try:
            data = parse_json_response(response.content)
            return ClaimVerdict(
                claim_text=claim_text,
                verdict=data.get("verdict", "UNVERIFIABLE"),
                evidence=data.get("evidence", ""),
                confidence=float(data.get("confidence", 0.5)),
            )
        except Exception as e:
            logger.warning("Failed to parse verification result: %s", e)
            return ClaimVerdict(claim_text=claim_text, verdict="UNVERIFIABLE")
