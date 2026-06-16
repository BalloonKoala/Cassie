"""Long-term memory for Cassie."""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

DEFAULT_DB_PATH = "/opt/cassie/data/memory.db"

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "on",
    "at", "by", "for", "with", "from", "that", "this", "it", "i", "you",
    "we", "they", "he", "she", "my", "your", "our", "their", "hi", "hey",
    "and", "or", "but", "not", "so", "if", "what", "when", "where", "who",
    "how", "why", "me", "tell", "please", "thanks", "thank", "cassie",
}


class MemoryManager:
    def __init__(self, config: dict) -> None:
        cassie_cfg = config.get("cassie", {})
        self._max_retrieved: int = int(cassie_cfg.get("max_retrieved_memories", 5))
        db_path_str: str = config.get("database", {}).get("path", DEFAULT_DB_PATH)
        self._db_path = Path(db_path_str)
        self._conn: Optional[sqlite3.Connection] = None

    def open(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()
        log.info("Memory database opened: %s", self._db_path)

    def _create_schema(self) -> None:
        assert self._conn is not None
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                keywords TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memories_updated ON memories(updated_at DESC);
        """)

    def store_facts(self, facts: list[str]) -> None:
        if not facts:
            return
        assert self._conn is not None
        now = time.time()
        for fact in facts:
            fact = fact.strip()
            if not fact:
                continue
            keywords = " ".join(self._extract_keywords(fact))
            existing_id = self._find_conflicting_memory(keywords)
            if existing_id is not None:
                self._conn.execute(
                    "UPDATE memories SET content=?, keywords=?, updated_at=? WHERE id=?",
                    (fact, keywords, now, existing_id),
                )
                log.debug("Memory updated (id=%d): %r", existing_id, fact)
            else:
                self._conn.execute(
                    "INSERT INTO memories (content, keywords, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (fact, keywords, now, now),
                )
                log.debug("Memory stored: %r", fact)

    def _find_conflicting_memory(self, new_keywords: str) -> Optional[int]:
        assert self._conn is not None
        if not new_keywords or len(new_keywords) < 4:
            return None
        key = max(new_keywords.split(), key=len) if new_keywords else None
        if not key or len(key) < 4:
            return None
        row = self._conn.execute(
            "SELECT id FROM memories WHERE keywords LIKE ? ORDER BY updated_at DESC LIMIT 1",
            (f"%{key}%",),
        ).fetchone()
        return row["id"] if row else None

    def retrieve_relevant(self, text: str) -> list[str]:
        assert self._conn is not None
        query_keywords = set(self._extract_keywords(text))
        if not query_keywords:
            return self._get_recent_memories(self._max_retrieved)

        rows = self._conn.execute(
            "SELECT id, content, keywords FROM memories ORDER BY updated_at DESC LIMIT 200"
        ).fetchall()

        scored: list[tuple[float, str]] = []
        for row in rows:
            mem_keywords = set(row["keywords"].split())
            overlap = len(query_keywords & mem_keywords)
            if overlap > 0:
                scored.append((overlap, row["content"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [content for _, content in scored[: self._max_retrieved]]

        if len(top) < self._max_retrieved:
            recent = self._get_recent_memories(self._max_retrieved - len(top))
            top_set = set(top)
            for mem in recent:
                if mem not in top_set:
                    top.append(mem)

        log.debug("Retrieved %d memories for query: %r", len(top), text[:50])
        return top

    def _get_recent_memories(self, limit: int) -> list[str]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT content FROM memories ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [row["content"] for row in rows]

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z]+", text.lower())
        return [
            w for w in words
            if len(w) > 2 and w not in STOPWORDS
        ]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
            log.info("Memory database closed")
