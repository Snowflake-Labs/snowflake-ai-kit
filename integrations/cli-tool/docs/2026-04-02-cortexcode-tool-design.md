# Cortexcode Tool Design Specification (Multi-IDE)

**Date:** April 2, 2026  
**Status:** Approved  
**Version:** 1.2

> **UPDATE (April 7, 2026):** Cursor now uses the Claude Code skill (`~/.claude/skills/cortex-code/`) instead of the standalone CLI tool for better integration with Claude Code sessions. This design doc describes the original architecture. VSCode and Windsurf continue to use the standalone CLI tool as designed.

## Overview

### Goal
Build a standalone CLI tool (`cortexcode-tool`) that brings cortex-code skill's Snowflake expertise to multiple IDEs (Cursor, VSCode, Windsurf), reusing all v2.0.0 security components while remaining independent from Claude Code installation.

### Key Requirements
- Standalone Python CLI tool installable system-wide
- Reuse all security components from cortex-code skill (copy/adapt, not import)
- Match cortex-code functionality: routing, security, discovery, approval modes
- **Multi-IDE integration via adapter pattern**: Cursor, VSCode, Windsurf (VSCode fork)
- Work without MCP server (quick start approach)
- Interactive terminal-based approval prompts (not IDE UI)
- Dynamic discovery of Cortex capabilities (not hardcoded)
- Production-ready with comprehensive error handling
- Generate IDE-specific integration files based on configuration

### Supported IDEs
- **Cursor**: `.cursor/rules/*.mdc` files (AI-driven suggestion)
- **VSCode**: `.vscode/tasks.json` + code snippets (task runner + snippets)
- **Windsurf**: VSCode-compatible integration (VSCode fork)

### Non-Goals
- Coupling to Claude Code or cortex-code skill installation
- Sharing configuration files with Claude Code
- IDE UI integration for approval prompts (terminal only)
- Real-time capability updates during operation
- Full VSCode/Cursor extension development (future enhancement)

---

## Architecture

### High-Level Flow (Multi-IDE)

```
User asks Snowflake question in IDE (Cursor/VSCode/Windsurf)
         ↓
IDE reads integration config:
  - Cursor: .cursor/rules/*.mdc → AI suggests cortexcode-tool
  - VSCode/Windsurf: User runs task or types snippet
         ↓
User executes: cortexcode-tool "question"
         ↓
Tool routes: Snowflake? → Yes
         ↓
Security wrapper checks approval mode
         ↓
[If prompt mode] Show approval prompt in terminal
         ↓
User approves → Execute Cortex Code CLI
         ↓
Stream results back to terminal
         ↓
User views results in IDE terminal
```

### Key Design Decisions

1. **Multi-IDE Adapter Pattern**
   - Core CLI is IDE-agnostic (works from any terminal)
   - IDE-specific adapters generate integration files
   - **Cursor adapter**: Generates `.cursor/rules/cortexcode-tool.mdc` with AI suggestions
   - **VSCode adapter**: Generates `.vscode/tasks.json` + code snippets for manual invocation
   - **Windsurf support**: Uses VSCode adapter (Windsurf is VSCode fork)
   - Configuration controls which IDEs to support: `ide.targets: ["cursor", "vscode"]`
   - Users can support multiple IDEs simultaneously

2. **Two Approval Points (Cursor Only)**
   - **Point 1:** Cursor suggests the tool (routing decision, AI-driven)
   - **Point 2:** Tool shows approval prompt in terminal (authorization)
   - Both serve distinct purposes: routing vs authorization
   - Default: `approval_mode: "prompt"` for security
   - Configurable: Users can set `approval_mode: "auto"` for speed
   - Note: VSCode/Windsurf users invoke tool manually (only one approval point)

3. **Independent Installation**
   - Development: `/Users/<username>/Documents/Code/CortexCode/cortexcode-tool/`
   - Installed: `~/.local/bin/cortexcode-tool` (preferred, no sudo required) or `/usr/local/bin/cortexcode-tool`
   - Configuration: `~/.config/cortexcode-tool/config.yaml`
   - Audit logs: `~/.config/cortexcode-tool/audit.log`
   - Cache: `~/.cache/cortexcode-tool/cortex-capabilities.json`
   - Cursor rules: `.cursor/rules/cortexcode-tool.mdc` (per-project)
   - VSCode config: `.vscode/tasks.json` + `.vscode/cortexcode.code-snippets` (per-project)

4. **IDE Integration Systems**
   
   **Cursor:**
   - Supports two rule formats:
     - **`.cursorrules`**: Single file in project root (simple markdown)
     - **`.cursor/rules/*.mdc`**: Multiple files with frontmatter (structured, preferred)
   - This tool uses `.cursor/rules/cortexcode-tool.mdc` format
   - Frontmatter required: `alwaysApply: true`
   - AI reads rules and suggests tool automatically
   - Based on analysis of existing Cursor installations
   
   **VSCode/Windsurf:**
   - Task Runner: `.vscode/tasks.json` for CLI invocation
   - Code Snippets: `.vscode/cortexcode.code-snippets` for quick access
   - User invokes manually (no AI suggestion system)
   - Windsurf is VSCode fork → uses same integration method
   - Optional: Settings recommendations in `.vscode/settings.json`

5. **Code Reuse Strategy**
   - Copy all Python code from `~/.claude/skills/cortex-code/`
   - Adapt imports and paths for standalone use
   - Maintain compatibility with cortex-code v2.0.0 security model
   - No dependencies on Claude Code installation

5. **Dynamic Capability Discovery**
   - Run `cortex skill list` at startup
   - Parse SKILL.md files from `~/.local/share/cortex/{version}/bundled_skills/`
   - Cache discovered capabilities with SHA256 validation
   - Generate .cursor/rules dynamically based on discovered triggers
   - Support 35+ bundled Cortex skills automatically

---

## Component Structure

### Project Layout

```
/Users/<username>/Documents/Code/CortexCode/cortexcode-tool/
├── cortexcode_tool/
│   ├── __init__.py
│   ├── main.py                        # CLI entry point
│   │
│   ├── security/                      # Copied from cortex-code
│   │   ├── __init__.py
│   │   ├── approval_handler.py        # Interactive approval prompts
│   │   ├── audit_logger.py            # JSONL audit logging
│   │   ├── cache_manager.py           # SHA256-validated caching
│   │   ├── config_manager.py          # Three-layer config
│   │   └── prompt_sanitizer.py        # PII removal, injection detection
│   │
│   ├── core/                          # Copied from cortex-code/scripts
│   │   ├── __init__.py
│   │   ├── route_request.py           # LLM-based routing
│   │   ├── execute_cortex.py          # Cortex CLI wrapper
│   │   ├── discover_cortex.py         # Capability discovery
│   │   └── read_cortex_sessions.py    # Session history enrichment
│   │
│   └── ide_adapters/                  # IDE-specific integrations
│       ├── __init__.py
│       ├── base_adapter.py            # Base adapter interface
│       ├── cursor_adapter.py          # Cursor .mdc generator
│       └── vscode_adapter.py          # VSCode tasks + snippets generator
│
├── .cursor/
│   └── rules/
│       └── cortexcode-tool.mdc        # Auto-generated for Cursor projects
│
├── .vscode/
│   ├── tasks.json                     # Auto-generated for VSCode projects
│   └── cortexcode.code-snippets       # Auto-generated for VSCode projects
│
├── config.yaml.example                # Template configuration
├── setup.sh                           # Installation script
├── uninstall.sh                       # Cleanup script
├── README.md                          # User documentation
├── CHANGELOG.md                       # Version history
├── LICENSE                            # Apache 2.0
│
└── tests/
    ├── test_routing.py
    ├── test_security.py
    ├── test_discovery.py
    └── test_integration.py
```

### Component Responsibilities

#### `main.py` - CLI Entry Point
- Parse command-line arguments
- Load configuration from `~/.config/cortexcode-tool/config.yaml`
- Initialize security components (ConfigManager, AuditLogger, CacheManager)
- Orchestrate routing → approval → execution flow
- Handle errors and user interrupts (Ctrl+C)
- Format output for terminal display

**Interface:**
```bash
# Query execution
cortexcode-tool "Show me top 10 customers by revenue"
cortexcode-tool --envelope RO "List databases"
cortexcode-tool --config /path/to/config.yaml "query"

# Capability and IDE config management
cortexcode-tool --discover-capabilities        # Force rediscovery
cortexcode-tool --generate-ide-config          # Generate for all configured IDEs
cortexcode-tool --generate-ide-config cursor   # Generate Cursor config only
cortexcode-tool --generate-ide-config vscode   # Generate VSCode config only
cortexcode-tool --generate-ide-config all      # Generate all IDE configs
cortexcode-tool --validate-config              # Validate configuration

# Info
cortexcode-tool --version
cortexcode-tool --help
```

#### `security/` - Security Components
Copied directly from cortex-code v2.0.0 with path adaptations:

- **approval_handler.py**: Interactive terminal approval prompts
  - Tool prediction with confidence scoring
  - Display approval prompt with tool list, envelope, confidence
  - Parse user response (yes/no/yes to all)
  - Return ApprovalResult dataclass

- **audit_logger.py**: JSONL structured logging
  - Mandatory for auto/envelope_only modes
  - Log: routing decisions, tool predictions, approvals, executions, errors
  - Size-based rotation with SHA256 hashing
  - Configurable retention period (default 30 days)
  - Secure permissions (0600)

- **cache_manager.py**: Secure caching with integrity validation
  - SHA256 fingerprint validation on every read
  - TTL expiration with auto-cleanup
  - Path traversal prevention
  - Secure permissions (0600 files, 0700 directories)
  - Cache location: `~/.cache/cortexcode-tool/`

- **config_manager.py**: Three-layer configuration
  - Precedence: org policy > user config > defaults
  - Org policy: `~/.snowflake/cortex/cortexcode-tool-policy.yaml`
  - User config: `~/.config/cortexcode-tool/config.yaml`
  - Deep merge with validation
  - Path expansion for `~/` and environment variables

- **prompt_sanitizer.py**: PII removal and injection detection
  - Remove: credit cards, SSN, emails, phone numbers
  - Detect injection attempts: complete content removal (not masking)
  - Structure-preserving processing
  - Configurable via `sanitize_conversation_history` setting

#### `core/` - Core Functionality
Copied from cortex-code/scripts with adaptations:

- **route_request.py**: LLM-based semantic routing
  - Load cached Cortex capabilities
  - Use LLM reasoning (not keyword matching)
  - Return: `{"route": "cortex"|"general", "confidence": 0.95, "reason": "..."}`
  - Route to cortex: Snowflake operations, Cortex features, data quality
  - Route to general: Local files, non-Snowflake databases, git operations

- **execute_cortex.py**: Cortex CLI execution wrapper
  - Build enriched prompt with context
  - Apply security envelope (RO/RW/RESEARCH/DEPLOY/NONE)
  - Execute: `cortex -p "..." --output-format stream-json --input-format stream-json`
  - Parse NDJSON event stream in real-time
  - Handle tool_use events and results
  - Stream output to terminal

- **discover_cortex.py**: Dynamic capability discovery
  - Run `cortex skill list` to enumerate skills
  - Read SKILL.md from `~/.local/share/cortex/{version}/bundled_skills/`
  - Parse frontmatter: name, description, triggers
  - Extract "Use when" patterns
  - Cache with CacheManager (SHA256 validation)
  - Return structured capabilities JSON

- **read_cortex_sessions.py**: Session history enrichment
  - Read recent Cortex sessions from `~/.local/share/cortex/sessions/`
  - Parse session files (JSONL format)
  - Sanitize with PromptSanitizer (PII removal)
  - Return formatted context for prompt enrichment

#### `ide_adapters/` - Multi-IDE Integration

**base_adapter.py** - Base adapter interface:
- Abstract base class defining adapter contract
- Methods: `generate_config()`, `get_output_path()`, `validate_capabilities()`
- All IDE adapters inherit from this base
- Ensures consistent behavior across IDEs

**cursor_adapter.py** - Cursor integration:
- Read cached capabilities from discover_cortex
- Generate `.cursor/rules/cortexcode-tool.mdc` markdown file dynamically
- Include frontmatter: `alwaysApply: true`
- Include all discovered skill triggers and patterns
- Format for Cursor's rule interpretation (MDC format)
- Strengthen Snowflake detection keywords

**vscode_adapter.py** - VSCode/Windsurf integration:
- Read cached capabilities from discover_cortex
- Generate `.vscode/tasks.json` for task runner
- Generate `.vscode/cortexcode.code-snippets` for code snippets
- Optionally generate `.vscode/settings.json` recommendations
- Works for both VSCode and Windsurf (VSCode fork)

**Generated .cursor/rules/cortexcode-tool.mdc format:**
```markdown
---
alwaysApply: true
---

# Cortexcode Tool Integration

This project has access to cortexcode-tool, a CLI that provides Snowflake expertise via Cortex Code.

## When to suggest cortexcode-tool

### ALWAYS suggest for questions about:
- Snowflake databases, warehouses, schemas, tables, views
- SQL queries for Snowflake data
- Data quality checks, validation, profiling
- Cortex AI features: Cortex Search, Cortex Analyst, ML functions
- Semantic views, data modeling
- Snowpark (Python/Scala), dynamic tables, streams, tasks
- Snowflake security, roles, policies, governance
- [Additional triggers from discovered capabilities]

### Keywords that trigger tool suggestion:
snowflake, warehouse, cortex, semantic view, data quality, snowpark, 
dynamic table, stream, task, stage, pipe, [discovered keywords]

### How to suggest:
When you detect a Snowflake-related question, respond:
"I can help with that using cortexcode-tool. Run:
\`\`\`bash
cortexcode-tool "your question here"
\`\`\`"

## Tool usage examples

1. Query Snowflake data:
   \`cortexcode-tool "Show me top 10 customers by revenue"\`

2. Data quality check:
   \`cortexcode-tool "Check data quality for SALES_DATA table"\`

3. Create semantic view:
   \`cortexcode-tool "Create semantic view for customer analytics"\`

4. Analyze schema:
   \`cortexcode-tool "What tables are in the ANALYTICS schema?"\`

## Security
- Tool will show approval prompt before executing (default)
- Configure ~/.config/cortexcode-tool/config.yaml to change approval mode
- All operations logged to ~/.config/cortexcode-tool/audit.log
```

**Generated .vscode/tasks.json format:**
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Cortex: Query Snowflake",
      "type": "shell",
      "command": "cortexcode-tool",
      "args": ["${input:userQuery}"],
      "presentation": {
        "echo": true,
        "reveal": "always",
        "panel": "new"
      },
      "problemMatcher": []
    },
    {
      "label": "Cortex: Data Quality Check",
      "type": "shell",
      "command": "cortexcode-tool",
      "args": ["Check data quality for ${input:tableName}"],
      "presentation": {
        "echo": true,
        "reveal": "always",
        "panel": "new"
      },
      "problemMatcher": []
    }
  ],
  "inputs": [
    {
      "id": "userQuery",
      "type": "promptString",
      "description": "Enter your Snowflake question"
    },
    {
      "id": "tableName",
      "type": "promptString",
      "description": "Enter table name (e.g., SALES_DATA)"
    }
  ]
}
```

**Generated .vscode/cortexcode.code-snippets format:**
```json
{
  "Cortex Query": {
    "prefix": "cortex",
    "body": [
      "cortexcode-tool \"$1\""
    ],
    "description": "Run Cortex Code query for Snowflake"
  },
  "Cortex Data Quality": {
    "prefix": "cortex-dq",
    "body": [
      "cortexcode-tool \"Check data quality for ${1:TABLE_NAME}\""
    ],
    "description": "Run data quality check"
  },
  "Cortex Semantic View": {
    "prefix": "cortex-sv",
    "body": [
      "cortexcode-tool \"Create semantic view for ${1:dataset}\""
    ],
    "description": "Create semantic view"
  }
}
```

**VSCode/Windsurf Usage:**
- Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
- Type "Tasks: Run Task"
- Select "Cortex: Query Snowflake" or other task
- Or: Type `cortex<Tab>` in terminal to expand snippet

---

## Security Architecture

### Approval Modes

Three modes matching cortex-code v2.0.0:

1. **prompt** (default, high security)
   - User shown terminal approval prompt before execution
   - Display: predicted tools, envelope, confidence score
   - User input: yes/no/yes to all
   - No audit logging required (interactive approval is the audit)
   - Best for: Interactive use, untrusted prompts, production

2. **auto** (medium security, v1.x compatibility)
   - All operations auto-approved
   - Mandatory audit logging
   - Envelopes still enforced
   - Best for: Automated workflows, trusted environments

3. **envelope_only** (medium security, faster)
   - No tool prediction (skips LLM call)
   - Auto-approved with audit logging
   - Relies on envelope blocklist only
   - Best for: Trusted environments, low latency needs

### Security Envelopes

Define which tools are blocked during Cortex execution:

- **RO** (Read-Only): Blocks Edit, Write, destructive Bash commands
- **RW** (Read-Write): Blocks destructive operations (rm -rf, sudo)
- **RESEARCH**: Read access plus web tools, blocks write operations
- **DEPLOY**: Full access with no blocklist (use cautiously)
- **NONE**: Custom blocklist via --disallowed-tools parameter

Envelopes enforced via `--disallowed-tools` flag to Cortex CLI.

### Built-in Protections

1. **Prompt Sanitization**: Automatic PII removal (credit cards, SSN, emails, phone numbers)
2. **Injection Detection**: Complete content removal when injection attempts detected
3. **Credential Blocking**: Prevents routing when paths like `~/.ssh/`, `.env`, `credentials.json` detected
4. **Secure Caching**: SHA256 fingerprint validation, TTL expiration, secure permissions (0600)
5. **Audit Logging**: Structured JSONL logs (mandatory for auto/envelope_only modes)
6. **Organization Policy**: Enterprise override via `~/.snowflake/cortex/cortexcode-tool-policy.yaml`

### Two Approval Points Design

**Point 1: Cursor Suggestion (Routing)**
- Cursor reads .cursor/rules
- Detects Snowflake keywords/patterns
- Suggests: "Use cortexcode-tool for this?"
- User decides whether to invoke tool

**Point 2: Tool Approval Prompt (Authorization)**
- Tool shows terminal prompt with:
  - Predicted tools (e.g., snowflake_sql_execute, Write)
  - Security envelope (RO/RW/RESEARCH/DEPLOY)
  - Confidence score (e.g., 85%)
- User approves specific operations
- Can be disabled via `approval_mode: "auto"`

**Why both are needed:**
- Point 1 = "Should we use Snowflake specialist?" (routing)
- Point 2 = "Are these specific operations safe?" (authorization)
- Distinct purposes, not redundant

**Strengthened .cursor/rules:**
- Include all discovered skill triggers dynamically
- Explicit keywords from Cortex capabilities
- Clear suggestion format for Cursor to parse
- Examples for each common use case

### Configuration Precedence

Three-layer configuration system:

1. **Organization Policy** (highest priority)
   - Location: `~/.snowflake/cortex/cortexcode-tool-policy.yaml`
   - Enforced by enterprise admins
   - Overrides user configuration
   - Example: Force prompt mode for all users

2. **User Configuration**
   - Location: `~/.config/cortexcode-tool/config.yaml`
   - User-specific settings
   - Overrides defaults
   - Example: Set auto mode for personal use

3. **Defaults** (lowest priority)
   - Hardcoded in ConfigManager
   - Used when no config file exists
   - Secure defaults: prompt mode, sanitization enabled

**Example config.yaml:**
```yaml
security:
  # Approval mode: prompt (default), auto (v1.x compat), envelope_only (faster)
  approval_mode: "prompt"
  
  # Tool prediction confidence threshold (0.0-1.0)
  tool_prediction_confidence_threshold: 0.7
  
  # Audit logging (mandatory for auto/envelope_only)
  audit_log_path: "~/.config/cortexcode-tool/audit.log"
  audit_log_rotation: "10MB"
  audit_log_retention: 30  # days
  
  # Prompt sanitization
  sanitize_conversation_history: true
  
  # Secure caching
  cache_dir: "~/.cache/cortexcode-tool"
  cache_ttl: 86400  # 24 hours
  
  # Credential file blocking patterns
  credential_file_allowlist:
    - "~/.ssh/**"
    - "~/.aws/credentials"
    - "~/.snowflake/**"
    - "**/.env"
    - "**/credentials.json"
  
  # Allowed security envelopes
  allowed_envelopes:
    - "RO"
    - "RW"
    - "RESEARCH"
    - "DEPLOY"

cortex:
  # Default Snowflake connection
  connection_name: "default"
  
  # Default security envelope if not specified
  default_envelope: "RW"
  
  # Cortex CLI path (auto-detected if not specified)
  cli_path: "cortex"
```

---

## Dynamic Discovery System

### Discovery Process

1. **Trigger Discovery**
   - Run on: first tool invocation, explicit `--discover-capabilities` flag
   - Execute: `cortex skill list` to enumerate available skills
   - Parse output: skill names and status

2. **Metadata Extraction**
   - Locate: `~/.local/share/cortex/{version}/bundled_skills/`
   - For each discovered skill:
     - Read SKILL.md file
     - Parse frontmatter: name, description
     - Extract "Use when" section (trigger patterns)
     - Extract example keywords

3. **Capability Caching**
   - Structure discovered data as JSON:
     ```json
     {
       "version": "1.0.48",
       "discovered_at": "2026-04-02T10:30:00Z",
       "skills": [
         {
           "name": "data-quality",
           "description": "Data quality monitoring and validation",
           "triggers": [
             "data quality",
             "data validation",
             "DMF",
             "table comparison"
           ],
           "examples": ["Check data quality for...", "Validate schema..."]
         },
         {
           "name": "semantic-view",
           "description": "Cortex Analyst semantic views",
           "triggers": [
             "semantic view",
             "data model",
             "cortex analyst"
           ],
           "examples": ["Create semantic view...", "Build data model..."]
         }
       ]
     }
     ```
   - Cache location: `~/.cache/cortexcode-tool/cortex-capabilities.json`
   - SHA256 fingerprint validation on every read
   - TTL: 24 hours (configurable)

4. **.cursor/rules Generation**
   - Read cached capabilities
   - Extract all triggers and keywords
   - Generate markdown with:
     - Comprehensive trigger patterns
     - Keyword list for detection
     - Usage examples per skill category
   - Write to: `.cursor/rules`
   - Auto-regenerate when capabilities change

### Supported Cortex Skills (Auto-Discovered)

Tool discovers all bundled skills automatically. As of Cortex v1.0.48, includes:

- **Data Management**: data-quality, dynamic-tables, iceberg, lineage, integrations
- **AI/ML**: cortex-ai-functions, cortex-agent, machine-learning, semantic-view
- **Development**: snowpark-python, snowpark-scala, streamlit
- **Analytics**: dashboard, query-optimization
- **Governance**: security-policies, data-governance
- ...and 20+ more

New skills in future Cortex releases are discovered automatically without code changes.

### Discovery Cache Invalidation

Cache invalidated when:
- TTL expires (24 hours default)
- SHA256 fingerprint mismatch detected
- Cortex version changes
- User runs `--discover-capabilities` flag
- Cache file missing or corrupted

After invalidation, fresh discovery triggered automatically.

---

## Error Handling

### Error Categories and Handling

#### 1. Missing Dependencies
- **Error**: Cortex CLI not found
- **Detection**: `which cortex` returns empty
- **Handling**:
  ```
  ERROR: Cortex Code CLI not found
  
  Please install Cortex Code CLI:
  curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | sh
  
  Documentation: https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli
  ```
- **Exit code**: 2

#### 2. Configuration Errors
- **Error**: Invalid config.yaml syntax
- **Detection**: YAML parse exception
- **Handling**:
  ```
  ERROR: Invalid configuration file: ~/.config/cortexcode-tool/config.yaml
  
  YAML parse error at line 15: unexpected character
  
  Check syntax at: https://yaml.org/
  Or restore from: cp config.yaml.example config.yaml
  ```
- **Exit code**: 3

- **Error**: Invalid approval_mode value
- **Detection**: ConfigManager validation
- **Handling**:
  ```
  ERROR: Invalid approval_mode: "invalid_mode"
  
  Valid options: prompt, auto, envelope_only
  
  Fix in: ~/.config/cortexcode-tool/config.yaml
  ```
- **Exit code**: 3

#### 3. Discovery Errors
- **Error**: Cannot discover Cortex capabilities
- **Detection**: `cortex skill list` fails
- **Handling**:
  ```
  ERROR: Failed to discover Cortex capabilities
  
  Cortex CLI error: connection timeout
  
  Troubleshooting:
  1. Check Cortex CLI: cortex --version
  2. Check Snowflake connection: cortex connections list
  3. Check network connectivity
  
  To skip discovery and use defaults: cortexcode-tool --no-discover "query"
  ```
- **Exit code**: 4

#### 4. Routing Errors
- **Error**: Cannot determine routing
- **Detection**: route_request.py returns error
- **Handling**:
  ```
  ERROR: Cannot determine routing for query
  
  LLM routing failed: API timeout
  
  Fallback: Treat as general query (no Cortex routing)
  
  To force Cortex routing: cortexcode-tool --force-cortex "query"
  ```
- **Exit code**: 0 (graceful degradation)

#### 5. Security Errors
- **Error**: Prompt contains credential file path
- **Detection**: PromptSanitizer credential blocking
- **Handling**:
  ```
  ERROR: Prompt contains credential file path
  
  Detected patterns: ~/.ssh/id_rsa
  
  Security policy blocks routing queries with credential paths.
  
  Remove credential references from query or adjust allowlist in:
  ~/.config/cortexcode-tool/config.yaml
  ```
- **Exit code**: 5

- **Error**: Cache integrity validation failed
- **Detection**: CacheManager SHA256 mismatch
- **Handling**:
  ```
  WARNING: Cache integrity validation failed
  
  Cache file may have been tampered with. Invalidating and rediscovering...
  
  [Automatic rediscovery proceeds]
  ```
- **Exit code**: 0 (auto-recovery)

#### 6. Approval Errors
- **Error**: User denies approval
- **Detection**: ApprovalHandler returns deny
- **Handling**:
  ```
  INFO: User denied execution
  
  No operations performed. Query cancelled.
  ```
- **Exit code**: 0 (user choice, not error)

- **Error**: Approval prompt timeout
- **Detection**: No input for 60 seconds
- **Handling**:
  ```
  ERROR: Approval prompt timed out
  
  No response received within 60 seconds. Query cancelled.
  
  To auto-approve, set approval_mode: "auto" in config.
  ```
- **Exit code**: 6

#### 7. Execution Errors
- **Error**: Cortex execution failed
- **Detection**: Non-zero exit code from cortex CLI
- **Handling**:
  ```
  ERROR: Cortex execution failed
  
  Exit code: 1
  Error output:
  [stderr from cortex]
  
  Troubleshooting:
  1. Check Snowflake connection: cortex connections list
  2. Verify query syntax
  3. Check permissions for requested operations
  
  Audit log: ~/.config/cortexcode-tool/audit.log
  ```
- **Exit code**: 7

- **Error**: Connection refused
- **Detection**: Cortex CLI connection error
- **Handling**:
  ```
  ERROR: Cannot connect to Snowflake
  
  Cortex reported: connection refused
  
  Troubleshooting:
  1. Check connection config: cortex connections list
  2. Verify Snowflake credentials
  3. Check network connectivity
  4. Verify warehouse is running
  
  Documentation: https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli
  ```
- **Exit code**: 8

#### 8. User Interrupts
- **Error**: User presses Ctrl+C
- **Detection**: KeyboardInterrupt exception
- **Handling**:
  ```
  
  ^C
  INFO: User interrupted execution
  
  Cancelling Cortex operation...
  Done. No changes committed.
  ```
- **Exit code**: 130 (standard for SIGINT)

### Error Recovery Strategy

**Graceful Degradation:**
- Routing failures → treat as general query (no Cortex)
- Cache corruption → auto-invalidate and rediscover
- Discovery failures → use cached data if available, else inform user

**Auto-Recovery:**
- Cache integrity failures → fresh discovery
- Connection timeouts → retry with exponential backoff (3 attempts)
- Permission errors → suggest envelope adjustment

**User Guidance:**
- Every error includes troubleshooting steps
- Link to relevant documentation
- Suggest configuration fixes where applicable
- Show audit log location for debugging

**Audit Trail:**
- All errors logged to audit.log (if audit enabled)
- Include: timestamp, error type, user query, resolution action
- Helps with post-mortem analysis

---

## Installation and Setup

### Installation Flow

1. **Prerequisites Check**
   - Verify Python 3.8+ installed: `python3 --version`
   - Verify Cortex CLI installed: `which cortex`
   - If missing, show installation instructions

2. **Development Setup** (optional, for contributors)
   ```bash
   git clone <repo-url> /Users/<username>/Documents/Code/CortexCode/cortexcode-tool
   cd cortexcode-tool
   ```

3. **System Installation**
   ```bash
   ./setup.sh
   ```
   
   **setup.sh actions:**
   - Copy `cortexcode_tool/` to `~/.local/lib/cortexcode-tool/` (preferred, user-local) or `/usr/local/lib/cortexcode-tool/` (system-wide, requires sudo)
   - Create symlink: `~/.local/bin/cortexcode-tool` → `~/.local/lib/cortexcode-tool/main.py`
   - Ensure `~/.local/bin` is in PATH (add to ~/.zshrc or ~/.bashrc if needed)
   - Make main.py executable: `chmod +x`
   - Add shebang: `#!/usr/bin/env python3`
   - Create config directory: `~/.config/cortexcode-tool/`
   - Copy `config.yaml.example` → `~/.config/cortexcode-tool/config.yaml`
   - Create cache directory: `~/.cache/cortexcode-tool/`
   - Set permissions: 0700 for directories, 0600 for config files
   - Run initial discovery: `cortexcode-tool --discover-capabilities`
   - Generate IDE configs: `cortexcode-tool --generate-ide-config` (reads `ide.targets` from config.yaml)
   - Creates IDE-specific files based on configuration:
     - Cursor: `.cursor/rules/cortexcode-tool.mdc`
     - VSCode: `.vscode/tasks.json` + `.vscode/cortexcode.code-snippets`
   - Show success message with next steps

4. **Verification**
   ```bash
   cortexcode-tool --version
   cortexcode-tool --help
   cortexcode-tool "Show databases"  # Interactive test
   ```

5. **IDE Integration Verification**
   
   **Cursor:**
   - `.cursor/rules/cortexcode-tool.mdc` already generated by setup.sh
   - Open project in Cursor
   - Cursor automatically loads rules from `.cursor/rules/*.mdc`
   - Test: Ask Cursor a Snowflake question
   - Expected: Cursor suggests cortexcode-tool
   
   **VSCode/Windsurf:**
   - `.vscode/tasks.json` and `.vscode/cortexcode.code-snippets` already generated
   - Open project in VSCode or Windsurf
   - Press `Cmd+Shift+P` → "Tasks: Run Task" → "Cortex: Query Snowflake"
   - Or type `cortex<Tab>` in terminal to expand snippet
   - Expected: Tool executes from terminal

### Uninstallation

```bash
./uninstall.sh
```

**uninstall.sh actions:**
- Remove: `~/.local/bin/cortexcode-tool` (or `/usr/local/bin/cortexcode-tool`)
- Remove: `~/.local/lib/cortexcode-tool/` (or `/usr/local/lib/cortexcode-tool/`)
- Ask user: "Remove configuration? (~/.config/cortexcode-tool/)" [y/N]
- Ask user: "Remove cache? (~/.cache/cortexcode-tool/)" [y/N]
- Ask user: "Remove audit logs?" [y/N]
- Show summary of removed items

### Configuration Management

**Initial Configuration:**
```bash
cp config.yaml.example ~/.config/cortexcode-tool/config.yaml
$EDITOR ~/.config/cortexcode-tool/config.yaml
```

**Configuration Validation:**
```bash
cortexcode-tool --validate-config
```

Output:
```
Configuration valid: ~/.config/cortexcode-tool/config.yaml

Loaded settings:
  approval_mode: prompt
  audit_log_path: ~/.config/cortexcode-tool/audit.log
  sanitize_conversation_history: true
  cache_ttl: 86400 seconds (24 hours)

Organization policy: Not found (using user config)
```

**Update Configuration:**
- Edit: `~/.config/cortexcode-tool/config.yaml`
- No restart required (loaded per invocation)
- Validate: `cortexcode-tool --validate-config`

### IDE Integration Setup

**Automatic (via setup.sh):**
- IDE config files generated automatically based on `ide.targets` in config.yaml
- Placed in current directory (`.cursor/rules/` or `.vscode/`)
- User commits to version control

**Manual Regeneration:**
```bash
cortexcode-tool --generate-ide-config          # All configured IDEs
cortexcode-tool --generate-ide-config cursor   # Cursor only
cortexcode-tool --generate-ide-config vscode   # VSCode only
cortexcode-tool --generate-ide-config all      # All supported IDEs
```

**Cursor Example Output:**
```
Discovering Cortex capabilities...
Discovered 35 skills

Generating .cursor/rules/cortexcode-tool.mdc...
Written to: ./.cursor/rules/cortexcode-tool.mdc

Next steps:
1. Review: cat .cursor/rules/cortexcode-tool.mdc
2. Commit: git add .cursor/rules && git commit -m "Add cortexcode-tool integration"
3. Test in Cursor: Ask a Snowflake question
```

**VSCode Example Output:**
```
Discovering Cortex capabilities...
Discovered 35 skills

Generating .vscode/tasks.json...
Written to: ./.vscode/tasks.json

Generating .vscode/cortexcode.code-snippets...
Written to: ./.vscode/cortexcode.code-snippets

Next steps:
1. Review: cat .vscode/tasks.json
2. Commit: git add .vscode && git commit -m "Add cortexcode-tool integration"
3. Test in VSCode: Cmd+Shift+P → Tasks: Run Task → Cortex: Query Snowflake
```

**Custom Location:**
```bash
cortexcode-tool --generate-ide-config cursor --output /path/to/.cursor/rules/cortexcode-tool.mdc
cortexcode-tool --generate-ide-config vscode --output /path/to/.vscode/
```

---

## Testing Strategy

### Test Coverage

1. **Unit Tests** (`tests/test_*.py`)
   - ConfigManager: configuration loading, precedence, validation
   - CacheManager: caching, SHA256 validation, TTL expiration
   - PromptSanitizer: PII removal, injection detection
   - ApprovalHandler: approval prompt parsing, result handling
   - AuditLogger: JSONL formatting, rotation, retention

2. **Integration Tests** (`tests/test_integration.py`)
   - End-to-end: CLI invocation → routing → approval → execution
   - Discovery: `cortex skill list` → cache → .cursor/rules generation
   - Security: approval modes, envelope enforcement, credential blocking
   - Error handling: missing dependencies, invalid config, execution failures

3. **Routing Tests** (`tests/test_routing.py`)
   - Snowflake queries → route to cortex
   - Local file operations → route to general
   - Ambiguous queries → confidence scores
   - Edge cases: typos, mixed queries

4. **Security Tests** (`tests/test_security.py`)
   - Prompt sanitization: PII removal effectiveness
   - Injection detection: various attack patterns
   - Credential blocking: path pattern matching
   - Cache tampering: SHA256 validation
   - Approval bypass attempts
   - Organization policy enforcement

5. **Discovery Tests** (`tests/test_discovery.py`)
   - Capability discovery: parsing SKILL.md files
   - Cache invalidation: TTL, version changes, corruption
   - .cursor/rules generation: format, completeness
   - Error recovery: missing skills, parse failures

### Testing Tools

- **pytest**: Test runner
- **pytest-mock**: Mocking Cortex CLI calls
- **pytest-cov**: Coverage reporting
- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Type checking

### Test Execution

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=cortexcode_tool --cov-report=html tests/

# Run specific test file
pytest tests/test_routing.py

# Run specific test
pytest tests/test_routing.py::test_snowflake_routing
```

---

## Documentation

### User Documentation

1. **README.md**
   - Overview and key features
   - Quick start guide
   - Installation instructions
   - Basic usage examples
   - Troubleshooting common issues
   - Link to full documentation

2. **docs/USER_GUIDE.md**
   - Detailed usage instructions
   - All CLI flags and options
   - Configuration reference
   - Security architecture explanation
   - Approval modes comparison
   - Envelope reference
   - Advanced use cases

3. **docs/IDE_INTEGRATION.md**
   - Multi-IDE integration overview
   - Cursor: Setting up .cursor/rules, customizing detection
   - VSCode/Windsurf: Task runner setup, snippets usage
   - Best practices per IDE

4. **docs/SECURITY.md**
   - Security features overview
   - Threat model
   - Approval modes detailed
   - Organization policy setup
   - Audit logging format
   - Compliance considerations

5. **docs/TROUBLESHOOTING.md**
   - Common error messages and fixes
   - Connection issues
   - Configuration problems
   - Discovery failures
   - Performance optimization

### Developer Documentation

1. **docs/CONTRIBUTING.md**
   - Development setup
   - Code style guide
   - Testing requirements
   - Pull request process

2. **docs/ARCHITECTURE.md**
   - Component diagram
   - Data flow
   - Security architecture
   - Extension points

3. **Code Comments**
   - Docstrings for all public functions
   - Inline comments for complex logic
   - Type hints throughout

### Generated Documentation

1. **.cursor/rules**
   - Auto-generated from discovered capabilities
   - Updated automatically when capabilities change
   - Committed to version control

2. **config.yaml.example**
   - Comprehensive configuration template
   - Inline comments explaining each option
   - Examples for common scenarios

---

## Success Criteria

### Functional Requirements
- ✅ Standalone CLI tool installable system-wide
- ✅ Reuses all cortex-code v2.0.0 security components
- ✅ Dynamic capability discovery (not hardcoded)
- ✅ Interactive terminal approval prompts
- ✅ Three approval modes: prompt, auto, envelope_only
- ✅ Security envelopes: RO, RW, RESEARCH, DEPLOY, NONE
- ✅ LLM-based semantic routing
- ✅ **Multi-IDE integration via adapter pattern**
- ✅ **Cursor**: `.cursor/rules/*.mdc` with AI suggestions
- ✅ **VSCode/Windsurf**: Task runner + code snippets
- ✅ Comprehensive error handling with recovery

### Security Requirements
- ✅ Prompt sanitization (PII removal, injection detection)
- ✅ Credential file blocking
- ✅ Secure caching with SHA256 validation
- ✅ Audit logging (JSONL format)
- ✅ Organization policy enforcement
- ✅ Two approval points (Cursor + tool)
- ✅ Configurable security levels

### User Experience Requirements
- ✅ Simple CLI interface: `cortexcode-tool "question"`
- ✅ Clear error messages with troubleshooting steps
- ✅ Progress indicators for long operations
- ✅ Graceful handling of user interrupts (Ctrl+C)
- ✅ Automatic discovery and setup

### Quality Requirements
- ✅ Comprehensive test coverage (unit + integration)
- ✅ Type hints throughout codebase
- ✅ Code formatting with black
- ✅ Linting with flake8
- ✅ Documentation for users and developers

### Performance Requirements
- ✅ Discovery cached with 24-hour TTL
- ✅ Routing decision < 2 seconds
- ✅ Tool prediction (if enabled) < 3 seconds
- ✅ Total overhead < 5 seconds per query

---

## Future Enhancements (Out of Scope)

1. **MCP Server Implementation**
   - Alternative to CLI approach
   - Requires Cursor MCP support
   - More integrated but more complex

2. **Real-Time Capability Updates**
   - Monitor Cortex version changes
   - Auto-regenerate .cursor/rules
   - Notification system

3. **GUI Configuration Tool**
   - Visual config editor
   - Interactive capability browser
   - Approval history viewer

4. **Multi-User Audit Dashboard**
   - Web-based audit log viewer
   - Team usage analytics
   - Compliance reporting

5. **Advanced Context Enrichment**
   - Project-specific context
   - Recent file changes
   - Git history integration

6. **Custom Skill Development**
   - Framework for user-defined skills
   - Local skill registry
   - Skill marketplace

---

## Appendix

### Configuration Reference

Complete config.yaml structure:

```yaml
security:
  approval_mode: "prompt"  # prompt | auto | envelope_only
  tool_prediction_confidence_threshold: 0.7
  audit_log_path: "~/.config/cortexcode-tool/audit.log"
  audit_log_rotation: "10MB"
  audit_log_retention: 30
  sanitize_conversation_history: true
  cache_dir: "~/.cache/cortexcode-tool"
  cache_ttl: 86400
  credential_file_allowlist:
    - "~/.ssh/**"
    - "~/.aws/credentials"
    - "~/.snowflake/**"
    - "**/.env"
    - "**/credentials.json"
  allowed_envelopes:
    - "RO"
    - "RW"
    - "RESEARCH"
    - "DEPLOY"

cortex:
  connection_name: "default"
  default_envelope: "RW"
  cli_path: "cortex"

ide:
  # Which IDEs to generate integration files for
  targets:
    - "cursor"   # Generate .cursor/rules/cortexcode-tool.mdc
    - "vscode"   # Generate .vscode/tasks.json + snippets
  # Or: ["cursor"], ["vscode"], ["all"]
  
  # IDE-specific settings
  cursor:
    rules_path: ".cursor/rules/cortexcode-tool.mdc"
    auto_regenerate_rules: true
  
  vscode:
    tasks_path: ".vscode/tasks.json"
    snippets_path: ".vscode/cortexcode.code-snippets"
    generate_settings_recommendations: false

logging:
  level: "INFO"  # DEBUG | INFO | WARNING | ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Audit Log Format

JSONL structure:

```jsonl
{"timestamp": "2026-04-02T10:30:00Z", "event": "routing_decision", "query": "Show databases", "route": "cortex", "confidence": 0.95, "reason": "Snowflake query"}
{"timestamp": "2026-04-02T10:30:02Z", "event": "tool_prediction", "tools": ["snowflake_sql_execute"], "confidence": 0.85, "envelope": "RW"}
{"timestamp": "2026-04-02T10:30:05Z", "event": "approval_request", "approval_mode": "prompt"}
{"timestamp": "2026-04-02T10:30:10Z", "event": "approval_granted", "user_response": "yes"}
{"timestamp": "2026-04-02T10:30:15Z", "event": "execution_start", "envelope": "RW", "command": "cortex -p '...'"}
{"timestamp": "2026-04-02T10:30:20Z", "event": "execution_complete", "exit_code": 0, "duration": 5.2}
{"timestamp": "2026-04-02T10:30:20Z", "event": "security_action", "action": "pii_sanitized", "count": 2}
```

### Exit Codes Reference

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Missing dependency |
| 3 | Configuration error |
| 4 | Discovery error |
| 5 | Security error |
| 6 | Approval timeout |
| 7 | Execution error |
| 8 | Connection error |
| 130 | User interrupt (Ctrl+C) |

---

**End of Design Specification**
