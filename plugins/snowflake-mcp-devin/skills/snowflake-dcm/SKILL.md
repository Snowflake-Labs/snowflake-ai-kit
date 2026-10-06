---
name: snowflake-dcm
description: >-
  Manage Database Change Management (DCM) projects in Snowflake.
  DCM is infrastructure-as-code for Snowflake objects — databases,
  schemas, tables, and roles defined in manifest.yml with DEFINE blocks.
---

# Snowflake DCM (Database Change Management)

DCM lets you manage Snowflake infrastructure as code — databases, schemas, tables, roles, and grants defined declaratively in YAML manifests and deployed through the Snowflake CLI or SQL.

## When to use

- User asks about infrastructure-as-code for Snowflake
- User mentions DCM projects, manifest.yml, or DEFINE blocks
- User wants to deploy, inspect, or manage database objects as code
- User asks about the three-tier role pattern

## Discovery

**List deployed DCM/dbt projects:**
```sql
SHOW DBT PROJECTS IN ACCOUNT;
```

**Describe a project:**
```sql
DESCRIBE DBT PROJECT my_db.my_schema.my_project;
```

## Concepts

### Manifest structure

DCM projects use `manifest.yml` with DEFINE blocks:

```yaml
# manifest.yml
- DEFINE DATABASE analytics_db:
    comment: "Analytics database managed by DCM"

- DEFINE SCHEMA analytics_db.reporting:
    comment: "Reporting schema"

- DEFINE TABLE analytics_db.reporting.daily_metrics:
    columns:
      - name: METRIC_DATE
        type: DATE
        not_null: true
      - name: METRIC_NAME
        type: VARCHAR(256)
      - name: METRIC_VALUE
        type: NUMBER(18,4)
    comment: "Daily business metrics"
```

### Three-tier role pattern

DCM automatically creates three roles per project:
- `<project>_ADMIN` — full DDL on project objects
- `<project>_READWRITE` — DML (INSERT, UPDATE, DELETE) on project tables
- `<project>_READONLY` — SELECT on project tables and views

### CLI commands

```bash
# Deploy a DCM project
snow dcm deploy --manifest manifest.yml

# Execute a deployed project
snow dcm execute my_db.my_schema.my_project

# List deployed projects
snow dcm list
```

### SQL commands

```sql
-- Execute a deployed project
EXECUTE DBT PROJECT my_db.my_schema.my_project;

-- Alter a project
ALTER DBT PROJECT my_db.my_schema.my_project SET COMMENT = 'Updated';

-- Drop a project
DROP DBT PROJECT my_db.my_schema.my_project;
```

## Drift detection

After deployment, compare the manifest against live state:
1. `DESCRIBE DBT PROJECT <name>` — see what was deployed
2. `SHOW TABLES/SCHEMAS/DATABASES` — see current state
3. Re-deploy to reconcile drift

## Tips

- DCM projects are idempotent — re-deploying applies only the delta
- Use version control for manifest.yml — track changes over time
- Grant the three-tier roles to users/groups as needed for access control
- DCM works alongside dbt — DCM manages infrastructure, dbt manages transforms
