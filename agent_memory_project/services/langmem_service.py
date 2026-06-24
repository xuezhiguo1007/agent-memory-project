"""
Langmem Memory Service - 基于 PostgreSQL 的 LangChain 风格记忆管理服务

这个服务使用 PostgreSQL 作为存储后端，实现了 LangChain 风格的记忆管理能力：
1. 短期会话记忆（Short-term Memory） - 基于当前会话上下文
2. 长期记忆（Long-term Memory） - 基于 Persistent Memory
3. 实体记忆（Entity Memory） - 提取和追踪会话中的关键实体

主要特性：
- PostgreSQL 存储（支持 JSONB、全文搜索、异步操作）
- 支持对话历史的自动管理
- 支持记忆压缩和摘要生成
- 支持实体提取和追踪
- 支持向量检索（可选）
- 与 Hermes 三层架构无缝集成
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg

from agent_memory_project import PROJECT_ROOT


def utc_now() -> str:
    """获取当前 UTC 时间"""
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class MemoryMessage:
    """记忆消息单元"""
    message_id: int
    session_id: str
    role: str
    content: str
    created_at: str
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "score": self.score,
        }


@dataclass(slots=True)
class EntityRecord:
    """实体记录"""
    entity_id: int
    entity_name: str
    entity_type: str
    description: str
    created_at: str
    updated_at: str
    occurrences: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "occurrences": self.occurrences,
        }


@dataclass(slots=True)
class MemorySnapshot:
    """记忆快照"""
    session_id: str
    messages: list[MemoryMessage]
    entities: list[EntityRecord]
    summary: str
    token_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "messages": [m.to_dict() for m in self.messages],
            "entities": [e.to_dict() for e in self.entities],
            "summary": self.summary,
            "token_count": self.token_count,
        }


class LangmemService:
    """
    Langmem 记忆服务 - PostgreSQL 实现

    提供 LangChain 风格的记忆管理能力，包括：
    - 会话记忆管理
    - 实体追踪
    - 记忆压缩与摘要
    - PostgreSQL 全文搜索支持
    """

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or PROJECT_ROOT
        self.config_path = self.project_root / "config" / "langmem_config.json"

        # PostgreSQL 连接配置
        self.pg_config = {
            "host": "localhost",
            "port": 5432,
            "database": "langmem_db",
            "user": "langmem_user",
            "password": "langmem_password",
        }

        # 默认配置
        self.default_config = {
            "max_messages_per_session": 100,
            "max_tokens_per_snapshot": 4000,
            "entity_extraction_enabled": True,
            "auto_compression_enabled": True,
            "compression_threshold": 50,
            "supported_entity_types": [
                "person",
                "project",
                "concept",
                "tool",
                "file",
                "api",
                "task",
            ],
            "pg_connection": self.pg_config,
        }

        self._ensure_layout()
        self.config = self._load_config()

        # 更新 PostgreSQL 连接配置
        if "pg_connection" in self.config:
            self.pg_config.update(self.config["pg_connection"])

        # 连接池（延迟初始化）
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """初始化 PostgreSQL 连接池和数据库表"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.pg_config["host"],
                port=self.pg_config["port"],
                database=self.pg_config["database"],
                user=self.pg_config["user"],
                password=self.pg_config["password"],
                min_size=5,
                max_size=20,
            )
            await self._ensure_tables()

    async def close(self) -> None:
        """关闭连接池"""
        if self._pool:
            await self._pool.close()
            self._pool = None

    # ==================== 消息管理 ====================

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryMessage:
        """添加消息到会话"""
        normalized_content = " ".join(content.split())
        if not normalized_content:
            raise ValueError("Message content must not be empty.")

        normalized_session = session_id.strip()
        normalized_role = role.strip() or "user"
        if not normalized_session:
            raise ValueError("session_id must not be empty.")

        await self.initialize()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO langmem_messages (session_id, role, content, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING message_id, session_id, role, content, created_at, metadata
                """,
                normalized_session,
                normalized_role,
                normalized_content,
                utc_now(),
                json.dumps(metadata or {}, ensure_ascii=False),
            )

        message = self._row_to_message(row)

        # 自动实体提取
        if self.config["entity_extraction_enabled"]:
            await self._extract_entities_from_message(
                normalized_session, normalized_content
            )

        return message

    async def list_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[MemoryMessage]:
        """列出会话的所有消息"""
        limit = limit or self.config["max_messages_per_session"]
        await self.initialize()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT message_id, session_id, role, content, created_at, metadata
                FROM langmem_messages
                WHERE session_id = $1
                ORDER BY message_id ASC
                LIMIT $2
                """,
                session_id.strip(),
                limit,
            )

        return [self._row_to_message(row) for row in rows]

    async def search_messages(
        self, session_id: str, query: str, limit: int = 10
    ) -> tuple[list[MemoryMessage], str]:
        """搜索会话消息（使用 PostgreSQL 全文搜索）"""
        normalized_session = session_id.strip()
        normalized_query = " ".join(query.split())
        if not normalized_session:
            raise ValueError("session_id must not be empty.")
        if not normalized_query:
            raise ValueError("Query must not be empty.")

        await self.initialize()

        async with self._pool.acquire() as conn:
            # 使用 PostgreSQL 的全文搜索功能
            rows = await conn.fetch(
                """
                SELECT
                    message_id, session_id, role, content, created_at, metadata,
                    ts_rank_cd(content_tsvector, plainto_tsquery($3)) AS score
                FROM langmem_messages
                WHERE session_id = $1
                    AND content_tsvector @@ plainto_tsquery($3)
                ORDER BY score DESC
                LIMIT $2
                """,
                normalized_session,
                limit,
                normalized_query,
            )

        messages = [self._row_to_message(row) for row in rows]
        summary = self._summarize_messages(messages)
        return messages, summary

    async def get_message_count(self, session_id: str) -> int:
        """获取会话消息数量"""
        await self.initialize()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COUNT(*) as count
                FROM langmem_messages
                WHERE session_id = $1
                """,
                session_id.strip(),
            )

        return int(row["count"])

    async def clear_session(self, session_id: str) -> int:
        """清空会话的所有消息"""
        await self.initialize()

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM langmem_messages
                WHERE session_id = $1
                """,
                session_id.strip(),
            )

            # 解析 DELETE 的结果，获取删除数量
            deleted_count = int(result.split()[-1]) if result else 0
            return deleted_count

    # ==================== 实体管理 ====================

    async def add_entity(
        self,
        entity_name: str,
        entity_type: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> EntityRecord:
        """添加或更新实体"""
        normalized_name = entity_name.strip()
        normalized_type = entity_type.strip().lower()
        normalized_desc = description.strip()

        if not normalized_name:
            raise ValueError("entity_name must not be empty.")
        if normalized_type not in self.config["supported_entity_types"]:
            raise ValueError(
                f"Unsupported entity_type: {entity_type}. "
                f"Supported types: {', '.join(self.config['supported_entity_types'])}"
            )

        now = utc_now()
        await self.initialize()

        async with self._pool.acquire() as conn:
            # 检查实体是否已存在
            existing = await conn.fetchrow(
                """
                SELECT entity_id, occurrences
                FROM langmem_entities
                WHERE entity_name = $1 AND entity_type = $2
                """,
                normalized_name,
                normalized_type,
            )

            if existing:
                # 更新现有实体
                entity_id = int(existing["entity_id"])
                new_occurrences = int(existing["occurrences"]) + 1

                row = await conn.fetchrow(
                    """
                    UPDATE langmem_entities
                    SET description = $1, metadata = $2, updated_at = $3, occurrences = $4
                    WHERE entity_id = $5
                    RETURNING entity_id, entity_name, entity_type, description, metadata,
                              created_at, updated_at, occurrences
                    """,
                    normalized_desc,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                    new_occurrences,
                    entity_id,
                )
            else:
                # 创建新实体
                row = await conn.fetchrow(
                    """
                    INSERT INTO langmem_entities
                        (entity_name, entity_type, description, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING entity_id, entity_name, entity_type, description, metadata,
                              created_at, updated_at, occurrences
                    """,
                    normalized_name,
                    normalized_type,
                    normalized_desc,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                    now,
                )

        return self._row_to_entity(row)

    async def list_entities(
        self, entity_type: str | None = None, limit: int = 50
    ) -> list[EntityRecord]:
        """列出所有实体"""
        await self.initialize()

        async with self._pool.acquire() as conn:
            if entity_type:
                rows = await conn.fetch(
                    """
                    SELECT entity_id, entity_name, entity_type, description, metadata,
                           created_at, updated_at, occurrences
                    FROM langmem_entities
                    WHERE entity_type = $1
                    ORDER BY occurrences DESC, updated_at DESC
                    LIMIT $2
                    """,
                    entity_type.strip().lower(),
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT entity_id, entity_name, entity_type, description, metadata,
                           created_at, updated_at, occurrences
                    FROM langmem_entities
                    ORDER BY occurrences DESC, updated_at DESC
                    LIMIT $1
                    """,
                    limit,
                )

        return [self._row_to_entity(row) for row in rows]

    async def search_entities(self, query: str, limit: int = 10) -> list[EntityRecord]:
        """搜索实体（使用 PostgreSQL 全文搜索）"""
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise ValueError("Query must not be empty.")

        await self.initialize()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    entity_id, entity_name, entity_type, description, metadata,
                    created_at, updated_at, occurrences,
                    ts_rank_cd(search_tsvector, plainto_tsquery($1)) AS score
                FROM langmem_entities
                WHERE search_tsvector @@ plainto_tsquery($1)
                ORDER BY score DESC
                LIMIT $2
                """,
                normalized_query,
                limit,
            )

        return [self._row_to_entity(row) for row in rows]

    # ==================== 记忆快照与压缩 ====================

    async def get_memory_snapshot(self, session_id: str) -> MemorySnapshot:
        """获取会话记忆快照"""
        messages = await self.list_messages(session_id)
        entities = await self.list_entities(limit=20)
        summary = self._generate_session_summary(messages)
        token_count = self._estimate_token_count(messages, entities, summary)

        return MemorySnapshot(
            session_id=session_id,
            messages=messages,
            entities=entities,
            summary=summary,
            token_count=token_count,
        )

    async def compress_memory(self, session_id: str) -> dict[str, Any]:
        """
        压缩会话记忆

        当消息数量超过阈值时，自动压缩旧消息并保留摘要
        """
        message_count = await self.get_message_count(session_id)

        if message_count <= self.config["compression_threshold"]:
            return {
                "session_id": session_id,
                "compressed": False,
                "message_count": message_count,
                "reason": "Below compression threshold",
            }

        messages = await self.list_messages(session_id)
        summary = self._generate_session_summary(messages)

        # 保留最近的 N 条消息，删除旧消息
        keep_count = self.config["compression_threshold"] // 2
        old_message_ids = [msg.message_id for msg in messages[:-keep_count]] if keep_count > 0 else [msg.message_id for msg in messages]

        await self.initialize()
        async with self._pool.acquire() as conn:
            # 删除旧消息
            if old_message_ids:
                await conn.execute(
                    """
                    DELETE FROM langmem_messages
                    WHERE message_id = ANY($1)
                    """,
                    old_message_ids,
                )

        # 创建压缩摘要消息
        await self.add_message(
            session_id,
            "system",
            f"[COMPRESSED SESSION SUMMARY]\n{summary}",
            {"compressed": True, "original_count": message_count},
        )

        return {
            "session_id": session_id,
            "compressed": True,
            "original_count": message_count,
            "remaining_count": keep_count + 1,
            "summary": summary,
        }

    # ==================== 会话管理 ====================

    async def list_sessions(self) -> list[dict[str, Any]]:
        """列出所有会话"""
        await self.initialize()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT session_id,
                       COUNT(*) as message_count,
                       MIN(created_at) as first_message,
                       MAX(created_at) as last_message
                FROM langmem_messages
                GROUP BY session_id
                ORDER BY last_message DESC
                """
            )

        return [
            {
                "session_id": row["session_id"],
                "message_count": int(row["message_count"]),
                "first_message": row["first_message"],
                "last_message": row["last_message"],
            }
            for row in rows
        ]

    # ==================== 配置管理 ====================

    def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        """更新服务配置"""
        self.config.update(updates)

        # 更新 PostgreSQL 连接配置
        if "pg_connection" in updates:
            self.pg_config.update(updates["pg_connection"])

        self.config_path.write_text(
            json.dumps(self.config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.config

    # ==================== 私有方法 ====================

    async def _extract_entities_from_message(
        self, session_id: str, content: str
    ) -> None:
        """从消息中提取实体"""
        # 简化的实体提取规则
        entity_patterns = {
            "person": [
                r"用户\s*[\"']([^\"']+)[\"']",
                r"开发者\s*[\"']([^\"']+)[\"']",
                r"作者\s*[\"']([^\"']+)[\"']",
            ],
            "project": [
                r"项目\s*[\"']([^\"']+)[\"']",
                r"仓库\s*[\"']([^\"']+)[\"']",
            ],
            "file": [
                r"文件\s*[\"']([^\"']+)[\"']",
                r"([a-zA-Z0-9_\-/]+\.(py|js|ts|md|json|yaml))",
            ],
            "tool": [
                r"工具\s*[\"']([^\"']+)[\"']",
                r"使用\s*([a-zA-Z0-9_\-]+)\s*命令",
            ],
            "concept": [
                r"概念\s*[\"']([^\"']+)[\"']",
                r"架构\s*[\"']([^\"']+)[\"']",
            ],
        }

        extracted = []
        for entity_type, patterns in entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    if match and len(match) > 2:
                        extracted.append((match, entity_type))

        for entity_name, entity_type in extracted:
            try:
                await self.add_entity(
                    entity_name,
                    entity_type,
                    f"从会话 {session_id} 中提取",
                    {"session_id": session_id},
                )
            except ValueError:
                pass

    def _generate_session_summary(self, messages: list[MemoryMessage]) -> str:
        """生成会话摘要"""
        if not messages:
            return "(empty session)"

        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]

        summary_parts = [
            f"会话包含 {len(messages)} 条消息",
            f"用户提问 {len(user_messages)} 次",
            f"助手回复 {len(assistant_messages)} 次",
        ]

        # 提取前几条关键消息
        key_messages = messages[:3]
        if key_messages:
            snippets = []
            for msg in key_messages:
                snippet = msg.content[:100]
                snippets.append(f"[{msg.role}] {snippet}")
            summary_parts.append("\n关键对话片段:\n" + "\n".join(snippets))

        return "\n".join(summary_parts)

    def _summarize_messages(self, messages: list[MemoryMessage]) -> str:
        """为搜索结果生成摘要"""
        if not messages:
            return ""
        snippets = [f"[{msg.role}] {msg.content[:80]}..." for msg in messages[:3]]
        return " | ".join(snippets)

    def _estimate_token_count(
        self, messages: list[MemoryMessage], entities: list[EntityRecord], summary: str
    ) -> int:
        """估算 token 数量"""
        # 简化的 token 估算：每个字符约 0.3 token
        total_chars = 0
        for msg in messages:
            total_chars += len(msg.content)
        for entity in entities:
            total_chars += len(entity.description)
        total_chars += len(summary)
        return int(total_chars * 0.3)

    def _row_to_message(self, row: asyncpg.Record) -> MemoryMessage:
        """将数据库行转换为 MemoryMessage"""
        metadata = {}
        if row.get("metadata"):
            try:
                metadata = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else dict(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        score = row.get("score")
        normalized_score = round(float(score), 4) if score is not None else None

        return MemoryMessage(
            message_id=int(row["message_id"]),
            session_id=str(row["session_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            created_at=str(row["created_at"]),
            score=normalized_score,
            metadata=metadata,
        )

    def _row_to_entity(self, row: asyncpg.Record) -> EntityRecord:
        """将数据库行转换为 EntityRecord"""
        metadata = {}
        if row.get("metadata"):
            try:
                metadata = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else dict(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        return EntityRecord(
            entity_id=int(row["entity_id"]),
            entity_name=str(row["entity_name"]),
            entity_type=str(row["entity_type"]),
            description=str(row["description"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            occurrences=int(row.get("occurrences", 1)),
            metadata=metadata,
        )

    async def _ensure_tables(self) -> None:
        """确保 PostgreSQL 表结构存在"""
        async with self._pool.acquire() as conn:
            # 创建消息表
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS langmem_messages (
                    message_id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    content_tsvector TSVECTOR
                )
                """
            )

            # 创建实体表
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS langmem_entities (
                    entity_id SERIAL PRIMARY KEY,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    occurrences INTEGER DEFAULT 1,
                    search_tsvector TSVECTOR,
                    UNIQUE(entity_name, entity_type)
                )
                """
            )

            # 创建索引
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON langmem_messages(session_id)
                """
            )

            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_tsvector
                ON langmem_messages USING GIN(content_tsvector)
                """
            )

            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entities_tsvector
                ON langmem_entities USING GIN(search_tsvector)
                """
            )

            # 创建触发器以自动更新全文搜索向量
            await conn.execute(
                """
                CREATE OR REPLACE FUNCTION update_message_tsvector()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.content_tsvector := to_tsvector('english', NEW.content);
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql
                """
            )

            await conn.execute(
                """
                DROP TRIGGER IF EXISTS trigger_update_message_tsvector
                ON langmem_messages
                """
            )

            await conn.execute(
                """
                CREATE TRIGGER trigger_update_message_tsvector
                BEFORE INSERT OR UPDATE ON langmem_messages
                FOR EACH ROW EXECUTE FUNCTION update_message_tsvector()
                """
            )

            await conn.execute(
                """
                CREATE OR REPLACE FUNCTION update_entity_tsvector()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.search_tsvector := to_tsvector('english',
                        COALESCE(NEW.entity_name, '') || ' ' ||
                        COALESCE(NEW.entity_type, '') || ' ' ||
                        COALESCE(NEW.description, '')
                    );
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql
                """
            )

            await conn.execute(
                """
                DROP TRIGGER IF EXISTS trigger_update_entity_tsvector
                ON langmem_entities
                """
            )

            await conn.execute(
                """
                CREATE TRIGGER trigger_update_entity_tsvector
                BEFORE INSERT OR UPDATE ON langmem_entities
                FOR EACH ROW EXECUTE FUNCTION update_entity_tsvector()
                """
            )

    def _load_config(self) -> dict[str, Any]:
        """加载配置"""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return self.default_config.copy()
        return self.default_config.copy()

    def _ensure_layout(self) -> None:
        """确保配置目录存在"""
        config_dir = self.config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        # 保存默认配置
        if not self.config_path.exists():
            self.config_path.write_text(
                json.dumps(self.default_config, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )