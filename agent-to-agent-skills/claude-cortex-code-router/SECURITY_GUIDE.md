# Security Best Practices Guide

**Version:** 2.0.0  
**Last Updated:** April 1, 2026

## Table of Contents

- [Overview](#overview)
- [Deployment Models](#deployment-models)
- [Personal Use Configuration](#personal-use-configuration)
- [Team Deployment Configuration](#team-deployment-configuration)
- [Enterprise Deployment Configuration](#enterprise-deployment-configuration)
- [Open Source Distribution](#open-source-distribution)
- [Security Checklist](#security-checklist)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Incident Response Playbook](#incident-response-playbook)

---

## Overview

This guide provides security best practices for deploying the cortex-code skill v2.0.0 across different environments. Choose the configuration that matches your threat model and operational requirements.

**Security Layers:**
1. **Configuration security**: Approval modes, org policies
2. **Runtime security**: Sanitization, credential blocking
3. **Audit security**: Logging, monitoring, alerting
4. **Operational security**: Access controls, incident response

---

## Deployment Models

### Model Comparison

| Aspect | Personal | Team | Enterprise |
|--------|----------|------|------------|
| **Approval Mode** | prompt recommended | prompt or auto | prompt required |
| **Audit Logging** | Optional | Recommended | Mandatory |
| **Org Policy** | N/A | Recommended | Required |
| **Log Aggregation** | No | Optional | Required |
| **Monitoring** | No | Recommended | Required |
| **Incident Response** | Informal | Document | Formal process |
| **Compliance** | N/A | Industry-specific | SOC 2, ISO 27001 |

---

## Personal Use Configuration

**Threat Model:** Individual developer, low compliance requirements, moderate security needs

### Recommended Configuration

```yaml
# ~/.claude/skills/cortex-code/config.yaml

security:
  # Use prompt mode for interactive approval
  approval_mode: "prompt"
  
  # Tool prediction threshold
  tool_prediction_confidence_threshold: 0.7
  
  # Enable sanitization
  sanitize_conversation_history: true
  
  # Audit logging (optional but recommended)
  audit_log_path: "~/.claude/skills/cortex-code/audit.log"
  audit_log_rotation: "10MB"
  audit_log_retention: 30
  
  # Secure caching
  cache_dir: "~/.cache/cortex-skill"
  cache_ttl: 86400
  
  # Credential protection
  credential_file_allowlist:
    - "~/.ssh/**"
    - "~/.aws/credentials"
    - "~/.snowflake/**"
    - "**/.env"
    - "**/credentials.json"
    - "**/.npmrc"
    - "**/.pypirc"
  
  # Allow all standard envelopes
  allowed_envelopes:
    - "RO"
    - "RW"
    - "RESEARCH"
    - "DEPLOY"
```

### Security Checklist

- [ ] Use prompt mode for approval
- [ ] Enable conversation history sanitization
- [ ] Protect config file: `chmod 600 config.yaml`
- [ ] Review audit logs periodically (if enabled)
- [ ] Keep skill updated to latest version
- [ ] Never share Snowflake credentials in prompts
- [ ] Use Snowflake SSO when possible
- [ ] Review approval prompts before accepting

### Optional Enhancements

**Enable audit logging:**
```yaml
security:
  approval_mode: "prompt"
  audit_log_path: "~/.claude/skills/cortex-code/audit.log"
```

**Use envelope_only for trusted workflows:**
```yaml
security:
  approval_mode: "envelope_only"  # Faster, still secure
```

---

## Team Deployment Configuration

**Threat Model:** Small team (5-50 developers), shared Snowflake account, collaboration needs, moderate-high security

### Recommended Configuration

**Organization Policy** (`~/.snowflake/cortex/claude-skill-policy.yaml`):
```yaml
# Enforced for all team members
security:
  # Require prompt mode for approval
  approval_mode: "prompt"
  
  # Mandatory audit logging
  audit_log_path: "~/.claude/skills/cortex-code/audit.log"
  audit_log_rotation: "10MB"
  audit_log_retention: 90  # 90 days for compliance
  
  # Enable sanitization
  sanitize_conversation_history: true
  
  # Credential protection (team-specific paths)
  credential_file_allowlist:
    - "~/.ssh/**"
    - "~/.aws/**"
    - "~/.snowflake/**"
    - "**/.env*"
    - "**/credentials.*"
    - "**/secrets.*"
  
  # Restrict envelopes
  allowed_envelopes:
    - "RO"
    - "RW"
    # RESEARCH and DEPLOY disabled for safety
```

### Deployment Steps

1. **Create Organization Policy**
   ```bash
   # Create policy directory
   mkdir -p ~/.snowflake/cortex
   
   # Deploy policy (from trusted source)
   cp team-policy.yaml ~/.snowflake/cortex/claude-skill-policy.yaml
   
   # Protect policy file
   chmod 600 ~/.snowflake/cortex/claude-skill-policy.yaml
   ```

2. **Centralize Audit Logs** (optional but recommended)
   ```bash
   # Symlink audit logs to shared location
   ln -s ~/shared/audit-logs/$(whoami)-audit.log \
     ~/.claude/skills/cortex-code/audit.log
   ```

3. **Team Training**
   - Review approval prompt workflow
   - Practice approving/denying tools
   - Understand credential allowlist
   - Know incident reporting process

### Security Checklist

- [ ] Deploy organization policy to all team members
- [ ] Protect policy file with restricted permissions
- [ ] Enable mandatory audit logging
- [ ] Document approved workflows and envelopes
- [ ] Train team on approval prompts
- [ ] Set up periodic audit log review
- [ ] Establish incident response process
- [ ] Monitor for policy violations
- [ ] Review logs weekly for anomalies
- [ ] Update policy as needed

### Monitoring

**Weekly Audit Review:**
```bash
# Count executions per user
cat ~/shared/audit-logs/*.log | jq -r '.user' | sort | uniq -c

# Find denied executions
cat ~/shared/audit-logs/*.log | jq 'select(.execution.approval_mode == "prompt" and .result.status == "denied")'

# Check for PII removal events
cat ~/shared/audit-logs/*.log | jq 'select(.security.pii_removed == true)'
```

---

## Enterprise Deployment Configuration

**Threat Model:** Large organization (50+ developers), compliance requirements (SOC 2, ISO 27001), centralized security, audit requirements

### Recommended Configuration

**Organization Policy** (`~/.snowflake/cortex/claude-skill-policy.yaml`):
```yaml
security:
  # Enforce prompt mode (no exceptions)
  approval_mode: "prompt"
  
  # Mandatory audit logging with extended retention
  audit_log_path: "/var/log/cortex-skill/audit.log"
  audit_log_rotation: "50MB"
  audit_log_retention: 365  # 1 year for compliance
  
  # Mandatory sanitization
  sanitize_conversation_history: true
  
  # Strict tool prediction threshold
  tool_prediction_confidence_threshold: 0.8
  
  # Comprehensive credential protection
  credential_file_allowlist:
    - "~/.ssh/**"
    - "~/.aws/**"
    - "~/.snowflake/**"
    - "~/.gcp/**"
    - "~/.azure/**"
    - "**/.env*"
    - "**/credentials.*"
    - "**/secrets.*"
    - "**/*_key.*"
    - "**/*-key.*"
    - "**/*.pem"
    - "**/*.key"
  
  # Restricted envelopes (RO only by default)
  allowed_envelopes:
    - "RO"
    # RW, RESEARCH, DEPLOY require approval request
```

### Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│         Centralized Policy Server               │
│  ~/.snowflake/cortex/claude-skill-policy.yaml   │
│  (deployed via configuration management)         │
└─────────────────────────┬───────────────────────┘
                          │ (Ansible/Puppet/Chef)
                          ↓
┌─────────────────────────────────────────────────┐
│           Developer Workstations                │
│   - Policy enforced automatically               │
│   - User config blocked or limited              │
│   - Audit logs centralized                      │
└─────────────────────────┬───────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────┐
│         Centralized Log Aggregation             │
│   - SIEM integration (Splunk, ELK, etc.)       │
│   - Real-time alerting                          │
│   - Anomaly detection                           │
│   - Compliance reporting                        │
└─────────────────────────────────────────────────┘
```

### Deployment Steps

1. **Policy Management**
   ```bash
   # Deploy via configuration management (example: Ansible)
   ansible-playbook deploy-cortex-skill-policy.yml \
     --extra-vars "policy_version=v2.0.0"
   ```

2. **Centralized Logging**
   ```bash
   # Configure rsyslog forwarding
   echo "*.* @@siem.example.com:514" >> /etc/rsyslog.conf
   
   # Or use filebeat for log shipping
   filebeat -c /etc/filebeat/filebeat.yml
   ```

3. **Access Control**
   ```bash
   # Restrict policy file
   chown root:root /etc/cortex-skill/policy.yaml
   chmod 444 /etc/cortex-skill/policy.yaml  # Read-only
   
   # Symlink to user directory
   ln -s /etc/cortex-skill/policy.yaml \
     ~/.snowflake/cortex/claude-skill-policy.yaml
   ```

4. **Monitoring Setup**
   - Integrate audit logs with SIEM
   - Configure alerting rules
   - Set up dashboards
   - Establish incident response workflows

### Security Checklist

- [ ] Deploy policy via configuration management
- [ ] Enforce read-only policy files
- [ ] Centralize all audit logs
- [ ] Integrate with SIEM (Splunk, ELK, etc.)
- [ ] Configure real-time alerting
- [ ] Set up anomaly detection
- [ ] Document security standards
- [ ] Train security team on incident response
- [ ] Conduct security audits quarterly
- [ ] Review and update policy monthly
- [ ] Test incident response procedures
- [ ] Maintain compliance documentation

### SIEM Integration

**Splunk Example:**
```bash
# Configure Splunk forwarder
cat > /opt/splunkforwarder/etc/system/local/inputs.conf << EOF
[monitor:///var/log/cortex-skill/*.log]
sourcetype = cortex_skill_audit
index = security
EOF
```

**ELK Stack Example:**
```yaml
# Filebeat configuration
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/cortex-skill/*.log
    json.keys_under_root: true
    json.add_error_key: true
    
output.elasticsearch:
  hosts: ["elk.example.com:9200"]
  index: "cortex-skill-audit-%{+yyyy.MM.dd}"
```

### Alerting Rules

**High-Priority Alerts:**
1. **Credential exposure attempt**
   - Trigger: `security.credential_blocked == true`
   - Action: Alert security team, investigate user intent

2. **Prompt injection detected**
   - Trigger: `security.sanitized == true` AND `security.pii_removed == false`
   - Action: Review prompt, update detection rules

3. **Policy violation**
   - Trigger: User attempted to modify policy file
   - Action: Alert security team, audit user actions

4. **Unusual tool execution**
   - Trigger: Tool used that wasn't in predicted list
   - Action: Review for false positive or attack

**Medium-Priority Alerts:**
1. **High execution volume**
   - Trigger: >100 executions per hour per user
   - Action: Check for automation or abuse

2. **Cache tampering**
   - Trigger: Fingerprint validation failure
   - Action: Investigate, re-discover capabilities

### Compliance Reporting

**Weekly Report:**
```bash
# Generate compliance report
cat /var/log/cortex-skill/*.log | \
  jq -r '[.timestamp, .user, .execution.approval_mode, .result.status] | @csv' | \
  sed '1i timestamp,user,approval_mode,status' > weekly-report.csv
```

**Monthly Metrics:**
- Total executions
- Approval mode distribution
- Tool usage breakdown
- PII removal count
- Credential blocking count
- Policy violations

---

## Open Source Distribution

**Threat Model:** Public distribution, unknown users, potential malicious use, need for security documentation

### Distribution Checklist

- [ ] Include SECURITY.md in repository
- [ ] Include MIGRATION.md for upgraders
- [ ] Include SECURITY_GUIDE.md (this document)
- [ ] Document secure defaults in README
- [ ] Provide config.yaml.example with best practices
- [ ] Include security audit findings and resolutions
- [ ] Document threat model assumptions
- [ ] Provide security issue reporting instructions
- [ ] Include license with security disclaimers
- [ ] Document supported versions and EOL dates

### Example config.yaml.example

```yaml
# Example configuration for cortex-code skill v2.0.0
#
# Copy to ~/.claude/skills/cortex-code/config.yaml and customize

security:
  # SECURITY: Use "prompt" mode for interactive approval
  # Options: "prompt" (most secure), "auto" (v1.x compat), "envelope_only"
  approval_mode: "prompt"
  
  # Tool prediction confidence threshold
  tool_prediction_confidence_threshold: 0.7
  
  # SECURITY: Enable audit logging if using auto or envelope_only modes
  audit_log_path: "~/.claude/skills/cortex-code/audit.log"
  audit_log_rotation: "10MB"
  audit_log_retention: 30
  
  # SECURITY: Enable conversation history sanitization
  sanitize_conversation_history: true
  
  # Secure caching directory
  cache_dir: "~/.cache/cortex-skill"
  cache_ttl: 86400  # 24 hours
  
  # SECURITY: Credential file allowlist - blocks routing if detected
  credential_file_allowlist:
    - "~/.ssh/**"
    - "~/.aws/credentials"
    - "~/.snowflake/**"
    - "**/.env"
    - "**/credentials.json"
  
  # Allowed security envelopes
  allowed_envelopes:
    - "RO"     # Read-only
    - "RW"     # Read-write
    - "RESEARCH"  # Research mode
    - "DEPLOY"    # Full access (use cautiously)
```

---

## Security Checklist

### Pre-Deployment

- [ ] Review threat model for your environment
- [ ] Choose appropriate deployment model
- [ ] Create configuration file
- [ ] Set approval mode based on needs
- [ ] Configure credential allowlist
- [ ] Enable audit logging (if needed)
- [ ] Protect configuration files (chmod 600)
- [ ] Test configuration loading
- [ ] Verify cache permissions
- [ ] Document security decisions

### Post-Deployment

- [ ] Test end-to-end workflow
- [ ] Verify approval prompts (if using prompt mode)
- [ ] Check audit log creation (if enabled)
- [ ] Test credential blocking
- [ ] Test PII sanitization
- [ ] Review initial audit logs
- [ ] Train users on approval workflow
- [ ] Document incident response process
- [ ] Schedule periodic security reviews
- [ ] Set up monitoring (if applicable)

### Ongoing

- [ ] Review audit logs weekly/monthly
- [ ] Update credential allowlist as needed
- [ ] Patch skill to latest version
- [ ] Review security incidents
- [ ] Update organization policy as needed
- [ ] Conduct security audits
- [ ] Train new team members
- [ ] Test incident response procedures
- [ ] Review and update documentation

---

## Monitoring and Alerting

### Personal Use

**Manual Monitoring:**
```bash
# Review recent audit logs
tail -100 ~/.claude/skills/cortex-code/audit.log | jq

# Count PII removal events
cat ~/.claude/skills/cortex-code/audit.log | \
  jq 'select(.security.pii_removed == true)' | wc -l

# Find failed executions
cat ~/.claude/skills/cortex-code/audit.log | \
  jq 'select(.result.status != "success")'
```

### Team Use

**Weekly Monitoring Script:**
```bash
#!/bin/bash
# monitor-cortex-skill.sh

LOG_DIR="/path/to/shared/audit-logs"
REPORT_FILE="weekly-report-$(date +%Y%m%d).txt"

echo "=== Cortex Skill Security Report ===" > $REPORT_FILE
echo "Date: $(date)" >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Total executions
echo "Total Executions:" >> $REPORT_FILE
cat $LOG_DIR/*.log | jq -s 'length' >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Executions by user
echo "Executions by User:" >> $REPORT_FILE
cat $LOG_DIR/*.log | jq -r '.user' | sort | uniq -c >> $REPORT_FILE
echo "" >> $REPORT_FILE

# PII removal events
echo "PII Removal Events:" >> $REPORT_FILE
cat $LOG_DIR/*.log | jq 'select(.security.pii_removed == true)' | wc -l >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Credential blocking events
echo "Credential Blocking Events:" >> $REPORT_FILE
cat $LOG_DIR/*.log | jq 'select(.status == "blocked")' | wc -l >> $REPORT_FILE

# Email report
mail -s "Cortex Skill Weekly Report" team@example.com < $REPORT_FILE
```

### Enterprise Use

**SIEM Dashboard (Splunk SPL Example):**
```spl
index=security sourcetype=cortex_skill_audit
| stats count by user, execution.approval_mode, result.status
| table user, count, execution.approval_mode, result.status
```

**Alert Rules (Splunk):**
```spl
# Alert on credential blocking
index=security sourcetype=cortex_skill_audit status="blocked"
| alert severity=high email=security@example.com

# Alert on high execution volume
index=security sourcetype=cortex_skill_audit
| bucket _time span=1h
| stats count by _time, user
| where count > 100
| alert severity=medium
```

---

## Incident Response Playbook

### Incident Types

1. **Prompt Injection Attempt**
2. **Credential Exposure Attempt**
3. **Unauthorized Tool Execution**
4. **Cache Tampering**
5. **Policy Violation**

### Response Procedures

#### 1. Prompt Injection Attempt

**Detection:**
- Audit log shows `security.sanitized == true`
- Unusual prompts detected

**Response:**
1. **Investigate**
   - Review original prompt (if available)
   - Check if injection was successful
   - Identify user and intent

2. **Contain**
   - No containment needed (already blocked)
   - Verify sanitization worked correctly

3. **Remediate**
   - Update detection patterns if new attack vector
   - Document incident
   - Train user if accidental

4. **Follow-up**
   - Monitor user for repeat attempts
   - Update security awareness training

#### 2. Credential Exposure Attempt

**Detection:**
- Audit log shows `status: "blocked"` with `pattern_matched`
- User reports blocked prompt

**Response:**
1. **Investigate**
   - Review which credential pattern was matched
   - Determine if legitimate use case or attack
   - Check if credentials were actually exposed

2. **Contain**
   - Verify blocking worked correctly
   - Check for other exposure vectors

3. **Remediate**
   - If legitimate: add exception or update allowlist
   - If malicious: escalate to security team
   - Rotate credentials if exposed

4. **Follow-up**
   - Document incident
   - Update credential allowlist if needed
   - Train user on proper credential handling

#### 3. Unauthorized Tool Execution

**Detection:**
- Tool executed not in approved list
- Envelope violation detected

**Response:**
1. **Investigate**
   - Review tool prediction accuracy
   - Check if envelope was bypassed
   - Identify root cause

2. **Contain**
   - Review all recent executions by user
   - Check for configuration tampering

3. **Remediate**
   - Fix tool prediction if false negative
   - Update envelope configuration
   - Patch vulnerability if found

4. **Follow-up**
   - Test fix thoroughly
   - Document root cause
   - Update security controls

#### 4. Cache Tampering

**Detection:**
- SHA256 fingerprint mismatch
- Cache validation failure

**Response:**
1. **Investigate**
   - Determine how cache was modified
   - Check for malicious intent
   - Review access logs

2. **Contain**
   - Clear tampered cache
   - Rediscover capabilities
   - Check other users' caches

3. **Remediate**
   - Restrict cache directory permissions
   - Investigate attacker access
   - Patch vulnerability if found

4. **Follow-up**
   - Monitor for repeat attempts
   - Update security controls
   - Document incident

---

## Additional Resources

- [SECURITY.md](SECURITY.md) - Security policy and features
- [MIGRATION.md](MIGRATION.md) - v1.x to v2.0.0 migration guide
- [README.md](README.md) - General documentation
- [Design Document](docs/superpowers/specs/2026-04-01-cortex-code-security-hardening-design.md)

---

**Contact:** For questions about security best practices, contact security@snowflake.com

**License:** Copyright © 2026 Snowflake Inc. All rights reserved.
