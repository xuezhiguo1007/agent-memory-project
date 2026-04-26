from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from agent_memory_project import PROJECT_ROOT

ENTRY_SEPARATOR = "\n§\n"


@dataclass(slots=True)
class PersistentStore:
    target: str
    path: Path
    char_limit: int
    title: str


class PersistentMemoryService:
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or PROJECT_ROOT
        self.hermes_root = self.project_root / "generated_memories" / "hermes"
        self.memories_dir = self.hermes_root / "memories"
        self.stores = {
            "memory": PersistentStore(
                target="memory",
                path=self.memories_dir / "MEMORY.md",
                char_limit=2200,
                title="MEMORY",
            ),
            "user": PersistentStore(
                target="user",
                path=self.memories_dir / "USER.md",
                char_limit=1375,
                title="USER PROFILE",
            ),
        }
        self._ensure_layout()

    def list_entries(self, target: str) -> list[str]:
        store = self._store(target)
        content = store.path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        return [
            entry.strip() for entry in content.split(ENTRY_SEPARATOR) if entry.strip()
        ]

    def add_entry(self, target: str, content: str) -> dict[str, object]:
        normalized = self._normalize_entry(content)
        entries = self.list_entries(target)
        updated_entries = self._merge_entries(entries, normalized)
        self._write_entries(target, updated_entries)
        return self.get_store_state(target)

    def replace_entry(
        self, target: str, old_text: str, content: str
    ) -> dict[str, object]:
        normalized = self._normalize_entry(content)
        updated_entries = self._replace_or_remove(
            target, old_text, replacement=normalized
        )
        self._write_entries(target, updated_entries)
        return self.get_store_state(target)

    def remove_entry(self, target: str, old_text: str) -> dict[str, object]:
        updated_entries = self._replace_or_remove(target, old_text, replacement=None)
        self._write_entries(target, updated_entries)
        return self.get_store_state(target)

    def get_store_state(self, target: str) -> dict[str, object]:
        store = self._store(target)
        entries = self.list_entries(target)
        used = len(self._serialize_entries(entries))
        return {
            "target": target,
            "entries": entries,
            "usage": f"{used}/{store.char_limit}",
            "used_chars": used,
            "char_limit": store.char_limit,
            "snapshot": self.render_snapshot(target),
        }

    def render_snapshot(self, target: str) -> str:
        store = self._store(target)
        entries = self.list_entries(target)
        used = len(self._serialize_entries(entries))
        percentage = int((used / store.char_limit) * 100) if store.char_limit else 0
        lines = [
            "══════════════════════════════════════════════",
            f"{store.title} [{percentage}% - {used}/{store.char_limit} chars]",
            "══════════════════════════════════════════════",
        ]
        if not entries:
            lines.append("(empty)")
            return "\n".join(lines)
        lines.append("\n§\n".join(entries))
        return "\n".join(lines)

    def render_system_prompt_block(self) -> str:
        return "\n\n".join(
            [
                self.render_snapshot("memory"),
                self.render_snapshot("user"),
            ]
        )

    def _replace_or_remove(
        self,
        target: str,
        old_text: str,
        replacement: str | None,
    ) -> list[str]:
        needle = old_text.strip()
        if not needle:
            raise ValueError("old_text must not be empty.")

        entries = self.list_entries(target)
        matched = [entry for entry in entries if needle in entry]
        if not matched:
            raise ValueError(f"No entry matched substring: {old_text}")
        if len(matched) > 1:
            raise ValueError(f"Substring matched multiple entries: {old_text}")

        updated: list[str] = []
        for entry in entries:
            if needle not in entry:
                updated.append(entry)
                continue
            if replacement is not None:
                updated.append(replacement)
        return updated

    def _write_entries(self, target: str, entries: list[str]) -> None:
        store = self._store(target)
        payload = self._serialize_entries(entries)
        if len(payload) > store.char_limit:
            raise ValueError(
                f"{store.title} at {len(self._serialize_entries(self.list_entries(target)))}/"
                f"{store.char_limit} chars. Adding this entry would exceed the limit."
            )
        store.path.write_text(payload, encoding="utf-8")

    def _store(self, target: str) -> PersistentStore:
        value = target.strip().lower()
        if value not in self.stores:
            supported = ", ".join(sorted(self.stores))
            raise ValueError(f"Unsupported target: {target}. Use one of: {supported}.")
        return self.stores[value]

    def _normalize_entry(self, content: str) -> str:
        normalized = "\n".join(
            line.rstrip() for line in content.strip().splitlines()
        ).strip()
        if not normalized:
            raise ValueError("Memory content must not be empty.")
        return normalized

    def _merge_entries(self, entries: list[str], new_entry: str) -> list[str]:
        if not entries:
            return [new_entry]

        new_tokens = self._tokens(new_entry)
        updated = list(entries)
        for index, entry in enumerate(entries):
            current_tokens = self._tokens(entry)
            overlap = new_tokens & current_tokens
            similarity = len(overlap) / max(
                min(len(new_tokens), len(current_tokens)), 1
            )

            if new_entry == entry or new_entry in entry:
                return updated
            if entry in new_entry:
                updated[index] = new_entry
                return updated
            if similarity >= 0.75:
                updated[index] = self._prefer_richer_entry(entry, new_entry)
                return updated

        updated.append(new_entry)
        return updated

    def _prefer_richer_entry(self, left: str, right: str) -> str:
        left_score = (len(self._tokens(left)), len(left))
        right_score = (len(self._tokens(right)), len(right))
        return right if right_score >= left_score else left

    def _tokens(self, text: str) -> set[str]:
        normalized = text.lower()
        latin_tokens = re.findall(r"[a-z0-9]+", normalized)
        chinese_chunks = re.findall(r"[\u4e00-\u9fff]+", normalized)
        tokens = {token for token in latin_tokens if len(token) > 1}
        for chunk in chinese_chunks:
            tokens.add(chunk)
            for index in range(len(chunk) - 1):
                tokens.add(chunk[index : index + 2])
        return tokens

    def _serialize_entries(self, entries: list[str]) -> str:
        if not entries:
            return ""
        return ENTRY_SEPARATOR.join(entries)

    def _ensure_layout(self) -> None:
        self.hermes_root.mkdir(parents=True, exist_ok=True)
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        for store in self.stores.values():
            store.path.touch(exist_ok=True)
