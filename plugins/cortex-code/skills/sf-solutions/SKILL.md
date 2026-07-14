---
name: sf-solutions
description: "Discover, install, and teardown Snowflake industry solution accelerators. Usage: $sf-solutions (list all), $sf-solutions retail (filter by industry), $sf-solutions:predictive-maintenance (install), $sf-solutions:predictive-maintenance teardown, $sf-solutions:predictive-maintenance next (post-install guidance). Triggers: solutions, industry, MLEU, manufacturing, predictive maintenance, supply chain, energy, utilities, logistics, IoT, OEE, GNN, retail, demand forecasting, LTV, customer lifetime value, healthcare, clinical, patient safety, next steps, what to do next."
user-invocable: true
metadata:
  author: Snowflake
  version: 2.0.0
  repository: https://github.com/Snowflake-Labs/snowflake-ai-kit
---

# Snowflake Industry Solutions

Install pre-built Snowflake solution accelerators from multiple industry repositories. Solutions are registered in `registry.json` alongside this skill.

## Parse Arguments

Parse the action from `$ARGUMENTS`:
- If `$ARGUMENTS` is empty → run **List** flow (all industries)
- If `$ARGUMENTS` matches an industry name in registry.json → run **List** flow (filtered)
- If `$ARGUMENTS` contains a solution name (e.g., `predictive-maintenance`) → run **Install** flow
- If `$ARGUMENTS` contains a solution name followed by `teardown` → run **Teardown** flow
- If `$ARGUMENTS` contains a solution name followed by `next` → run **Next Actions** flow
- Otherwise → show usage help

## Step 1: Load the Registry

Read `registry.json` from the same directory as this skill file. The registry has this structure:

```json
[
  {
    "industry": "<industry-id>",
    "description": "<industry description>",
    "repo": "<github-repo-url>",
    "solutions": [
      {"name": "<solution-name>", "description": "<short description>"}
    ]
  }
]
```

## Step 2: List Available Solutions

If no solution name was provided (or an industry name was provided as a filter):

1. Read registry.json
2. If an industry filter is specified, include only matching entries
3. Present a table:

```
Available Solutions:
┌───┬──────────────────────────────────┬───────────────────┬─────────────────────────────────┐
│ # │ Solution                         │ Industry          │ Description                     │
├───┼──────────────────────────────────┼───────────────────┼─────────────────────────────────┤
│ 1 │ predictive-maintenance           │ MLEU              │ CoWork, Cortex Analyst, SPCS    │
│ 2 │ supply-chain-intelligence        │ MLEU              │ Cortex Search, Semantic Model   │
│ 3 │ gnn-supply-chain-risk            │ MLEU              │ GNN, PyTorch, SPCS GPU          │
│ 4 │ ltv-prediction                   │ Retail            │ Customer LTV, ML pipeline       │
│ 5 │ demand-forecasting               │ Retail            │ Time series, Cortex Forecast    │
│ 6 │ clinical-quality-agent           │ Healthcare        │ Cortex Agent, Patient Safety    │
└───┴──────────────────────────────────┴───────────────────┴─────────────────────────────────┘

To install: $sf-solutions:<solution-name>
To remove:  $sf-solutions:<solution-name> teardown
Filter by industry: $sf-solutions <industry-name>
```

**STOP** after listing. Do not install anything unless explicitly requested.

## Step 3: Resolve Repository for a Solution

When a solution name is provided (e.g., `$sf-solutions:predictive-maintenance`):

1. Search registry.json for the solution name across all industries
2. Identify the matching industry entry and its `repo` URL
3. If not found, show available solutions and stop

Store the resolved values:
- `$REPO_URL` — the GitHub repository URL
- `$INDUSTRY` — the industry identifier
- `$SOLUTION_NAME` — the solution name

## Step 4: Locate or Clone the Repository

Search for the repository locally in order:

```bash
# Check common locations (using the repo name from the URL)
REPO_DIR_NAME=$(basename "$REPO_URL" .git)
for dir in \
  "./$REPO_DIR_NAME" \
  "../$REPO_DIR_NAME" \
  "$HOME/$REPO_DIR_NAME" \
  "$HOME/projects/$REPO_DIR_NAME" \
  "/tmp/$REPO_DIR_NAME"; do
  if [ -d "$dir/solutions" ]; then
    echo "FOUND: $dir"
    break
  fi
done
```

If NOT found in any location, clone it:

```bash
git clone "$REPO_URL" "/tmp/$REPO_DIR_NAME"
```

If the clone fails (private repo, no git, no network), show a clear error:

> Could not locate or clone the repository. Either:
> 1. Clone it manually: `git clone <repo-url>`
> 2. Or navigate to the directory containing it before invoking this skill.

**STOP** — do not proceed without the repository.

Store the resolved path as `$REPO_ROOT` for subsequent steps.

## Step 5: Install a Solution

### 5a. Validate the solution exists

```bash
test -f "$REPO_ROOT/solutions/$SOLUTION_NAME/manifest.json"
```

If not found, show available solutions and stop.

### 5b. Read the manifest

```bash
cat "$REPO_ROOT/solutions/$SOLUTION_NAME/manifest.json"
```

### 5c. Query current account info

```sql
SELECT CURRENT_ORGANIZATION_NAME() AS ORG,
       CURRENT_ACCOUNT_NAME() AS ACCOUNT,
       CURRENT_REGION() AS REGION,
       CURRENT_ROLE() AS ROLE;
```

### 5d. Present the installation plan

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

### 5e. Wait for user confirmation

**Do NOT proceed without explicit "yes" from the user.**

### 5f. Execute setup.sql

Read and execute the setup script statement by statement:

```bash
cat "$REPO_ROOT/solutions/$SOLUTION_NAME/scripts/setup.sql"
```

Execute each statement via `snowflake_sql_execute`. Use `timeout_seconds: 600` for data loading statements. Log progress after each major section.

### 5g. Execute data.sql (if exists)

```bash
test -f "$REPO_ROOT/solutions/$SOLUTION_NAME/scripts/data.sql"
```

If it exists, execute it statement by statement with `timeout_seconds: 600`.

### 5h. Confirm success

```sql
SHOW SCHEMAS IN DATABASE <database>;
```

Report what was created.

### 5i. Load next actions guide

```bash
cat "$REPO_ROOT/solutions/$SOLUTION_NAME/NEXT_ACTIONS.md"
```

If the file exists, read it and present the recommended next steps to the user. This file contains solution-specific guidance (e.g., how to use the installed agent, sample queries to try, dashboards to open). If the user has follow-up questions about what to do next, refer back to this file for answers.

## Step 6: Teardown a Solution

When `teardown` is specified:

### 6a. Read the manifest to identify objects

```bash
cat "$REPO_ROOT/solutions/$SOLUTION_NAME/manifest.json"
```

### 6b. Show what will be removed

```
This will permanently remove:
  - Database: <database> (and all schemas/objects within)
  - Warehouses: <list>

This action cannot be undone. Proceed?
```

### 6c. Wait for explicit confirmation

### 6d. Execute teardown.sql (if exists)

```bash
cat "$REPO_ROOT/solutions/$SOLUTION_NAME/scripts/teardown.sql"
```

If no teardown.sql exists, drop the database:

```sql
DROP DATABASE IF EXISTS <database>;
```

### 6e. Confirm teardown complete

## Step 7: Next Actions

When `next` is specified (e.g., `$sf-solutions:ltv-prediction next`):

1. Resolve the repository using Steps 3 and 4 (registry lookup + locate/clone)
2. Read the next actions guide:

```bash
cat "$REPO_ROOT/solutions/$SOLUTION_NAME/NEXT_ACTIONS.md"
```

3. If the file exists, present its contents to the user and answer any follow-up questions based on it
4. If the file does not exist, suggest the user check the solution's README or manifest for guidance

## Notes

- This skill requires `git` on the user's machine for the clone fallback
- Solutions are self-contained — each has its own SQL scripts and sample data
- The registry.json file is the source of truth for which solutions exist and where they live
- Each industry repository follows the same convention: `solutions/<name>/manifest.json`
- Each solution may include a `NEXT_ACTIONS.md` with post-install guidance
- To add a new solution: update registry.json with the solution entry under the appropriate industry
