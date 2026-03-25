#!/usr/bin/env bash
#
# Snowflake AI Kit — Unified Installer
#
# One command to install skills, builder apps, or both.
# Also installs Snowflake CLI (snow) and Cortex Code CLI (cortex) if missing.
#
# Usage:
#   # Interactive (prompts for what to install)
#   bash <(curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.sh)
#
#   # Skills only (delegates to install_skills.sh)
#   bash <(curl -sSL .../install.sh) --skills-only
#
#   # Skills + a builder app
#   bash <(curl -sSL .../install.sh) --app claude-agent
#   bash <(curl -sSL .../install.sh) --app cortex-agent
#
#   # Everything (skills + all builder apps)
#   bash <(curl -sSL .../install.sh) --all
#
#   # Pass-through to install_skills.sh
#   bash <(curl -sSL .../install.sh) --list
#   bash <(curl -sSL .../install.sh) --agent cursor
#

set -e

# Colors
G='\033[0;32m' Y='\033[1;33m' R='\033[0;31m' B='\033[1m' D='\033[2m' N='\033[0m'

REPO_URL="https://github.com/Snowflake-Labs/snowflake-ai-kit.git"
REPO_RAW="https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main"

msg()  { echo -e "  $*"; }
ok()   { echo -e "  ${G}✓${N} $*"; }
warn() { echo -e "  ${Y}!${N} $*"; }
die()  { echo -e "  ${R}✗${N} $*" >&2; exit 1; }
step() { echo -e "\n${B}$*${N}"; }

# ─── Prereq checks ─────────────────────────────────────────

check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    return 1
  fi
  return 0
}

check_prereqs() {
  local missing=""
  check_cmd python3 || missing="$missing python3"
  check_cmd node    || missing="$missing node"
  check_cmd npm     || missing="$missing npm"

  if [[ -n "$missing" ]]; then
    warn "Missing prerequisites:$missing"
    return 1
  fi
  ok "Prerequisites OK (python3, node, npm)"
  return 0
}

check_snowflake_auth() {
  # Check for Snowflake connection config
  if [[ -f "$HOME/.snowflake/connections.toml" ]]; then
    ok "Snowflake config found (~/.snowflake/connections.toml)"
    return 0
  elif [[ -n "$SNOWFLAKE_HOST" ]] || [[ -n "$SNOWFLAKE_ACCOUNT" ]]; then
    ok "Snowflake config found (environment variables)"
    return 0
  else
    warn "No Snowflake config detected."
    msg "  You'll need one of:"
    msg "    - ~/.snowflake/connections.toml (recommended)"
    msg "    - SNOWFLAKE_HOST + SNOWFLAKE_ACCOUNT + SNOWFLAKE_PAT env vars"
    msg "  See: https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials"
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
  die "Could not install Snowflake CLI. Install manually: https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation"
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
  die "Could not install Cortex Code CLI. Install manually: https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli"
}

# ─── Detect repo root ──────────────────────────────────────

find_repo_root() {
  # Check if we're inside the repo already
  if [[ -d "snowflake-skills" ]] && [[ -f "README.md" ]]; then
    echo "."
    return 0
  fi

  # Check if repo is cloned in current directory
  if [[ -d "snowflake-ai-kit/snowflake-skills" ]]; then
    echo "snowflake-ai-kit"
    return 0
  fi

  return 1
}

ensure_repo() {
  local root
  if root=$(find_repo_root); then
    REPO_ROOT="$root"
    ok "Found repo at $REPO_ROOT"
  else
    step "Cloning snowflake-ai-kit..."
    if check_cmd git; then
      git clone "$REPO_URL" snowflake-ai-kit 2>/dev/null || die "Failed to clone repo"
      REPO_ROOT="snowflake-ai-kit"
      ok "Cloned to ./snowflake-ai-kit"
    else
      die "git is required to install builder apps. Install git or use --skills-only."
    fi
  fi
}

# ─── Install skills ────────────────────────────────────────

install_skills() {
  local root
  if root=$(find_repo_root); then
    bash "$root/snowflake-skills/install_skills.sh" "$@"
  else
    # Download and run remotely
    curl -sSL "$REPO_RAW/snowflake-skills/install_skills.sh" | bash -s -- "$@"
  fi
}

# ─── Install builder app ───────────────────────────────────

install_app() {
  local app="$1"
  local app_dir="$REPO_ROOT/builder-apps/$app"

  if [[ ! -d "$app_dir" ]]; then
    die "App not found: $app_dir"
  fi

  step "Setting up $app..."

  # Check prereqs (fail hard — these are required for app setup)
  check_prereqs || die "Install missing prerequisites and try again."
  check_snowflake_auth || true  # warn but continue — user can configure later

  # Create .env.local
  if [[ ! -f "$app_dir/.env.local" ]]; then
    cp "$app_dir/.env.example" "$app_dir/.env.local"
    ok "Created .env.local from .env.example"
  else
    msg ".env.local already exists, skipping"
  fi

  # Install Python deps
  msg "Installing Python dependencies..."
  if check_cmd uv; then
    (cd "$app_dir" && uv pip install -r requirements.txt)
  else
    (cd "$app_dir" && pip install -r requirements.txt)
  fi

  # App-specific: claude-agent has editable packages
  if [[ "$app" == "claude-agent" ]]; then
    if check_cmd uv; then
      (cd "$app_dir" && uv pip install -e packages/snowflake-tools-core -e packages/snowflake-mcp-server)
    else
      (cd "$app_dir" && pip install -e packages/snowflake-tools-core -e packages/snowflake-mcp-server)
    fi
  fi
  ok "Python dependencies installed"

  # Install Node deps
  msg "Installing Node dependencies..."
  (cd "$app_dir/client" && npm install)
  ok "Node dependencies installed"

  # App-specific: claude-agent needs projects dir
  if [[ "$app" == "claude-agent" ]]; then
    mkdir -p "$app_dir/projects"
  fi

  # Done — print next steps
  echo ""
  ok "$app is ready"
  echo ""
  if [[ "$app" == "cortex-agent" ]]; then
    msg "Next steps:"
    msg "  1. Run ${B}setup.sql${N} in a Snowflake worksheet to create sample data + agent"
    msg "  2. Edit ${B}$app_dir/.env.local${N} with your Snowflake credentials"
    msg "  3. Start the app: ${B}cd $app_dir && ./scripts/dev.sh${N}"
  elif [[ "$app" == "claude-agent" ]]; then
    msg "Next steps:"
    msg "  1. Edit ${B}$app_dir/.env.local${N} with your Snowflake + Anthropic credentials"
    msg "  2. Start the app: ${B}cd $app_dir && ./scripts/dev.sh${N}"
  fi
}

# ─── Interactive mode ───────────────────────────────────────

interactive() {
  echo ""
  echo -e "${B}Snowflake AI Kit — Installer${N}"
  echo "──────────────────────────────"
  echo ""

  # Upfront prereq check
  step "Checking prerequisites..."
  local has_prereqs=true
  check_prereqs || has_prereqs=false
  check_snowflake_auth || true

  # Install Snowflake CLIs if missing
  step "Installing Snowflake CLI and Cortex Code CLI (if needed)..."
  install_snowflake_cli
  install_cortex_code_cli
  echo ""

  echo "What would you like to install?"
  echo ""
  echo -e "  ${B}1${N}  Skills only — add Snowflake skills to your AI coding agent"
  if [[ "$has_prereqs" == "true" ]]; then
    echo -e "  ${B}2${N}  Skills + Claude Agent App — needs Anthropic API key"
    echo -e "  ${B}3${N}  Skills + Cortex Agent App — no external API key needed"
    echo -e "  ${B}4${N}  Everything — skills + all builder apps"
  else
    echo -e "  ${D}2  Skills + Claude Agent App (requires python3, node, npm)${N}"
    echo -e "  ${D}3  Skills + Cortex Agent App (requires python3, node, npm)${N}"
    echo -e "  ${D}4  Everything (requires python3, node, npm)${N}"
  fi
  echo ""
  printf "  Choose [1-4]: "
  read -r choice

  case "$choice" in
    1)
      install_skills
      ;;
    2)
      install_skills
      ensure_repo
      install_app "claude-agent"
      ;;
    3)
      install_skills
      ensure_repo
      install_app "cortex-agent"
      ;;
    4)
      install_skills
      ensure_repo
      install_app "claude-agent"
      install_app "cortex-agent"
      ;;
    *)
      die "Invalid choice: $choice"
      ;;
  esac
}

# ─── Parse arguments ────────────────────────────────────────

MODE=""
APP=""
PASSTHROUGH_ARGS=""

# Collect args — some are for us, some pass through to install_skills.sh
while [ $# -gt 0 ]; do
  case $1 in
    --skills-only|-s)
      MODE="skills"
      shift
      ;;
    --app)
      MODE="app"
      APP="$2"
      if [[ "$APP" != "claude-agent" ]] && [[ "$APP" != "cortex-agent" ]]; then
        die "Unknown app: $APP (choose: claude-agent, cortex-agent)"
      fi
      shift 2
      ;;
    --all)
      MODE="all"
      shift
      ;;
    --list|-l)
      # Pass through to install_skills.sh
      install_skills --list
      exit 0
      ;;
    --help|-h)
      echo "Snowflake AI Kit — Unified Installer"
      echo ""
      echo "Installs Snowflake CLI (snow) and Cortex Code CLI (cortex) automatically,"
      echo "then sets up skills, builder apps, or both."
      echo ""
      echo "Usage: install.sh [OPTIONS]"
      echo ""
      echo "Modes:"
      echo "  (no flags)             Interactive — prompts for what to install"
      echo "  --skills-only, -s      Install skills only (no builder apps)"
      echo "  --app NAME             Install skills + a builder app (claude-agent or cortex-agent)"
      echo "  --all                  Install skills + all builder apps"
      echo ""
      echo "Pass-through options (forwarded to install_skills.sh):"
      echo "  --agent, -a NAME       Install for specific agent (cursor, windsurf, claude, gemini, cortex)"
      echo "  --external, -e URL SK  Install skills from an external repo"
      echo "  --list, -l             List available skills"
      echo ""
      echo "Examples:"
      echo "  install.sh                          # Interactive"
      echo "  install.sh --skills-only            # Just skills, auto-detect agents"
      echo "  install.sh --app cortex-agent       # Skills + Cortex Agent app"
      echo "  install.sh --all --agent cursor     # Everything, skills for Cursor only"
      echo "  install.sh --list                   # List available skills"
      exit 0
      ;;
    *)
      # Collect remaining args to pass through to install_skills.sh
      PASSTHROUGH_ARGS="$PASSTHROUGH_ARGS $1"
      shift
      ;;
  esac
done

# ─── Execute ────────────────────────────────────────────────

if [[ -z "$MODE" ]] && [[ -z "$PASSTHROUGH_ARGS" ]]; then
  interactive
  exit 0
fi

# If there are pass-through args but no explicit mode, treat as skills-only
if [[ -z "$MODE" ]] && [[ -n "$PASSTHROUGH_ARGS" ]]; then
  MODE="skills"
fi

# Install Snowflake CLIs if missing
step "Installing Snowflake CLI and Cortex Code CLI (if needed)..."
install_snowflake_cli
install_cortex_code_cli

case "$MODE" in
  skills)
    install_skills $PASSTHROUGH_ARGS
    ;;
  app)
    install_skills $PASSTHROUGH_ARGS
    ensure_repo
    install_app "$APP"
    ;;
  all)
    install_skills $PASSTHROUGH_ARGS
    ensure_repo
    install_app "claude-agent"
    install_app "cortex-agent"
    ;;
esac

echo ""
echo -e "${G}All done!${N}"
echo ""
