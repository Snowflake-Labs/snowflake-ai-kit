"""Pydantic models for API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request body for /api/chat."""

    message: str
    agent_name: str
    database: str
    schema_name: str
    conversation_id: str | None = None


class AgentInfo(BaseModel):
    """Summary of a Cortex Agent."""

    name: str
    database: str
    schema_name: str
    comment: str | None = None
    created_on: str | None = None


class AgentDescription(BaseModel):
    """Detailed agent info including sample questions."""

    sample_questions: list[str] = []


class ConversationResponse(BaseModel):
    """Response for a conversation."""

    id: str
    agent_name: str
    title: str
    thread_id: str | None = None
    created_at: str
    updated_at: str


class AgentEvent(BaseModel):
    """Normalized SSE event sent to the frontend."""

    type: str  # text, sql, chart, tool_use, error, done
    content: str = ""
    sql: str | None = None
    chart_spec: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
