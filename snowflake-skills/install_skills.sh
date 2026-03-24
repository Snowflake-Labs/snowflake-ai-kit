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
#   # Install for a specific agent
#   curl -sSL .../install_skills.sh | bash -s -- --agent cursor
#
#   # Install specific skills only
#   curl -sSL .../install_skills.sh | bash -s -- docker-dev-setup drizzle-orm-setup
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
SNOWFLAKE_SKILLS="cortex-ai-pipeline cortex-search-rag dynamic-tables-pipeline iceberg-tables ml-model-registry snowpipe-streaming-java snowpipe-streaming-python ssis-to-dbt-replatform-migration tasks-and-streams"

# General-purpose skills (not Snowflake-specific)
GENERAL_SKILLS="docker-dev-setup drizzle-orm-setup supabase-auth-rls"

# All available skills
ALL_SKILLS="$SNOWFLAKE_SKILLS $GENERAL_SKILLS"

msg()  { echo -e "  $*"; }
ok()   { echo -e "  ${G}✓${N} $*"; }
warn() { echo -e "  ${Y}!${N} $*"; }
die()  { echo -e "  ${R}✗${N} $*" >&2; exit 1; }

get_skill_description() {
  case "$1" in
    "docker-dev-setup") echo "Containerize apps with Dockerfile, Compose, and Dev Containers" ;;
    "drizzle-orm-setup") echo "Scaffold Drizzle ORM with TypeScript schema and migrations" ;;
    "supabase-auth-rls") echo "Scaffold Supabase with schema, RLS policies, and auth" ;;
    "cortex-ai-pipeline") echo "Build AI enrichment pipelines with Cortex AI Functions (classify, sentiment, summarize)" ;;
    "cortex-search-rag") echo "Build RAG pipelines with Cortex Search and AI_COMPLETE" ;;
    "dynamic-tables-pipeline") echo "Build declarative data pipelines with Dynamic Tables (medallion architecture)" ;;
    "iceberg-tables") echo "Create and manage Apache Iceberg tables on Snowflake" ;;
    "ml-model-registry") echo "Train, register, and deploy ML models with Snowflake Model Registry" ;;
    "snowpipe-streaming-java") echo "Stream data into Snowflake via Java Snowpipe Streaming SDK" ;;
    "snowpipe-streaming-python") echo "Stream data into Snowflake via Python Snowpipe Streaming SDK" ;;
    "ssis-to-dbt-replatform-migration") echo "Migrate SSIS packages to dbt + Snowflake" ;;
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
    "cortex-ai-pipeline") echo "templates/setup.sql templates/enrich-pipeline.sql templates/batch-insights.sql" ;;
    "cortex-search-rag") echo "templates/setup.sql templates/search-service.sql templates/rag-query.sql" ;;
    "dynamic-tables-pipeline") echo "templates/setup.sql templates/bronze.sql templates/silver.sql templates/gold.sql" ;;
    "iceberg-tables") echo "templates/setup.sql templates/snowflake-managed.sql templates/external-catalog.sql" ;;
    "ml-model-registry") echo "templates/setup.sql templates/train-and-register.py templates/deploy-service.py" ;;
    "snowpipe-streaming-java") echo "" ;;
    "snowpipe-streaming-python") echo "src/config_manager.py src/data_generator.py src/models.py src/parallel_streaming_orchestrator.py src/reconciliation_manager.py src/snowpipe_streaming_manager.py src/streaming_app.py" ;;
    "ssis-to-dbt-replatform-migration") echo "references/phase0-briefing.md references/replatform-output-structure.md references/session-diary.md references/snowflake-sql-patterns.md" ;;
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
    cortex)   target_dir=".cortex/skills/$skill"; ext="" ;;
    *) die "Unknown agent: $agent" ;;
  esac

  local skills_path
  skills_path=$(get_skill_path "$skill")

  if [[ "$agent" == "cortex" ]]; then
    # Cortex Code: download entire skill directory
    mkdir -p "$target_dir"
    curl -sSL "$REPO_RAW/$skills_path/$skill/SKILL.md" -o "$target_dir/SKILL.md" 2>/dev/null || {
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
      curl -sSL "$REPO_RAW/$skills_path/$skill/$f" -o "$target_dir/$f" 2>/dev/null || true
    done
  else
    # Other agents: copy SKILL.md as a rule file
    mkdir -p "$target_dir"
    local filename="${skill}${ext}"
    curl -sSL "$REPO_RAW/$skills_path/$skill/SKILL.md" -o "$target_dir/$filename" 2>/dev/null || {
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
    --help|-h)
      echo "Snowflake AI Kit — Skills Installer"
      echo ""
      echo "Usage: install_skills.sh [OPTIONS] [SKILL ...]"
      echo ""
      echo "Options:"
      echo "  --agent, -a NAME   Install for specific agent (cursor, windsurf, claude, cortex)"
      echo "  --list, -l         List available skills"
      echo "  --help, -h         Show this help"
      echo ""
      echo "If no agent is specified, installs for all detected agents."
      echo "If no skills are specified, installs all available skills."
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

  # If nothing detected, default to all
  if [[ -z "$AGENTS" ]]; then
    AGENTS="cursor windsurf claude"
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
