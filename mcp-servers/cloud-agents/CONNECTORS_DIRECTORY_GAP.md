# Connectors Directory Submission — Gap Analysis

Mapping our Cloud Agents MCP server against Anthropic's Connectors Directory requirements.

Reference: https://claude.com/docs/connectors/building/submission

---

## Submission Type

**Remote MCP server** (internet-hosted, provides tools to Claude)

- Our server is currently stdio-based (local). For directory submission, it would need to be a **remote HTTPS server** or packaged as a **Desktop extension (MCPB)**.
- Decision needed: remote hosted vs MCPB desktop extension?

---

## Requirements Checklist

### 1. Security — Meet Anthropic's security standards

| Requirement | Status | Notes |
|---|---|---|
| No secrets in code | PASS | Token read from env/file, never hardcoded |
| Credential redaction in errors | PASS | `auth.mjs` redacts tokens in error messages |
| No data collection beyond function | PASS | State dir stores handles/events, no conversation data |

### 2. Tool Annotations — title, readOnlyHint, destructiveHint

| Tool | title | readOnlyHint | destructiveHint | Status |
|---|---|---|---|---|
| cloud_agent_spawn | MISSING | false | false | NEEDS title |
| cloud_agent_send_input | MISSING | false | false | NEEDS title |
| cloud_agent_output | MISSING | true | — | NEEDS title + readOnlyHint |
| cloud_agent_wait | MISSING | true | — | NEEDS title + readOnlyHint |
| cloud_agent_status | MISSING | true | — | NEEDS title + readOnlyHint |
| cloud_agent_list | MISSING | true | — | NEEDS title + readOnlyHint |
| cloud_agent_close | MISSING | — | true | NEEDS title + destructiveHint |
| cloud_agent_resume | MISSING | false | false | NEEDS title |

**Action:** Add `annotations` block to all 8 tools in `tools.mjs`.

### 3. Authentication — OAuth 2.0 for authenticated services

| Requirement | Status | Notes |
|---|---|---|
| OAuth 2.0 | NOT IMPLEMENTED | Currently uses session token / PAT. Need OAuth flow for directory. |
| Dynamic client registration | NOT IMPLEMENTED | Would need Snowflake OAuth app |

**Action:** This is the biggest gap. Snowflake supports OAuth — need to implement the OAuth 2.0 flow where:
- User clicks "Connect" in Claude.ai
- Redirected to Snowflake OAuth consent
- Token returned to connector
- Refresh token used for session maintenance

### 4. Privacy Policy

| Requirement | Status | Notes |
|---|---|---|
| Privacy Policy section in README | MISSING | Need to add |
| privacy_policies array in manifest | N/A (remote server) | Only for local connectors |
| HTTPS URL to privacy policy | MISSING | Need Snowflake legal to provide |

**Action:** Add privacy policy (data collection: account URL, session tokens for auth; no conversation data stored; no third-party sharing).

### 5. Documentation — Clear setup and usage instructions

| Requirement | Status | Notes |
|---|---|---|
| Public documentation URL | PARTIAL | TESTING.md exists but is internal-focused |
| Usage instructions | PASS | README.md covers tools and usage |

---

## Tool Design (Review Criteria)

### Separate read and write tools

| Requirement | Status | Notes |
|---|---|---|
| No catch-all tool with method param | PASS | Each tool has a specific purpose |
| Read vs write separation | PASS | output/status/list are read-only; spawn/send_input/close are write |

### Tool names under 64 chars

| Requirement | Status |
|---|---|
| All names < 64 chars | PASS (longest: `cloud_agent_send_input` = 22 chars) |

### Narrow, accurate descriptions

| Requirement | Status | Notes |
|---|---|---|
| Descriptions match behavior | PASS | Each tool's description is accurate |
| No prompt-injection patterns | PASS | Descriptions only state what the tool does |

---

## Portal Submission Steps vs Our Readiness

| Step | Ready? | Gap |
|---|---|---|
| 1. Introduction | YES | — |
| 2. Connection | NO | Need remote HTTPS endpoint (not stdio) |
| 3. Tools | PARTIAL | Missing annotations (title, hints) |
| 4. Listing | PARTIAL | Need tagline, icon, categories, slug |
| 5. Use cases | YES | Can describe |
| 6. Company | YES | Snowflake |
| 7. Authentication | NO | Need OAuth 2.0 implementation |
| 8. Data handling | YES | First-party API, no health data |
| 9. Test & launch | NO | Need test account for reviewers |
| 10. Compliance | PARTIAL | Need legal review |
| 11. Review | — | After all above |

---

## Critical Gaps (Blocking)

1. **Transport:** Currently stdio. Directory requires remote HTTPS or MCPB.
2. **OAuth 2.0:** No OAuth flow. Need Snowflake OAuth app + token exchange.
3. **Tool annotations:** Missing `title` and hints on all 8 tools.
4. **Privacy policy:** Need legal-approved policy + HTTPS URL.

## Non-Blocking Gaps

- Icon / branding assets
- Tagline (55 char max)
- Categories
- Test account for Anthropic reviewers
- Public documentation URL

---

## Recommendation

**Short-term (feature branch):** Fix tool annotations — easy, no architecture change.

**Medium-term (requires product decision):**
- Remote HTTPS deployment (SPCS? Lambda? Cloud Run?) vs MCPB desktop extension
- OAuth 2.0 implementation (depends on Snowflake OAuth app availability)
- Privacy policy (legal team)

**Long-term (GA dependency):**
- Cloud Agents API on customer accounts (not just Snowhouse)
- OAuth consent flow for customer accounts
