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


class MemoryItem(BaseModel):
    memory_id: str
    content: str
    source: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    score: float | None = None


class MemoryCreateReq(BaseModel):
    content: str = Field(..., description="Memory content to persist.")
    source: str = Field(default="api", description="Source label of the memory.")
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorySearchReq(BaseModel):
    query: str = Field(..., description="Search query for memory recall.")
    limit: int = Field(default=5, ge=1, le=50)


class MemorySearchResult(BaseModel):
    query: str
    total: int
    items: list[MemoryItem] = Field(default_factory=list)
