# Changelog

All notable changes to the cortex-code skill project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-04-02

### 🎉 Major Release: Security Enhancements

Version 2.0.0 is a major release introducing comprehensive security enhancements and new capabilities while maintaining backward compatibility through configuration.

**Migration Recommended**: See [MIGRATION.md](MIGRATION.md) for upgrade instructions and new features.

---

### ✨ Added

#### Security Features

- **Configurable Approval Modes** (#1)
  - `prompt` mode: User approval required before execution (new default)
  - `auto` mode: Auto-approve with mandatory audit logging (v1.x behavior)
  - `envelope_only` mode: Rely on envelope blocklist only
  - Resolves Critical Finding #1: Auto-approval bypass

- **Prompt Sanitization** (#2)
  - Automatic PII removal (credit cards, SSN, emails, phone numbers)
  - Prompt injection detection with complete content removal
  - Session history sanitization
  - Resolves High Finding #2: Prompt injection attacks

- **Credential File Protection** (#6)
  - Blocks routing when credential file paths detected
  - Configurable allowlist patterns
  - Case-insensitive matching with wildcard support
  - Resolves Medium Finding #6: LLM routing credential exposure

- **Secure Caching** (#4)
  - Moved from insecure `/tmp` to `~/.cache/cortex-skill/`
  - SHA256 fingerprint validation for cache integrity
  - Tamper detection with automatic invalidation
  - File permissions: 0600 (owner read/write only)
  - Resolves Medium Finding #4: Insecure /tmp cache

- **Audit Logging** (#7)
  - Structured JSONL format (machine-readable)
  - Mandatory for `auto` and `envelope_only` modes
  - Size-based log rotation (configurable)
  - Configurable retention period (default 30 days)
  - Logs: routing, execution, security actions, results
  - Resolves Medium Finding #7: No audit trail

- **Organization Policy Override** (#8)
  - Enterprise policy support at `~/.snowflake/cortex/claude-skill-policy.yaml`
  - Policy overrides user configuration
  - Centralized security control for teams/enterprises
  - Resolves part of Finding #8: Enterprise deployment

#### Security Components

- **ConfigManager** (`security/config_manager.py`)
  - Three-layer configuration precedence (org policy > user > defaults)
  - Deep merge with validation
  - Path expansion for `~/` and environment variables
  - Validation for approval modes, envelopes, numeric ranges

- **AuditLogger** (`security/audit_logger.py`)
  - JSONL logging with UTC timestamps
  - SHA256-based log rotation
  - Secure file permissions (0600)
  - Thread-safe single-process design

- **CacheManager** (`security/cache_manager.py`)
  - SHA256 fingerprint validation
  - TTL expiration with auto-cleanup
  - Path traversal prevention via key validation
  - Secure permissions (0600 files, 0700 directories)

- **PromptSanitizer** (`security/prompt_sanitizer.py`)
  - PII removal (credit cards, SSN, emails, phones)
  - Injection detection (complete content removal)
  - Conversation history sanitization
  - Structure-preserving processing

- **ApprovalHandler** (`security/approval_handler.py`)
  - Tool prediction with confidence scoring
  - Approval prompt formatting with warnings
  - User response parsing (approve/approve_all/deny)
  - ApprovalResult dataclass

- **Security Wrapper** (`scripts/security_wrapper.py`)
  - Main orchestrator integrating all security components
  - Routing integration (cortex vs claude)
  - Three execution modes (prompt/auto/envelope_only)
  - Credential blocking at routing layer
  - Mandatory audit logging

#### Documentation

- **SECURITY.md**: Security policy, threat model, configuration guide
- **MIGRATION.md**: v1.x to v2.0.0 upgrade guide with rollback procedures
- **SECURITY_GUIDE.md**: Best practices for personal/team/enterprise deployments
- **config.yaml.example**: Comprehensive configuration template with examples
- **Updated README.md**: v2.0.0 features, security section, migration notice
- **Updated SKILL.md**: Security wrapper workflow, troubleshooting

#### Testing

- **Security Validation Tests** (`tests/security/test_attack_scenarios.py`)
  - 46 attack scenario tests
  - Prompt injection, credential exposure, cache tampering
  - PII leakage, approval bypass, config security

- **Regression Tests** (`tests/regression/test_v1_compatibility.py`)
  - 22 compatibility tests
  - Auto mode behaves like v1.x
  - Backward compatibility validation

- **E2E Integration Tests** (`tests/integration/test_e2e_execution.py`)
  - 29 end-to-end tests
  - Full pipeline for all approval modes
  - Complex multi-stage scenarios

- **Total Test Suite**: 209 tests (all passing)

---

### 🔄 Changed

#### Breaking Changes

1. **Default Approval Behavior**
   - v1.x: All operations auto-approved
   - v2.0.0: Approval prompt shown by default (`approval_mode: "prompt"`)
   - **Migration**: Set `approval_mode: "auto"` for v1.x behavior

2. **Cache Location**
   - v1.x: `/tmp/cortex-capabilities.json`
   - v2.0.0: `~/.cache/cortex-skill/cortex-capabilities.json`
   - **Impact**: First run rediscovers capabilities (2-5 seconds)
   - **Action**: No manual intervention required

3. **Audit Logging Requirement**
   - v1.x: No audit logging
   - v2.0.0: Mandatory for `auto` and `envelope_only` modes
   - **Impact**: Log files created automatically
   - **Action**: Configure rotation/retention if needed

4. **PII Sanitization**
   - v1.x: No sanitization
   - v2.0.0: Enabled by default
   - **Impact**: PII replaced with placeholders
   - **Action**: Disable via `sanitize_conversation_history: false` if needed

5. **Credential File Blocking**
   - v1.x: No blocking
   - v2.0.0: Blocks routing for credential paths
   - **Impact**: Prompts with credential paths rejected
   - **Action**: Remove credential references from prompts

#### Modified Scripts

- **execute_cortex.py**: Added approval mode support (prompt/auto/envelope_only)
- **route_request.py**: Added credential file blocking at routing layer
- **discover_cortex.py**: Use CacheManager instead of `/tmp`, integrity validation
- **read_cortex_sessions.py**: PII sanitization for session content

#### Configuration

- New `config.yaml` structure with security settings
- Organization policy override support
- Environment variable overrides (`CORTEX_SKILL_CONFIG`, `CORTEX_SKILL_ORG_POLICY`)

---

### 🔒 Security Enhancements

The following security features were added in v2.0.0:

- **Configurable Approval Modes**
  - Three modes: prompt (secure default), auto (v1.x compatibility), envelope_only
  
- **Prompt Sanitization**
  - Automatic PII removal and injection detection
  
- **Enhanced Documentation**
  - Comprehensive security documentation and best practices
  
- **Secure Caching**
  - Moved from `/tmp` to `~/.cache/cortex-skill/` with SHA256 validation
  
- **Session Sanitization**
  - PII removal from conversation history
  
- **Credential Protection**
  - Allowlist-based credential path blocking
  
- **Audit Logging**
  - Structured JSONL logs with mandatory logging for auto modes
  
- **Organization Policy**
  - Enterprise policy override support

---

### 🔒 Security

- **Secure by Default**: New installations use `prompt` mode (most secure)
- **Defense in Depth**: Multiple security layers (sanitization, approval, audit)
- **Least Privilege**: Tool access controlled via envelopes
- **Transparency**: All operations logged when auto-approval enabled
- **Compliance**: GDPR/CCPA PII removal, SOC 2 audit logging

---

### 📚 Documentation Improvements

- Comprehensive security policy documentation
- Migration guide with rollback procedures
- Deployment best practices for personal/team/enterprise
- Configuration examples by deployment type
- Incident response playbooks
- Troubleshooting guides for security features
- SIEM integration examples (Splunk, ELK)

---

### 🧪 Testing Improvements

- **209 tests** covering all security features
- Attack scenario validation (prompt injection, credential exposure, etc.)
- v1.x compatibility regression tests
- End-to-end integration tests for all approval modes
- All tests passing with <2 second execution time

---

### ⚠️ Deprecations

None. All v1.x functionality preserved via configuration.

---

### 🚀 Performance

- Cache integrity validation adds ~10ms per cache read
- Tool prediction adds ~50-100ms in prompt mode
- Sanitization adds ~5-10ms per prompt
- Overall impact: <200ms for typical operations

---

### 📦 Dependencies

No new external dependencies. Uses Python standard library only.

---

## [1.0.0] - 2026-03-19

### Initial Release

- Dynamic Cortex Code capability discovery
- LLM-based semantic routing (Snowflake vs general tasks)
- Security envelope support (RO, RW, RESEARCH, DEPLOY, NONE)
- Programmatic mode via `--input-format stream-json`
- Context enrichment with conversation history
- Session file parsing for historical context
- Multi-agent collaboration pattern

---

## Migration Notes

### Upgrading from 1.x to 2.0.0

**Quick Migration** (maintain v1.x behavior):
```yaml
# ~/.claude/skills/cortex-code/config.yaml
security:
  approval_mode: "auto"
  audit_log_path: "~/.claude/skills/cortex-code/audit.log"
```

**Secure Migration** (recommended):
```yaml
# Use defaults (prompt mode)
# No configuration file needed
```

See [MIGRATION.md](MIGRATION.md) for detailed upgrade instructions.

---

## Security Disclosure

Security issues should be reported to security@snowflake.com. Do not publicly disclose security vulnerabilities. See [SECURITY.md](SECURITY.md) for disclosure policy.

---

## Links

- [README.md](README.md) - General usage and features
- [SECURITY.md](SECURITY.md) - Security policy and threat model
- [MIGRATION.md](MIGRATION.md) - v1.x to v2.0.0 upgrade guide
- [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - Deployment best practices
- [config.yaml.example](config.yaml.example) - Configuration template
- [GitHub Issues](https://github.com/sfc-gh-tjia/claude_skill_cortexcode/issues)

---

**Copyright © 2026 Snowflake Inc. All rights reserved.**
