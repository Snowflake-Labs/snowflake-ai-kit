#!/usr/bin/env bash
#
# Snowflake AI Kit — Installer
#
# Installs Snowflake CLI (snow), Cortex Code CLI (cortex), and optionally
# agent integrations (Claude Code, Cursor, Codex) with the Cortex Code
# router skill, if not already present, then verifies your Snowflake connection.
#
# Usage:
#   bash <(curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.sh)
#
#   # Check what's installed
#   bash <(curl -sSL .../install.sh) --check
#

set -e

# Colors
G='\033[0;32m' Y='\033[1;33m' R='\033[0;31m' B='\033[1m' N='\033[0m'

REPO_URL="https://github.com/Snowflake-Labs/snowflake-ai-kit.git"
SKILL_DIR="${HOME}/.claude/skills/cortex-code"
TROUBLESHOOT="https://github.com/Snowflake-Labs/snowflake-ai-kit#troubleshooting"

msg()  { echo -e "  $*"; }
ok()   { echo -e "  ${G}✓${N} $*"; }
warn() { echo -e "  ${Y}!${N} $*"; }
die()  { echo -e "  ${R}✗${N} $*" >&2; exit 1; }
step() { echo -e "\n${B}$*${N}"; }

# ─── Prereq checks ─────────────────────────────────────────

check_cmd() {
  command -v "$1" &>/dev/null
}

check_snowflake_auth() {
  if [[ -f "$HOME/.snowflake/connections.toml" ]]; then
    ok "Snowflake config found (~/.snowflake/connections.toml)"
    return 0
  elif [[ -f "$HOME/.snowflake/config.toml" ]]; then
    ok "Snowflake config found (~/.snowflake/config.toml)"
    return 0
  elif [[ -n "$SNOWFLAKE_HOST" ]] || [[ -n "$SNOWFLAKE_ACCOUNT" ]]; then
    ok "Snowflake config found (environment variables)"
    return 0
  else
    warn "No Snowflake connection configured."
    msg "  Set one up (shared by both snow and cortex CLIs):"
    msg "    snow connection add"
    msg "  This creates ~/.snowflake/connections.toml, used by both tools."
    msg "  Docs: https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials"
    msg "  More help: $TROUBLESHOOT"
    return 1
  fi
}

install_snowflake_cli() {
  if check_cmd snow; then
    ok "Snowflake CLI (snow) already installed"
    return 0
  fi

  msg "Installing Snowflake CLI..."
  if check_cmd pipx; then
    pipx install snowflake-cli && ok "Snowflake CLI installed via pipx" && return 0
  elif check_cmd pip3; then
    pip3 install snowflake-cli && ok "Snowflake CLI installed via pip3" && return 0
  elif check_cmd pip; then
    pip install snowflake-cli && ok "Snowflake CLI installed via pip" && return 0
  elif check_cmd brew; then
    brew tap snowflakedb/snowflake-cli && brew install snowflake-cli && ok "Snowflake CLI installed via brew" && return 0
  fi
  die "Could not install Snowflake CLI. See $TROUBLESHOOT"
}

install_cortex_code_cli() {
  if check_cmd cortex; then
    ok "Cortex Code CLI (cortex) already installed"
    return 0
  fi

  msg "Installing Cortex Code CLI..."
  if curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | sh; then
    ok "Cortex Code CLI installed"
    return 0
  fi
  die "Could not install Cortex Code CLI. See $TROUBLESHOOT"
}

install_claude_code_cli() {
  if check_cmd claude; then
    ok "Claude Code CLI (claude) already installed"
    return 0
  fi

  msg "Installing Claude Code CLI..."

  # If npm not found, try to install Node.js first
  if ! check_cmd npm; then
    msg "  Node.js not found -- attempting to install..."
    if check_cmd brew; then
      brew install node 2>/dev/null && msg "  Node.js installed via brew"
    elif check_cmd apt-get; then
      curl -fsSL https://deb.nodesource.com/setup_lts.x 2>/dev/null | sudo -E bash - 2>/dev/null && sudo apt-get install -y nodejs 2>/dev/null && msg "  Node.js installed via apt"
    elif check_cmd yum; then
      curl -fsSL https://rpm.nodesource.com/setup_lts.x 2>/dev/null | sudo bash - 2>/dev/null && sudo yum install -y nodejs 2>/dev/null && msg "  Node.js installed via yum"
    fi
  fi

  if check_cmd npm; then
    npm install -g @anthropic-ai/claude-code 2>/dev/null && ok "Claude Code CLI installed via npm" && return 0
  fi
  warn "Could not install Claude Code CLI (requires Node.js + npm)."
  msg "  Install Node.js from https://nodejs.org then re-run."
  msg "  Or install manually: npm install -g @anthropic-ai/claude-code"
  return 1
}

# ─── Skill installation ──────────────────────────────────────

install_skills() {
  if [ -f "${SKILL_DIR}/SKILL.md" ] && ! $UPDATE; then
    ok "Claude-to-Cortex Code Router skill already installed"
    msg "  Re-run with --update to overwrite"
    return 0
  fi

  msg "Installing Claude-to-Cortex Code Router skill..."

  tmp_dir=$(mktemp -d)
  trap "rm -rf '$tmp_dir'" EXIT

  src=""

  # Try cloning the repo
  if git clone --depth 1 "$REPO_URL" "$tmp_dir/repo" 2>/dev/null; then
    if [ -d "$tmp_dir/repo/agent-to-agent-skills/claude-cortex-code-router" ]; then
      src="$tmp_dir/repo/agent-to-agent-skills/claude-cortex-code-router"
    fi
  fi

  # Fallback: check if script is running from within the repo
  if [ -z "$src" ] || [ ! -f "$src/SKILL.md" ]; then
    script_dir="$(cd "$(dirname "$0")" && pwd)"
    local_src="$script_dir/agent-to-agent-skills/claude-cortex-code-router"
    if [ -f "$local_src/SKILL.md" ]; then
      msg "  Using local repo as source..."
      src="$local_src"
    fi
  fi

  if [ -z "$src" ] || [ ! -f "$src/SKILL.md" ]; then
    warn "Could not find skill source (clone failed and not running from repo)."
    msg "  Manual install: git clone $REPO_URL && copy agent-to-agent-skills/claude-cortex-code-router/ to $SKILL_DIR/"
    return 1
  fi

  mkdir -p "$SKILL_DIR/scripts" "$SKILL_DIR/security/policies" "$SKILL_DIR/references"

  # Core skill definition
  cp "$src/SKILL.md" "$SKILL_DIR/"
  cp "$src/README.md" "$SKILL_DIR/"
  cp "$src/config.yaml.example" "$SKILL_DIR/"

  # Scripts
  for f in discover_cortex.py execute_cortex.py predict_tools.py \
           read_cortex_sessions.py route_request.py security_wrapper.py; do
    cp "$src/scripts/$f" "$SKILL_DIR/scripts/"
  done

  # Security module
  for f in __init__.py approval_handler.py audit_logger.py \
           cache_manager.py config_manager.py prompt_sanitizer.py; do
    cp "$src/security/$f" "$SKILL_DIR/security/"
  done
  cp "$src/security/policies/default_policy.yaml" "$SKILL_DIR/security/policies/"

  # References
  for f in cortex-cli-reference.md routing-examples.md; do
    cp "$src/references/$f" "$SKILL_DIR/references/"
  done

  # Optional docs
  for f in SECURITY.md; do
    [ -f "$src/$f" ] && cp "$src/$f" "$SKILL_DIR/"
  done

  ok "Claude-to-Cortex Code Router skill installed to ${SKILL_DIR}/"
  return 0
}

# ─── Cursor integration ──────────────────────────────────────

install_cursor_skill() {
  local cursor_skill_dir="$HOME/.cursor/skills-cursor/cortex-code"
  local cursor_rules_dir="$HOME/.cursor/rules"

  if [ -f "${cursor_skill_dir}/SKILL.md" ] && ! $UPDATE; then
    ok "Cursor skill already installed"
    msg "  Re-run with --update to overwrite"
    return 0
  fi

  # Locate the repo root (works when running from within the repo)
  local repo_root
  repo_root="$(cd "$(dirname "$0")" && pwd)"

  if [ -f "$repo_root/integrations/cursor/install.sh" ]; then
    msg "Installing Cursor integration..."
    bash "$repo_root/integrations/cursor/install.sh"
    return $?
  fi

  # Fallback: try from a temp clone
  if [ -n "$tmp_dir" ] && [ -f "$tmp_dir/repo/integrations/cursor/install.sh" ]; then
    bash "$tmp_dir/repo/integrations/cursor/install.sh"
    return $?
  fi

  warn "Could not find Cursor integration installer."
  msg "  Manual install: git clone $REPO_URL && bash integrations/cursor/install.sh"
  return 1
}

# ─── Codex integration ───────────────────────────────────────

install_codex_tool() {
  if command -v cortexcode-tool &>/dev/null && ! $UPDATE; then
    ok "cortexcode-tool already installed"
    msg "  Re-run with --update to overwrite"
    return 0
  fi

  local repo_root
  repo_root="$(cd "$(dirname "$0")" && pwd)"

  if [ -f "$repo_root/integrations/codex/install.sh" ]; then
    msg "Installing Codex integration (cortexcode-tool)..."
    bash "$repo_root/integrations/codex/install.sh"
    return $?
  fi

  if [ -n "$tmp_dir" ] && [ -f "$tmp_dir/repo/integrations/codex/install.sh" ]; then
    bash "$tmp_dir/repo/integrations/codex/install.sh"
    return $?
  fi

  warn "Could not find Codex integration installer."
  msg "  Manual install: git clone $REPO_URL && bash integrations/codex/install.sh"
  return 1
}

# ─── Parse arguments ────────────────────────────────────────

CHECK_ONLY=false
UPDATE=false
WITH_CLAUDE=false
WITH_CURSOR=false
WITH_CODEX=false
WITH_ALL=false

while [ $# -gt 0 ]; do
  case $1 in
    --check|-c)
      CHECK_ONLY=true
      shift
      ;;
    --update|-u)
      UPDATE=true
      shift
      ;;
    --with-claude)
      WITH_CLAUDE=true
      shift
      ;;
    --with-cursor)
      WITH_CURSOR=true
      shift
      ;;
    --with-codex)
      WITH_CODEX=true
      shift
      ;;
    --with-all)
      WITH_ALL=true
      shift
      ;;
    --help|-h)
      echo "Snowflake AI Kit — Installer"
      echo ""
      echo "Installs Snowflake CLI (snow), Cortex Code CLI (cortex), and optionally"
      echo "agent integrations (Claude Code, Cursor, Codex) with the Cortex Code router skill."
      echo ""
      echo "Usage: install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --check, -c      Check installation status without installing"
      echo "  --update, -u     Re-install skills (overwrite existing)"
      echo "  --with-claude    Also install Claude Code CLI and Claude-to-Cortex router skill"
      echo "  --with-cursor    Install Cortex Code skill + routing rule for Cursor"
      echo "  --with-codex     Install cortexcode-tool CLI for Codex"
      echo "  --with-all       Install integrations for all supported agents"
      echo "  --help, -h       Show this help"
      exit 0
      ;;
    *)
      die "Unknown option: $1 (use --help)"
      ;;
  esac
done

# --with-all enables all agent integrations
if $WITH_ALL; then
  WITH_CLAUDE=true
  WITH_CURSOR=true
  WITH_CODEX=true
fi

# ─── Execute ────────────────────────────────────────────────

echo ""
echo -e "${B}Snowflake AI Kit — Installer${N}"
echo "──────────────────────────────"
echo ""

if $CHECK_ONLY; then
  step "Checking installation status..."
  check_cmd snow   && ok "Snowflake CLI (snow) installed"   || warn "Snowflake CLI (snow) not found"
  check_cmd cortex && ok "Cortex Code CLI (cortex) installed" || warn "Cortex Code CLI (cortex) not found"
  check_cmd claude && ok "Claude Code CLI (claude) installed" || warn "Claude Code CLI (claude) not found"
  [ -f "${SKILL_DIR}/SKILL.md" ] && ok "Claude Code router skill installed" || warn "Claude Code router skill not found"
  [ -f "$HOME/.cursor/skills-cursor/cortex-code/SKILL.md" ] && ok "Cursor skill installed" || warn "Cursor skill not found"
  [ -f "$HOME/.cursor/rules/cortex-snowflake-routing.mdc" ] && ok "Cursor routing rule installed" || warn "Cursor routing rule not found"
  check_cmd cortexcode-tool && ok "cortexcode-tool installed (Codex/CLI)" || warn "cortexcode-tool not found (Codex/CLI)"
  check_snowflake_auth || true
  echo ""
  exit 0
fi

step "Installing CLIs..."
install_snowflake_cli
install_cortex_code_cli

# Claude Code CLI is opt-in (but if already installed, just ensure skill is there)
install_claude=false
if $WITH_CLAUDE; then
  install_claude=true
elif check_cmd claude; then
  install_claude=true
elif [ -t 0 ]; then
  echo ""
  msg "Claude Code CLI is optional (requires Node.js + Anthropic API key)."
  printf "  Install Claude Code CLI and router skill? (y/N) "
  read -r answer
  case "$answer" in
    [Yy]*) install_claude=true ;;
  esac
fi

if $install_claude; then
  install_claude_code_cli || true

  step "Installing Claude Code router skill..."
  install_skills || true
else
  msg "Skipping Claude Code CLI (use --with-claude to include)"
fi

# Cursor integration (opt-in)
if $WITH_CURSOR; then
  step "Installing Cursor integration..."
  install_cursor_skill || true
fi

# Codex integration (opt-in)
if $WITH_CODEX; then
  step "Installing Codex integration..."
  install_codex_tool || true
fi

step "Checking Snowflake connection..."
check_snowflake_auth || true

echo ""
echo -e "${G}All done!${N}"
echo ""
echo "Next steps:"
echo "  snow --version       # Verify Snowflake CLI"
echo "  cortex --version     # Verify Cortex Code CLI"
if $install_claude; then
  echo "  claude --version     # Verify Claude Code CLI"
fi
if $WITH_CURSOR; then
  echo "  # Restart Cursor to activate the routing rule"
fi
if $WITH_CODEX; then
  echo "  cortexcode-tool --version  # Verify Codex CLI tool"
fi
echo "  cortex               # Start Cortex Code"
echo ""
