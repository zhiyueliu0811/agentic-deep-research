"""记忆管理器：协调向量存储 + 结构化存储的检索与写入。"""

from __future__ import annotations

import hashlib
import json
import time

from langchain_core.messages import HumanMessage

from deep_research.memory.vector_store import VectorMemoryStore
from deep_research.memory.structured_store import StructuredMemoryStore
from deep_research.memory.schemas import Entity, MemoryClaim, Evidence, Contradiction
from deep_research.llm import get_chat_model_for_task
from deep_research.utils import parse_json_response
from deep_research import logging as dr_logging

logger = dr_logging.get_logger(__name__)

MEMORY_CONTEXT_PROMPT = """
<历史研究记忆>
以下是与此查询相关的历史研究记录，可作为参考：
{memories}
</历史研究记忆>
"""

STRUCTURED_EXTRACT_PROMPT = """你是一名知识工程师。从以下研究报告中提取结构化知识。

报告内容：
{report_text}

请提取并返回 JSON：
```json
{{
  "entities": [
    {{"name": "实体名", "type": "technology|person|organization|concept|dataset|metric", "description": "一句话描述", "importance": 1-10}}
  ],
  "claims": [
    {{"text": "具体断言", "source_url": "来源URL或null", "confidence": 0.0-1.0}}
  ],
  "contradictions": [
    {{"claim_a": "断言A", "claim_b": "断言B", "description": "冲突说明"}}
  ]
}}
```

规则：
- entities: 只提取报告中明确讨论的技术/人物/组织/概念，importance 根据引用频率和对结论的重要性判断
- claims: 提取带有具体数据的可验证断言，每条最多 10 条
- contradictions: 检测报告中自相矛盾的地方，没有则返回空数组
"""


def _similarity(text1: str, text2: str) -> float:
    """简单的词级 Jaccard 相似度，用于跨会话去重。"""
    words1 = set(text1.split())
    words2 = set(text2.split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


class MemoryManager:
    """封装语义检索（向量）+ 结构化存储（Entity/Claim/Evidence/Contradiction）。"""

    def __init__(self, persist_dir: str | None = None) -> None:
        self._store = VectorMemoryStore(persist_dir=persist_dir)
        self._structured = StructuredMemoryStore(persist_dir=persist_dir)
        self._model = get_chat_model_for_task("extracting")
        logger.info("MemoryManager initialized (semantic=%d, entities=%d, claims=%d)",
                     self._store.count(),
                     self._structured.stats()["entities"],
                     self._structured.stats()["claims"])

    # ---- 语义检索（保留原有接口）----

    def retrieve_context(self, user_query: str, top_k: int = 3) -> str:
        results = self._store.search_memory(user_query, top_k=top_k)
        if not results:
            return ""

        lines = []
        for r in results:
            lines.append(f"- [{r['id']}] {r['content'][:500]}")
        return MEMORY_CONTEXT_PROMPT.format(memories="\n".join(lines))

    def store_from_report(self, user_query: str, final_report: str) -> str | None:
        """同时存入原始文本（向量检索）和结构化信息。"
        自动检测跨会话重复——相似度 > 85% 的旧记忆会被更新而非新建。"""
        if not final_report or len(final_report) < 100:
            return None

        # 跨会话去重：检查是否已有高度相似的内容
        existing = self._store.search_memory(user_query, top_k=3)
        for ex in existing:
            if _similarity(final_report[:500], ex.get("content", "")[:500]) > 0.85:
                logger.info("Memory dedup: updating existing doc %s instead of creating new", ex["id"])
                # 更新现有记忆而非新建
                self._store.update_memory(
                    doc_id=ex["id"],
                    content=final_report[:2000],
                    metadata={"query": user_query, "timestamp": time.time(), "length": len(final_report), "updated": True},
                )
                return ex["id"]

        # 向量存储
        content = final_report[:2000]
        doc_id = hashlib.md5(f"{user_query}:{time.time()}".encode()).hexdigest()[:12]
        self._store.add_memory(
            doc_id=doc_id,
            content=content,
            metadata={"query": user_query, "timestamp": time.time(), "length": len(final_report)},
        )

        # 结构化抽取与存储
        self.extract_and_store_structured(final_report, doc_id)

        return doc_id

    # ---- 结构化记忆 ----

    def extract_and_store_structured(self, report_text: str, report_id: str = "") -> dict:
        """用 LLM 从报告中抽取 Entity/Claim/Contradiction 并存入结构化存储。"""
        prompt = STRUCTURED_EXTRACT_PROMPT.format(report_text=report_text[:6000])
        response = self._model.invoke([HumanMessage(content=prompt)])

        try:
            data = parse_json_response(response.content)
        except Exception as e:
            logger.warning("Failed to parse structured extraction: %s", e)
            return {"entities": 0, "claims": 0, "contradictions": 0}

        count = {"entities": 0, "claims": 0, "contradictions": 0}

        for e_data in data.get("entities", [])[:15]:
            try:
                entity = Entity(
                    name=e_data["name"],
                    type=e_data.get("type", "concept"),
                    description=e_data.get("description", ""),
                    importance=float(e_data.get("importance", 5)),
                )
                self._structured.upsert_entity(entity)
                count["entities"] += 1
            except Exception:
                pass

        for c_data in data.get("claims", [])[:10]:
            try:
                claim = MemoryClaim(
                    text=c_data["text"],
                    source_url=c_data.get("source_url"),
                    confidence=float(c_data.get("confidence", 0.5)),
                )
                self._structured.upsert_claim(claim)
                count["claims"] += 1
            except Exception:
                pass

        for ct_data in data.get("contradictions", [])[:5]:
            try:
                contradiction = Contradiction(
                    description=ct_data.get("description", ""),
                )
                self._structured.upsert_contradiction(contradiction)
                count["contradictions"] += 1
            except Exception:
                pass

        logger.info("Structured extraction: %s", count)
        return count

    def query_entities(self, query: str, top_k: int = 5) -> list[Entity]:
        """查询相关实体。"""
        return self._structured.search_entities(query, top_k=top_k)

    def query_claims(self, query: str, top_k: int = 5) -> list[MemoryClaim]:
        """查询相关 Claim。"""
        return self._structured.search_claims(query, top_k=top_k)

    def get_contradictions(self) -> list[Contradiction]:
        """获取所有知识冲突。"""
        return self._structured.get_contradictions()

    def stats(self) -> dict:
        return {
            "semantic": self._store.count(),
            "entities": self._structured.stats()["entities"],
            "claims": self._structured.stats()["claims"],
            "evidence": self._structured.stats()["evidence"],
            "contradictions": self._structured.stats()["contradictions"],
        }

    def count(self) -> int:
        return self._store.count()
