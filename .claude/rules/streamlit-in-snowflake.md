---
name: streamlit-in-snowflake
description: "Deploy Streamlit apps to Snowflake with warehouse or container runtimes. Use for: CREATE STREAMLIT, Streamlit in Snowflake, SiS, deploying dashboards, interactive apps on Snowflake, Snowflake CLI streamlit deploy, environment.yml, pyproject.toml, Snowsight apps. Triggers: streamlit snowflake, deploy streamlit, create streamlit, SiS app, streamlit dashboard, warehouse runtime, container runtime, compute pool streamlit, snow streamlit deploy."
---

# Streamlit in Snowflake

Deploy a Streamlit app that runs entirely inside Snowflake — your data never leaves the platform. Choose warehouse runtime (simple, auto-scaled) or container runtime (custom packages, GPU access).

## When to Use

- User wants to deploy a Streamlit app to Snowflake
- User mentions `CREATE STREAMLIT`, Streamlit in Snowflake, or SiS
- User wants an interactive dashboard or data app running inside Snowflake
- User needs to choose between warehouse and container runtimes
- User wants to use Snowflake CLI (`snow streamlit deploy`) to manage apps

## Tools Used

- `snowflake_sql_execute` — Create stages, streamlit objects, grant access
- `ask_user_question` — Confirm runtime choice, warehouse, compute pool
- `read` / `write` / `edit` — Create app files and configuration

## Bundled Files

```
streamlit-in-snowflake/
├── SKILL.md                        # This file (agent instructions)
├── README.md                       # Human-facing docs
└── templates/
    ├── setup.sql                   # Stage, warehouse, grants
    ├── deploy-warehouse.sql        # Warehouse runtime deployment
    ├── deploy-container.sql        # Container runtime deployment
    └── streamlit_app.py            # Starter app with Snowflake data access
```

---

## Phase 0: Briefing

Present this to the user before starting:

> **Streamlit in Snowflake** lets you build and deploy interactive Python apps that run inside Snowflake. Your data stays in-platform — no ETL, no external hosting.
>
> Two runtime options:
> - **Warehouse runtime** — Runs on virtual warehouses. Simpler setup, each viewer gets their own instance. Best for dashboards and data apps. Dependencies via `environment.yml`.
> - **Container runtime** — Runs on compute pools (SPCS). Install any PyPI package, use GPU, custom Docker. Best for ML apps and complex dependencies. Dependencies via `pyproject.toml` or `requirements.txt`.
>
> I'll help you:
> 1. Set up the stage and infrastructure
> 2. Create your app code
> 3. Deploy to Snowflake
> 4. Configure access control

---

## Workflow

### Step 1: Gather Requirements

Ask the user:
- **What does the app do?** (dashboard, data entry, ML inference, admin tool)
- **Which data?** Database, schema, tables the app will query
- **Runtime preference?** Warehouse (simple) vs container (flexible)

**Decision guide** — recommend runtime based on needs:

| Need | Runtime | Why |
|------|---------|-----|
| Simple dashboard with charts/tables | Warehouse | Easier setup, auto-scaled |
| Standard Python packages (pandas, plotly, altair) | Warehouse | Most common packages available |
| Custom PyPI packages or pip install | Container | Full pip access via `pyproject.toml` |
| GPU / ML inference | Container | Compute pools support GPU nodes |
| External API calls | Either | Both support external access integrations |
| Multi-page app | Either | Both support multi-file apps |

**Defaults if not specified:**
- Runtime: `warehouse`
- Warehouse: `{{WAREHOUSE}}`
- Database/Schema: `{{DATABASE}}.{{SCHEMA}}`

### Step 2: Set Up Infrastructure

Load `templates/setup.sql` and customize with user values:
- Replace `{{DATABASE}}`, `{{SCHEMA}}`, `{{WAREHOUSE}}` with user values
- If container runtime, replace `{{COMPUTE_POOL}}` too

Execute the setup SQL to create the stage and supporting objects.

**⚠️ MANDATORY STOPPING POINT**: Confirm infrastructure is ready before proceeding.

### Step 3: Create App Code

Load `templates/streamlit_app.py` as a starting point.

Customize based on user requirements:
- Replace the sample query with actual tables/columns
- Add appropriate visualizations (st.dataframe, st.bar_chart, st.plotly_chart, etc.)
- Add filters and interactivity as needed

**Key patterns for Snowflake apps:**
```python
# Get Snowflake session (works inside SiS automatically)
from snowflake.snowpark.context import get_active_session
session = get_active_session()

# Query data
df = session.sql("SELECT * FROM my_table LIMIT 1000").to_pandas()

# Use a different warehouse for heavy queries
session.sql("USE WAREHOUSE analytics_wh").collect()
```

**Dependencies file** — create based on runtime:

For **warehouse runtime** — `environment.yml`:
```yaml
name: streamlit_app
channels:
  - snowflake
dependencies:
  - plotly
  - scipy
```

For **container runtime** — `pyproject.toml`:
```toml
[project]
name = "streamlit-app"
version = "1.0.0"
dependencies = [
    "plotly",
    "scipy",
]
```

### Step 4: Deploy to Snowflake

**Option A: SQL deployment** (works everywhere)

Load the appropriate deployment template:
- Warehouse runtime: `templates/deploy-warehouse.sql`
- Container runtime: `templates/deploy-container.sql`

The deployment stages files, creates the STREAMLIT object, and activates the live version.

**Option B: Snowflake CLI** (local development)

If user has Snowflake CLI 3.14+:
```bash
snow streamlit deploy --open
```

With `snowflake.yml`:
```yaml
definition_version: 2
entities:
  my_streamlit:
    type: streamlit
    identifier: {{APP_NAME}}
    query_warehouse: {{WAREHOUSE}}
    main_file: streamlit_app.py
    artifacts:
      - streamlit_app.py
      - environment.yml
```

### Step 5: Configure Access and Verify

Grant USAGE on the Streamlit object so other roles can view the app:

```sql
GRANT USAGE ON STREAMLIT {{DATABASE}}.{{SCHEMA}}.{{APP_NAME}} TO ROLE {{VIEWER_ROLE}};
```

**Verify** the app is running:
```sql
SHOW STREAMLITS IN SCHEMA {{DATABASE}}.{{SCHEMA}};
DESCRIBE STREAMLIT {{DATABASE}}.{{SCHEMA}}.{{APP_NAME}};
```

The app URL follows the pattern:
`https://<account>.snowflakecomputing.com/#/streamlit-apps/{{DATABASE}}.{{SCHEMA}}.{{APP_NAME}}`

---

## Runtime Reference

### Warehouse Runtimes

| Runtime Name | Python |
|-------------|--------|
| `SYSTEM$ST_WAREHOUSE_RUNTIME_PY3_9` | 3.9 |
| `SYSTEM$ST_WAREHOUSE_RUNTIME_PY3_10` | 3.10 |
| `SYSTEM$ST_WAREHOUSE_RUNTIME_PY3_11` | 3.11 |
| (default — latest) | Latest |

- Each viewer gets a personal instance
- Dependencies: `environment.yml` with `snowflake` channel
- `QUERY_WAREHOUSE` runs both app code and SQL queries
- Tip: Use a small dedicated warehouse for code, switch to larger for queries

### Container Runtimes

| Runtime Name | Python |
|-------------|--------|
| `SYSTEM$ST_CONTAINER_RUNTIME_PY3_11` | 3.11 |

- Runs on compute pools (SPCS)
- Dependencies: `pyproject.toml` or `requirements.txt`
- `COMPUTE_POOL` runs app code, `QUERY_WAREHOUSE` runs SQL queries
- Requires `EXTERNAL_ACCESS_INTEGRATIONS` for pip installs from PyPI

### Key SQL Commands

```sql
CREATE STREAMLIT ...          -- Create the app object
ALTER STREAMLIT ... SET ...   -- Change runtime, warehouse, etc.
ALTER STREAMLIT ... ADD LIVE VERSION FROM LAST  -- Activate latest code
DROP STREAMLIT ...            -- Remove the app
SHOW STREAMLITS ...           -- List apps
DESCRIBE STREAMLIT ...        -- View app details
```

### Access Control

| Privilege | Object | Purpose |
|-----------|--------|---------|
| `CREATE STREAMLIT` | Schema | Create new apps |
| `READ` | Stage | Read source files |
| `USAGE` | Warehouse | Run app code / queries |
| `USAGE` | Compute Pool | Container runtime only |
| `USAGE` | Streamlit object | View the app |

---

## Output

- A deployed Streamlit app running inside Snowflake (warehouse or container runtime) accessible via Snowsight URL
- App source code, dependency file, and deployment configuration staged in Snowflake
- Access grants configured so specified roles can view the app

## Stopping Points

- **Step 1**: Confirm runtime choice before proceeding
- **Step 3**: Review app code before deploying
- **Step 5**: Ask if user wants to grant access to additional roles

## Common Patterns

**External API access:**
```sql
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION my_api_access
  ALLOWED_NETWORK_RULES = (my_network_rule)
  ENABLED = TRUE;

ALTER STREAMLIT my_app SET
  EXTERNAL_ACCESS_INTEGRATIONS = (my_api_access);
```

**Secrets (warehouse runtime):**
```sql
CREATE OR REPLACE SECRET my_secret
  TYPE = GENERIC_STRING
  SECRET_STRING = 'my-api-key';

ALTER STREAMLIT my_app SET
  SECRETS = ('api_key' = my_db.my_schema.my_secret);
```

**Git integration:**
```sql
CREATE STREAMLIT my_app
  FROM @my_db.my_schema.my_repo/branches/main/
  MAIN_FILE = 'streamlit_app.py'
  QUERY_WAREHOUSE = my_warehouse;
```
