#!/usr/bin/env bash
#
# Snowflake AI Kit — Skills Installer
#
# Installs Snowflake skills for your AI coding agent.
#
# Usage:
#   # Install all skills for all supported agents
#   curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/snowflake-skills/install_skills.sh | bash
#
#   # Install for a specific agent (cursor, windsurf, claude, gemini, cortex)
#   curl -sSL .../install_skills.sh | bash -s -- --agent cursor
#   curl -sSL .../install_skills.sh | bash -s -- --agent gemini
#
#   # Install specific skills only
#   curl -sSL .../install_skills.sh | bash -s -- docker-dev-setup drizzle-orm-setup
#
#   # Install skills from an external repo
#   curl -sSL .../install_skills.sh | bash -s -- --external https://raw.githubusercontent.com/org/repo/main skill-a skill-b
#
#   # List available skills
#   curl -sSL .../install_skills.sh | bash -s -- --list
#

set -e

# Colors
G='\033[0;32m' Y='\033[1;33m' R='\033[0;31m' B='\033[1m' N='\033[0m'

REPO_RAW="https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main"
SNOWFLAKE_SKILLS_PATH="snowflake-skills"
GENERAL_SKILLS_PATH="general-skills"

# Snowflake-specific skills
SNOWFLAKE_SKILLS="cortex-agents cortex-ai-pipeline cortex-mcp-server cortex-search-rag data-product-sharing dynamic-tables-pipeline iceberg-tables ml-model-registry snowflake-docs snowflake-postgres snowpipe-streaming-java snowpipe-streaming-python ssis-to-dbt-replatform-migration streamlit-in-snowflake tasks-and-streams"

# General-purpose skills (not Snowflake-specific)
GENERAL_SKILLS="docker-dev-setup drizzle-orm-setup supabase-auth-rls"

# External skills (fetched from other repos)
# Format: EXTERNAL_<NAME>_RAW_URL, EXTERNAL_<NAME>_SKILLS
# To add an external source, define the URL and skill list, then add skills to EXTERNAL_SKILLS.
# Example:
#   EXTERNAL_MYORG_RAW_URL="https://raw.githubusercontent.com/myorg/skills/main"
#   EXTERNAL_MYORG_SKILLS="my-skill-a my-skill-b"
#   EXTERNAL_SKILLS="$EXTERNAL_MYORG_SKILLS"
EXTERNAL_SKILLS=""

# All available skills
ALL_SKILLS="$SNOWFLAKE_SKILLS $GENERAL_SKILLS $EXTERNAL_SKILLS"

msg()  { echo -e "  $*"; }
ok()   { echo -e "  ${G}✓${N} $*"; }
warn() { echo -e "  ${Y}!${N} $*"; }
die()  { echo -e "  ${R}✗${N} $*" >&2; exit 1; }

get_skill_description() {
  case "$1" in
    "docker-dev-setup") echo "Containerize apps with Dockerfile, Compose, and Dev Containers" ;;
    "drizzle-orm-setup") echo "Scaffold Drizzle ORM with TypeScript schema and migrations" ;;
    "supabase-auth-rls") echo "Scaffold Supabase with schema, RLS policies, and auth" ;;
    "cortex-agents") echo "Create Cortex Agents with Analyst, Search, and custom tools" ;;
    "cortex-ai-pipeline") echo "Build AI enrichment pipelines with Cortex AI Functions (classify, sentiment, summarize)" ;;
    "cortex-mcp-server") echo "Create managed MCP servers to expose Snowflake tools to AI clients" ;;
    "cortex-search-rag") echo "Build RAG pipelines with Cortex Search and AI_COMPLETE" ;;
    "data-product-sharing") echo "Share data products via secure shares, listings, and the Snowflake Marketplace" ;;
    "dynamic-tables-pipeline") echo "Build declarative data pipelines with Dynamic Tables (medallion architecture)" ;;
    "iceberg-tables") echo "Create and manage Apache Iceberg tables on Snowflake" ;;
    "ml-model-registry") echo "Train, register, and deploy ML models with Snowflake Model Registry" ;;
    "snowflake-docs") echo "Snowflake documentation reference via llms.txt index" ;;
    "snowflake-postgres") echo "Create and manage fully managed Postgres instances on Snowflake" ;;
    "snowpipe-streaming-java") echo "Stream data into Snowflake via Java Snowpipe Streaming SDK" ;;
    "snowpipe-streaming-python") echo "Stream data into Snowflake via Python Snowpipe Streaming SDK" ;;
    "ssis-to-dbt-replatform-migration") echo "Migrate SSIS packages to dbt + Snowflake" ;;
    "streamlit-in-snowflake") echo "Deploy Streamlit apps to Snowflake with warehouse or container runtimes" ;;
    "tasks-and-streams") echo "Build CDC pipelines with Snowflake Streams and Tasks" ;;
    *) echo "Unknown skill" ;;
  esac
}

# Get extra files to download for each skill (besides SKILL.md and README.md)
get_skill_files() {
  case "$1" in
    "docker-dev-setup") echo "references/compose-patterns.md references/dockerfile-patterns.md references/troubleshooting.md templates/compose.yaml templates/devcontainer.json templates/Dockerfile.go templates/Dockerfile.node templates/Dockerfile.python templates/dockerignore" ;;
    "drizzle-orm-setup") echo "references/query-patterns.md references/schema-patterns.md references/troubleshooting.md templates/db.ts templates/drizzle.config.ts templates/schema.ts" ;;
    "supabase-auth-rls") echo "references/auth-helpers.md references/rls-patterns.md references/troubleshooting.md templates/migration-rls.sql templates/migration-schema.sql" ;;
    "cortex-agents") echo "templates/setup.sql templates/create-agent.sql templates/invoke-agent.sql" ;;
    "cortex-ai-pipeline") echo "templates/setup.sql templates/enrich-pipeline.sql templates/batch-insights.sql" ;;
    "cortex-mcp-server") echo "templates/setup.sql templates/create-mcp-server.sql templates/connect-client.sql" ;;
    "cortex-search-rag") echo "templates/setup.sql templates/search-service.sql templates/rag-query.sql" ;;
    "data-product-sharing") echo "templates/setup.sql templates/create-share.sql templates/create-listing.sql templates/consumer-access.sql" ;;
    "dynamic-tables-pipeline") echo "templates/setup.sql templates/bronze.sql templates/silver.sql templates/gold.sql" ;;
    "iceberg-tables") echo "templates/setup.sql templates/snowflake-managed.sql templates/external-catalog.sql" ;;
    "ml-model-registry") echo "templates/setup.sql templates/train-and-register.py templates/deploy-service.py" ;;
    "snowflake-docs") echo "" ;;
    "snowflake-postgres") echo "templates/setup.sql templates/sample-data.sql" ;;
    "snowpipe-streaming-java") echo "" ;;
    "snowpipe-streaming-python") echo "src/config_manager.py src/data_generator.py src/models.py src/parallel_streaming_orchestrator.py src/reconciliation_manager.py src/snowpipe_streaming_manager.py src/streaming_app.py" ;;
    "ssis-to-dbt-replatform-migration") echo "references/phase0-briefing.md references/replatform-output-structure.md references/session-diary.md references/snowflake-sql-patterns.md" ;;
    "streamlit-in-snowflake") echo "templates/setup.sql templates/deploy-warehouse.sql templates/deploy-container.sql templates/streamlit_app.py" ;;
    "tasks-and-streams") echo "templates/setup.sql templates/cdc-pipeline.sql templates/task-graph.sql" ;;
    *) echo "" ;;
  esac
}

# Resolve the remote path for a skill (snowflake-skills/ or general-skills/)
get_skill_path() {
  case "$1" in
    docker-dev-setup|drizzle-orm-setup|supabase-auth-rls) echo "$GENERAL_SKILLS_PATH" ;;
    *) echo "$SNOWFLAKE_SKILLS_PATH" ;;
  esac
}

# Resolve the base URL for a skill (supports external repos via EXTERNAL_REPO_URL)
get_skill_url() {
  local skill="$1"
  local skills_path
  skills_path=$(get_skill_path "$skill")

  # External skills use EXTERNAL_REPO_URL (set by --external flag)
  if [[ -n "$EXTERNAL_REPO_URL" ]] && echo "$EXTERNAL_SKILLS" | grep -qw "$skill"; then
    echo "$EXTERNAL_REPO_URL/$skill"
  else
    echo "$REPO_RAW/$skills_path/$skill"
  fi
}

EXTERNAL_REPO_URL=""

show_list() {
  echo ""
  echo -e "${B}Snowflake Skills${N}"
  echo "──────────────────────────────"
  echo ""
  for skill in $SNOWFLAKE_SKILLS; do
    desc=$(get_skill_description "$skill")
    printf "  ${B}%-38s${N} %s\n" "$skill" "$desc"
  done
  echo ""
  echo -e "${B}General-Purpose Skills${N}"
  echo "──────────────────────────────"
  echo ""
  for skill in $GENERAL_SKILLS; do
    desc=$(get_skill_description "$skill")
    printf "  ${B}%-38s${N} %s\n" "$skill" "$desc"
  done
  echo ""
  echo "Install all:     curl -sSL .../install_skills.sh | bash"
  echo "Install one:     curl -sSL .../install_skills.sh | bash -s -- docker-dev-setup"
  echo "External:        curl -sSL .../install_skills.sh | bash -s -- --external https://raw.githubusercontent.com/org/repo/main skill-name"
  echo ""
}

install_skill_for_agent() {
  local skill="$1"
  local agent="$2"
  local target_dir=""
  local ext=""

  case "$agent" in
    cursor)   target_dir=".cursor/rules"; ext=".mdc" ;;
    windsurf) target_dir=".windsurf/rules"; ext=".md" ;;
    claude)   target_dir=".claude/rules"; ext=".md" ;;
    gemini)   target_dir=".gemini"; ext=".md" ;;
    cortex)   target_dir=".cortex/skills/$skill"; ext="" ;;
    *) die "Unknown agent: $agent" ;;
  esac

  local base_url
  base_url=$(get_skill_url "$skill")

  if [[ "$agent" == "cortex" ]]; then
    # Cortex Code: download entire skill directory
    mkdir -p "$target_dir"
    curl -sSL "$base_url/SKILL.md" -o "$target_dir/SKILL.md" 2>/dev/null || {
      warn "Failed to download $skill/SKILL.md"
      return 1
    }
    # Download extra files
    local files
    files=$(get_skill_files "$skill")
    for f in $files; do
      local dir
      dir=$(dirname "$target_dir/$f")
      mkdir -p "$dir"
      curl -sSL "$base_url/$f" -o "$target_dir/$f" 2>/dev/null || true
    done
  else
    # Other agents: copy SKILL.md as a rule file
    mkdir -p "$target_dir"
    local filename="${skill}${ext}"
    curl -sSL "$base_url/SKILL.md" -o "$target_dir/$filename" 2>/dev/null || {
      warn "Failed to download $skill for $agent"
      return 1
    }
  fi
}

# ─── Parse arguments ────────────────────────────────────────

AGENT=""
SELECTED_SKILLS=""
LIST_ONLY=false

while [ $# -gt 0 ]; do
  case $1 in
    --agent|-a) AGENT="$2"; shift 2 ;;
    --list|-l)  LIST_ONLY=true; shift ;;
    --external|-e)
      # External skill sourcing: --external BASE_RAW_URL skill1 [skill2 ...]
      EXTERNAL_REPO_URL="$2"; shift 2
      # Consume all remaining non-flag args as external skill names
      while [[ $# -gt 0 ]] && [[ "$1" != --* ]]; do
        EXTERNAL_SKILLS="$EXTERNAL_SKILLS $1"
        ALL_SKILLS="$ALL_SKILLS $1"
        SELECTED_SKILLS="$SELECTED_SKILLS $1"
        shift
      done
      ;;
    --help|-h)
      echo "Snowflake AI Kit — Skills Installer"
      echo ""
      echo "Usage: install_skills.sh [OPTIONS] [SKILL ...]"
      echo ""
      echo "Options:"
      echo "  --agent, -a NAME       Install for specific agent (cursor, windsurf, claude, gemini, cortex)"
      echo "  --external, -e URL SK  Install skills from an external repo (URL = raw base URL)"
      echo "  --list, -l             List available skills"
      echo "  --help, -h             Show this help"
      echo ""
      echo "Agents:"
      echo "  cursor     .cursor/rules/*.mdc"
      echo "  windsurf   .windsurf/rules/*.md"
      echo "  claude     .claude/rules/*.md"
      echo "  gemini     .gemini/*.md"
      echo "  cortex     .cortex/skills/<name>/SKILL.md"
      echo ""
      echo "If no agent is specified, installs for all detected agents."
      echo "If no skills are specified, installs all available skills."
      echo ""
      echo "External skill sourcing:"
      echo "  install_skills.sh --external https://raw.githubusercontent.com/org/repo/main skill-a skill-b"
      echo "  Fetches SKILL.md from <URL>/<skill>/SKILL.md for each listed skill."
      exit 0
      ;;
    -*) die "Unknown option: $1 (use --help)" ;;
    *)  SELECTED_SKILLS="$SELECTED_SKILLS $1"; shift ;;
  esac
done

if $LIST_ONLY; then
  show_list
  exit 0
fi

# Default to all skills if none specified
SELECTED_SKILLS="${SELECTED_SKILLS:-$ALL_SKILLS}"
SELECTED_SKILLS=$(echo "$SELECTED_SKILLS" | xargs) # trim

# Detect which agents to install for
AGENTS=""
if [[ -n "$AGENT" ]]; then
  AGENTS="$AGENT"
else
  # Auto-detect based on existing config directories or common agents
  [[ -d ".cursor" ]] || [[ -d ".cursor/rules" ]] && AGENTS="$AGENTS cursor"
  [[ -d ".windsurf" ]] || [[ -d ".windsurf/rules" ]] && AGENTS="$AGENTS windsurf"
  [[ -d ".claude" ]] || [[ -d ".claude/rules" ]] && AGENTS="$AGENTS claude"
  [[ -d ".gemini" ]] && AGENTS="$AGENTS gemini"

  # If nothing detected, default to common agents
  if [[ -z "$AGENTS" ]]; then
    AGENTS="cursor windsurf claude gemini"
  fi
fi

AGENTS=$(echo "$AGENTS" | xargs)

# ─── Install ────────────────────────────────────────────────

echo ""
echo -e "${B}Snowflake AI Kit — Skills Installer${N}"
echo "────────────────────────────────────"
echo ""

skill_count=0
for skill in $SELECTED_SKILLS; do
  # Validate skill name
  if ! echo "$ALL_SKILLS" | grep -qw "$skill"; then
    warn "Unknown skill: $skill (skipping)"
    continue
  fi

  for agent in $AGENTS; do
    install_skill_for_agent "$skill" "$agent" && ok "$skill → $agent" || true
  done
  ((skill_count++)) || true
done

echo ""
if [[ $skill_count -gt 0 ]]; then
  echo -e "${G}Done!${N} Installed $skill_count skill(s) for: $AGENTS"
  echo ""
  echo "Skills are ready to use. Your AI coding agent will load them automatically."
else
  warn "No skills were installed."
fi
echo ""
