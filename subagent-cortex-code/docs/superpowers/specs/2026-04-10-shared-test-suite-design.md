# Test Suite Design: Shared Scripts Validation

**Date:** 2026-04-10  
**Status:** Approved  
**Context:** Monorepo migration with 4 integrations sharing common code

## Overview

Create a comprehensive test suite for the `subagent-cortex-code` monorepo that validates:
- Shared scripts and security modules work correctly
- Recent bug fixes (cortex v1.0.50+ compatibility, stdin hang, allowed-tools removal)
- Parameterization (`__CODING_AGENT__` placeholder) works across all 4 integrations
- Installation scripts correctly deploy to each coding agent

## Goals

1. **Validate bug fixes** - Prove 3 critical bug fixes work (100% coverage of fixes)
2. **Test critical paths** - 70% coverage of routing, execution, and security code
3. **Verify parameterization** - All 4 integrations (Claude Code, Cursor, Codex, CLI tool) work
4. **Enable CI/CD** - Fast unit tests (<30s), comprehensive integration tests (~2 min)
5. **Prevent regressions** - Catch issues before they reach production

## Architecture

### Test Directory Structure

```
subagent-cortex-code/
├── tests/
│   ├── shared/                    # Tests for shared/ code
│   │   ├── conftest.py           # Shared fixtures
│   │   ├── unit/                 # Fast unit tests
│   │   │   ├── test_route_request.py
│   │   │   ├── test_execute_cortex.py
│   │   │   ├── test_discover_cortex.py
│   │   │   ├── test_config_manager.py
│   │   │   ├── test_security_wrapper.py
│   │   │   ├── test_cache_manager.py
│   │   │   └── test_prompt_sanitizer.py
│   │   ├── integration/          # End-to-end flow tests
│   │   │   ├── test_e2e_routing.py
│   │   │   └── test_parameterization.py
│   │   └── regression/           # Bug fix validation
│   │       ├── test_bug_fixes.py
│   │       └── test_cortex_v1_0_50.py
│   │
│   └── integrations/              # Integration-specific tests
│       ├── claude-code/
│       │   ├── test_install.py
│       │   └── test_skill_loading.py
│       ├── cursor/
│       │   ├── test_install.py
│       │   └── test_cursorrules.py
│       ├── codex/
│       │   ├── test_install.py
│       │   └── test_setup_guidance.py
│       └── cli-tool/
│           ├── test_install.py
│           └── test_cli_execution.py
```

**Design Rationale:**
- Clear separation: shared tests for shared code, integration tests for integration code
- Fast feedback: Unit tests run in seconds for quick iteration
- Comprehensive coverage: Integration tests catch real-world issues
- Parallel execution: Structure supports running tests independently

## Test Framework & Tooling

**Framework:** pytest (already in use, mature ecosystem)

**Key Features Used:**
- **Fixtures** - Shared setup/teardown (temp dirs, mock configs, mock cortex CLI)
- **Parametrization** - Test same logic across all 4 coding agents
- **Markers** - Tag tests by type: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Mock/Patch** - Mock subprocess calls to cortex CLI (no actual Cortex/Snowflake required)

**Test Execution Modes:**

```bash
# Fast: Unit tests only (~30 seconds)
pytest tests/shared/unit/

# Medium: Unit + integration (~2 minutes)
pytest tests/shared/

# Full: Everything including integration-specific (~5 minutes)
pytest tests/

# Bug fixes only
pytest tests/shared/regression/

# Specific integration
pytest tests/integrations/claude-code/
```

**Coverage Requirements:**
- Minimum for PR merge: 60% overall, 100% of bug fix code
- Goal: 70% of shared scripts, 80% of security modules
- Report: HTML coverage report generated

## Critical Path Test Cases

### 1. Routing Logic (`test_route_request.py`)

**Purpose:** Validate semantic routing and credential blocking

**Test Cases:**
- `test_snowflake_indicators_route_to_cortex()` - Keywords → cortex
- `test_coding_agent_indicators_route_to_agent()` - Non-Snowflake → agent
- `test_sql_with_snowflake_context()` - SQL + context → cortex
- `test_sql_without_context()` - Generic SQL → agent
- `test_credential_blocking_ssh()` - `~/.ssh/` path → blocked
- `test_credential_blocking_env_file()` - `.env` file → blocked
- `test_no_indicators_defaults_to_coding_agent()` - Safe default
- `test_parameterization_placeholder()` - Returns `__CODING_AGENT__` not hardcoded

**Coverage Target:** 80% (routing is critical security boundary)

### 2. Execution Logic (`test_execute_cortex.py`)

**Purpose:** Validate bug fixes and execution flow

**Critical Bug Fix Tests:**
- `test_stdin_devnull_prevents_hanging()` - **Bug #2 fix:** Verify `stdin=subprocess.DEVNULL`
- `test_no_allowed_tools_flag()` - **Bug #3 fix:** Ensure `--allowed-tools` NOT in command
- `test_disallowed_tools_only()` - **Bug #3 fix:** Verify `--disallowed-tools` used instead

**Envelope Tests:**
- `test_ro_envelope_blocks_write_tools()` - RO → Edit/Write disallowed
- `test_rw_envelope_minimal_restrictions()` - RW → only destructive ops disallowed
- `test_auto_approval_mode()` - `--input-format stream-json` enables auto-approval

**Tool Management:**
- `test_tool_inversion_prompt_mode()` - Allowed tools → inverted to disallowed list

**Coverage Target:** 75% (execution is critical path)

### 3. Discovery Logic (`test_discover_cortex.py`)

**Purpose:** Validate cortex v1.0.50+ format compatibility

**Critical Bug Fix Tests:**
- `test_parse_old_format()` - **Bug #1:** Handles "skill-name /path" format
- `test_parse_new_format_with_headers()` - **Bug #1 fix:** Handles `[BUNDLED]` headers
- `test_parse_new_format_indented_entries()` - **Bug #1 fix:** Handles `  - skill-name: /path`
- `test_skip_section_headers()` - Skips `[BUNDLED]`, `[PROJECT]`, `[GLOBAL]`
- `test_mixed_format_handling()` - Backward compatibility
- `test_discovers_32_skills()` - Mock v1.0.50+ output → 32 skills

**Coverage Target:** 85% (parser must be robust)

### 4. Configuration Management (`test_config_manager.py`)

**Purpose:** Validate parameterization and config precedence

**Parameterization Tests:**
- `test_default_path_uses_placeholder()` - Contains `__CODING_AGENT__`
- `test_placeholder_not_expanded_in_defaults()` - Not expanded too early
- `test_user_config_override_works()` - User config takes precedence
- `test_org_policy_override()` - Org policy highest precedence
- `test_expanduser_on_final_paths()` - `~` expansion works

**Coverage Target:** 70%

### 5. Security Orchestration (`test_security_wrapper.py`)

**Purpose:** Validate end-to-end security flow

**Orchestration Tests:**
- `test_routes_to_coding_agent_for_non_snowflake()` - Status: "routed_to_coding_agent"
- `test_routes_to_cortex_for_snowflake()` - Executes via cortex
- `test_blocks_credential_files()` - Status: "blocked"
- `test_sanitization_when_enabled()` - PII removed
- `test_audit_logging_on_execution()` - Every execution logged

**Coverage Target:** 75%

## Integration Tests

### End-to-End Flow (`test_e2e_routing.py`)

**Full System Tests:**
- `test_full_snowflake_query_flow()` - Prompt → route → execute → audit
- `test_full_local_file_flow()` - Prompt → route to agent → return decision
- `test_credential_blocking_flow()` - Credential → blocked immediately
- `test_approval_mode_prompt()` - Returns awaiting_approval status
- `test_approval_mode_auto()` - Executes immediately with audit
- `test_envelope_ro_restrictions()` - RO blocks write operations
- `test_envelope_rw_permissions()` - RW allows snowflake operations

**Mocking Strategy:**
- Mock cortex CLI subprocess calls
- Mock filesystem (use tmp_path)
- Real config/audit/cache managers (test actual behavior)

### Parameterization Validation (`test_parameterization.py`)

**Cross-Agent Tests:**
- `test_install_replaces_placeholder_claude()` - Placeholder → "claude"
- `test_install_replaces_placeholder_cursor()` - Placeholder → "cursor"
- `test_install_replaces_placeholder_codex()` - Placeholder → "codex"
- `test_routing_returns_correct_agent_name()` - Returns agent-specific name
- `test_config_paths_use_agent_directory()` - Audit log → correct `~/.{agent}/` path
- `test_cross_platform_sed_replacement()` - BSD sed (macOS) & GNU sed (Linux) work

**Approach:**
- Parametrized fixtures: `@pytest.fixture(params=["claude", "cursor", "codex"])`
- Run same test logic for all agents
- Validate sed replacement on both macOS and Linux

## Regression Tests

### Bug Fix Validation (`test_bug_fixes.py`)

**Bug #1: Parser Failed on Cortex v1.0.50+ Format**

```python
def test_bug1_new_cortex_format_parser():
    """Cortex v1.0.50+ uses [BUNDLED] headers and indented entries."""
    mock_output = """[BUNDLED]
  - snowflake-query: /path/to/skill
  - data-quality: /path/to/skill
[PROJECT]
  - custom-skill: /path/to/skill
"""
    skills = parse_cortex_skill_list(mock_output)
    assert len(skills) == 3
    assert "snowflake-query" in skills
```

**Bug #2: Execution Hung Without stdin=DEVNULL**

```python
def test_bug2_stdin_devnull_prevents_hang():
    """stdin=DEVNULL prevents cortex waiting on stdin forever."""
    with patch('subprocess.Popen') as mock_popen:
        execute_cortex_streaming(prompt="test", envelope="RW")
        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs['stdin'] == subprocess.DEVNULL
```

**Bug #3: --allowed-tools Blocked Snowflake MCP Tools**

```python
def test_bug3_no_allowed_tools_flag():
    """--allowed-tools creates pattern-match that blocks MCP tools."""
    cmd = build_cortex_command(envelope="RW", approval_mode="auto")
    assert "--allowed-tools" not in cmd
    assert "--disallowed-tools" in cmd  # Use blocklist only
```

### Version Compatibility (`test_cortex_v1_0_50.py`)

- `test_backward_compatibility_old_format()` - Pre-v1.0.50 still works
- `test_forward_compatibility_new_format()` - v1.0.50+ works
- `test_mixed_version_environments()` - Both formats in hybrid setups

## Integration-Specific Tests

### Install Script Pattern

**Each integration gets:**
- `test_install_script_creates_directories()` - Correct directory structure
- `test_install_copies_shared_scripts()` - All 6 scripts copied
- `test_install_copies_security_modules()` - All 6 modules copied
- `test_install_replaces_coding_agent_placeholder()` - Placeholder replaced
- `test_install_copies_skill_definition()` - skill.md/SKILL.md copied
- `test_install_creates_default_config()` - config.yaml from example
- `test_uninstall_removes_files()` - Clean uninstall, backups preserved

**Agent-Specific Variations:**
- **Claude Code:** Target `~/.claude/`, file `skill.md`
- **Cursor:** Target `~/.cursor/`, file `SKILL.md`, test `.cursorrules.template`
- **Codex:** Target `~/.codex/`, test `setup_guidance.md`
- **CLI Tool:** Target `~/.local/bin/`, test executable permissions

## Test Fixtures & Utilities

### Shared Fixtures (`tests/shared/conftest.py`)

```python
@pytest.fixture
def temp_dir():
    """Temporary directory for test isolation."""

@pytest.fixture
def mock_cortex_output_old_format():
    """Mock cortex skill list (pre-v1.0.50)."""
    return "skill-name /path/to/skill"

@pytest.fixture
def mock_cortex_output_new_format():
    """Mock cortex skill list (v1.0.50+)."""
    return "[BUNDLED]\n  - skill-name: /path"

@pytest.fixture(params=["claude", "cursor", "codex"])
def coding_agent(request):
    """Parametrized fixture for all agents."""
    return request.param

@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager with test defaults."""

@pytest.fixture
def mock_audit_logger(tmp_path):
    """Mock AuditLogger writing to temp file."""
```

### Test Markers

```python
# pytest.ini
[tool.pytest.ini_options]
markers = [
    "unit: Fast unit tests (no external dependencies)",
    "integration: Integration tests (mock cortex CLI)",
    "slow: Tests requiring actual cortex CLI",
    "regression: Regression tests for bug fixes",
    "cross_platform: macOS/Linux compatibility tests"
]
```

### Mocking Strategy

- **subprocess.Popen** - Mock all cortex CLI calls for unit/integration tests
- **Path operations** - Use `tmp_path` fixture for filesystem isolation
- **ConfigManager** - Mock to return test configurations
- **Time-based tests** - Use `freezegun` for audit log timestamps

## Implementation Plan

### Phase 1: Infrastructure Setup (~30 min)

- Create `tests/shared/` directory structure
- Set up `conftest.py` with shared fixtures
- Configure pytest markers and coverage reporting
- Add `pytest.ini` or `pyproject.toml` configuration

### Phase 2: Regression Tests (~45 min)

**Priority: Validate bug fixes first**

- `test_bug_fixes.py` - All 3 bug fixes with before/after cases
- `test_cortex_v1_0_50.py` - Version compatibility tests
- Run tests to verify fixes work

### Phase 3: Critical Path Unit Tests (~90 min)

- `test_route_request.py` - Routing logic + credential blocking
- `test_execute_cortex.py` - Execution + bug fix validation
- `test_discover_cortex.py` - Parser with new format support
- `test_config_manager.py` - Parameterization support
- `test_security_wrapper.py` - Orchestration logic

**Milestone:** Core functionality validated

### Phase 4: Integration Tests (~60 min)

- `test_e2e_routing.py` - Full flow tests
- `test_parameterization.py` - Cross-agent validation
- Verify mocking strategy works correctly

### Phase 5: Integration-Specific Tests (~45 min)

- Install script tests for all 4 integrations
- Smoke tests for integration-specific features
- Cross-platform sed tests (macOS/Linux)

**Total Estimated Time:** ~4 hours

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test-shared:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11']
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install pytest pytest-cov pytest-mock
      - run: pytest tests/shared/unit/ --cov=shared/ --cov-report=xml
      - uses: codecov/codecov-action@v3
        if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.11'

  test-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install pytest pytest-mock
      - run: pytest tests/shared/integration/ -v

  test-integrations:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install pytest
      - run: pytest tests/integrations/ --maxfail=1 -v
```

### Pre-Commit Hooks

```bash
# .pre-commit-config.yaml (optional)
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: pytest tests/shared/unit/ -q
        language: system
        pass_filenames: false
```

## Test Maintenance

### Running Tests

```bash
# Development workflow
pytest tests/shared/unit/ -v                    # Fast feedback
pytest tests/shared/ --cov=shared/              # Full shared tests with coverage
pytest tests/ --cov=shared/ --cov-report=html   # Complete suite

# Before PR
pytest tests/ -v --cov=shared/ --cov-report=html

# Specific test file
pytest tests/shared/unit/test_route_request.py -v

# Specific test function
pytest tests/shared/unit/test_route_request.py::test_snowflake_indicators_route_to_cortex -v
```

### When to Update Tests

- **Adding features:** Write tests first (TDD approach)
- **Fixing bugs:** Add regression test, then fix
- **Changing APIs:** Update affected tests
- **Refactoring:** Tests should pass without changes (if API stable)

### Performance Guidelines

- **Unit tests:** <30 seconds total
- **Integration tests:** <2 minutes total
- **Full suite:** <5 minutes total
- If tests slow down, investigate and optimize

## Success Criteria

### Coverage Requirements Met

- ✅ 100% coverage of bug fix code
- ✅ 70% coverage of shared scripts
- ✅ 60% overall coverage minimum for PR merge

### All Tests Pass

- ✅ Unit tests pass on Python 3.8-3.11
- ✅ Integration tests pass on macOS and Linux
- ✅ Regression tests validate all 3 bug fixes
- ✅ Parameterization tests pass for all 4 integrations

### CI/CD Integration Working

- ✅ GitHub Actions workflow runs on push/PR
- ✅ Coverage reports uploaded to Codecov
- ✅ Tests complete in <5 minutes

### Documentation Complete

- ✅ README.md updated with test instructions
- ✅ Test strategy documented in this spec
- ✅ Test failures provide clear error messages

## Future Enhancements

**Not in scope for initial implementation:**

- Property-based testing (hypothesis) for fuzzing
- Performance benchmarks for routing/execution
- Integration tests with real Cortex CLI (`@pytest.mark.slow`)
- Mutation testing to validate test quality
- Test data generators for complex scenarios

**Rationale:** Focus on validating the monorepo migration and bug fixes first. These enhancements can be added later if needed.

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov plugin](https://pytest-cov.readthedocs.io/)
- [Monorepo test structure best practices](https://martinfowler.com/articles/microservice-testing/)
- Bug fix commit: `17d08fa` (3 bugs resolved)

---

**End of Design Document**
