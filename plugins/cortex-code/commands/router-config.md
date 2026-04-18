---
description: Show or update Cortex auto-routing configuration (approval mode, envelope, audit)
argument-hint: '[--show | --set <key>=<value>]'
allowed-tools: Bash(python:*), Bash(cat:*), Bash(mkdir:*)
---

View or modify Cortex auto-routing configuration.

Raw slash-command arguments:
`$ARGUMENTS`

## Configuration File

Location: `~/.claude/skills/cortex-code/config.yaml`

Example config template is at `${CLAUDE_PLUGIN_ROOT}/scripts/router/config.yaml.example`.

## Behavior

### If `--show` or no arguments:

Read and display the current configuration:

```bash
cat ~/.claude/skills/cortex-code/config.yaml 2>/dev/null || echo "No config found — using defaults"
```

Present the settings in a readable format:
- **Approval mode**: prompt (default) | auto | envelope_only
- **Allowed envelopes**: RO, RW, RESEARCH, DEPLOY
- **Audit log path**: where logs are written
- **Sanitization**: enabled/disabled
- **Cache directory**: where capabilities are cached

If no config file exists, show the defaults from the example config and tell the user:
```
No custom config found. Using secure defaults (approval_mode: prompt).
To customize, copy the example:
  mkdir -p ~/.claude/skills/cortex-code
  cp "${CLAUDE_PLUGIN_ROOT}/scripts/router/config.yaml.example" ~/.claude/skills/cortex-code/config.yaml
```

### If `--set <key>=<value>`:

Supported keys:
- `approval_mode` — one of: prompt, auto, envelope_only
- `sanitize` — true or false

For `approval_mode`:
1. Validate the value is one of the three allowed modes
2. If config file doesn't exist, copy the example first
3. Update the `approval_mode` line in the config
4. Confirm the change to the user
5. If switching to `auto` or `envelope_only`, remind the user that audit logging is mandatory

For `sanitize`:
1. Update `sanitize_conversation_history` in the config
2. If disabling, warn: "Disabling PII sanitization is not recommended for production use."

For any other key, tell the user to edit the config file directly:
```
Edit ~/.claude/skills/cortex-code/config.yaml directly for advanced settings.
See ${CLAUDE_PLUGIN_ROOT}/scripts/router/config.yaml.example for all options.
```
