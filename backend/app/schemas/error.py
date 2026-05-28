"""Pydantic models for API error payloads."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str = Field(description="Human-readable error message")
    code: str = Field(description="Stable machine-readable error code")
    request_id: str | None = Field(default=None, description="Request trace identifier")
