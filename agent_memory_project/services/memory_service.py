from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent_memory_project import PROJECT_ROOT


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def tokenize(text: str) -> set[str]:
    normalized = text.lower()
    tokens: set[str] = set()

    latin_tokens = re.findall(r"[a-z0-9]+", normalized)
    tokens.update(token for token in latin_tokens if len(token) > 1)

    for chunk in re.findall(r"[\u4e00-\u9fff]+", normalized):
        if len(chunk) == 1:
            tokens.add(chunk)
            continue
        tokens.add(chunk)
        for index in range(len(chunk) - 1):
            tokens.add(chunk[index : index + 2])

    return tokens


@dataclass(slots=True)
class MemoryRecord:
    memory_id: str
    content: str
    source: str
    tags: list[str]
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "source": self.source,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryRecord":
        return cls(
            memory_id=payload["memory_id"],
            content=payload["content"],
            source=payload["source"],
            tags=list(payload.get("tags", [])),
            metadata=dict(payload.get("metadata", {})),
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            score=payload.get("score"),
        )


class MemoryService:
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or PROJECT_ROOT
        self.root_dir = self.project_root / "generated_memories"
        self.memories_dir = self.root_dir / "memories"
        self._ensure_layout()

    def list_memories(self) -> list[MemoryRecord]:
        items = [
            MemoryRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(self.memories_dir.glob("*.json"))
        ]
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    def remember(
        self,
        *,
        content: str,
        source: str = "unknown",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        normalized_content = " ".join(content.split())
        if not normalized_content:
            raise ValueError("Memory content must not be empty.")

        now = utc_now().isoformat()
        memory = MemoryRecord(
            memory_id=new_id("memory"),
            content=normalized_content,
            source=source.strip() or "unknown",
            tags=self._normalize_tags(tags or []),
            metadata=dict(metadata or {}),
            created_at=now,
            updated_at=now,
        )
        self._save_memory(memory)
        return memory

    def search_memories(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise ValueError("Query must not be empty.")

        query_tokens = tokenize(normalized_query)
        scored_items: list[MemoryRecord] = []
        for memory in self.list_memories():
            haystack_tokens = tokenize(memory.content)
            haystack_tokens.update(tokenize(" ".join(memory.tags)))
            overlap = query_tokens & haystack_tokens
            if not overlap:
                continue
            score = len(overlap) / max(len(query_tokens), 1)
            scored_items.append(
                MemoryRecord(
                    memory_id=memory.memory_id,
                    content=memory.content,
                    source=memory.source,
                    tags=memory.tags,
                    metadata=memory.metadata,
                    created_at=memory.created_at,
                    updated_at=memory.updated_at,
                    score=round(score, 4),
                )
            )

        scored_items.sort(
            key=lambda item: ((item.score or 0.0), item.updated_at),
            reverse=True,
        )
        return scored_items[:limit]

    def _save_memory(self, memory: MemoryRecord) -> None:
        payload = json.dumps(memory.to_dict(), ensure_ascii=False, indent=2)
        (self.memories_dir / f"{memory.memory_id}.json").write_text(
            payload,
            encoding="utf-8",
        )

    def _ensure_layout(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.memories_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in tags:
            value = tag.strip().lower()
            if value and value not in normalized:
                normalized.append(value)
        return normalized[:12]
