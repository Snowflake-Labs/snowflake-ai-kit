# Cortex CLI Reference

## Core Commands

### Headless Execution
```bash
cortex -p "your prompt here" --output-format stream-json
```

Executes Cortex in headless mode with streaming JSON output.

**Output Format**: NDJSON (newline-delimited JSON)
- Each line is a complete JSON object
- Events stream in real-time as they occur

### Permission Management
```bash
cortex -p "prompt" --disallowed-tools "Write" "Edit" "Bash(rm -rf *)"
```

Explicitly blocks unsafe tools or command patterns. The Cortex Code wrappers use `--disallowed-tools` for envelope enforcement because `--allowed-tools` can block Snowflake MCP tools by pattern mismatch.

### Skill Discovery
```bash
cortex skill list
```

Lists all available skills (bundled and custom).

### Connection Management
```bash
cortex connections list
```

Shows all configured Snowflake connections.

### Search Operations
```bash
cortex search object <pattern>
cortex search docs <query>
```

Searches Snowflake objects or documentation.

## Event Stream Types

### System Events
```json
{
  "type": "system",
  "subtype": "init",
  "session_id": "unique-session-id",
  "tools": ["read", "write", "bash", ...],
  "model": "auto"
}
```

Initialization event at session start.

### Assistant Events
```json
{
  "type": "assistant",
  "session_id": "...",
  "message": {
    "role": "assistant",
    "content": [
      {"type": "text", "text": "Response here"},
      {"type": "tool_use", "id": "...", "name": "bash", "input": {...}}
    ]
  }
}
```

Cortex's responses and tool invocations.

### User Events
```json
{
  "type": "user",
  "session_id": "...",
  "message": {
    "role": "user",
    "content": [
      {"type": "tool_result", "tool_use_id": "...", "content": "result or error"}
    ]
  }
}
```

Tool results or user input (including permission denials).

### Result Events
```json
{
  "type": "result",
  "session_id": "...",
  "subtype": "success",
  "result": "Final outcome text",
  "is_error": false,
  "duration_ms": 5234,
  "num_turns": 3
}
```

Final session result.

## Permission Denials

When a tool is blocked by the current envelope, Cortex returns a permission-denial event in the stream.

**Handling**:
1. Detect the permission denial in the event stream
2. Extract the requested tool or command pattern from the context
3. Ask the user to approve a more appropriate envelope, or keep the request blocked
4. Re-invoke Cortex with the approved envelope/blocklist only when policy allows it

## Available Tools in Cortex

- `snowflake_sql_execute` - Execute SQL queries on Snowflake
- `bash` - Run bash commands
- `read` - Read files
- `write` - Write files
- `edit` - Edit files
- `glob` - File pattern matching
- `grep` - Content search
- `web_fetch` - Fetch web content
- `ask_user_question` - Ask user questions
- `task` - Task management
- Plus skill-specific tools

## Common Patterns

### Simple Query
```bash
cortex -p "Show top 10 customers" \
  --output-format stream-json \
  --disallowed-tools "Edit" "Write" "Bash"
```

### Data Quality Check
```bash
cortex -p "Check data quality for SALES_DATA table" \
  --output-format stream-json \
  --disallowed-tools "Bash(rm *)" "Bash(rm -rf *)" "Bash(sudo *)"
```

### With Context Enrichment
```bash
cortex -p "# Previous Context
User asked about customer segmentation.

# Recent Cortex Work
Ran RFM analysis on customers table.

# Current Request
Create a dynamic table for high-value customers" \
  --output-format stream-json \
  --disallowed-tools "Bash(rm *)" "Bash(rm -rf *)" "Bash(sudo *)"
```

## Configuration Files

### Settings Location
`~/.snowflake/cortex/settings.json`

Key settings:
- `cortexAgentConnectionName` - Default Snowflake connection
- `model` - AI model to use
- Other Cortex-specific preferences

### Trust Settings
`~/.snowflake/cortex/cortex.json`

Project-specific trust and permissions.

### Session Files
`~/.local/share/cortex/sessions/*.jsonl`

Stored session transcripts for context enrichment.

## Error Handling

### Connection Errors
```
Error: Connection refused
```
**Solution**: Check Snowflake connection:
```bash
cortex connections list
```

### Tool Permission Errors
```
Permission denied: Tool denied by envelope or policy
```
**Solution**: Use the least-privileged envelope that supports the request. Do not switch to broader envelopes unless the user explicitly approves and policy allows it.

### Model Errors
```
Error: Rate limit exceeded
```
**Solution**: Cortex routes through Snowflake Cortex AI. Check Snowflake quotas.

## Best Practices

1. **Start Conservative**: Begin with RO or RW envelopes and expand only when approved
2. **Enrich Context**: Always provide relevant background from Claude session
3. **Read Sessions**: Check recent Cortex work to avoid duplicate operations
4. **Handle Streams**: Parse NDJSON line-by-line, don't wait for completion
5. **Timeout Handling**: Set reasonable timeouts (30-60s for complex queries)
6. **Error Recovery**: Detect permission denials early and ask before changing envelopes

## Limitations

- **No Persistent Sessions**: Each invocation is stateless
- **No `--resume`**: Session resumption not available in headless mode
- **Organization Policies**: Some flags may be blocked (e.g., `--bypass`, `--dangerously-allow-all-tool-calls`)
- **Tool Restrictions**: Envelope blocklists are enforced through `--disallowed-tools`
- **Rate Limits**: Subject to Snowflake Cortex AI rate limits
