from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_memory_project import PROJECT_ROOT


def tokenize(text: str) -> set[str]:
    normalized = text.lower()
    latin_tokens = re.findall(r"[a-z0-9]+", normalized)
    chinese_chunks = re.findall(r"[\u4e00-\u9fff]+", normalized)
    tokens = {token for token in latin_tokens if len(token) > 1}
    for chunk in chinese_chunks:
        tokens.add(chunk)
        for index in range(len(chunk) - 1):
            tokens.add(chunk[index : index + 2])
    return tokens


@dataclass(slots=True)
class SkillRecord:
    slug: str
    skill_name: str
    description: str
    triggers: list[str]
    steps: list[str]
    examples: list[str]
    content: str
    metadata: dict[str, Any]
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "skill_name": self.skill_name,
            "description": self.description,
            "triggers": self.triggers,
            "steps": self.steps,
            "examples": self.examples,
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score,
        }


class SkillService:
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or PROJECT_ROOT
        self.hermes_root = self.project_root / "generated_memories" / "hermes"
        self.skills_dir = self.hermes_root / "skills"
        self._ensure_layout()

    def save_skill(
        self,
        *,
        skill_name: str,
        description: str,
        triggers: list[str] | None = None,
        steps: list[str] | None = None,
        examples: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SkillRecord:
        slug = self._slug(skill_name)
        record = SkillRecord(
            slug=slug,
            skill_name=skill_name.strip(),
            description=description.strip(),
            triggers=self._clean_list(triggers or []),
            steps=self._clean_list(steps or []),
            examples=self._clean_list(examples or []),
            content="",
            metadata=dict(metadata or {}),
        )
        if not record.skill_name or not record.description:
            raise ValueError("skill_name and description are required.")

        skill_dir = self.skills_dir / slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md = self._render_skill_md(record)
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
        (skill_dir / "metadata.json").write_text(
            json.dumps(
                record.to_dict() | {"content": skill_md}, ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        record.content = skill_md
        return record

    def list_skills(self) -> list[SkillRecord]:
        items: list[SkillRecord] = []
        for skill_dir in sorted(
            path for path in self.skills_dir.iterdir() if path.is_dir()
        ):
            metadata_path = skill_dir / "metadata.json"
            if not metadata_path.exists():
                continue
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            items.append(
                SkillRecord(
                    slug=payload.get("slug", skill_dir.name),
                    skill_name=payload["skill_name"],
                    description=payload["description"],
                    triggers=list(payload.get("triggers", [])),
                    steps=list(payload.get("steps", [])),
                    examples=list(payload.get("examples", [])),
                    content=payload.get("content", ""),
                    metadata=dict(payload.get("metadata", {})),
                    score=payload.get("score"),
                )
            )
        return items

    def list_skill_catalog(self) -> list[dict[str, Any]]:
        catalog: list[dict[str, Any]] = []
        for skill in self.list_skills():
            catalog.append(
                {
                    "slug": skill.slug,
                    "skill_name": skill.skill_name,
                    "description": skill.description,
                    "triggers": skill.triggers,
                }
            )
        return catalog

    def view_skill(self, slug: str) -> SkillRecord:
        normalized_slug = self._slug(slug)
        metadata_path = self.skills_dir / normalized_slug / "metadata.json"
        if not metadata_path.exists():
            raise ValueError(f"Skill not found: {slug}")
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        return SkillRecord(
            slug=payload.get("slug", normalized_slug),
            skill_name=payload["skill_name"],
            description=payload["description"],
            triggers=list(payload.get("triggers", [])),
            steps=list(payload.get("steps", [])),
            examples=list(payload.get("examples", [])),
            content=payload.get("content", ""),
            metadata=dict(payload.get("metadata", {})),
            score=payload.get("score"),
        )

    def match_skills(self, query: str, limit: int = 5) -> list[SkillRecord]:
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise ValueError("Query must not be empty.")

        query_tokens = tokenize(normalized_query)
        scored: list[SkillRecord] = []
        for skill in self.list_skills():
            haystack = " ".join(
                [
                    skill.skill_name,
                    skill.description,
                    " ".join(skill.triggers),
                    skill.content,
                ]
            )
            overlap = query_tokens & tokenize(haystack)
            if not overlap:
                continue
            score = round(len(overlap) / max(len(query_tokens), 1), 4)
            scored.append(
                SkillRecord(
                    slug=skill.slug,
                    skill_name=skill.skill_name,
                    description=skill.description,
                    triggers=skill.triggers,
                    steps=skill.steps,
                    examples=skill.examples,
                    content=skill.content,
                    metadata=skill.metadata,
                    score=score,
                )
            )
        scored.sort(key=lambda item: (item.score or 0.0, item.skill_name), reverse=True)
        return scored[:limit]

    def _render_skill_md(self, record: SkillRecord) -> str:
        lines = [f"# {record.skill_name}", "", record.description]
        if record.triggers:
            lines.extend(
                ["", "## Triggers", *[f"- {item}" for item in record.triggers]]
            )
        if record.steps:
            lines.extend(
                [
                    "",
                    "## Steps",
                    *[
                        f"{index}. {step}"
                        for index, step in enumerate(record.steps, start=1)
                    ],
                ]
            )
        if record.examples:
            lines.extend(
                ["", "## Examples", *[f"- {item}" for item in record.examples]]
            )
        return "\n".join(lines).strip() + "\n"

    def _clean_list(self, values: list[str]) -> list[str]:
        items: list[str] = []
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in items:
                items.append(normalized)
        return items

    def _slug(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
        return slug.strip("-") or "skill"

    def _ensure_layout(self) -> None:
        self.hermes_root.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
