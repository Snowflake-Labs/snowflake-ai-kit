---
name: sf-solutions
description: "Discover, install, and teardown Snowflake industry solution accelerators from sf-mleu-solutions. Usage: $sf-solutions (list all), $sf-solutions:predictive-maintenance (install), $sf-solutions:predictive-maintenance teardown. Triggers: solutions, MLEU, manufacturing, predictive maintenance, supply chain, energy, utilities, logistics, IoT, OEE, GNN."
user-invocable: true
metadata:
  author: Snowflake
  version: 1.0.0
  repository: https://github.com/Snowflake-Labs/sf-mleu-solutions
---

# Snowflake Industry Solutions

Install pre-built Snowflake solution accelerators from the [sf-mleu-solutions](https://github.com/Snowflake-Labs/sf-mleu-solutions) repository.

## Parse Arguments

Parse the action from `$ARGUMENTS`:
- If `$ARGUMENTS` is empty → run **List** flow
- If `$ARGUMENTS` contains a solution name (e.g., `predictive-maintenance`) → run **Install** flow
- If `$ARGUMENTS` contains a solution name followed by `teardown` → run **Teardown** flow
- Otherwise → show usage help

## Step 1: Locate the sf-mleu-solutions Repository

Search for the repository in order:

```bash
# Check common locations
for dir in \
  "./sf-mleu-solutions" \
  "../sf-mleu-solutions" \
  "$HOME/sf-mleu-solutions" \
  "$HOME/projects/sf-mleu-solutions" \
  "/tmp/sf-mleu-solutions"; do
  if [ -d "$dir/solutions" ]; then
    echo "FOUND: $dir"
    break
  fi
done
```

If NOT found in any location, clone it:

```bash
git clone https://github.com/Snowflake-Labs/sf-mleu-solutions.git /tmp/sf-mleu-solutions
```

If the clone fails (private repo, no git, no network), show a clear error:

> Could not locate or clone sf-mleu-solutions. Either:
> 1. Clone it manually: `git clone https://github.com/Snowflake-Labs/sf-mleu-solutions.git`
> 2. Or navigate to the directory containing it before invoking this skill.

**STOP** — do not proceed without the repository.

Store the resolved path as `$REPO_ROOT` for subsequent steps.

## Step 2: List Available Solutions (default action)

If no solution name was provided, scan for available solutions:

```bash
find "$REPO_ROOT/solutions" -maxdepth 2 -name "manifest.json" -exec cat {} \;
```

Present a table to the user:

```
Available Solutions:
┌───┬──────────────────────────────────┬───────────────┬─────────────────────────────────┐
│ # │ Solution                         │ Industry      │ Key Features                    │
├───┼──────────────────────────────────┼───────────────┼─────────────────────────────────┤
│ 1 │ predictive-maintenance           │ Manufacturing │ CoWork, Cortex Analyst, SPCS    │
│ 2 │ supply-chain-intelligence        │ Manufacturing │ Cortex Search, Semantic Model   │
│ 3 │ gnn-supply-chain-risk            │ Manufacturing │ GNN, PyTorch, SPCS GPU          │
└───┴──────────────────────────────────┴───────────────┴─────────────────────────────────┘

To install: $sf-solutions:<solution-name>
To remove:  $sf-solutions:<solution-name> teardown
```

**STOP** after listing. Do not install anything unless explicitly requested.

## Step 3: Install a Solution

When a solution name is provided (e.g., `$sf-solutions:predictive-maintenance`):

### 3a. Validate the solution exists

```bash
test -f "$REPO_ROOT/solutions/$SOLUTION_NAME/manifest.json"
```

If not found, show available solutions and stop.

### 3b. Read the manifest

```bash
cat "$REPO_ROOT/solutions/$SOLUTION_NAME/manifest.json"
```

### 3c. Query current account info

```sql
SELECT CURRENT_ORGANIZATION_NAME() AS ORG,
       CURRENT_ACCOUNT_NAME() AS ACCOUNT,
       CURRENT_REGION() AS REGION,
       CURRENT_ROLE() AS ROLE;
```

### 3d. Present the installation plan

Show the user a summary combining manifest data and account info:

```
Solution: <name> v<version>
Industry: <industry>
Database: <database>
Schemas:  <comma-separated schemas>
Role Required: <role>

Target Account:
  Organization: <ORG>
  Account:      <ACCOUNT>
  Region:       <REGION>
  Current Role: <ROLE>

What will be created:
  <bullet list from manifest.objects_created or inferred from setup.sql>

Proceed with installation?
```

### 3e. Wait for user confirmation

**Do NOT proceed without explicit "yes" from the user.**

### 3f. Execute setup.sql

Read and execute the setup script statement by statement:

```bash
cat "$REPO_ROOT/solutions/$SOLUTION_NAME/scripts/setup.sql"
```

Execute each statement via `snowflake_sql_execute`. Use `timeout_seconds: 600` for data loading statements. Log progress after each major section.

### 3g. Execute data.sql (if exists)

```bash
test -f "$REPO_ROOT/solutions/$SOLUTION_NAME/scripts/data.sql"
```

If it exists, execute it statement by statement with `timeout_seconds: 600`.

### 3h. Confirm success

```sql
SHOW SCHEMAS IN DATABASE <database>;
```

Report what was created and provide next steps (e.g., "Open Snowflake Intelligence and ask a question about your equipment").

## Step 4: Teardown a Solution

When `teardown` is specified:

### 4a. Read the manifest to identify objects

```bash
cat "$REPO_ROOT/solutions/$SOLUTION_NAME/manifest.json"
```

### 4b. Show what will be removed

```
This will permanently remove:
  - Database: <database> (and all schemas/objects within)
  - Warehouses: <list>

This action cannot be undone. Proceed?
```

### 4c. Wait for explicit confirmation

### 4d. Execute teardown.sql (if exists)

```bash
cat "$REPO_ROOT/solutions/$SOLUTION_NAME/scripts/teardown.sql"
```

If no teardown.sql exists, drop the database:

```sql
DROP DATABASE IF EXISTS <database>;
```

### 4e. Confirm teardown complete

## Notes

- This skill requires `git` on the user's machine for the clone fallback
- Solutions are self-contained — each has its own SQL scripts and sample data
- The sf-mleu-solutions repository is the source of truth for solution content
- For Claude Code / Codex users: install the companion plugin instead — `claude plugin install Snowflake-Labs/sf-mleu-solutions/plugins/claude-code`
