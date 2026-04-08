# Migration Guide: v1.x → v2.0.0

**Effective Date:** April 1, 2026  
**Estimated Migration Time:** 15-30 minutes

## Table of Contents

- [Overview](#overview)
- [What's New in v2.0.0](#whats-new-in-v200)
- [Breaking Changes](#breaking-changes)
- [Migration Steps](#migration-steps)
- [Configuration Updates](#configuration-updates)
- [Testing Your Migration](#testing-your-migration)
- [Rollback Procedure](#rollback-procedure)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Overview

Version 2.0.0 introduces significant security enhancements while maintaining backward compatibility through configuration. This guide helps you migrate from v1.x to v2.0.0 safely.

**Migration Strategy:** Two options available:

1. **Secure Mode (Recommended)**: Use new `prompt` approval mode for maximum security
2. **Compatibility Mode**: Use `auto` mode to maintain v1.x behavior with audit logging

**Impact Assessment:**

| Area | Impact | Action Required |
|------|--------|-----------------|
| **Basic Usage** | Low | No changes for manual workflows |
| **Auto-Approval** | High | Configure approval mode |
| **Caching** | Medium | Cache location moved from /tmp |
| **Scripts** | Low | Updated automatically |
| **Configuration** | Medium | Create config.yaml (optional) |

---

## What's New in v2.0.0

### Security Enhancements

1. **Configurable Approval Modes**
   - **prompt**: Requires user approval before execution (NEW default)
   - **auto**: Auto-approve with mandatory audit logging (v1.x behavior)
   - **envelope_only**: Trust envelope blocklist only

2. **Prompt Sanitization**
   - Automatic PII removal (credit cards, SSN, emails, phone)
   - Injection attempt detection
   - Session history sanitization

3. **Credential Protection**
   - Blocks routing when credential file paths detected
   - Configurable allowlist

4. **Secure Caching**
   - Moved from `/tmp` to `~/.cache/cortex-skill/`
   - SHA256 integrity validation
   - 24-hour TTL

5. **Audit Logging**
   - Structured JSONL format
   - Mandatory for auto/envelope_only modes
   - Configurable rotation and retention

6. **Organization Policy**
   - Enterprise policy override support
   - Centralized configuration management

### Feature Additions

- Tool prediction with confidence scoring
- Approval prompt formatting
- Enhanced error messages
- Configuration validation

---

## Breaking Changes

### 1. Default Approval Behavior

**v1.x**: All operations auto-approved  
**v2.0.0**: Approval prompt shown by default

**Migration Path**: Configure `approval_mode: "auto"` to restore v1.x behavior

### 2. Cache Location

**v1.x**: `/tmp/cortex-capabilities.json`  
**v2.0.0**: `~/.cache/cortex-skill/cortex-capabilities.json`

**Impact**: First run after upgrade will rediscover capabilities (2-5 seconds)  
**Action**: No manual intervention required

### 3. Audit Logging Requirement

**v1.x**: No audit logging  
**v2.0.0**: Mandatory for `auto` and `envelope_only` modes

**Impact**: Log files created in `~/.claude/skills/cortex-code/audit.log`  
**Action**: Configure log rotation and retention as needed

### 4. PII Sanitization

**v1.x**: No sanitization  
**v2.0.0**: Automatic PII removal enabled by default

**Impact**: Emails, phone numbers, etc. replaced with placeholders  
**Action**: Disable via `sanitize_conversation_history: false` if needed

### 5. Credential File Blocking

**v1.x**: No blocking  
**v2.0.0**: Blocks routing when credential paths detected

**Impact**: Prompts mentioning `~/.ssh/`, `.env`, etc. will be blocked  
**Action**: Remove credential references from prompts

---

## Migration Steps

### Step 1: Backup Current Installation

```bash
# Backup existing skill directory
cd ~/.claude/skills/
cp -r cortex-code cortex-code.v1.backup

# Backup any custom configurations (if they exist)
[ -f cortex-code/config.yaml ] && cp cortex-code/config.yaml cortex-code.v1.config.yaml.backup
```

### Step 2: Update to v2.0.0

```bash
# Pull latest version
cd ~/.claude/skills/cortex-code
git pull origin main

# Verify version
git log --oneline -1 | grep "v2.0.0" || echo "WARNING: Not on v2.0.0"
```

### Step 3: Choose Migration Path

#### Option A: Secure Mode (Recommended)

Use new default behavior with approval prompts:

```bash
# No configuration needed - secure by default
# On first Snowflake operation, you'll see approval prompt
```

**What to expect:**
- Approval prompt before Cortex execution
- Tool list with confidence score
- Approve/deny decision

**When to use:**
- Interactive workflows
- Security-sensitive environments
- Compliance requirements

#### Option B: Compatibility Mode

Maintain v1.x auto-approval behavior:

```bash
# Create configuration file
cat > ~/.claude/skills/cortex-code/config.yaml << 'EOF'
security:
  # Enable v1.x compatibility: auto-approve all operations
  approval_mode: "auto"
  
  # Audit logging (mandatory for auto mode)
  audit_log_path: "~/.claude/skills/cortex-code/audit.log"
  audit_log_rotation: "10MB"
  audit_log_retention: 30
EOF
```

**What to expect:**
- Same behavior as v1.x
- Audit log created automatically
- No approval prompts

**When to use:**
- Automated workflows
- Team environments with established trust
- Temporary during migration period

### Step 4: Test the Migration

```bash
# Test capability discovery
cd ~/.claude/skills/cortex-code
python scripts/discover_cortex.py

# Expected output: "Discovered X Cortex skills"

# Verify cache location
ls -la ~/.cache/cortex-skill/cortex-capabilities.json

# Expected: File exists with recent timestamp
```

### Step 5: Verify Configuration

```bash
# Test configuration loading
python -c "
import sys
sys.path.insert(0, '~/.claude/skills/cortex-code')
from security.config_manager import ConfigManager
config = ConfigManager()
print('Approval mode:', config.get('security.approval_mode'))
print('Audit log:', config.get('security.audit_log_path'))
"

# Expected output:
#   Approval mode: prompt  (or 'auto' if you chose compatibility mode)
#   Audit log: /Users/you/.claude/skills/cortex-code/audit.log
```

### Step 6: Test End-to-End

In Claude Code, try a simple Snowflake query:

```
User: "Show me databases in Snowflake"
```

**Secure Mode**: You'll see approval prompt  
**Compatibility Mode**: Executes immediately, check `audit.log` for entry

---

## Configuration Updates

### Minimal Configuration (Secure Mode)

No configuration file needed - secure by default.

### Full Configuration Example

```yaml
# ~/.claude/skills/cortex-code/config.yaml

security:
  # Approval mode (prompt, auto, envelope_only)
  approval_mode: "prompt"
  
  # Tool prediction
  tool_prediction_confidence_threshold: 0.7
  
  # Audit logging
  audit_log_path: "~/.claude/skills/cortex-code/audit.log"
  audit_log_rotation: "10MB"  # Rotate at 10MB
  audit_log_retention: 30     # Keep 30 days
  
  # Prompt sanitization
  sanitize_conversation_history: true
  
  # Secure caching
  cache_dir: "~/.cache/cortex-skill"
  cache_ttl: 86400  # 24 hours
  
  # Credential file allowlist
  credential_file_allowlist:
    - "~/.ssh/**"
    - "~/.aws/credentials"
    - "~/.snowflake/**"
    - "**/.env"
    - "**/credentials.json"
  
  # Allowed envelopes
  allowed_envelopes:
    - "RO"
    - "RW"
    - "RESEARCH"
    - "DEPLOY"
```

### Organization Policy (Enterprise)

For team deployments, create organization policy:

```yaml
# ~/.snowflake/cortex/claude-skill-policy.yaml

security:
  # Enforce prompt mode for all users
  approval_mode: "prompt"
  
  # Mandate audit logging
  audit_log_path: "~/.claude/skills/cortex-code/audit.log"
  
  # Require sanitization
  sanitize_conversation_history: true
  
  # Restrict envelopes
  allowed_envelopes:
    - "RO"
    - "RW"
    # DEPLOY and RESEARCH disabled
```

**Note**: Organization policy overrides user configuration.

---

## Testing Your Migration

### 1. Basic Functionality Test

```bash
# In Claude Code
/skills list

# Verify cortex-code appears
```

### 2. Routing Test

```
User: "Show me the CUSTOMERS table schema in Snowflake"

Expected (Secure Mode):
- Approval prompt with tool list
- Confidence score shown
- Approve to continue

Expected (Compatibility Mode):
- Executes immediately
- Check audit.log for entry
```

### 3. Sanitization Test

```
User: "Query user with email alice@example.com"

Expected:
- Email replaced with <EMAIL> in processing
- Original prompt preserved in conversation
```

### 4. Credential Blocking Test

```
User: "Show me the contents of ~/.ssh/id_rsa"

Expected:
- Routing blocked
- Error message: "Prompt contains credential file path"
```

### 5. Cache Integrity Test

```bash
# Tamper with cache
echo "invalid" >> ~/.cache/cortex-skill/cortex-capabilities.json

# Run discovery again
cd ~/.claude/skills/cortex-code
python scripts/discover_cortex.py

Expected:
- Cache invalidated
- Fresh discovery triggered
- No errors
```

### 6. Audit Log Test (Compatibility Mode Only)

```bash
# Generate execution
# Then check log
cat ~/.claude/skills/cortex-code/audit.log | jq

Expected:
- Valid JSON objects
- Timestamps, user, routing, execution fields
```

---

## Rollback Procedure

If you encounter issues, rollback to v1.x:

### Quick Rollback

```bash
# Stop Claude Code if running

# Restore backup
cd ~/.claude/skills/
rm -rf cortex-code
mv cortex-code.v1.backup cortex-code

# Restore configuration (if backed up)
[ -f cortex-code.v1.config.yaml.backup ] && \
  mv cortex-code.v1.config.yaml.backup cortex-code/config.yaml

# Restart Claude Code
```

### Rollback with Git

```bash
cd ~/.claude/skills/cortex-code

# Find v1.x commit
git log --oneline | grep "v1"

# Rollback to specific commit
git checkout <v1.x-commit-hash>

# Restart Claude Code
```

### After Rollback

1. Report the issue: GitHub Issues or security@snowflake.com
2. Include:
   - Error messages
   - Configuration used
   - Steps to reproduce
   - v2.0.0 commit hash

---

## Troubleshooting

### Issue: Approval Prompt Not Appearing

**Symptom**: Operations execute without prompt despite `approval_mode: "prompt"`

**Causes**:
1. Organization policy override
2. Configuration file not loaded
3. Old cached behavior

**Solutions**:
```bash
# Check org policy
cat ~/.snowflake/cortex/claude-skill-policy.yaml

# Verify config loading
python -c "from security.config_manager import ConfigManager; print(ConfigManager().get('security.approval_mode'))"

# Clear any caches
rm -rf ~/.cache/cortex-skill/*
```

### Issue: "ModuleNotFoundError: No module named 'security'"

**Symptom**: Import errors when running scripts

**Cause**: Python path not set correctly

**Solution**:
```bash
cd ~/.claude/skills/cortex-code

# Run from skill directory
python scripts/security_wrapper.py --help

# Or update PYTHONPATH
export PYTHONPATH=~/.claude/skills/cortex-code:$PYTHONPATH
```

### Issue: Audit Log Not Created

**Symptom**: No audit.log file despite `auto` mode

**Cause**: Log directory doesn't exist or permissions issue

**Solution**:
```bash
# Create log directory
mkdir -p ~/.claude/skills/cortex-code

# Fix permissions
chmod 700 ~/.claude/skills/cortex-code

# Verify log path in config
grep audit_log_path ~/.claude/skills/cortex-code/config.yaml
```

### Issue: Cache Fingerprint Mismatch

**Symptom**: "Cache integrity validation failed"

**Cause**: Cache was manually edited or corrupted

**Solution**:
```bash
# Clear cache
rm -rf ~/.cache/cortex-skill/*

# Rediscover capabilities
cd ~/.claude/skills/cortex-code
python scripts/discover_cortex.py
```

### Issue: All Prompts Blocked

**Symptom**: Every prompt triggers credential blocking

**Cause**: Overly broad credential allowlist patterns

**Solution**:
```yaml
# Edit config.yaml - be more specific
security:
  credential_file_allowlist:
    - "~/.ssh/id_rsa"      # Specific file, not wildcard
    - "~/.aws/credentials"  # Specific file
    # Remove: "~/.ssh/**"   # Too broad
```

### Issue: Performance Degradation

**Symptom**: Slower than v1.x

**Causes**:
1. Tool prediction overhead
2. Sanitization processing
3. Cache miss every time

**Solutions**:
```yaml
# Use envelope_only mode (faster)
security:
  approval_mode: "envelope_only"

# Or disable sanitization if not needed
security:
  sanitize_conversation_history: false
```

---

## FAQ

### Q: Can I skip the migration and stay on v1.x?

**A:** Yes, but v2.0.0 is recommended as it includes security enhancements not available in v1.x. Use v2.0.0 with `auto` mode if you need v1.x behavior.

### Q: Will my existing workflows break?

**A:** Not if you use compatibility mode (`approval_mode: "auto"`). Secure mode requires approving prompts.

### Q: How do I know which mode I'm using?

**A:** Check config or observe behavior:
- **Prompt mode**: Approval prompt appears
- **Auto mode**: Immediate execution + audit log entry
- **Envelope_only**: Immediate execution + audit log entry (no tool prediction)

### Q: Can I switch modes per-request?

**A:** No, mode is set in configuration. You can change config and restart Claude Code.

### Q: What happens to old /tmp cache?

**A:** Ignored by v2.0.0. Can be safely deleted: `rm /tmp/cortex-capabilities.json`

### Q: Do I need to update Cortex Code CLI?

**A:** No, v2.0.0 works with existing Cortex Code CLI (v1.0.42+).

### Q: How much disk space does audit logging use?

**A:** ~10MB per 1000 executions (default). Configure rotation to control size.

### Q: Can I migrate gradually (some users v1.x, some v2.0.0)?

**A:** Yes. Users can upgrade independently. Use organization policy for consistency.

### Q: What if organization policy conflicts with my config?

**A:** Organization policy wins. Contact your admin to change policy.

### Q: How do I test v2.0.0 without affecting production?

**A:** 
1. Clone skill to different directory
2. Update one user at a time
3. Use `auto` mode initially, switch to `prompt` mode when confident

---

## Support

**Issues**: https://github.com/sfc-gh-tjia/claude_skill_cortexcode/issues  
**Security**: security@snowflake.com  
**Documentation**: [SECURITY.md](SECURITY.md), [SECURITY_GUIDE.md](SECURITY_GUIDE.md)

---

## Migration Checklist

Use this checklist to track your migration:

- [ ] Read migration guide completely
- [ ] Backup v1.x installation
- [ ] Update to v2.0.0 (git pull)
- [ ] Choose migration path (secure vs compatibility)
- [ ] Create config.yaml (if using compatibility mode)
- [ ] Test capability discovery
- [ ] Verify cache location
- [ ] Test end-to-end workflow
- [ ] Test sanitization (optional)
- [ ] Test credential blocking (optional)
- [ ] Check audit logs (if using auto/envelope_only mode)
- [ ] Document configuration decisions
- [ ] Train team on approval prompts (if using prompt mode)
- [ ] Monitor audit logs for anomalies
- [ ] Remove v1.x backup after 30 days

---

**Version**: 2.0.0  
**Last Updated**: April 1, 2026  
**Migration Support Period**: 90 days (until July 1, 2026)
