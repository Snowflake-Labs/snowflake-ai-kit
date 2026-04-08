"""FastAPI backend for the Cortex Agent App.

Provides REST + SSE endpoints for the React frontend to interact with
Cortex Agents running on Snowflake.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from server.config import AppConfig
from server.cortex_agent import CortexAgentClient
from server.models import AgentInfo, AgentDescription, ChatRequest, ConversationResponse

load_dotenv(".env.local")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = AppConfig.from_env()
agent_client = CortexAgentClient(config)

# In-memory conversation store
_conversations: dict[str, dict] = {}

app = FastAPI(
    title="Cortex Agent App",
    description="Chat UI for Snowflake Cortex Agents",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "database": config.snowflake_database,
        "schema": config.snowflake_schema,
    }


@app.get("/api/agents")
async def list_agents() -> list[AgentInfo]:
    """List available Cortex Agents."""
    try:
        agents = await agent_client.list_agents()
    except Exception as e:
        logger.exception("Failed to list agents")
        raise HTTPException(status_code=500, detail=str(e))

    results = []
    for a in agents:
        results.append(AgentInfo(
            name=a.get("name", ""),
            database=a.get("database_name", config.snowflake_database or ""),
            schema_name=a.get("schema_name", config.snowflake_schema or ""),
            comment=a.get("comment"),
            created_on=a.get("created_on"),
        ))
    return results


@app.get("/api/agents/{database}/{schema}/{name}/describe")
async def describe_agent(database: str, schema: str, name: str) -> AgentDescription:
    """Describe a Cortex Agent — returns sample questions."""
    try:
        result = await agent_client.describe_agent(database, schema, name)
    except Exception as e:
        logger.exception("Failed to describe agent %s.%s.%s", database, schema, name)
        raise HTTPException(status_code=500, detail=str(e))

    return AgentDescription(sample_questions=result.get("sample_questions", []))


@app.get("/api/conversations")
async def list_conversations() -> list[ConversationResponse]:
    """List all conversations."""
    convos = [ConversationResponse(**c) for c in _conversations.values()]
    return sorted(convos, key=lambda c: c.updated_at, reverse=True)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Run a Cortex Agent. Returns an SSE stream."""
    now = datetime.now(timezone.utc).isoformat()

    conversation_id = req.conversation_id
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        _conversations[conversation_id] = {
            "id": conversation_id,
            "agent_name": req.agent_name,
            "title": req.message[:60],
            "thread_id": None,
            "created_at": now,
            "updated_at": now,
        }

    if conversation_id in _conversations:
        _conversations[conversation_id]["updated_at"] = now

    async def event_stream():
        async for event in agent_client.run_agent(
            agent_name=req.agent_name,
            database=req.database,
            schema=req.schema_name,
            message=req.message,
            conversation_id=conversation_id,
        ):
            data = json.dumps(event, default=str)
            yield f"event: {event.get('type', 'message')}\ndata: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Serve React frontend in production
CLIENT_BUILD = Path(__file__).parent.parent / "client" / "dist"
if CLIENT_BUILD.exists():
    app.mount("/", StaticFiles(directory=str(CLIENT_BUILD), html=True))
