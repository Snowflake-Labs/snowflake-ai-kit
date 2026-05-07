#!/bin/bash
# Comprehensive test script for all 4 integrations

set -e

echo "======================================"
echo "Testing All 4 Cortex Code Integrations"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Helper function
test_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $1"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $1"
        ((FAILED++))
    fi
}

echo "1. Testing Claude Code Integration"
echo "-----------------------------------"
if [ -d ~/.claude/skills/cortex-code ]; then
    echo -e "${GREEN}✓ Directory exists${NC}"

    # Check parameterization
    if grep -q "cursor\|codex" ~/.claude/skills/cortex-code/scripts/route_request.py; then
        echo -e "${RED}✗ Wrong parameterization - found wrong agent name${NC}"
        ((FAILED++))
    else
        echo -e "${GREEN}✓ Parameterization correct${NC}"
        ((PASSED++))
    fi

    # Check files
    [ -f ~/.claude/skills/cortex-code/skill.md ]
    test_result "skill.md exists"

    [ -f ~/.claude/skills/cortex-code/scripts/route_request.py ]
    test_result "route_request.py exists"

    # Test routing
    cd ~/.claude/skills/cortex-code/scripts
    python3 route_request.py --prompt "Show Snowflake databases" > /tmp/claude_test.json 2>&1
    if grep -q "cortex" /tmp/claude_test.json; then
        echo -e "${GREEN}✓ Routing works${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Routing failed${NC}"
        ((FAILED++))
    fi
else
    echo -e "${RED}✗ Claude Code not installed${NC}"
    ((FAILED++))
fi
echo ""

echo "2. Testing Cursor Integration"
echo "------------------------------"
if [ -d ~/.cursor/skills/cortex-code ]; then
    echo -e "${GREEN}✓ Directory exists${NC}"

    # Check parameterization
    if grep -q "claude\|codex" ~/.cursor/skills/cortex-code/scripts/route_request.py; then
        echo -e "${RED}✗ Wrong parameterization - found wrong agent name${NC}"
        ((FAILED++))
    else
        echo -e "${GREEN}✓ Parameterization correct${NC}"
        ((PASSED++))
    fi

    # Check files
    [ -f ~/.cursor/skills/cortex-code/SKILL.md ]
    test_result "SKILL.md exists"

    [ -f ~/.cursor/skills/cortex-code/.cursorrules.template ]
    test_result ".cursorrules.template exists"

    # Test routing
    cd ~/.cursor/skills/cortex-code/scripts
    python3 route_request.py --prompt "List warehouses" > /tmp/cursor_test.json 2>&1
    if grep -q "cortex" /tmp/cursor_test.json; then
        echo -e "${GREEN}✓ Routing works${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Routing failed${NC}"
        ((FAILED++))
    fi
else
    echo -e "${RED}✗ Cursor not installed${NC}"
    ((FAILED++))
fi
echo ""

echo "3. Testing Codex Integration"
echo "----------------------------"
if command -v cortexcode-tool &> /dev/null; then
    echo -e "${GREEN}✓ cortexcode-tool exists${NC}"

    cortexcode-tool --version &> /tmp/codex_tool_version.txt
    test_result "cortexcode-tool --version runs"

    [ -f ~/.local/lib/cortexcode-tool/config.yaml ]
    test_result "Codex config exists"

    if grep -q 'approval_mode: "prompt"' ~/.local/lib/cortexcode-tool/config.yaml; then
        echo -e "${GREEN}✓ Codex approval mode defaults to prompt${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Codex approval mode is not prompt${NC}"
        ((FAILED++))
    fi
else
    echo -e "${RED}✗ cortexcode-tool not installed for Codex${NC}"
    ((FAILED++))
fi
echo ""

echo "4. Testing CLI Tool"
echo "-------------------"
if [ -f ~/.local/bin/cortexcode-tool ]; then
    echo -e "${GREEN}✓ CLI tool exists${NC}"

    # Check executable
    [ -x ~/.local/bin/cortexcode-tool ]
    test_result "CLI tool is executable"

    # Test execution (if implemented)
    if ~/.local/bin/cortexcode-tool --version &> /dev/null; then
        echo -e "${GREEN}✓ CLI tool runs${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠ CLI tool exists but --version not implemented${NC}"
    fi
else
    echo -e "${RED}✗ CLI tool not installed${NC}"
    ((FAILED++))
fi
echo ""

echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
