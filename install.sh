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

# ─── Parse arguments ────────────────────────────────────────

CHECK_ONLY=false

while [ $# -gt 0 ]; do
  case $1 in
    --check|-c)
      CHECK_ONLY=true
      shift
      ;;
    --help|-h)
      echo "Snowflake AI Kit — CLI Installer"
      echo ""
      echo "Installs Snowflake CLI (snow) and Cortex Code CLI (cortex)."
      echo ""
      echo "Usage: install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --check, -c    Check installation status without installing"
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
  check_snowflake_auth || true
  echo ""
  exit 0
fi

step "Installing Snowflake CLI and Cortex Code CLI..."
install_snowflake_cli
install_cortex_code_cli

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
