# Security Policy

**Last Updated:** April 1, 2026  
**Effective Date:** April 1, 2026

## Table of Contents

- [Overview](#overview)
- [Security Features](#security-features)
- [Threat Model](#threat-model)
- [Configuration](#configuration)
- [Approval Modes](#approval-modes)
- [Audit Logging](#audit-logging)
- [Incident Response](#incident-response)
- [Reporting Security Issues](#reporting-security-issues)
- [Security Best Practices](#security-best-practices)

---

## Overview

The cortex-code skill implements a layered security architecture to protect against unauthorized data access, prompt injection attacks, and other security threats when integrating Claude Code with Cortex Code CLI.

**Security Principles:**
- **Secure by default**: Prompt mode requires user approval before execution
- **Defense in depth**: Multiple security layers (sanitization, approval, audit)
- **Least privilege**: Tool access controlled via security envelopes
- **Transparency**: All operations logged when auto-approval enabled
- **Configurability**: Enterprise policy override support

---

## Security Features

### 1. Configurable Approval Modes

Three modes balance security and convenience:

| Mode | Security Level | Use Case | Auto-Approval | Audit Log |
|------|----------------|----------|---------------|-----------|
| **prompt** | High | Default, interactive use | No | Optional |
| **auto** | Medium | Automated workflows | Yes | Mandatory |
| **envelope_only** | Medium | Trust envelopes only | Yes | Mandatory |

**Default**: `prompt` (most secure)

### 2. Prompt Sanitization

Automatic removal of:
- **PII**: Credit cards, SSN, emails, phone numbers
- **Injection attempts**: Commands that manipulate LLM behavior
- **Sensitive paths**: Credential files from allowlist

**Detection method**: Regex-based pattern matching  
**Action on detection**: Complete content removal (not just masking)

### 3. Credential File Protection

Blocks routing when prompts contain paths from allowlist:
- `~/.ssh/` (SSH keys)
- `~/.aws/credentials` (AWS credentials)
- `~/.snowflake/` (Snowflake credentials)
- `.env` files
- `credentials.json`

**Configuration**: `security.credential_file_allowlist`

### 4. Secure Caching

Secure cache directory:
- **Location**: `~/.cache/cortex-skill/` (user-only permissions)
- **Integrity**: SHA256 fingerprint validation
- **TTL**: 24-hour expiration for capabilities cache
- **Permissions**: 0600 (owner read/write only)

### 5. Audit Logging

Structured JSONL logging when auto-approval enabled:
- **Format**: One JSON object per line (machine-readable)
- **Rotation**: Configurable size-based rotation (default 10MB)
- **Retention**: Configurable retention period (default 30 days)
- **Permissions**: 0600 (owner read/write only)

**Logged events**:
- Routing decisions (cortex vs claude)
- Tool predictions and approval status
- Execution results and durations
- Security actions (PII removal, injection detection, credential blocking)

### 6. Organization Policy Override

Administrators can enforce security policies:
- **Location**: `~/.snowflake/cortex/claude-skill-policy.yaml`
- **Precedence**: Overrides user configuration
- **Use cases**: Enterprise compliance, team standards

---

## Threat Model

### Threats Addressed

| Threat | Mitigation | Security Feature |
|--------|------------|------------------|
| **Prompt Injection** | Sanitization | PromptSanitizer removes injection patterns |
| **PII Leakage** | Sanitization | PII removed before processing |
| **Credential Exposure** | Blocking | Credential allowlist blocks routing |
| **Unauthorized Execution** | Approval | Prompt mode requires user approval |
| **Cache Tampering** | Integrity | SHA256 fingerprint validation |
| **Audit Evasion** | Mandatory logging | Auto mode requires audit logs |
| **Privilege Escalation** | Envelopes | Tool access restricted by envelope |
| **Session Hijacking** | Sanitization | PII removed from session history |

### Threats NOT Addressed

- **Network attacks**: MITM, DNS poisoning (rely on Cortex Code CLI security)
- **Endpoint compromise**: If attacker has shell access, skill security bypassed
- **Snowflake platform security**: Database permissions managed by Snowflake
- **Side-channel attacks**: Timing attacks, cache timing (not in scope)

### Assumptions

- Cortex Code CLI is authentic and unmodified
- User's operating system is not compromised
- Snowflake credentials are managed securely
- Claude Code installation is trusted

---

## Configuration

### Configuration File Locations

1. **Organization Policy** (highest priority):
   ```
   ~/.snowflake/cortex/claude-skill-policy.yaml
   ```

2. **User Configuration**:
   ```
   ~/.claude/skills/cortex-code/config.yaml
   ```

3. **Default Configuration** (built-in fallback)

### Example Configuration

```yaml
# ~/.claude/skills/cortex-code/config.yaml

security:
  # Approval mode (prompt, auto, envelope_only)
  approval_mode: "prompt"  # Default: most secure
  
  # Tool prediction threshold
  tool_prediction_confidence_threshold: 0.7
  
  # Audit logging
  audit_log_path: "~/.claude/skills/cortex-code/audit.log"
  audit_log_rotation: "10MB"
  audit_log_retention: 30  # days
  
  # Prompt sanitization
  sanitize_conversation_history: true
  
  # Secure caching
  cache_dir: "~/.cache/cortex-skill"
  cache_ttl: 86400  # 24 hours
  
  # Credential file allowlist (block routing if detected)
  credential_file_allowlist:
    - "~/.ssh/**"
    - "~/.aws/credentials"
    - "~/.snowflake/**"
    - "**/.env"
    - "**/credentials.json"
  
  # Security envelopes
  allowed_envelopes:
    - "RO"
    - "RW"
    - "RESEARCH"
    - "DEPLOY"  # Requires confirmation
```

### Environment Variables

- `CORTEX_SKILL_CONFIG`: Override default config path
- `CORTEX_SKILL_ORG_POLICY`: Override default org policy path

---

## Approval Modes

### Prompt Mode (Default)

**Security**: High  
**User Experience**: Interactive

**Behavior**:
1. Security wrapper predicts required tools
2. User shown approval prompt with tool list and confidence
3. User approves/denies execution
4. If approved, execution proceeds with allowed tools only

**When to use**:
- Interactive sessions
- Untrusted prompts
- Production environments
- Compliance requirements

**Example**:
```
Cortex Code needs to execute the following tools:

  • snowflake_sql_execute
  • Read
  • Write

Envelope: RW
Confidence: 85%

Approve execution? [yes/no]
```

### Auto Mode

**Security**: Medium  
**User Experience**: Automatic

**Behavior**:
1. All predicted tools auto-approved
2. Execution proceeds without user interaction
3. **Mandatory audit logging** enabled
4. Envelopes still enforced

**When to use**:
- Trusted environments
- Automated workflows
- Team collaboration

**Requirements**:
- Audit logging must be configured
- User accepts auto-approval risks

### Envelope-Only Mode

**Security**: Medium  
**User Experience**: Automatic

**Behavior**:
1. No tool prediction performed
2. Execution proceeds with envelope blocklist only
3. **Mandatory audit logging** enabled
4. Relies on Cortex Code's envelope enforcement

**When to use**:
- Trust Cortex Code's envelope system
- Minimize latency (no tool prediction)
- Simplified approval flow

---

## Audit Logging

### Log Format

JSONL (JSON Lines) format - one JSON object per line:

```json
{
  "timestamp": "2026-04-01T10:30:00.123456Z",
  "version": "2.0.0",
  "audit_id": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "event_type": "cortex_execution",
  "user": "alice",
  "session_id": "claude-session-123",
  "cortex_session_id": "cortex-session-456",
  "routing": {
    "decision": "cortex",
    "confidence": 0.95
  },
  "execution": {
    "envelope": "RW",
    "approval_mode": "auto",
    "auto_approved": true,
    "predicted_tools": ["snowflake_sql_execute", "Read"],
    "allowed_tools": ["snowflake_sql_execute", "Read"]
  },
  "result": {
    "status": "success",
    "duration_ms": 1234
  },
  "security": {
    "sanitized": true,
    "pii_removed": true
  }
}
```

### Log Rotation

**Trigger**: Size-based (default 10MB)  
**Naming**: `audit.log.1`, `audit.log.2`, etc.  
**Retention**: Configurable days (default 30)

### Log Analysis

Query logs using standard JSON tools:

```bash
# Count executions by approval mode
cat audit.log | jq -r '.execution.approval_mode' | sort | uniq -c

# Find all PII removal events
cat audit.log | jq 'select(.security.pii_removed == true)'

# Execution duration statistics
cat audit.log | jq -r '.result.duration_ms' | awk '{sum+=$1; count++} END {print sum/count}'

# Failed executions
cat audit.log | jq 'select(.result.status != "success")'
```

---

## Incident Response

### Suspected Prompt Injection

**Detection**: Check audit logs for `security.sanitized == true`

**Response**:
1. Review the original prompt (if available)
2. Check if injection pattern was correctly detected
3. Verify complete content removal (not just masking)
4. Update pattern list if new attack vector identified

### Credential Exposure Attempt

**Detection**: Check audit logs for blocked routing with credential patterns

**Response**:
1. Identify which credential pattern was matched
2. Verify blocking worked correctly
3. Check if legitimate use case (update allowlist if false positive)
4. Investigate user intent if suspicious

### Unauthorized Tool Execution

**Detection**: Tools executed outside approved list

**Response**:
1. Check approval mode configuration
2. Review tool prediction accuracy
3. Verify envelope enforcement
4. Check for configuration tampering

### Cache Tampering

**Detection**: SHA256 fingerprint mismatch on cache read

**Response**:
1. Cache automatically invalidated
2. Fresh capabilities discovery triggered
3. Log incident for review
4. Investigate if tampering was intentional

---

## Reporting Security Issues

**Do NOT** publicly disclose security vulnerabilities.

**Reporting Process**:
1. Email: security@snowflake.com
2. Subject: "[cortex-code skill] Security Issue"
3. Include:
   - Version number
   - Detailed description
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

**Response Time**:
- Critical: 24 hours
- High: 48 hours
- Medium: 5 business days
- Low: 10 business days

**Disclosure Policy**:
- Coordinated disclosure after patch available
- 90-day disclosure deadline
- Credit given to reporters (if desired)

---

## Security Best Practices

### For Personal Use

1. **Use prompt mode** (default) for interactive sessions
2. **Review approval prompts** before accepting
3. **Enable sanitization** for conversation history
4. **Rotate audit logs** regularly if using auto mode
5. **Keep credentials secure** - never paste in prompts

### For Team Deployments

1. **Use organization policy** to enforce team standards
2. **Centralize audit logs** for monitoring
3. **Review logs regularly** for anomalies
4. **Train users** on prompt mode approval process
5. **Document approved envelopes** for team workflows

### For Enterprise Deployments

1. **Require prompt mode** via organization policy
2. **Mandate audit logging** for all executions
3. **Centralized log aggregation** (SIEM integration)
4. **Regular security audits** of configurations
5. **Incident response plan** for security events
6. **Access control** for organization policy files
7. **Monitoring and alerting** on suspicious patterns

### Configuration Security

1. **Protect config files**: `chmod 600 config.yaml`
2. **Protect audit logs**: `chmod 600 audit.log`
3. **Protect cache directory**: `chmod 700 ~/.cache/cortex-skill/`
4. **Review org policy** before deployment
5. **Version control** organization policy (with appropriate access controls)

### Credential Management

1. **Never paste credentials** in prompts
2. **Use credential files** (but keep them in allowlist)
3. **Rotate credentials** regularly
4. **Use Snowflake SSO** when possible
5. **Monitor credential usage** via Snowflake audit logs

---

## Compliance Considerations

### Data Privacy

- PII removed before processing (GDPR, CCPA compliance)
- Audit logs may contain operational metadata (review retention requirements)
- Session history sanitized before caching

### Security Standards

- **SOC 2**: Audit logging, access controls, incident response
- **ISO 27001**: Configuration management, secure defaults, encryption
- **NIST**: Defense in depth, least privilege, separation of duties

### Industry-Specific

- **HIPAA**: Additional safeguards required for PHI
- **PCI DSS**: Never process credit card data (sanitization removes it)
- **FedRAMP**: May require additional controls and audit logging

**Note**: This skill is a development tool, not a production data processing system. Organizations must assess their own compliance requirements.

---

## Additional Resources

- [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - Detailed security best practices
- [README.md](README.md) - General documentation

---

**Contact**: For questions about this security policy, contact the Snowflake Integration Team.

**License**: Copyright © 2026 Snowflake Inc. All rights reserved.
