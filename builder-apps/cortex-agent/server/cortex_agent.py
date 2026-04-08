"""Cortex Agents REST API client.

Handles listing agents, creating threads, and running agents with SSE streaming.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

import httpx

from server.config import AppConfig

logger = logging.getLogger(__name__)


class CortexAgentClient:
    """Client for the Cortex Agents REST API."""

    def __init__(self, config: AppConfig):
        self.config = config
        # conversation_id -> (thread_id, last_message_id)
        self._threads: dict[str, tuple[str, str]] = {}

    async def _run_sql(self, sql: str) -> list[dict[str, Any]]:
        """Execute a SQL statement via the Snowflake SQL API and return rows as dicts."""
        base_url = self.config.get_base_url()
        url = f"{base_url}/api/v2/statements"

        body: dict[str, Any] = {
            "statement": sql,
            "timeout": 30,
        }
        if self.config.snowflake_warehouse:
            body["warehouse"] = self.config.snowflake_warehouse.upper()
        if self.config.snowflake_role:
            body["role"] = self.config.snowflake_role.upper()

        async with httpx.AsyncClient(verify=True, timeout=30) as client:
            resp = await client.post(url, headers=self.config.get_auth_headers(), json=body)
            resp.raise_for_status()

        data = resp.json()

        # Extract column names and row data
        columns = [col["name"] for col in data.get("resultSetMetaData", {}).get("rowType", [])]
        rows = data.get("data", [])
        return [dict(zip(columns, row)) for row in rows]

    async def list_agents(self) -> list[dict[str, Any]]:
        """List all Cortex Agents the current user/role can access."""
        rows = await self._run_sql("SHOW AGENTS IN ACCOUNT")
        return rows

    async def describe_agent(self, database: str, schema: str, name: str) -> dict[str, Any]:
        """Describe a Cortex Agent and extract sample questions from its spec."""
        rows = await self._run_sql(f"DESCRIBE AGENT {database}.{schema}.{name}")
        if not rows:
            return {"sample_questions": []}

        row = rows[0]
        agent_spec_raw = row.get("agent_spec", "{}")
        try:
            agent_spec = json.loads(agent_spec_raw)
        except (json.JSONDecodeError, TypeError):
            agent_spec = {}

        instructions = agent_spec.get("instructions", {})
        sample_questions = [
            q["question"] for q in instructions.get("sample_questions", []) if "question" in q
        ]

        return {"sample_questions": sample_questions}

    async def create_thread(self) -> str:
        """Create a new conversation thread. Returns the thread ID."""
        base_url = self.config.get_base_url()
        url = f"{base_url}/api/v2/cortex/threads"

        async with httpx.AsyncClient(verify=True, timeout=30) as client:
            resp = await client.post(
                url,
                headers=self.config.get_auth_headers(),
                json={"origin_application": "cortex-agent-app"},
            )
            resp.raise_for_status()

        data = resp.json()
        thread_id = data.get("thread_id", data.get("id", ""))
        logger.info("Created thread: %s", thread_id)
        return thread_id

    async def run_agent(
        self,
        agent_name: str,
        database: str,
        schema: str,
        message: str,
        conversation_id: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run a Cortex Agent and yield normalized SSE events.

        Manages thread creation and message threading automatically.

        Args:
            agent_name: Name of the agent.
            database: Database where the agent lives.
            schema: Schema where the agent lives.
            message: User message.
            conversation_id: Conversation ID for thread tracking.

        Yields dicts with keys:
            type: text | sql | chart | tool_use | error | done
            content: text content
            sql: SQL string (for sql type)
            chart_spec: Vega-Lite JSON string (for chart type)
            message_id: assistant message ID (for threading)
            conversation_id: conversation ID
        """
        base_url = self.config.get_base_url()

        # Get or create thread for this conversation
        thread_id, parent_message_id = self._threads.get(conversation_id, (None, None))
        if not thread_id:
            try:
                thread_id = await self.create_thread()
                parent_message_id = 0  # First message in thread
            except Exception as e:
                yield {"type": "error", "content": f"Failed to create thread: {e}"}
                return

        url = f"{base_url}/api/v2/databases/{database}/schemas/{schema}/agents/{agent_name}:run"

        body: dict[str, Any] = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": message}],
                }
            ],
            "thread_id": thread_id,
            "parent_message_id": parent_message_id,
            "stream": True,
        }

        logger.info("Running agent %s (thread=%s, parent=%s)", agent_name, thread_id, parent_message_id)

        last_message_id = parent_message_id

        try:
            headers = self.config.get_auth_headers()
            headers["Accept"] = "text/event-stream"
            async with httpx.AsyncClient(verify=True, timeout=httpx.Timeout(300, connect=30)) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers=headers,
                    json=body,
                ) as resp:
                    if resp.status_code != 200:
                        error_text = ""
                        async for chunk in resp.aiter_text():
                            error_text += chunk
                        yield {"type": "error", "content": f"Agent API error ({resp.status_code}): {error_text}"}
                        return

                    buffer = ""
                    async for chunk in resp.aiter_text():
                        buffer += chunk
                        lines = buffer.split("\n")
                        buffer = lines.pop()  # Keep incomplete line

                        current_event_type = ""
                        for line in lines:
                            if line.startswith("event: "):
                                current_event_type = line[7:].strip()
                            elif line.startswith("data: "):
                                data_str = line[6:]
                                try:
                                    data = json.loads(data_str)
                                except json.JSONDecodeError:
                                    continue

                                events = _parse_cortex_event(current_event_type, data)
                                for event in events:
                                    event["conversation_id"] = conversation_id
                                    # Track message ID for threading
                                    if event.get("message_id"):
                                        last_message_id = event["message_id"]
                                    yield event

        except httpx.ReadTimeout:
            yield {"type": "error", "content": "Agent response timed out"}
        except Exception as e:
            logger.exception("Agent run failed")
            yield {"type": "error", "content": f"Agent error: {e}"}

        # Update thread state for next message
        if last_message_id and last_message_id != parent_message_id:
            self._threads[conversation_id] = (thread_id, last_message_id)
        elif thread_id:
            self._threads[conversation_id] = (thread_id, parent_message_id)

        yield {"type": "done", "content": "", "conversation_id": conversation_id}


def _parse_cortex_event(event_type: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a Cortex Agent SSE event into normalized frontend events.

    Cortex Agent SSE event types:
        message.delta — incremental content (text, tool_use, tool_results)
        response.text — final aggregated text
        response.chart — Vega-Lite chart specification
        metadata — message tracking info (role, message_id)
        response — final event (may contain aggregated content)
    """
    events: list[dict[str, Any]] = []

    if event_type == "message.delta":
        delta = data.get("delta", {})
        content_blocks = delta.get("content", [])

        for block in content_blocks:
            block_type = block.get("type", "")

            if block_type == "text":
                text = block.get("text", "")
                if text:
                    events.append({"type": "text", "content": text})

            elif block_type == "tool_use":
                tool_name = block.get("name", "")
                tool_input = block.get("input", {})
                events.append({
                    "type": "tool_use",
                    "content": f"Using tool: {tool_name}",
                    "tool_name": tool_name,
                    "tool_input": json.dumps(tool_input, default=str) if tool_input else "",
                })

            elif block_type == "tool_results":
                results = block.get("content", [])
                for result in results:
                    result_type = result.get("type", "")
                    if result_type == "text":
                        events.append({"type": "text", "content": result.get("text", "")})
                    elif result_type == "json":
                        json_data = result.get("json", {})
                        # Check if it contains SQL
                        sql = json_data.get("sql", json_data.get("query", ""))
                        if sql:
                            events.append({"type": "sql", "content": sql, "sql": sql})
                        else:
                            events.append({
                                "type": "text",
                                "content": json.dumps(json_data, indent=2, default=str),
                            })

    elif event_type == "response.text":
        text = data.get("text", "")
        if text:
            events.append({"type": "text", "content": text})

    elif event_type == "response.chart":
        chart_spec = data.get("chart_spec", data)
        events.append({
            "type": "chart",
            "content": "Chart generated",
            "chart_spec": json.dumps(chart_spec, default=str),
        })

    elif event_type == "metadata":
        # Track the assistant message ID for threading
        message_id = data.get("message_id", "")
        role = data.get("role", "")
        if message_id and role == "assistant":
            events.append({
                "type": "metadata",
                "content": "",
                "message_id": message_id,
            })

    elif event_type == "response":
        # Final response event — may contain aggregated content
        # We've already streamed deltas, so usually nothing to do here
        pass

    elif event_type == "response.status":
        status = data.get("status", "")
        if status:
            events.append({"type": "status", "content": status})

    elif event_type == "error":
        msg = data.get("message", data.get("error", str(data)))
        events.append({"type": "error", "content": msg})

    return events
