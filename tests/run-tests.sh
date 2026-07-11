#!/usr/bin/env bash
#
# run-tests.sh -- Test harness for Snowflake AI Kit (Mac/Linux)
#
# Validates plugin structure, runs unit tests, checks content sanity.
# Designed for the plugin architecture (plugins/cortex-code/).
#
# Usage:
#   bash tests/run-tests.sh              # Run all tests
#   bash tests/run-tests.sh --skip-unit  # Skip unit tests
#   bash tests/run-tests.sh --verbose    # Show extra detail
#

set -uo pipefail
# Note: we intentionally do NOT set -e because test checks use commands that
# may return non-zero, and we want to keep running to report all results.

PASS=0; FAIL=0; WARN=0; SKIP=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$REPO_ROOT/plugins/cortex-code"
ROUTER_DIR="$PLUGIN_DIR/scripts/router"

SKIP_UNIT=false
VERBOSE=false
INTEGRATION=false
for arg in "$@"; do
    case "$arg" in
        --skip-unit)    SKIP_UNIT=true ;;
        --verbose)      VERBOSE=true ;;
        --integration)  INTEGRATION=true ;;
    esac
done

# --- Helpers -------------------------------------------------------

pass() { printf "  \033[32mPASS\033[0m  %s\n" "$1"; ((PASS++)); }
fail() { printf "  \033[31mFAIL\033[0m  %s\n" "$1"; ((FAIL++)); }
warn() { printf "  \033[33mWARN\033[0m  %s\n" "$1"; ((WARN++)); }
skip() { printf "  \033[90mSKIP\033[0m  %s\n" "$1"; ((SKIP++)); }
section() { printf "\n\033[36m%s\033[0m\n" "$1"; }

check() {
    # check "label" <condition exit code>
    local label="$1"; shift
    if "$@" >/dev/null 2>&1; then
        pass "$label"
    else
        fail "$label"
    fi
}

check_warn() {
    local label="$1"; shift
    if "$@" >/dev/null 2>&1; then
        pass "$label"
    else
        warn "$label"
    fi
}

# ===================================================================
echo ""
echo "Snowflake AI Kit -- Test Harness (Mac/Linux)"
echo "============================================="

# === 1. CLI availability ===========================================

section "CLIs"

check "python3 in PATH" command -v python3
check "git in PATH"     command -v git

check_warn "cortex CLI in PATH"  command -v cortex
check_warn "snow CLI in PATH"    command -v snow

if command -v cortex >/dev/null 2>&1; then
    if cortex --version >/dev/null 2>&1; then
        pass "cortex --version runs ($(cortex --version 2>&1 | head -1))"
    else
        fail "cortex --version runs"
    fi
fi

# === 2. Plugin file structure ======================================

section "Plugin structure"

# Plugin manifest
check "plugin.json exists" test -f "$PLUGIN_DIR/.claude-plugin/plugin.json"

# Skills dirs
check "skills/cortex-router exists"  test -d "$PLUGIN_DIR/skills/cortex-router"
check "skills/cortex-run exists"     test -d "$PLUGIN_DIR/skills/cortex-run"
check "skills/cortex-setup exists"   test -d "$PLUGIN_DIR/skills/cortex-setup"
check "skills/sf-solutions exists"   test -d "$PLUGIN_DIR/skills/sf-solutions"

# Core router scripts
ROUTER_SCRIPTS=(
    "config.yaml.example"
    "discover_cortex.py"
    "envelope_policy.py"
    "execute_cortex.py"
    "predict_tools.py"
    "prompt_filter.py"
    "read_cortex_sessions.py"
    "route_request.py"
    "session_state.py"
)

all_router=true
for f in "${ROUTER_SCRIPTS[@]}"; do
    if [ ! -f "$ROUTER_DIR/$f" ]; then
        fail "router script: $f"
        all_router=false
    fi
done
if $all_router; then
    pass "All ${#ROUTER_SCRIPTS[@]} router scripts present"
fi

# Test files exist alongside code
check "test_envelope_policy.py exists" test -f "$ROUTER_DIR/test_envelope_policy.py"
check "test_plugin_units.py exists"    test -f "$ROUTER_DIR/test_plugin_units.py"

# === 3. Codex plugin & marketplace manifests =======================

section "Codex plugin & marketplace"

# .codex-plugin/plugin.json exists
CODEX_MANIFEST="$PLUGIN_DIR/.codex-plugin/plugin.json"
check ".codex-plugin/plugin.json exists" test -f "$CODEX_MANIFEST"

# .codex-plugin/plugin.json is valid JSON
if python3 -c "import json; json.load(open('$CODEX_MANIFEST'))" 2>/dev/null; then
    pass ".codex-plugin/plugin.json is valid JSON"
else
    fail ".codex-plugin/plugin.json is valid JSON"
fi

# marketplace.json exists
MARKETPLACE_JSON="$REPO_ROOT/.agents/plugins/marketplace.json"
check "marketplace.json exists" test -f "$MARKETPLACE_JSON"

# marketplace.json is valid JSON
if python3 -c "import json; json.load(open('$MARKETPLACE_JSON'))" 2>/dev/null; then
    pass "marketplace.json is valid JSON"
else
    fail "marketplace.json is valid JSON"
fi

# Marketplace source path resolves to actual plugin directory
if python3 -c "
import json, os, sys
mkt = json.load(open('$MARKETPLACE_JSON'))
for p in mkt.get('plugins', []):
    src_path = p.get('source', {}).get('path', '')
    resolved = os.path.normpath(os.path.join('$REPO_ROOT', src_path))
    if not os.path.isdir(resolved):
        sys.exit(1)
" 2>/dev/null; then
    pass "marketplace source path resolves to plugin directory"
else
    fail "marketplace source path resolves to plugin directory"
fi

# Both manifests share the same name and version
if python3 -c "
import json, sys
claude = json.load(open('$PLUGIN_DIR/.claude-plugin/plugin.json'))
codex  = json.load(open('$CODEX_MANIFEST'))
if claude['name'] != codex['name']:
    sys.exit(1)
if claude['version'] != codex['version']:
    sys.exit(1)
" 2>/dev/null; then
    pass "Claude and Codex manifests have matching name+version"
else
    fail "Claude and Codex manifests have matching name+version"
fi

# Codex manifest has required interface block
if python3 -c "
import json, sys
codex = json.load(open('$CODEX_MANIFEST'))
iface = codex.get('interface', {})
required = ['displayName', 'shortDescription', 'category']
for key in required:
    if key not in iface:
        sys.exit(1)
" 2>/dev/null; then
    pass "Codex manifest has required interface fields"
else
    fail "Codex manifest has required interface fields"
fi

# Codex manifest declares hooks
if python3 -c "
import json, sys
codex = json.load(open('$CODEX_MANIFEST'))
if 'hooks' not in codex:
    sys.exit(1)
" 2>/dev/null; then
    pass "Codex manifest declares hooks"
else
    fail "Codex manifest declares hooks"
fi

# === 4. Content sanity checks ======================================

section "Content checks"

# plugin.json must be valid JSON
if python3 -c "import json; json.load(open('$PLUGIN_DIR/.claude-plugin/plugin.json'))" 2>/dev/null; then
    pass "plugin.json is valid JSON"
else
    fail "plugin.json is valid JSON"
fi

# envelope_policy.py must define the decide function
if grep -q "^def decide(" "$ROUTER_DIR/envelope_policy.py" 2>/dev/null; then
    pass "envelope_policy.py defines decide()"
else
    fail "envelope_policy.py defines decide()"
fi

# execute_cortex.py must use --permission-prompt-tool stdio
if grep -q "permission-prompt-tool" "$ROUTER_DIR/execute_cortex.py" 2>/dev/null; then
    pass "execute_cortex.py uses --permission-prompt-tool"
else
    fail "execute_cortex.py uses --permission-prompt-tool"
fi

# execute_cortex.py must import envelope_policy
if grep -q "from envelope_policy import" "$ROUTER_DIR/execute_cortex.py" 2>/dev/null; then
    pass "execute_cortex.py imports envelope_policy"
else
    fail "execute_cortex.py imports envelope_policy"
fi

# session_state.py must define load/save/clear
for fn in load_active_session save_active_session clear_active_session; do
    if grep -q "def $fn" "$ROUTER_DIR/session_state.py" 2>/dev/null; then
        pass "session_state.py defines $fn()"
    else
        fail "session_state.py defines $fn()"
    fi
done

# config.yaml.example is non-empty
if [ -s "$ROUTER_DIR/config.yaml.example" ]; then
    pass "config.yaml.example is non-empty"
else
    fail "config.yaml.example is non-empty"
fi

# === 5. Unit tests =================================================

section "Unit tests"

if $SKIP_UNIT; then
    skip "Unit tests (--skip-unit)"
else
    # Run envelope policy tests
    echo "  Running test_envelope_policy.py..."
    OUTPUT=$(cd "$ROUTER_DIR" && python3 test_envelope_policy.py 2>&1)
    if echo "$OUTPUT" | grep -q "^[0-9]*/[0-9]* passed$"; then
        TOTAL_LINE=$(echo "$OUTPUT" | grep "^[0-9]*/[0-9]* passed$")
        PASSED=$(echo "$TOTAL_LINE" | cut -d/ -f1)
        TOTAL=$(echo "$TOTAL_LINE" | cut -d/ -f2 | cut -d' ' -f1)
        if [ "$PASSED" = "$TOTAL" ]; then
            pass "test_envelope_policy.py: $TOTAL_LINE"
        else
            fail "test_envelope_policy.py: $TOTAL_LINE"
        fi
    else
        fail "test_envelope_policy.py: could not parse results"
        if $VERBOSE; then echo "$OUTPUT"; fi
    fi

    # Run plugin unit tests
    echo "  Running test_plugin_units.py..."
    OUTPUT=$(cd "$ROUTER_DIR" && python3 test_plugin_units.py 2>&1)
    if echo "$OUTPUT" | grep -q "^[0-9]*/[0-9]* passed$"; then
        TOTAL_LINE=$(echo "$OUTPUT" | grep "^[0-9]*/[0-9]* passed$")
        PASSED=$(echo "$TOTAL_LINE" | cut -d/ -f1)
        TOTAL=$(echo "$TOTAL_LINE" | cut -d/ -f2 | cut -d' ' -f1)
        if [ "$PASSED" = "$TOTAL" ]; then
            pass "test_plugin_units.py: $TOTAL_LINE"
        else
            fail "test_plugin_units.py: $TOTAL_LINE"
        fi
    else
        fail "test_plugin_units.py: could not parse results"
        if $VERBOSE; then echo "$OUTPUT"; fi
    fi
fi

# === 6. Integration tests (optional, requires cortex CLI + Snowflake connection) ===

section "Integration tests"

if ! $INTEGRATION; then
    skip "Integration tests (use --integration to run)"
else
    if ! command -v cortex >/dev/null 2>&1; then
        skip "Integration tests (cortex CLI not found)"
    else
        echo "  Running test_integration.py (this may take 30-90s)..."
        OUTPUT=$(cd "$ROUTER_DIR" && python3 test_integration.py 2>&1)
        EXIT_CODE=$?
        if echo "$OUTPUT" | grep -q "^[0-9]*/[0-9]* passed$"; then
            TOTAL_LINE=$(echo "$OUTPUT" | grep "^[0-9]*/[0-9]* passed$")
            PASSED_INT=$(echo "$TOTAL_LINE" | cut -d/ -f1)
            TOTAL_INT=$(echo "$TOTAL_LINE" | cut -d/ -f2 | cut -d' ' -f1)
            if [ "$PASSED_INT" = "$TOTAL_INT" ]; then
                pass "test_integration.py: $TOTAL_LINE"
            else
                fail "test_integration.py: $TOTAL_LINE"
            fi
        elif echo "$OUTPUT" | grep -q "^SKIP:"; then
            skip "test_integration.py: $(echo "$OUTPUT" | grep "^SKIP:" | head -1)"
        else
            fail "test_integration.py: could not parse results (exit=$EXIT_CODE)"
        fi
        if $VERBOSE; then echo "$OUTPUT"; fi
    fi
fi

# === 7. Snowflake connection =======================================

section "Snowflake connection"

CONN_TOML="$HOME/.snowflake/connections.toml"
CFG_TOML="$HOME/.snowflake/config.toml"
if [ -f "$CONN_TOML" ] || [ -f "$CFG_TOML" ] || [ -n "${SNOWFLAKE_HOST:-}" ] || [ -n "${SNOWFLAKE_ACCOUNT:-}" ]; then
    pass "Snowflake connection configured"
else
    warn "Snowflake connection configured (no connections.toml or env vars found)"
fi

# === Summary =======================================================

echo ""
echo "============================================="
TOTAL=$((PASS + FAIL + WARN + SKIP))
printf "Results (%d tests): " "$TOTAL"
printf "\033[32m%d passed\033[0m, " "$PASS"
if [ "$FAIL" -gt 0 ]; then
    printf "\033[31m%d failed\033[0m, " "$FAIL"
else
    printf "0 failed, "
fi
printf "\033[33m%d warnings\033[0m, " "$WARN"
printf "\033[90m%d skipped\033[0m\n" "$SKIP"
echo ""

if [ "$FAIL" -gt 0 ]; then
    printf "\033[31mSOME TESTS FAILED -- review output above.\033[0m\n"
    exit 1
elif [ "$WARN" -gt 0 ]; then
    printf "\033[33mAll critical checks passed. Warnings are non-blocking.\033[0m\n"
    exit 0
else
    printf "\033[32mAll tests passed.\033[0m\n"
    exit 0
fi
