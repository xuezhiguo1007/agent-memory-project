from __future__ import annotations

from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResCodeEnum(Enum):
    SUCCESS = (0, "Success")
    COMMON_ERROR = (1, "Server error")

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class CommonRes(BaseModel, Generic[T]):
    code: int = Field(default=ResCodeEnum.SUCCESS.code)
    message: str = Field(default=ResCodeEnum.SUCCESS.message)
    data: T | None = Field(default=None)

    @classmethod
    def success(cls, data: T | None = None) -> "CommonRes[T]":
        return cls(
            code=ResCodeEnum.SUCCESS.code,
            message=ResCodeEnum.SUCCESS.message,
            data=data,
        )

    @classmethod
    def error(
        cls,
        code: int = ResCodeEnum.COMMON_ERROR.code,
        message: str = ResCodeEnum.COMMON_ERROR.message,
    ) -> "CommonRes[None]":
        return cls(code=code, message=message, data=None)


class PersistentEntryActionReq(BaseModel):
    target: str = Field(..., description="memory or user")
    content: str = Field(..., description="Entry content")


class PersistentReplaceReq(BaseModel):
    target: str = Field(..., description="memory or user")
    old_text: str = Field(..., description="Unique substring to identify an entry")
    content: str = Field(..., description="Replacement content")


class PersistentRemoveReq(BaseModel):
    target: str = Field(..., description="memory or user")
    old_text: str = Field(..., description="Unique substring to identify an entry")


class PersistentStoreState(BaseModel):
    target: str
    entries: list[str] = Field(default_factory=list)
    usage: str
    used_chars: int
    char_limit: int
    snapshot: str


class PersistentPromptBlock(BaseModel):
    prompt_block: str


class SkillCreateReq(BaseModel):
    skill_name: str
    description: str
    triggers: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillItem(BaseModel):
    slug: str
    skill_name: str
    description: str
    triggers: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class SkillCatalogItem(BaseModel):
    slug: str
    skill_name: str
    description: str
    triggers: list[str] = Field(default_factory=list)


class SkillMatchReq(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=50)


class SkillMatchResult(BaseModel):
    query: str
    total: int
    items: list[SkillItem] = Field(default_factory=list)


class SessionEventCreateReq(BaseModel):
    role: str = Field(default="user")
    content: str


class SessionEventItem(BaseModel):
    event_id: int
    session_id: str
    role: str
    content: str
    created_at: str
    score: float | None = None


class SessionSearchReq(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=50)


class SessionSearchResult(BaseModel):
    session_id: str
    query: str
    total: int
    summary: str
    items: list[SessionEventItem] = Field(default_factory=list)


class SessionExtractReq(BaseModel):
    query: str | None = Field(default=None)
    limit: int = Field(default=10, ge=1, le=50)


class ExtractionSuggestionItem(BaseModel):
    kind: str
    title: str
    content: str
    rationale: str


class SessionExtractResult(BaseModel):
    session_id: str
    summary: str
    suggestions: list[ExtractionSuggestionItem] = Field(default_factory=list)


class MaterializeSuggestionReq(BaseModel):
    kind: str
    title: str
    content: str


class MaterializeSuggestionResult(BaseModel):
    destination: str
    payload: dict[str, Any] = Field(default_factory=dict)


# ==================== Langmem Schemas ====================


class LangmemMessageCreateReq(BaseModel):
    session_id: str
    role: str = Field(default="user")
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LangmemMessageItem(BaseModel):
    message_id: int
    session_id: str
    role: str
    content: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class LangmemEntityCreateReq(BaseModel):
    entity_name: str
    entity_type: str
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LangmemEntityItem(BaseModel):
    entity_id: int
    entity_name: str
    entity_type: str
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    occurrences: int


class LangmemSearchReq(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)


class LangmemSearchResult(BaseModel):
    session_id: str
    query: str
    total: int
    summary: str
    items: list[LangmemMessageItem] = Field(default_factory=list)


class LangmemMemorySnapshot(BaseModel):
    session_id: str
    messages: list[LangmemMessageItem] = Field(default_factory=list)
    entities: list[LangmemEntityItem] = Field(default_factory=list)
    summary: str
    token_count: int


class LangmemCompressResult(BaseModel):
    session_id: str
    compressed: bool
    original_count: int | None = None
    remaining_count: int | None = None
    summary: str | None = None
    message_count: int | None = None
    reason: str | None = None


class LangmemSessionInfo(BaseModel):
    session_id: str
    message_count: int
    first_message: str
    last_message: str


class LangmemConfigUpdateReq(BaseModel):
    max_messages_per_session: int | None = None
    max_tokens_per_snapshot: int | None = None
    entity_extraction_enabled: bool | None = None
    auto_compression_enabled: bool | None = None
    compression_threshold: int | None = None


class LangmemConfig(BaseModel):
    max_messages_per_session: int
    max_tokens_per_snapshot: int
    entity_extraction_enabled: bool
    auto_compression_enabled: bool
    compression_threshold: int
    supported_entity_types: list[str] = Field(default_factory=list)
