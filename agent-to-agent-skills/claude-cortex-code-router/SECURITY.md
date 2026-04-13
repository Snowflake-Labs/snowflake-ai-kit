# Security Policy

**Version:** 2.0.0

## Overview

The cortex-code skill implements a layered security architecture to protect against unauthorized data access, prompt injection, and credential exposure when integrating Claude Code with Cortex Code CLI.

**Principles:** Secure by default (prompt mode) · Defense in depth (sanitization → approval → audit) · Least privilege (envelope-based tool control) · Transparency (mandatory logging for auto-approval)

## Security Features

### Approval Modes

| Mode | Security | Auto-Approval | Audit Log |
|------|----------|---------------|-----------|
| **prompt** (default) | High | No | Optional |
| **auto** | Medium | Yes | Mandatory |
| **envelope_only** | Medium | Yes | Mandatory |

### Prompt Sanitization

- **PII removal:** Credit cards, SSN, emails, phone numbers (regex-based, complete content removal)
- **Injection detection:** Commands that manipulate LLM behavior
- **Session sanitization:** PII stripped from conversation history before caching

### Credential File Protection

Blocks routing when prompts contain paths from a configurable allowlist: `~/.ssh/`, `~/.aws/credentials`, `~/.snowflake/`, `.env` files, `credentials.json`, etc.

### Secure Caching

- **Location:** `~/.cache/cortex-skill/` (user-only permissions, 0600)
- **Integrity:** SHA256 fingerprint validation with tamper detection
- **TTL:** 24-hour expiration

### Audit Logging

Structured JSONL logging (mandatory for auto/envelope_only modes):
- Routing decisions, tool predictions, execution results, security actions
- Size-based rotation (default 10MB), configurable retention (default 30 days)
- File permissions: 0600

### Organization Policy Override

Administrators enforce security via `~/.snowflake/cortex/claude-skill-policy.yaml` — overrides user configuration. Deploy via Ansible/Puppet/Chef for team-wide enforcement.

## Threat Model

### Addressed

| Threat | Mitigation |
|--------|------------|
| Prompt Injection | PromptSanitizer removes injection patterns |
| PII Leakage | PII removed before processing |
| Credential Exposure | Credential allowlist blocks routing |
| Unauthorized Execution | Prompt mode requires user approval |
| Cache Tampering | SHA256 fingerprint validation |
| Audit Evasion | Mandatory logging for auto modes |
| Privilege Escalation | Tool access restricted by envelope |

### Not Addressed

- Network attacks (MITM, DNS) — rely on Cortex Code CLI security
- Endpoint compromise — if attacker has shell access, skill security is bypassed
- Snowflake platform security — database permissions managed by Snowflake

### Assumptions

- Cortex Code CLI is authentic and unmodified
- User's OS is not compromised
- Snowflake credentials are managed securely

## Approval Modes

### Prompt Mode (Default)

User sees predicted tools + confidence score → approves or denies before execution. Best for interactive sessions and compliance requirements.

### Auto Mode

All predicted tools auto-approved. Mandatory audit logging. Envelopes still enforced. Best for trusted/automated environments and v1.x compatibility.

### Envelope-Only Mode

No tool prediction. Auto-approved with audit logging. Relies on Cortex Code's envelope enforcement. Fastest option.

## Audit Log Format

```json
{
  "timestamp": "2026-04-01T10:30:00.123456Z",
  "event_type": "cortex_execution",
  "user": "alice",
  "routing": { "decision": "cortex", "confidence": 0.95 },
  "execution": { "envelope": "RW", "approval_mode": "auto", "predicted_tools": ["snowflake_sql_execute"] },
  "result": { "status": "success", "duration_ms": 1234 },
  "security": { "sanitized": true, "pii_removed": true }
}
```

Query with standard tools:

```bash
cat audit.log | jq 'select(.security.pii_removed == true)'     # PII events
cat audit.log | jq 'select(.result.status != "success")'        # Failures
```

## Incident Response

| Incident | Detection | Response |
|----------|-----------|----------|
| Prompt injection | `security.sanitized == true` in logs | Review prompt, update patterns if new vector |
| Credential exposure | Blocked routing with `pattern_matched` | Verify blocking, rotate credentials if exposed |
| Unauthorized tool exec | Tool not in approved list | Check envelope config, fix prediction if false negative |
| Cache tampering | SHA256 mismatch | Cache auto-invalidated, fresh discovery triggered |

## Reporting Security Issues

**Do NOT** publicly disclose vulnerabilities.

1. Email: security@snowflake.com
2. Subject: `[cortex-code skill] Security Issue`
3. Include: version, description, steps to reproduce, impact

Response times: Critical 24h · High 48h · Medium 5 days · Low 10 days.

## Configuration

See [config.yaml.example](config.yaml.example) for all settings and deployment profiles.

## References

- [README.md](README.md) — Installation and usage
- [SKILL.md](SKILL.md) — Full skill definition
