from __future__ import annotations

import json
from dataclasses import dataclass

from agent_memory_project.llm.openai_client import (
    create_chat_model,
    require_openai_config,
)
from agent_memory_project.services.session_search_service import SessionEvent


@dataclass(slots=True)
class ExtractionSuggestion:
    kind: str
    title: str
    content: str
    rationale: str

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "title": self.title,
            "content": self.content,
            "rationale": self.rationale,
        }


class MemoryOrchestratorService:
    def summarize_events(self, events: list[SessionEvent]) -> str:
        if not events:
            return ""

        try:
            require_openai_config()
        except RuntimeError:
            return self._fallback_summary(events)
        return self._llm_summary(events)

    def extract_suggestions(
        self, events: list[SessionEvent]
    ) -> list[ExtractionSuggestion]:
        if not events:
            return []

        try:
            require_openai_config()
        except RuntimeError:
            return self._fallback_suggestions(events)
        return self._llm_suggestions(events)

    def _fallback_summary(self, events: list[SessionEvent]) -> str:
        snippets = [f"[{event.role}] {event.content}" for event in events[:3]]
        return " | ".join(snippets)

    def _fallback_suggestions(
        self, events: list[SessionEvent]
    ) -> list[ExtractionSuggestion]:
        suggestions: list[ExtractionSuggestion] = []
        for event in events:
            content = event.content
            lowered = content.lower()
            if any(keyword in content for keyword in ("偏好", "喜欢", "不喜欢")):
                suggestions.append(
                    ExtractionSuggestion(
                        kind="persistent_user",
                        title="User Preference",
                        content=content,
                        rationale="Detected a stable user preference signal in session history.",
                    )
                )
            if any(
                keyword in content
                for keyword in ("约定", "环境", "配置", "workflow", "convention")
            ):
                suggestions.append(
                    ExtractionSuggestion(
                        kind="persistent_memory",
                        title="Environment or Convention",
                        content=content,
                        rationale="Detected an environment fact or project convention worth persisting.",
                    )
                )
            if any(
                keyword in lowered
                for keyword in ("步骤", "workflow", "checklist", "process", "run tests")
            ):
                suggestions.append(
                    ExtractionSuggestion(
                        kind="skill",
                        title="Reusable Workflow",
                        content=content,
                        rationale="Detected reusable procedural guidance that may belong in a skill.",
                    )
                )
        deduped: list[ExtractionSuggestion] = []
        seen: set[tuple[str, str]] = set()
        for suggestion in suggestions:
            key = (suggestion.kind, suggestion.content)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(suggestion)
        return deduped[:10]

    def _llm_summary(self, events: list[SessionEvent]) -> str:
        model = create_chat_model()
        transcript = "\n".join(f"[{event.role}] {event.content}" for event in events)
        prompt = (
            "Summarize the following session fragments in 2-4 concise sentences. "
            "Focus on decisions, preferences, conventions, and reusable workflow details.\n\n"
            f"{transcript}"
        )
        response = model.invoke(prompt)
        return str(response.content).strip()

    def _llm_suggestions(
        self, events: list[SessionEvent]
    ) -> list[ExtractionSuggestion]:
        model = create_chat_model()
        transcript = "\n".join(f"[{event.role}] {event.content}" for event in events)
        prompt = (
            "Extract high-value memory suggestions from the session fragments below.\n"
            "Return strict JSON as a list of objects with keys: kind, title, content, rationale.\n"
            "Allowed kinds: persistent_user, persistent_memory, skill.\n"
            "Only include stable facts, preferences, conventions, or reusable workflows.\n\n"
            f"{transcript}"
        )
        response = model.invoke(prompt)
        payload = json.loads(str(response.content))
        suggestions: list[ExtractionSuggestion] = []
        for item in payload:
            suggestions.append(
                ExtractionSuggestion(
                    kind=str(item["kind"]),
                    title=str(item["title"]),
                    content=str(item["content"]),
                    rationale=str(item["rationale"]),
                )
            )
        return suggestions[:10]
