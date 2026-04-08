# Extended Troubleshooting Guide

## Common Issues and Solutions

### 1. Skill Not Triggering

#### Symptom
Cortex Code skill doesn't activate when asking Snowflake questions.

#### Diagnosis
```bash
# Check if skill is loaded
ls -la ~/.claude/skills/cortex-code/

# Test routing logic
python ~/.claude/skills/cortex-code/scripts/route_request.py \
  --prompt "Show me Snowflake tables"
```

#### Solutions

**A. Skill not loaded**
```bash
# Ensure skill directory exists
mkdir -p ~/.claude/skills/cortex-code

# Copy skill files
cp -r cortex-code ~/.claude/skills/

# Restart Claude Code
```

**B. Description too vague**
Edit `~/.claude/skills/cortex-code/SKILL.md` frontmatter:
```yaml
description: Routes Snowflake-related operations... [ADD MORE TRIGGER KEYWORDS]
```

**C. Routing logic issue**
Add keywords to `scripts/route_request.py`:
```python
SNOWFLAKE_INDICATORS = [
    "snowflake", "cortex", "warehouse",
    # Add your specific terms
    "your_warehouse_name",
    "your_database_name"
]
```

---

### 2. Cortex CLI Not Found

#### Symptom
```
Error: cortex: command not found
```

#### Diagnosis
```bash
which cortex
echo $PATH
```

#### Solutions

**A. Cortex not installed**
Check Snowflake documentation for Cortex Code installation.

**B. Cortex not in PATH**
```bash
# Find Cortex installation
find ~ -name "cortex" -type f 2>/dev/null

# Add to PATH (adjust path as needed)
export PATH="$HOME/.snowflake/cortex/bin:$PATH"

# Make permanent (add to ~/.zshrc or ~/.bashrc)
echo 'export PATH="$HOME/.snowflake/cortex/bin:$PATH"' >> ~/.zshrc
```

**C. Verify installation**
```bash
cortex --version
cortex connections list
```

---

### 3. Permission Denied Errors

#### Symptom
```
Permission denied: Tool denied: headless mode requires --allowed-tools
```

#### Explanation
This is EXPECTED behavior. Organization policy blocks `--dangerously-allow-all-tool-calls`, so we use `--allowed-tools` explicitly.

#### Diagnosis
```bash
# Check predicted tools
python ~/.claude/skills/cortex-code/scripts/predict_tools.py \
  --prompt "Your query here"
```

#### Solutions

**A. Tool prediction incomplete**
Update `scripts/predict_tools.py` to include missing tool:
```python
BASE_SNOWFLAKE_TOOLS = [
    "snowflake_sql_execute",
    "bash",
    "read",
    # Add missing tool
    "write"
]
```

**B. Runtime tool addition**
The skill should handle this automatically by:
1. Detecting permission denial
2. Asking user for approval
3. Re-invoking with updated tools

If this fails, check `scripts/execute_cortex.py` for proper permission handling.

---

### 4. Snowflake Connection Errors

#### Symptom
```
Error: Connection refused
Error: No connection configured
```

#### Diagnosis
```bash
# Check connections
cortex connections list

# Check settings
cat ~/.snowflake/cortex/settings.json
```

#### Solutions

**A. No connection configured**
```bash
# Configure connection via Cortex
cortex config set cortexAgentConnectionName "your_connection_name"
```

**B. Connection not active**
Verify connection in Snowflake:
```sql
-- Test connection
SELECT CURRENT_USER();
```

**C. Authentication expired**
```bash
# Re-authenticate
# (Method depends on your auth setup: SSO, username/password, key-pair)
```

---

### 5. Capabilities Cache Stale

#### Symptom
Skill doesn't recognize new Cortex skills or features.

#### Diagnosis
```bash
# Check cache age
ls -la /tmp/cortex-capabilities.json

# View cached capabilities
cat /tmp/cortex-capabilities.json | jq
```

#### Solutions

**A. Manual refresh**
```bash
python ~/.claude/skills/cortex-code/scripts/discover_cortex.py
```

**B. Automatic refresh**
Capabilities are cached per Claude session. Start new session to refresh.

**C. Force discovery**
Delete cache and re-run:
```bash
rm /tmp/cortex-capabilities.json
python ~/.claude/skills/cortex-code/scripts/discover_cortex.py
```

---

### 6. Context Enrichment Too Large

#### Symptom
```
Error: Prompt too long
Error: Token limit exceeded
```

#### Diagnosis
```bash
# Check recent session sizes
python ~/.claude/skills/cortex-code/scripts/read_cortex_sessions.py --verbose
```

#### Solutions

**A. Reduce session limit**
Edit `scripts/read_cortex_sessions.py`:
```python
def find_recent_sessions(limit=1):  # Reduced from 3
```

**B. Summarize context**
Instead of full session content, extract key points only.

**C. Filter relevant context**
Only include Snowflake-related exchanges, skip others.

---

### 7. Routing Ambiguity

#### Symptom
Requests routed incorrectly (Snowflake query goes to Claude, or vice versa).

#### Diagnosis
```bash
# Test routing
python ~/.claude/skills/cortex-code/scripts/route_request.py \
  --prompt "Show me table data"

# Check confidence
# Low confidence (<70%) indicates ambiguity
```

#### Solutions

**A. Add explicit context**
User should mention "Snowflake" or "Cortex" explicitly:
- ✘ "Show me table data" (ambiguous)
- ✔ "Show me Snowflake table data" (clear)

**B. Improve routing logic**
Add context-aware checks in `scripts/route_request.py`:
```python
def analyze_with_llm_logic(prompt, capabilities, recent_context=None):
    # Include recent conversation context
    if recent_context and "snowflake" in recent_context.lower():
        snowflake_score += 2
```

**C. Ask user**
For low confidence (<70%), prompt user:
```python
if confidence < 0.7:
    # Ask user: "Are you referring to Snowflake?"
```

---

### 8. Script Execution Errors

#### Symptom
```
Permission denied: scripts/discover_cortex.py
```

#### Diagnosis
```bash
ls -la ~/.claude/skills/cortex-code/scripts/
```

#### Solutions

**A. Make scripts executable**
```bash
chmod +x ~/.claude/skills/cortex-code/scripts/*.py
```

**B. Check Python path**
```bash
which python3

# Scripts use #!/usr/bin/env python3
# Ensure python3 is in PATH
```

**C. Dependencies**
```bash
# Ensure standard library modules are available
python3 -c "import json, subprocess, sys, pathlib"
```

---

### 9. Streaming Output Errors

#### Symptom
```
Error parsing line: ...
Warning: Failed to parse JSON
```

#### Diagnosis
Cortex output format changed or corrupted.

#### Solutions

**A. Verify stream format**
```bash
# Test directly
cortex -p "test" --output-format stream-json
```

**B. Update parser**
If Cortex output format changed, update `scripts/execute_cortex.py` JSON parsing.

**C. Check for errors in stderr**
Cortex may output errors to stderr that interfere with stdout parsing.

---

### 10. Rate Limiting

#### Symptom
```
Error: Rate limit exceeded
Error: Too many requests
```

#### Explanation
Cortex Code routes through Snowflake Cortex AI, which has rate limits.

#### Solutions

**A. Check Snowflake quotas**
```sql
-- Query Snowflake to check usage
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE QUERY_TEXT LIKE '%CORTEX%'
ORDER BY START_TIME DESC
LIMIT 100;
```

**B. Implement backoff**
Add retry logic with exponential backoff in `scripts/execute_cortex.py`.

**C. Reduce frequency**
Space out Cortex calls, batch operations where possible.

---

## Advanced Debugging

### Enable Verbose Logging

Add logging to scripts:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Trace Execution Flow

```bash
# Enable Python tracing
python -m trace --trace ~/.claude/skills/cortex-code/scripts/route_request.py \
  --prompt "test"
```

### Monitor Cortex Sessions

```bash
# Watch session files in real-time
watch -n 1 'ls -lt ~/.local/share/cortex/sessions/*.jsonl | head -5'

# Tail latest session
tail -f $(ls -t ~/.local/share/cortex/sessions/*.jsonl | head -1)
```

### Test Integration

Create test script:
```bash
#!/bin/bash
echo "Testing Cortex integration..."

# Test 1: Discovery
python ~/.claude/skills/cortex-code/scripts/discover_cortex.py

# Test 2: Routing
python ~/.claude/skills/cortex-code/scripts/route_request.py \
  --prompt "Show Snowflake tables"

# Test 3: Tool prediction
python ~/.claude/skills/cortex-code/scripts/predict_tools.py \
  --prompt "Check data quality"

# Test 4: Session reading
python ~/.claude/skills/cortex-code/scripts/read_cortex_sessions.py

echo "All tests completed"
```

---

## Getting Help

1. **Check logs**: Look in `/tmp/` for any skill-related logs
2. **Test components**: Run scripts individually to isolate issues
3. **Verify setup**: Ensure both Claude Code and Cortex Code are properly configured
4. **Review recent changes**: Did Cortex Code update? Check for breaking changes
5. **Community**: Reach out to Claude Code or Snowflake communities

---

## Prevention

### Best Practices

1. **Regular cache refresh**: Start new Claude sessions periodically to refresh capabilities
2. **Monitor Cortex updates**: Watch for Cortex Code CLI updates that may change behavior
3. **Log routing decisions**: Keep track of what works and what doesn't
4. **Test after changes**: Run integration tests after modifying routing logic
5. **Document customizations**: Note any custom patterns added to routing

### Maintenance Schedule

- **Daily**: Check if skill is triggering correctly
- **Weekly**: Review routing accuracy, update patterns if needed
- **Monthly**: Refresh capabilities cache, check for Cortex updates
- **Quarterly**: Review and clean up Cortex session files if they grow too large
