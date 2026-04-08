#!/usr/bin/env bash
#
# Snowflake AI Kit — CLI Installer
#
# Installs Snowflake CLI (snow) and Cortex Code CLI (cortex) if not already present,
# then verifies your Snowflake connection.
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

  if git clone --depth 1 "$REPO_URL" "$tmp_dir/repo" 2>/dev/null; then
    src="$tmp_dir/repo/agent-to-agent-skills/claude-cortex-code-router"

    if [ ! -d "$src" ]; then
      warn "Skill directory not found in cloned repo."
      msg "  This may happen if the skill hasn't been merged to main yet."
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
    for f in cortex-cli-reference.md routing-examples.md troubleshooting-guide.md; do
      cp "$src/references/$f" "$SKILL_DIR/references/"
    done

    # Optional docs
    for f in CHANGELOG.md MIGRATION.md SECURITY.md SECURITY_GUIDE.md; do
      [ -f "$src/$f" ] && cp "$src/$f" "$SKILL_DIR/"
    done

    ok "Claude-to-Cortex Code Router skill installed to ${SKILL_DIR}/"
    return 0
  fi

  warn "Could not clone repo (SSH access required for Snowflake-Labs members)."
  msg "  Manual install: git clone $REPO_URL && copy agent-to-agent-skills/claude-cortex-code-router/ to $SKILL_DIR/"
  return 1
}

# ─── Parse arguments ────────────────────────────────────────

CHECK_ONLY=false
UPDATE=false

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
    --help|-h)
      echo "Snowflake AI Kit — CLI Installer"
      echo ""
      echo "Installs Snowflake CLI (snow), Cortex Code CLI (cortex), and skills."
      echo ""
      echo "Usage: install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --check, -c    Check installation status without installing"
      echo "  --update, -u   Re-install skills (overwrite existing)"
      echo "  --help, -h     Show this help"
      exit 0
      ;;
    *)
      die "Unknown option: $1 (use --help)"
      ;;
  esac
done

# ─── Execute ────────────────────────────────────────────────

echo ""
echo -e "${B}Snowflake AI Kit — CLI Installer${N}"
echo "──────────────────────────────────"
echo ""

if $CHECK_ONLY; then
  step "Checking installation status..."
  check_cmd snow   && ok "Snowflake CLI (snow) installed"   || warn "Snowflake CLI (snow) not found"
  check_cmd cortex && ok "Cortex Code CLI (cortex) installed" || warn "Cortex Code CLI (cortex) not found"
  [ -f "${SKILL_DIR}/SKILL.md" ] && ok "Claude-to-Cortex Code Router skill installed" || warn "Claude-to-Cortex Code Router skill not found"
  check_snowflake_auth || true
  echo ""
  exit 0
fi

step "Installing Snowflake CLI and Cortex Code CLI..."
install_snowflake_cli
install_cortex_code_cli

step "Installing skills..."
install_skills || true

step "Checking Snowflake connection..."
check_snowflake_auth || true

echo ""
echo -e "${G}All done!${N}"
echo ""
echo "Next steps:"
echo "  snow --version       # Verify Snowflake CLI"
echo "  cortex --version     # Verify Cortex Code CLI"
echo "  cortex               # Start Cortex Code"
echo ""
