"""基于 ChromaDB 多 Collection 的结构化记忆存储。"""

from __future__ import annotations

import os
import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings

import json as _json

from deep_research.memory.schemas import Entity, MemoryClaim, Evidence, Contradiction
from deep_research.memory.vector_store import VectorMemoryStore
from deep_research import logging as dr_logging

logger = dr_logging.get_logger(__name__)


def _clean_metadata(meta: dict) -> dict:
    """移除空列表和 None 值，ChromaDB 不兼容这些类型。"""
    return {k: v for k, v in meta.items() if v is not None and v != [] and v != {}}


class StructuredMemoryStore:
    """管理四个 ChromaDB Collection：entities, claims, evidence, contradictions。"""

    def __init__(self, persist_dir: str | None = None) -> None:
        persist_dir = persist_dir or os.path.join(os.getcwd(), "data", "chroma")
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._entities = self._client.get_or_create_collection("memory_entities")
        self._claims = self._client.get_or_create_collection("memory_claims")
        self._evidences = self._client.get_or_create_collection("memory_evidence")
        self._contradictions = self._client.get_or_create_collection("memory_contradictions")

        self._embedder = VectorMemoryStore(persist_dir=persist_dir)

        logger.info(
            "StructuredMemoryStore initialized: e=%d c=%d ev=%d ct=%d",
            self._entities.count(),
            self._claims.count(),
            self._evidences.count(),
            self._contradictions.count(),
        )

    def _search_collection(self, collection, query: str, top_k: int = 5) -> list[dict]:
        """在指定 collection 上执行语义检索。"""
        if collection.count() == 0:
            return []
        query_embedding = self._embedder._embed([query])
        n = min(top_k, collection.count())
        results = collection.query(query_embeddings=query_embedding, n_results=n)
        if not results or not results.get("documents") or not results["documents"][0]:
            return []
        return [
            {"id": doc_id, "content": doc, "metadata": meta}
            for doc_id, doc, meta in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0] if results.get("metadatas") else [{}] * len(results["ids"][0]),
            )
        ]

    # ---- Entity ----

    def upsert_entity(self, entity: Entity) -> str:
        entity.id = entity.id or uuid.uuid4().hex[:12]
        doc = entity.model_dump_json()
        self._entities.upsert(
            ids=[entity.id],
            documents=[f"{entity.name}: {entity.description}"],
            metadatas=[_clean_metadata(_json.loads(doc))],
        )
        logger.debug("Upserted entity: %s (%s)", entity.name, entity.id)
        return entity.id

    def search_entities(self, query: str, top_k: int = 5) -> list[Entity]:
        results = self._search_collection(self._entities, query, top_k=top_k)
        return [Entity(**r["metadata"]) for r in results if r.get("metadata")]

    # ---- Claim ----

    def upsert_claim(self, claim: MemoryClaim) -> str:
        claim.id = claim.id or uuid.uuid4().hex[:12]
        doc = claim.model_dump_json()
        self._claims.upsert(
            ids=[claim.id],
            documents=[claim.text],
            metadatas=[_clean_metadata(_json.loads(doc))],
        )
        logger.debug("Upserted claim: %s (%s)", claim.text[:60], claim.id)
        return claim.id

    def search_claims(self, query: str, top_k: int = 5) -> list[MemoryClaim]:
        results = self._search_collection(self._claims, query, top_k=top_k)
        return [MemoryClaim(**r["metadata"]) for r in results if r.get("metadata")]

    def get_claims_by_entity(self, entity_name: str) -> list[MemoryClaim]:
        """查询涉及某个实体的所有 Claim（ChromaDB metadata 过滤）。"""
        # json imported at top as _json
        try:
            result = self._claims.get(where={"entities": {"$contains": entity_name}})
        except Exception:
            return []
        return [
            MemoryClaim(**{**_json.loads(m), "id": i})
            for i, m in zip(result["ids"], result["metadatas"]) if m
        ]

    # ---- Evidence ----

    def upsert_evidence(self, evidence: Evidence) -> str:
        evidence.id = evidence.id or uuid.uuid4().hex[:12]
        doc = evidence.model_dump_json()
        self._evidences.upsert(
            ids=[evidence.id],
            documents=[evidence.description],
            metadatas=[_clean_metadata(_json.loads(doc))],
        )
        return evidence.id

    # ---- Contradiction ----

    def upsert_contradiction(self, contradiction: Contradiction) -> str:
        contradiction.id = contradiction.id or uuid.uuid4().hex[:12]
        doc = contradiction.model_dump_json()
        self._contradictions.upsert(
            ids=[contradiction.id],
            documents=[contradiction.description],
            metadatas=[_clean_metadata(_json.loads(doc))],
        )
        return contradiction.id

    def get_contradictions(self) -> list[Contradiction]:
        # json imported at top as _json
        if self._contradictions.count() == 0:
            return []
        result = self._contradictions.get()
        return [
            Contradiction(**{**_json.loads(m), "id": i})
            for i, m in zip(result["ids"], result["metadatas"]) if m
        ]

    # ---- Stats ----

    def stats(self) -> dict:
        return {
            "entities": self._entities.count(),
            "claims": self._claims.count(),
            "evidence": self._evidences.count(),
            "contradictions": self._contradictions.count(),
        }
