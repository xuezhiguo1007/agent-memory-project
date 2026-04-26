from __future__ import annotations

import logging

from fastapi import APIRouter, Path, Query

from agent_memory_project.api.schemas import (
    CommonRes,
    ExtractionSuggestionItem,
    MaterializeSuggestionReq,
    MaterializeSuggestionResult,
    PersistentEntryActionReq,
    PersistentPromptBlock,
    PersistentRemoveReq,
    PersistentReplaceReq,
    PersistentStoreState,
    ResCodeEnum,
    SessionExtractReq,
    SessionExtractResult,
    SessionEventCreateReq,
    SessionEventItem,
    SessionSearchReq,
    SessionSearchResult,
    SkillCatalogItem,
    SkillCreateReq,
    SkillItem,
    SkillMatchReq,
    SkillMatchResult,
)
from agent_memory_project.services.memory_orchestrator_service import (
    MemoryOrchestratorService,
)
from agent_memory_project.services.persistent_memory_service import (
    PersistentMemoryService,
)
from agent_memory_project.services.session_search_service import SessionSearchService
from agent_memory_project.services.skill_service import SkillService


class MemoryAPI:
    def __init__(self) -> None:
        self.router = APIRouter()
        self.persistent_service = PersistentMemoryService()
        self.skill_service = SkillService()
        self.session_service = SessionSearchService()
        self.orchestrator_service = MemoryOrchestratorService()
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/api/v1/persistent-memory",
            self.get_persistent_store,
            methods=["GET"],
            response_model=CommonRes[PersistentStoreState],
        )
        self.router.add_api_route(
            "/api/v1/persistent-memory/add",
            self.add_persistent_entry,
            methods=["POST"],
            response_model=CommonRes[PersistentStoreState],
        )
        self.router.add_api_route(
            "/api/v1/persistent-memory/replace",
            self.replace_persistent_entry,
            methods=["POST"],
            response_model=CommonRes[PersistentStoreState],
        )
        self.router.add_api_route(
            "/api/v1/persistent-memory/remove",
            self.remove_persistent_entry,
            methods=["POST"],
            response_model=CommonRes[PersistentStoreState],
        )
        self.router.add_api_route(
            "/api/v1/persistent-memory/prompt-block",
            self.get_persistent_prompt_block,
            methods=["GET"],
            response_model=CommonRes[PersistentPromptBlock],
        )
        self.router.add_api_route(
            "/api/v1/skills/catalog",
            self.list_skill_catalog,
            methods=["GET"],
            response_model=CommonRes[list[SkillCatalogItem]],
        )
        self.router.add_api_route(
            "/api/v1/skills",
            self.list_skills,
            methods=["GET"],
            response_model=CommonRes[list[SkillItem]],
        )
        self.router.add_api_route(
            "/api/v1/skills",
            self.create_skill,
            methods=["POST"],
            response_model=CommonRes[SkillItem],
        )
        self.router.add_api_route(
            "/api/v1/skills/match",
            self.match_skills,
            methods=["POST"],
            response_model=CommonRes[SkillMatchResult],
        )
        self.router.add_api_route(
            "/api/v1/skills/{slug}",
            self.view_skill,
            methods=["GET"],
            response_model=CommonRes[SkillItem],
        )
        self.router.add_api_route(
            "/api/v1/sessions",
            self.list_sessions,
            methods=["GET"],
            response_model=CommonRes[list[str]],
        )
        self.router.add_api_route(
            "/api/v1/sessions/{session_id}/events",
            self.list_session_events,
            methods=["GET"],
            response_model=CommonRes[list[SessionEventItem]],
        )
        self.router.add_api_route(
            "/api/v1/sessions/{session_id}/events",
            self.append_session_event,
            methods=["POST"],
            response_model=CommonRes[SessionEventItem],
        )
        self.router.add_api_route(
            "/api/v1/sessions/{session_id}/search",
            self.search_session,
            methods=["POST"],
            response_model=CommonRes[SessionSearchResult],
        )
        self.router.add_api_route(
            "/api/v1/sessions/{session_id}/extract",
            self.extract_session_memory,
            methods=["POST"],
            response_model=CommonRes[SessionExtractResult],
        )
        self.router.add_api_route(
            "/api/v1/sessions/{session_id}/materialize",
            self.materialize_suggestion,
            methods=["POST"],
            response_model=CommonRes[MaterializeSuggestionResult],
        )

    async def get_persistent_store(
        self,
        target: str = Query(...),
    ) -> CommonRes[PersistentStoreState]:
        try:
            state = self.persistent_service.get_store_state(target)
            return CommonRes.success(PersistentStoreState(**state))
        except Exception as exc:
            return self._error("get_persistent_store", exc)

    async def add_persistent_entry(
        self,
        req: PersistentEntryActionReq,
    ) -> CommonRes[PersistentStoreState]:
        try:
            state = self.persistent_service.add_entry(req.target, req.content)
            return CommonRes.success(PersistentStoreState(**state))
        except Exception as exc:
            return self._error("add_persistent_entry", exc)

    async def replace_persistent_entry(
        self,
        req: PersistentReplaceReq,
    ) -> CommonRes[PersistentStoreState]:
        try:
            state = self.persistent_service.replace_entry(
                req.target,
                req.old_text,
                req.content,
            )
            return CommonRes.success(PersistentStoreState(**state))
        except Exception as exc:
            return self._error("replace_persistent_entry", exc)

    async def remove_persistent_entry(
        self,
        req: PersistentRemoveReq,
    ) -> CommonRes[PersistentStoreState]:
        try:
            state = self.persistent_service.remove_entry(req.target, req.old_text)
            return CommonRes.success(PersistentStoreState(**state))
        except Exception as exc:
            return self._error("remove_persistent_entry", exc)

    async def get_persistent_prompt_block(self) -> CommonRes[PersistentPromptBlock]:
        try:
            block = self.persistent_service.render_system_prompt_block()
            return CommonRes.success(PersistentPromptBlock(prompt_block=block))
        except Exception as exc:
            return self._error("get_persistent_prompt_block", exc)

    async def list_skills(self) -> CommonRes[list[SkillItem]]:
        try:
            items = [
                SkillItem(**skill.to_dict())
                for skill in self.skill_service.list_skills()
            ]
            return CommonRes.success(items)
        except Exception as exc:
            return self._error("list_skills", exc)

    async def list_skill_catalog(self) -> CommonRes[list[SkillCatalogItem]]:
        try:
            items = [
                SkillCatalogItem(**item)
                for item in self.skill_service.list_skill_catalog()
            ]
            return CommonRes.success(items)
        except Exception as exc:
            return self._error("list_skill_catalog", exc)

    async def create_skill(self, req: SkillCreateReq) -> CommonRes[SkillItem]:
        try:
            skill = self.skill_service.save_skill(
                skill_name=req.skill_name,
                description=req.description,
                triggers=req.triggers,
                steps=req.steps,
                examples=req.examples,
                metadata=req.metadata,
            )
            return CommonRes.success(SkillItem(**skill.to_dict()))
        except Exception as exc:
            return self._error("create_skill", exc)

    async def match_skills(self, req: SkillMatchReq) -> CommonRes[SkillMatchResult]:
        try:
            items = self.skill_service.match_skills(req.query, req.limit)
            return CommonRes.success(
                SkillMatchResult(
                    query=req.query,
                    total=len(items),
                    items=[SkillItem(**skill.to_dict()) for skill in items],
                )
            )
        except Exception as exc:
            return self._error("match_skills", exc)

    async def view_skill(
        self,
        slug: str = Path(...),
    ) -> CommonRes[SkillItem]:
        try:
            skill = self.skill_service.view_skill(slug)
            return CommonRes.success(SkillItem(**skill.to_dict()))
        except Exception as exc:
            return self._error("view_skill", exc)

    async def list_sessions(self) -> CommonRes[list[str]]:
        try:
            return CommonRes.success(self.session_service.list_sessions())
        except Exception as exc:
            return self._error("list_sessions", exc)

    async def list_session_events(
        self,
        session_id: str = Path(...),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> CommonRes[list[SessionEventItem]]:
        try:
            items = self.session_service.list_events(session_id, limit)
            return CommonRes.success(
                [SessionEventItem(**item.to_dict()) for item in items]
            )
        except Exception as exc:
            return self._error("list_session_events", exc)

    async def append_session_event(
        self,
        req: SessionEventCreateReq,
        session_id: str = Path(...),
    ) -> CommonRes[SessionEventItem]:
        try:
            item = self.session_service.append_event(session_id, req.role, req.content)
            return CommonRes.success(SessionEventItem(**item.to_dict()))
        except Exception as exc:
            return self._error("append_session_event", exc)

    async def search_session(
        self,
        req: SessionSearchReq,
        session_id: str = Path(...),
    ) -> CommonRes[SessionSearchResult]:
        try:
            items, summary = self.session_service.search_events(
                session_id, req.query, req.limit
            )
            return CommonRes.success(
                SessionSearchResult(
                    session_id=session_id,
                    query=req.query,
                    total=len(items),
                    summary=summary,
                    items=[SessionEventItem(**item.to_dict()) for item in items],
                )
            )
        except Exception as exc:
            return self._error("search_session", exc)

    async def extract_session_memory(
        self,
        req: SessionExtractReq,
        session_id: str = Path(...),
    ) -> CommonRes[SessionExtractResult]:
        try:
            if req.query:
                items, _ = self.session_service.search_events(
                    session_id, req.query, req.limit
                )
            else:
                items = self.session_service.list_events(session_id, req.limit)
            summary = self.orchestrator_service.summarize_events(items)
            suggestions = self.orchestrator_service.extract_suggestions(items)
            return CommonRes.success(
                SessionExtractResult(
                    session_id=session_id,
                    summary=summary,
                    suggestions=[
                        ExtractionSuggestionItem(**item.to_dict())
                        for item in suggestions
                    ],
                )
            )
        except Exception as exc:
            return self._error("extract_session_memory", exc)

    async def materialize_suggestion(
        self,
        req: MaterializeSuggestionReq,
        session_id: str = Path(...),
    ) -> CommonRes[MaterializeSuggestionResult]:
        try:
            kind = req.kind.strip().lower()
            if kind == "persistent_user":
                payload = self.persistent_service.add_entry("user", req.content)
                return CommonRes.success(
                    MaterializeSuggestionResult(
                        destination="persistent:user", payload=payload
                    )
                )
            if kind == "persistent_memory":
                payload = self.persistent_service.add_entry("memory", req.content)
                return CommonRes.success(
                    MaterializeSuggestionResult(
                        destination="persistent:memory", payload=payload
                    )
                )
            if kind == "skill":
                payload = self.skill_service.save_skill(
                    skill_name=req.title,
                    description=req.content,
                    metadata={"source_session_id": session_id},
                ).to_dict()
                return CommonRes.success(
                    MaterializeSuggestionResult(destination="skills", payload=payload)
                )
            raise ValueError(f"Unsupported suggestion kind: {req.kind}")
        except Exception as exc:
            return self._error("materialize_suggestion", exc)

    def _error(self, label: str, exc: Exception):
        logging.exception("[%s] failed", label)
        return CommonRes.error(
            code=ResCodeEnum.COMMON_ERROR.code,
            message=str(exc),
        )
