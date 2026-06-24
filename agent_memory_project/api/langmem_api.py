"""
Langmem Memory API - PostgreSQL 实现的 LangChain 风格记忆管理 API 路由
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Path, Query

from agent_memory_project.api.schemas import (
    CommonRes,
    LangmemCompressResult,
    LangmemConfig,
    LangmemConfigUpdateReq,
    LangmemEntityCreateReq,
    LangmemEntityItem,
    LangmemMemorySnapshot,
    LangmemMessageCreateReq,
    LangmemMessageItem,
    LangmemSearchReq,
    LangmemSearchResult,
    LangmemSessionInfo,
    ResCodeEnum,
)
from agent_memory_project.services.langmem_service import LangmemService


class LangmemAPI:
    def __init__(self) -> None:
        self.router = APIRouter()
        self.langmem_service = LangmemService()
        self._register_routes()

    def _register_routes(self) -> None:
        # 消息管理
        self.router.add_api_route(
            "/api/v1/langmem/messages",
            self.add_message,
            methods=["POST"],
            response_model=CommonRes[LangmemMessageItem],
        )
        self.router.add_api_route(
            "/api/v1/langmem/sessions/{session_id}/messages",
            self.list_messages,
            methods=["GET"],
            response_model=CommonRes[list[LangmemMessageItem]],
        )
        self.router.add_api_route(
            "/api/v1/langmem/sessions/{session_id}/search",
            self.search_messages,
            methods=["POST"],
            response_model=CommonRes[LangmemSearchResult],
        )
        self.router.add_api_route(
            "/api/v1/langmem/sessions/{session_id}/count",
            self.get_message_count,
            methods=["GET"],
            response_model=CommonRes[dict[str, int]],
        )
        self.router.add_api_route(
            "/api/v1/langmem/sessions/{session_id}/clear",
            self.clear_session,
            methods=["DELETE"],
            response_model=CommonRes[dict[str, int]],
        )

        # 实体管理
        self.router.add_api_route(
            "/api/v1/langmem/entities",
            self.add_entity,
            methods=["POST"],
            response_model=CommonRes[LangmemEntityItem],
        )
        self.router.add_api_route(
            "/api/v1/langmem/entities",
            self.list_entities,
            methods=["GET"],
            response_model=CommonRes[list[LangmemEntityItem]],
        )
        self.router.add_api_route(
            "/api/v1/langmem/entities/search",
            self.search_entities,
            methods=["POST"],
            response_model=CommonRes[list[LangmemEntityItem]],
        )

        # 记忆快照与压缩
        self.router.add_api_route(
            "/api/v1/langmem/sessions/{session_id}/snapshot",
            self.get_memory_snapshot,
            methods=["GET"],
            response_model=CommonRes[LangmemMemorySnapshot],
        )
        self.router.add_api_route(
            "/api/v1/langmem/sessions/{session_id}/compress",
            self.compress_memory,
            methods=["POST"],
            response_model=CommonRes[LangmemCompressResult],
        )

        # 会话与配置管理
        self.router.add_api_route(
            "/api/v1/langmem/sessions",
            self.list_sessions,
            methods=["GET"],
            response_model=CommonRes[list[LangmemSessionInfo]],
        )
        self.router.add_api_route(
            "/api/v1/langmem/config",
            self.get_config,
            methods=["GET"],
            response_model=CommonRes[LangmemConfig],
        )
        self.router.add_api_route(
            "/api/v1/langmem/config",
            self.update_config,
            methods=["PUT"],
            response_model=CommonRes[LangmemConfig],
        )

        # 连接管理
        self.router.add_api_route(
            "/api/v1/langmem/connect",
            self.connect,
            methods=["POST"],
            response_model=CommonRes[dict[str, str]],
        )
        self.router.add_api_route(
            "/api/v1/langmem/disconnect",
            self.disconnect,
            methods=["POST"],
            response_model=CommonRes[dict[str, str]],
        )

    # ==================== 连接管理 ====================

    async def connect(self) -> CommonRes[dict[str, str]]:
        """连接到 PostgreSQL 数据库"""
        try:
            await self.langmem_service.initialize()
            return CommonRes.success({"status": "connected", "message": "Successfully connected to PostgreSQL"})
        except Exception as exc:
            return self._error("connect", exc)

    async def disconnect(self) -> CommonRes[dict[str, str]]:
        """断开 PostgreSQL 连接"""
        try:
            await self.langmem_service.close()
            return CommonRes.success({"status": "disconnected", "message": "Successfully disconnected from PostgreSQL"})
        except Exception as exc:
            return self._error("disconnect", exc)

    # ==================== 消息管理 ====================

    async def add_message(
        self,
        req: LangmemMessageCreateReq,
    ) -> CommonRes[LangmemMessageItem]:
        """添加消息到会话"""
        try:
            await self.langmem_service.initialize()
            message = await self.langmem_service.add_message(
                req.session_id, req.role, req.content, req.metadata
            )
            return CommonRes.success(LangmemMessageItem(**message.to_dict()))
        except Exception as exc:
            return self._error("add_message", exc)

    async def list_messages(
        self,
        session_id: str = Path(...),
        limit: int = Query(default=None, ge=1, le=500),
    ) -> CommonRes[list[LangmemMessageItem]]:
        """列出会话的所有消息"""
        try:
            await self.langmem_service.initialize()
            messages = await self.langmem_service.list_messages(session_id, limit)
            return CommonRes.success(
                [LangmemMessageItem(**msg.to_dict()) for msg in messages]
            )
        except Exception as exc:
            return self._error("list_messages", exc)

    async def search_messages(
        self,
        req: LangmemSearchReq,
        session_id: str = Path(...),
    ) -> CommonRes[LangmemSearchResult]:
        """搜索会话消息"""
        try:
            await self.langmem_service.initialize()
            messages, summary = await self.langmem_service.search_messages(
                session_id, req.query, req.limit
            )
            return CommonRes.success(
                LangmemSearchResult(
                    session_id=session_id,
                    query=req.query,
                    total=len(messages),
                    summary=summary,
                    items=[LangmemMessageItem(**msg.to_dict()) for msg in messages],
                )
            )
        except Exception as exc:
            return self._error("search_messages", exc)

    async def get_message_count(
        self,
        session_id: str = Path(...),
    ) -> CommonRes[dict[str, int]]:
        """获取会话消息数量"""
        try:
            await self.langmem_service.initialize()
            count = await self.langmem_service.get_message_count(session_id)
            return CommonRes.success({"session_id": session_id, "count": count})
        except Exception as exc:
            return self._error("get_message_count", exc)

    async def clear_session(
        self,
        session_id: str = Path(...),
    ) -> CommonRes[dict[str, int]]:
        """清空会话的所有消息"""
        try:
            await self.langmem_service.initialize()
            deleted_count = await self.langmem_service.clear_session(session_id)
            return CommonRes.success(
                {"session_id": session_id, "deleted_count": deleted_count}
            )
        except Exception as exc:
            return self._error("clear_session", exc)

    # ==================== 实体管理 ====================

    async def add_entity(
        self,
        req: LangmemEntityCreateReq,
    ) -> CommonRes[LangmemEntityItem]:
        """添加或更新实体"""
        try:
            await self.langmem_service.initialize()
            entity = await self.langmem_service.add_entity(
                req.entity_name, req.entity_type, req.description, req.metadata
            )
            return CommonRes.success(LangmemEntityItem(**entity.to_dict()))
        except Exception as exc:
            return self._error("add_entity", exc)

    async def list_entities(
        self,
        entity_type: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> CommonRes[list[LangmemEntityItem]]:
        """列出所有实体"""
        try:
            await self.langmem_service.initialize()
            entities = await self.langmem_service.list_entities(entity_type, limit)
            return CommonRes.success(
                [LangmemEntityItem(**entity.to_dict()) for entity in entities]
            )
        except Exception as exc:
            return self._error("list_entities", exc)

    async def search_entities(
        self,
        req: LangmemSearchReq,
    ) -> CommonRes[list[LangmemEntityItem]]:
        """搜索实体"""
        try:
            await self.langmem_service.initialize()
            entities = await self.langmem_service.search_entities(req.query, req.limit)
            return CommonRes.success(
                [LangmemEntityItem(**entity.to_dict()) for entity in entities]
            )
        except Exception as exc:
            return self._error("search_entities", exc)

    # ==================== 记忆快照与压缩 ====================

    async def get_memory_snapshot(
        self,
        session_id: str = Path(...),
    ) -> CommonRes[LangmemMemorySnapshot]:
        """获取会话记忆快照"""
        try:
            await self.langmem_service.initialize()
            snapshot = await self.langmem_service.get_memory_snapshot(session_id)
            return CommonRes.success(LangmemMemorySnapshot(**snapshot.to_dict()))
        except Exception as exc:
            return self._error("get_memory_snapshot", exc)

    async def compress_memory(
        self,
        session_id: str = Path(...),
    ) -> CommonRes[LangmemCompressResult]:
        """压缩会话记忆"""
        try:
            await self.langmem_service.initialize()
            result = await self.langmem_service.compress_memory(session_id)
            return CommonRes.success(LangmemCompressResult(**result))
        except Exception as exc:
            return self._error("compress_memory", exc)

    # ==================== 会话管理 ====================

    async def list_sessions(self) -> CommonRes[list[LangmemSessionInfo]]:
        """列出所有会话"""
        try:
            await self.langmem_service.initialize()
            sessions = await self.langmem_service.list_sessions()
            return CommonRes.success(
                [LangmemSessionInfo(**session) for session in sessions]
            )
        except Exception as exc:
            return self._error("list_sessions", exc)

    # ==================== 配置管理 ====================

    async def get_config(self) -> CommonRes[LangmemConfig]:
        """获取服务配置"""
        try:
            config = self.langmem_service.config
            return CommonRes.success(LangmemConfig(**config))
        except Exception as exc:
            return self._error("get_config", exc)

    async def update_config(
        self,
        req: LangmemConfigUpdateReq,
    ) -> CommonRes[LangmemConfig]:
        """更新服务配置"""
        try:
            updates = req.model_dump(exclude_unset=True)
            config = self.langmem_service.update_config(updates)
            return CommonRes.success(LangmemConfig(**config))
        except Exception as exc:
            return self._error("update_config", exc)

    def _error(self, label: str, exc: Exception):
        """错误处理"""
        logging.exception("[%s] failed", label)
        return CommonRes.error(
            code=ResCodeEnum.COMMON_ERROR.code,
            message=str(exc),
        )