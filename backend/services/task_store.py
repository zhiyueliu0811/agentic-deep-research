"""任务持久化存储：SQLite（默认）/ MySQL（可选）。

通过 config.yml 中 database.backend 切换，默认 sqlite 零依赖启动。
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from abc import ABC, abstractmethod

import yaml

from deep_research import logging as dr_logging

logger = dr_logging.get_logger(__name__)

_BACKEND: TaskBackend | None = None
_lock = threading.Lock()


def _load_db_config() -> dict:
    try:
        with open("config.yml", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("stages", {}).get("prod", {}).get("database", {})
    except Exception:
        return {}


# ===== Abstract Backend =====

class TaskBackend(ABC):
    @abstractmethod
    def create_task(self, thread_id: str, query: str) -> dict: ...
    @abstractmethod
    def get_task(self, thread_id: str) -> dict | None: ...
    @abstractmethod
    def update_task(self, thread_id: str, **kwargs) -> None: ...
    @abstractmethod
    def list_tasks(self) -> list[dict]: ...


# ===== SQLite Backend =====

class SQLiteBackend(TaskBackend):
    def __init__(self, db_path: str = "data/tasks.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = __import__("sqlite3").connect(db_path, check_same_thread=False)
        self._conn.row_factory = __import__("sqlite3").Row
        self._init_schema()

    def _init_schema(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                thread_id TEXT PRIMARY KEY,
                query TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                stage TEXT NOT NULL DEFAULT '',
                draft_report TEXT NOT NULL DEFAULT '',
                final_report TEXT NOT NULL DEFAULT '',
                verification TEXT NOT NULL DEFAULT 'null',
                error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def create_task(self, thread_id: str, query: str) -> dict:
        now = datetime.now().isoformat()
        self._conn.execute(
            "INSERT INTO tasks (thread_id, query, status, stage, created_at, updated_at) VALUES (?, ?, 'pending', '', ?, ?)",
            (thread_id, query, now, now),
        )
        self._conn.commit()
        return {"thread_id": thread_id, "status": "pending", "created_at": now}

    def get_task(self, thread_id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM tasks WHERE thread_id = ?", (thread_id,)).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def update_task(self, thread_id: str, **kwargs):
        if not kwargs:
            return
        kwargs["updated_at"] = datetime.now().isoformat()
        if "verification" in kwargs and kwargs["verification"] is not None:
            kwargs["verification"] = json.dumps(kwargs["verification"], ensure_ascii=False)
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [thread_id]
        self._conn.execute(f"UPDATE tasks SET {set_clause} WHERE thread_id = ?", values)
        self._conn.commit()

    def list_tasks(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT thread_id, query, status, created_at, updated_at FROM tasks WHERE status != 'deleted' ORDER BY created_at DESC"
        ).fetchall()
        return [{"thread_id": r["thread_id"], "query": r["query"], "status": r["status"],
                  "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows]

    def _row_to_dict(self, row) -> dict:
        return {
            "thread_id": row["thread_id"], "query": row["query"],
            "status": row["status"], "stage": row["stage"],
            "draft_report": row["draft_report"], "final_report": row["final_report"],
            "verification": json.loads(row["verification"]) if row["verification"] and row["verification"] != "null" else None,
            "error": row["error"], "created_at": row["created_at"], "updated_at": row["updated_at"],
        }


# ===== MySQL Backend =====

class MySQLBackend(TaskBackend):
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        import pymysql
        self._conn = pymysql.connect(host=host, port=port, user=user, password=password,
                                      database=database, charset="utf8mb4")
        self._init_schema()

    def _init_schema(self):
        with self._conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    thread_id VARCHAR(32) PRIMARY KEY,
                    query TEXT NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    stage VARCHAR(50) NOT NULL DEFAULT '',
                    draft_report MEDIUMTEXT NOT NULL DEFAULT '',
                    final_report MEDIUMTEXT NOT NULL DEFAULT '',
                    verification JSON,
                    error TEXT NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        self._conn.commit()

    def create_task(self, thread_id: str, query: str) -> dict:
        now = datetime.now().isoformat()
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (thread_id, query, status, stage, created_at, updated_at) VALUES (%s, %s, 'pending', '', %s, %s)",
                (thread_id, query, now, now),
            )
        self._conn.commit()
        return {"thread_id": thread_id, "status": "pending", "created_at": now}

    def get_task(self, thread_id: str) -> dict | None:
        with self._conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE thread_id = %s", (thread_id,))
            row = cur.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def update_task(self, thread_id: str, **kwargs):
        if not kwargs:
            return
        kwargs["updated_at"] = datetime.now().isoformat()
        if "verification" in kwargs and kwargs["verification"] is not None:
            kwargs["verification"] = json.dumps(kwargs["verification"], ensure_ascii=False)
        set_clause = ", ".join(f"{k} = %s" for k in kwargs)
        values = list(kwargs.values()) + [thread_id]
        with self._conn.cursor() as cur:
            cur.execute(f"UPDATE tasks SET {set_clause} WHERE thread_id = %s", values)
        self._conn.commit()

    def list_tasks(self) -> list[dict]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT thread_id, query, status, created_at, updated_at FROM tasks WHERE status != 'deleted' ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
        return [{"thread_id": r[0], "query": r[1], "status": r[2],
                  "created_at": r[3], "updated_at": r[4]} for r in rows]

    def _row_to_dict(self, row) -> dict:
        cols = ["thread_id", "query", "status", "stage", "draft_report", "final_report",
                "verification", "error", "created_at", "updated_at"]
        d = dict(zip(cols, row))
        if d.get("verification") and d["verification"] != "null":
            d["verification"] = json.loads(d["verification"]) if isinstance(d["verification"], str) else d["verification"]
        else:
            d["verification"] = None
        return d


# ===== Public API =====

def _get_backend() -> TaskBackend:
    global _BACKEND
    if _BACKEND is None:
        with _lock:
            if _BACKEND is None:
                cfg = _load_db_config()
                backend = cfg.get("backend", "sqlite")
                if backend == "mysql":
                    mysql_cfg = cfg.get("mysql", {})
                    try:
                        _BACKEND = MySQLBackend(
                            host=mysql_cfg.get("host", "localhost"),
                            port=mysql_cfg.get("port", 3306),
                            user=mysql_cfg.get("user", "root"),
                            password=mysql_cfg.get("password", ""),
                            database=mysql_cfg.get("database", "deep_research"),
                        )
                        logger.info("MySQL backend connected (%s:%s)", mysql_cfg.get("host"), mysql_cfg.get("port"))
                    except Exception as e:
                        logger.warning("MySQL unavailable, falling back to SQLite: %s", e)
                        _BACKEND = SQLiteBackend(cfg.get("sqlite", {}).get("path", "data/tasks.db"))
                else:
                    _BACKEND = SQLiteBackend(cfg.get("sqlite", {}).get("path", "data/tasks.db"))
                    logger.info("SQLite backend ready")
    return _BACKEND


def create_task(thread_id: str, query: str) -> dict:
    return _get_backend().create_task(thread_id, query)


def get_task(thread_id: str) -> dict | None:
    return _get_backend().get_task(thread_id)


def update_task(thread_id: str, **kwargs):
    return _get_backend().update_task(thread_id, **kwargs)


def list_tasks() -> list[dict]:
    return _get_backend().list_tasks()
