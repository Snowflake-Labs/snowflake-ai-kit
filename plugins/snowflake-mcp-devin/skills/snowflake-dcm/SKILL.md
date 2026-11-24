---
name: snowflake-dcm
description: >-
  Manage Database Change Management (DCM) projects in Snowflake.
  DCM is infrastructure-as-code for Snowflake objects: databases, schemas,
  tables, roles, and grants defined with DEFINE statements in SQL definition
  files, plus a manifest.yml for targets and templating.
---

# Snowflake DCM (Database Change Management)

DCM lets you manage Snowflake infrastructure as code. A DCM project has a `manifest.yml` (targets and templating) and SQL definition files with `DEFINE` statements. You plan the changes, review them, then deploy through SQL or the Snowflake CLI.

## When to use

- User asks about infrastructure-as-code for Snowflake
- User mentions DCM projects, manifest.yml, or DEFINE statements
- User wants to plan, deploy, inspect, or manage database objects as code
- User asks how to structure roles for a DCM project

## Discovery

**List DCM projects:**
```sql
SHOW DCM PROJECTS IN ACCOUNT;
```

**Describe a project and its deployments:**
```sql
DESCRIBE DCM PROJECT my_db.my_schema.my_project;
SHOW DEPLOYMENTS IN DCM PROJECT my_db.my_schema.my_project;
SHOW ENTITIES IN DCM PROJECT my_db.my_schema.my_project;
```

## Project layout

```
my_project/
├── manifest.yml
└── sources/
    └── definitions/
        └── analytics.sql
```

**manifest.yml** names the targets and the DCM project object for each:

```yaml
manifest_version: 2
type: DCM_PROJECT
default_target: DEV

targets:
  DEV:
    account_identifier: MYORG-MYACCOUNT
    project_name: MY_DB.MY_SCHEMA.MY_PROJECT
    project_owner: DCM_PROJECT_OWNER
```

**Definition files** declare the objects with `DEFINE`:

```sql
DEFINE DATABASE ANALYTICS_DB COMMENT = 'Analytics database managed by DCM';
DEFINE SCHEMA ANALYTICS_DB.REPORTING;
DEFINE TABLE ANALYTICS_DB.REPORTING.DAILY_METRICS (
  METRIC_DATE DATE NOT NULL,
  METRIC_NAME VARCHAR(256),
  METRIC_VALUE NUMBER(18,4)
) COMMENT = 'Daily business metrics';
```

### Role pattern

A common pattern is three roles per project, defined in the project like any other object:
- `<project>_ADMIN` — full DDL on project objects
- `<project>_READWRITE` — DML (INSERT, UPDATE, DELETE) on project tables
- `<project>_READONLY` — SELECT on project tables and views

DCM doesn't create these roles for you.

## SQL commands

```sql
-- Create the project object (needs CREATE DCM PROJECT on the schema)
CREATE DCM PROJECT IF NOT EXISTS my_db.my_schema.my_project;

-- Dry run: shows what would be created, altered, or dropped
EXECUTE DCM PROJECT my_db.my_schema.my_project
  PLAN
  FROM '@my_db.my_schema.my_stage/my_project';

-- Deploy after reviewing the plan
EXECUTE DCM PROJECT my_db.my_schema.my_project
  DEPLOY AS "add daily metrics"
  FROM '@my_db.my_schema.my_stage/my_project';
```

`FROM` takes a stage, a Git repository clone in Snowflake, or a workspace path. Always run `PLAN` before `DEPLOY`: a deploy drops objects that are no longer defined.

## CLI commands

From the folder that contains `manifest.yml`:

```bash
snow dcm create --if-not-exists   # project object for the default target
snow dcm plan                     # dry run
snow dcm deploy                   # deploy
snow dcm plan --target PROD       # another target from the manifest
```

See `snow dcm --help` for all commands.

## Drift detection

To check the account against the last deployment, plan from it:

```sql
EXECUTE DCM PROJECT my_db.my_schema.my_project PLAN FROM DEPLOYMENT LAST;
```

An empty changeset means the account matches. Otherwise, deploy again to reconcile.

## Tips

- Deploys are declarative: re-deploying applies only the difference
- Keep the manifest and definition files in version control
- Grant `PLAN` on the project to CI or developer roles that should dry-run but not deploy
- DCM works alongside dbt: DCM manages infrastructure, dbt manages transforms
