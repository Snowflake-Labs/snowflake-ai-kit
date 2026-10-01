#!/usr/bin/env bash
#
# Snowflake AI Kit — Installer
#
# Installs Snowflake CLI (snow) and Cortex Code CLI (cortex).
# Optionally installs Claude Code CLI and/or OpenAI Codex CLI,
# then verifies your Snowflake connection.
#
# Usage:
#   bash install.sh
#   bash install.sh --check
#   bash install.sh --with-claude --with-codex --with-opencode
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
    msg "  Docs: https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials"
    return 1
  fi
}

# ─── CLI installers ──────────────────────────────────────────

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
  if check_cmd npm; then
    npm install -g @anthropic-ai/claude-code 2>/dev/null && ok "Claude Code CLI installed via npm" && return 0
  fi
  warn "Could not install Claude Code CLI (requires Node.js + npm)."
  msg "  Install manually: npm install -g @anthropic-ai/claude-code"
  return 1
}

install_codex_cli() {
  if check_cmd codex; then
    ok "OpenAI Codex CLI (codex) already installed"
    return 0
  fi

  msg "Installing OpenAI Codex CLI..."
  if check_cmd npm; then
    npm install -g @openai/codex 2>/dev/null && ok "OpenAI Codex CLI installed via npm" && return 0
  fi
  warn "Could not install OpenAI Codex CLI (requires Node.js + npm)."
  msg "  Install manually: npm install -g @openai/codex"
  return 1
}

install_opencode_cli() {
  if check_cmd opencode; then
    ok "opencode CLI already installed"
    return 0
  fi

  msg "Installing opencode CLI..."
  if check_cmd npm; then
    npm install -g opencode-ai 2>/dev/null && ok "opencode CLI installed via npm" && return 0
  fi
  warn "Could not install opencode CLI (requires Node.js + npm)."
  msg "  Install manually: npm install -g opencode-ai"
  return 1
}

# Copy the Snowflake Cortex Code plugin to the global opencode config dir
install_opencode_plugin() {
  local SCRIPT_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local PLUGIN_SRC="$SCRIPT_DIR/plugins/cortex-code"

  # Resolve opencode global config directory (respects XDG_CONFIG_HOME)
  local OPENCODE_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"

  # --- plugin TS file ---
  mkdir -p "$OPENCODE_CONFIG/plugins"
  cp "$PLUGIN_SRC/.opencode/plugins/snowflake-cortex.ts" \
     "$OPENCODE_CONFIG/plugins/snowflake-cortex.ts"
  ok "opencode plugin installed ($OPENCODE_CONFIG/plugins/snowflake-cortex.ts)"

  # --- router scripts (needed by the TS plugin via import.meta.dir) ---
  local ROUTER_DEST="$OPENCODE_CONFIG/plugins/cortex-code-router/scripts/router"
  mkdir -p "$ROUTER_DEST"
  cp -r "$PLUGIN_SRC/scripts/router/." "$ROUTER_DEST/"
  ok "opencode router scripts installed ($OPENCODE_CONFIG/plugins/cortex-code-router/scripts/router/)"

  # --- rules file (global, applies to all opencode sessions) ---
  mkdir -p "$OPENCODE_CONFIG/rules"
  cp "$PLUGIN_SRC/.opencode/rules/snowflake.md" \
     "$OPENCODE_CONFIG/rules/snowflake.md"
  ok "opencode routing rules installed ($OPENCODE_CONFIG/rules/snowflake.md)"
}

# ─── Parse arguments ────────────────────────────────────────

CHECK_ONLY=false
WITH_CLAUDE=false
WITH_CODEX=false
WITH_OPENCODE=false

while [ $# -gt 0 ]; do
  case $1 in
    --check|-c)
      CHECK_ONLY=true
      shift
      ;;
    --with-claude)
      WITH_CLAUDE=true
      shift
      ;;
    --with-codex)
      WITH_CODEX=true
      shift
      ;;
    --with-opencode)
      WITH_OPENCODE=true
      shift
      ;;
    --help|-h)
      echo "Snowflake AI Kit — Installer"
      echo ""
      echo "Installs Snowflake CLI (snow) and Cortex Code CLI (cortex)."
      echo "Optionally installs Claude Code CLI and/or OpenAI Codex CLI."
      echo ""
      echo "Usage: install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --check, -c      Check installation status without installing"
      echo "  --with-claude    Also install Claude Code CLI"
      echo "  --with-codex     Also install OpenAI Codex CLI"
      echo "  --with-opencode  Also install opencode CLI and Snowflake plugin"
      echo "  --help, -h       Show this help"
      exit 0
      ;;
    *)
      die "Unknown option: $1 (use --help)"
      ;;
  esac
done

# ─── Execute ────────────────────────────────────────────────

echo ""
echo -e "${B}Snowflake AI Kit — Installer${N}"
echo "──────────────────────────────"
echo ""

if $CHECK_ONLY; then
  step "Checking installation status..."
  check_cmd snow     && ok "Snowflake CLI (snow) installed"        || warn "Snowflake CLI (snow) not found"
  check_cmd cortex   && ok "Cortex Code CLI (cortex) installed"    || warn "Cortex Code CLI (cortex) not found"
  check_cmd claude   && ok "Claude Code CLI (claude) installed"    || warn "Claude Code CLI (claude) not found"
  check_cmd codex    && ok "OpenAI Codex CLI (codex) installed"    || warn "OpenAI Codex CLI (codex) not found"
  check_cmd opencode && ok "opencode CLI installed"               || warn "opencode CLI not found"
  check_snowflake_auth || true
  echo ""
  exit 0
fi

step "Installing core CLIs..."
install_snowflake_cli
install_cortex_code_cli

# Optional: Claude Code CLI
if $WITH_CLAUDE || check_cmd claude; then
  step "Installing Claude Code CLI..."
  install_claude_code_cli || true
fi

# Optional: OpenAI Codex CLI
if $WITH_CODEX || check_cmd codex; then
  step "Installing OpenAI Codex CLI..."
  install_codex_cli || true
fi

# Optional: opencode CLI + plugin
if $WITH_OPENCODE || check_cmd opencode; then
  step "Installing opencode CLI and Snowflake plugin..."
  install_opencode_cli || true
  install_opencode_plugin || warn "Could not install opencode plugin (run: bash install.sh --with-opencode from the repo root)"
fi

# Plugin setup: add marketplace sources if the agent CLIs are present
step "Setting up plugins..."

if check_cmd codex; then
  if codex plugin marketplace list 2>/dev/null | grep -q "snowflake-ai-kit"; then
    ok "Codex marketplace already configured"
  else
    codex plugin marketplace add Snowflake-Labs/snowflake-ai-kit 2>/dev/null \
      && ok "Codex marketplace added (Snowflake-Labs/snowflake-ai-kit)" \
      || warn "Could not add Codex marketplace. Run: codex plugin marketplace add Snowflake-Labs/snowflake-ai-kit"
  fi
  if codex plugin list 2>/dev/null | grep -q "snowflake-cortex-code.*installed"; then
    ok "Codex plugin already installed"
  else
    codex plugin add snowflake-cortex-code@snowflake-ai-kit 2>/dev/null \
      && ok "Codex plugin installed (snowflake-cortex-code)" \
      || warn "Could not install Codex plugin. Run: codex plugin add snowflake-cortex-code@snowflake-ai-kit"
  fi
fi

if check_cmd claude; then
  if claude plugin marketplace list 2>/dev/null | grep -q "claude-plugins-official"; then
    ok "Claude Code marketplace already configured"
  else
    claude plugin marketplace add anthropics/claude-plugins-official 2>/dev/null \
      && ok "Claude Code marketplace added (anthropics/claude-plugins-official)" \
      || warn "Could not add Claude Code marketplace. Run: claude plugin marketplace add anthropics/claude-plugins-official"
  fi
  if claude plugin list 2>/dev/null | grep -q "snowflake-cortex-code"; then
    ok "Claude Code plugin already installed"
  else
    claude plugin install snowflake-cortex-code 2>/dev/null \
      && ok "Claude Code plugin installed (snowflake-cortex-code)" \
      || warn "Could not install Claude Code plugin. Run: claude plugin install snowflake-cortex-code"
  fi
fi

if ! check_cmd codex && ! check_cmd claude && ! check_cmd opencode; then
  msg "  No agent CLI found. Install one with --with-claude, --with-codex, or --with-opencode"
fi

step "Checking Snowflake connection..."
check_snowflake_auth || true

echo ""
echo -e "${G}All done!${N}"
echo ""
echo "Next steps:"
echo "  cortex               # Start Cortex Code (interactive AI assistant)"
echo "  snow --version       # Verify Snowflake CLI"
echo ""
