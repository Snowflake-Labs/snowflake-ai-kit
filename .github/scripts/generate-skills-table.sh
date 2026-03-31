#!/usr/bin/env bash
# Scans skill directories, extracts YAML frontmatter, and regenerates
# the skills tables in snowflake-skills/README.md and general-skills/README.md
# between the BEGIN/END markers.
#
# Exit codes:
#   0 — READMEs were updated (or already up to date)
#   1 — error

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BEGIN_MARKER="<!-- BEGIN_SKILLS_TABLE -->"
END_MARKER="<!-- END_SKILLS_TABLE -->"

# ---------- collect rows from a skills directory ----------

generate_rows() {
  local skills_dir="$1"
  local rows=""

  for skill_file in "$skills_dir"/*/SKILL.md; do
    [[ -f "$skill_file" ]] || continue
    dir="$(dirname "$skill_file")"

    # Skip TEMPLATE directory
    [[ "$(basename "$dir")" == "TEMPLATE" ]] && continue

    name="" desc=""

    # Parse YAML frontmatter (between --- lines)
    in_front=false
    while IFS= read -r line; do
      if [[ "$line" == "---" ]]; then
        if $in_front; then break; fi
        in_front=true
        continue
      fi
      if $in_front; then
        case "$line" in
          name:*)  name="$(echo "$line" | sed 's/^name:[[:space:]]*//' | tr -d '"')" ;;
          description:*)
            desc="$(echo "$line" | sed 's/^description:[[:space:]]*//' | tr -d '"')"
            # Truncate at ". Use " or ". Triggers" to get short summary
            desc="$(echo "$desc" | sed -E 's/\. Use (for|when).*$//' | sed 's/\. Triggers.*$//')"
            ;;
        esac
      fi
    done < "$skill_file"

    if [[ -z "$name" || -z "$desc" ]]; then
      echo "WARNING: $skill_file missing name or description in frontmatter" >&2
      continue
    fi

    # Use relative path from the skills dir for links
    reldir="$(basename "$dir")"
    rows+="| [$name]($reldir/) | $desc |"$'\n'
  done

  if [[ -z "$rows" ]]; then
    echo ""
    return
  fi

  # Sort rows alphabetically, drop empty lines
  echo -n "$rows" | sort | sed '/^$/d'
}

# ---------- splice rows into a README ----------

update_readme() {
  local readme="$1"
  local rows="$2"

  if [[ ! -f "$readme" ]]; then
    echo "WARNING: $readme not found, skipping" >&2
    return
  fi

  if [[ -z "$rows" ]]; then
    echo "WARNING: No skills found for $readme" >&2
    return
  fi

  # Write the replacement block to a temp file
  tmpfile="$(mktemp)"
  trap 'rm -f "$tmpfile"' EXIT

  {
    echo "$BEGIN_MARKER"
    echo "| Skill | What it does |"
    echo "|-------|-------------|"
    echo "$rows"
    echo "$END_MARKER"
  } > "$tmpfile"

  # Replace everything between markers (inclusive) with the new table block
  python3 -c "
import sys
readme = open('$readme').read()
begin, end = '$BEGIN_MARKER', '$END_MARKER'
i = readme.index(begin)
j = readme.index(end) + len(end)
table = open(sys.argv[1]).read().rstrip('\n')
open('$readme', 'w').write(readme[:i] + table + readme[j:])
" "$tmpfile"

  rm -f "$tmpfile"
  trap - EXIT
  echo "Skills table updated in $readme"
}

# ---------- run for all directories ----------

sf_rows="$(generate_rows "snowflake-skills")"
update_readme "snowflake-skills/README.md" "$sf_rows"

gen_rows="$(generate_rows "general-skills")"
update_readme "general-skills/README.md" "$gen_rows"

a2a_rows="$(generate_rows "agent-to-agent-skills")"
update_readme "agent-to-agent-skills/README.md" "$a2a_rows"
