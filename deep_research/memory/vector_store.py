"""基于 ChromaDB + DashScope Embedding 的向量记忆存储。

纯本地运行，ChromaDB 嵌入式模式，Embedding 通过 DashScope API 调用。
"""

from __future__ import annotations

import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from deep_research import logging as dr_logging
from deep_research.utils import load_config

logger = dr_logging.get_logger(__name__)

DEFAULT_COLLECTION = "research_memory"
_EMBEDDING_MODEL = "text-embedding-v4"
_EMBEDDING_DIMS = 1024


class VectorMemoryStore:
    """管理 ChromaDB 向量存储，负责记忆的增删查。"""

    def __init__(self, persist_dir: str | None = None, collection_name: str = DEFAULT_COLLECTION) -> None:
        persist_dir = persist_dir or os.path.join(os.getcwd(), "data", "chroma")
        os.makedirs(persist_dir, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._openai = self._build_embedding_client()
        logger.info("VectorMemoryStore initialized at %s (collection=%s)", persist_dir, collection_name)

    def _build_embedding_client(self) -> OpenAI:
        cfg = load_config(stage_name="prod")
        api_cfg = cfg.get("cognition", {}).get("openai", {})
        return OpenAI(
            api_key=api_cfg.get("api_key", ""),
            base_url=api_cfg.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """调用 DashScope Embedding API 获取向量。"""
        resp = self._openai.embeddings.create(model=_EMBEDDING_MODEL, input=texts)
        return [d.embedding for d in resp.data]

    def add_memory(self, doc_id: str, content: str, metadata: dict | None = None) -> None:
        """添加一条记忆到向量库。"""
        embedding = self._embed([content])
        self._collection.add(
            ids=[doc_id],
            embeddings=embedding,
            documents=[content],
            metadatas=[metadata or {}],
        )
        logger.info("Added memory: %s", doc_id)

    def search_memory(self, query: str, top_k: int = 3) -> list[dict]:
        """根据 query 检索最相关的历史记忆。"""
        if self._collection.count() == 0:
            return []
        query_embedding = self._embed([query])
        results = self._collection.query(query_embeddings=query_embedding, n_results=min(top_k, self._collection.count()))
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

    def count(self) -> int:
        return self._collection.count()
