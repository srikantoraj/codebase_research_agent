from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchPlan(BaseModel):
    search_terms: list[str] = Field(default_factory=list)
    reason: str = ""


class ToolExecutionRecord(BaseModel):
    tool_name: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    success: bool = True


class AgentStatus(BaseModel):
    status: Literal["running", "completed", "failed"]
    message: str = ""
