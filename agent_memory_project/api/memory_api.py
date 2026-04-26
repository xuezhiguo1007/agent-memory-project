from __future__ import annotations

import logging

from fastapi import APIRouter

from agent_memory_project.api.schemas import (
    CommonRes,
    MemoryCreateReq,
    MemoryItem,
    MemorySearchReq,
    MemorySearchResult,
    ResCodeEnum,
)
from agent_memory_project.services.memory_service import MemoryService


class MemoryAPI:
    def __init__(self) -> None:
        self.router = APIRouter()
        self.service = MemoryService()
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/api/v1/memories",
            self.list_memories,
            methods=["GET"],
            response_model=CommonRes[list[MemoryItem]],
        )
        self.router.add_api_route(
            "/api/v1/memories",
            self.create_memory,
            methods=["POST"],
            response_model=CommonRes[MemoryItem],
        )
        self.router.add_api_route(
            "/api/v1/memories/search",
            self.search_memories,
            methods=["POST"],
            response_model=CommonRes[MemorySearchResult],
        )

    async def list_memories(self) -> CommonRes[list[MemoryItem]]:
        items = [
            MemoryItem(**memory.to_dict()) for memory in self.service.list_memories()
        ]
        return CommonRes.success(items)

    async def create_memory(self, req: MemoryCreateReq) -> CommonRes[MemoryItem]:
        logging.info("[create_memory] source=%s", req.source)
        try:
            memory = self.service.remember(
                content=req.content,
                source=req.source,
                tags=req.tags,
                metadata=req.metadata,
            )
            return CommonRes.success(MemoryItem(**memory.to_dict()))
        except Exception as exc:
            logging.exception("[create_memory] failed")
            return CommonRes.error(
                code=ResCodeEnum.COMMON_ERROR.code,
                message=str(exc),
            )

    async def search_memories(
        self,
        req: MemorySearchReq,
    ) -> CommonRes[MemorySearchResult]:
        logging.info("[search_memories] query=%s", req.query)
        try:
            items = self.service.search_memories(req.query, req.limit)
            return CommonRes.success(
                MemorySearchResult(
                    query=req.query,
                    total=len(items),
                    items=[MemoryItem(**memory.to_dict()) for memory in items],
                )
            )
        except Exception as exc:
            logging.exception("[search_memories] failed")
            return CommonRes.error(
                code=ResCodeEnum.COMMON_ERROR.code,
                message=str(exc),
            )
