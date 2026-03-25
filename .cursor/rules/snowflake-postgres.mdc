---
name: snowflake-postgres
description: "Create and manage Snowflake Postgres instances — fully managed Postgres on Snowflake. Use for: CREATE POSTGRES INSTANCE, connecting with psql, network policies, sample schemas, suspend/resume, Postgres on Snowflake. Triggers: snowflake postgres, postgres instance, create postgres, managed postgres, psql snowflake."
---

# Snowflake Postgres

Create and manage fully managed Postgres instances on Snowflake. Each instance runs a dedicated Postgres database server with built-in connection pooling (PgBouncer), automated backups, and optional high availability.

## When to Use

- User wants to create a Postgres instance on Snowflake
- User mentions `CREATE POSTGRES INSTANCE` or Snowflake Postgres
- User wants to connect to Snowflake Postgres from psql or a GUI client
- User needs a network policy for Postgres ingress
- User wants to set up sample data on a Postgres instance
- User wants to suspend, resume, or manage Postgres instances

## Tools Used

- `snowflake_sql_execute` — Create instances, network policies, manage lifecycle
- `ask_user_question` — Confirm instance size, storage, network policy, version
- `read` / `write` / `edit` — Configure SQL templates with user-specific values

## Bundled Files

```
snowflake-postgres/
├── SKILL.md                        # This file (agent instructions)
├── README.md                       # Human-facing docs
└── templates/
    ├── setup.sql                   # Create instance + network policy
    └── sample-data.sql             # Sample ecommerce schema + data + queries
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User confirms instance configuration (size, storage, version, network)
- Step 3: User reviews and saves credentials after instance creation
- Step 5: User tests connection and runs sample queries

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Snowflake Postgres — What This Skill Does
>
> This skill creates a managed Postgres instance on Snowflake. Here's what happens:
>
> 1. **Configure** — Choose instance size, storage, Postgres version, and network policy
> 2. **Create instance** — `CREATE POSTGRES INSTANCE` provisions the database server
> 3. **Set up networking** — Create a network rule + policy for Postgres ingress
> 4. **Connect** — Get connection credentials and connect with psql or any Postgres client
> 5. **Load sample data** — Optionally create tables and run test queries
>
> **Requires:** ACCOUNTADMIN role (or a role with CREATE POSTGRES INSTANCE privilege)
>
> **Billable:** Instance creation incurs compute and storage costs.

**⚠️ MANDATORY STOPPING POINT**: Do NOT proceed until user explicitly approves.

---

## Step 1: Gather Configuration

Ask the user for their preferences using `ask_user_question`:

**Instance name:** A descriptive name (e.g., `dev-test`, `ecomm-prod`)

**Compute size:** (billable — confirm with user)
- `STANDARD_1` — 2 cores, 8 GB (dev/test)
- `STANDARD_2` — 4 cores, 16 GB (small production)
- `STANDARD_4` — 8 cores, 32 GB (medium production)
- `BURSTABLE_1` — 2 cores, 2 GB (hobby/getting started)

**Storage:** 10 GB minimum, default 10 GB for testing

**Postgres version:** 16, 17, or 18 (recommend latest: 18)

**High availability:** Yes/No (doubles cost, recommended for production)

**Network policy:** User's IP address or CIDR range for allowed connections

**⚠️ MANDATORY STOPPING POINT**: Confirm all settings with the user before executing any SQL.

---

## Step 2: Create Network Policy

Before creating the instance, set up networking. Read and customize `templates/setup.sql`:

```sql
-- Create network rule for Postgres ingress
CREATE OR REPLACE NETWORK RULE <instance_name>_pg_rule
  MODE = POSTGRES_INGRESS
  TYPE = IPV4
  VALUE_LIST = ('<user_ip>/32');

-- Create network policy using the rule
CREATE OR REPLACE NETWORK POLICY <instance_name>_pg_policy
  ALLOWED_NETWORK_RULE_LIST = ('<instance_name>_pg_rule');
```

Execute the SQL. This allows the user's IP to connect to the Postgres instance.

---

## Step 3: Create Postgres Instance

Using the configuration from Step 1, execute:

```sql
CREATE POSTGRES INSTANCE <instance_name>
  COMPUTE_POOL = '<compute_size>'
  STORAGE_SIZE_GB = <storage>
  POSTGRES_VERSION = '<version>'
  NETWORK_POLICY = '<instance_name>_pg_policy'
  AUTHENTICATION_AUTHORITY = POSTGRES
  AUTO_SUSPEND_SECS = 3600;
```

Add `ENABLE_HA = TRUE` if the user chose high availability.

After creation, retrieve credentials:

```sql
DESCRIBE POSTGRES INSTANCE <instance_name>;
```

**Important:** The credentials (including password) are shown only once at creation time. Instruct the user to save them securely (password manager recommended).

The connection details include:
- **Host:** `<instance>.snowflakecomputing.com`
- **Port:** 5432
- **Database:** postgres
- **Users:** `snowflake_admin` (admin) and `application` (app)

**⚠️ MANDATORY STOPPING POINT**: Ensure the user has saved the credentials before proceeding.

---

## Step 4: Connect

Show the user how to connect with their preferred client:

**psql (command line):**
```bash
psql "postgres://snowflake_admin:<password>@<host>:5432/postgres?sslmode=require"
```

**Connection string format:**
```
postgres://<user>:<password>@<host>:5432/postgres?sslmode=require
```

**GUI clients** (pgAdmin, DBeaver, DataGrip): Use the host, port, database, username, and password from Step 3. Enable SSL.

---

## Step 5: Load Sample Data (Optional)

If the user wants sample data, read and execute `templates/sample-data.sql`. This creates:
- `customers` table (10 rows)
- `products` table (10 rows)
- `orders` table with foreign keys (10 rows)
- Example queries: order details join, top customers, sales by category

**Note:** Sample data SQL runs via psql against the Postgres instance, not via `snowflake_sql_execute` (which targets Snowflake, not Postgres).

---

## Instance Management

### List instances
```sql
SHOW POSTGRES INSTANCES;
```

### Describe an instance
```sql
DESCRIBE POSTGRES INSTANCE <instance_name>;
```

### Suspend (stop billing for compute)
```sql
ALTER POSTGRES INSTANCE <instance_name> SUSPEND;
```

### Resume
```sql
ALTER POSTGRES INSTANCE <instance_name> RESUME;
```

### Drop (permanent — destroys all data)
```sql
DROP POSTGRES INSTANCE <instance_name>;
```

### Reset credentials
```sql
ALTER POSTGRES INSTANCE <instance_name> RESET ACCESS FOR snowflake_admin;
```

---

## Common Issues

| Issue | Solution |
|-------|----------|
| **`invalid property 'STORAGE_SIZE'`** | Use `STORAGE_SIZE_GB` (not `STORAGE_SIZE`) |
| **`Missing option(s): [AUTHENTICATION_AUTHORITY]`** | Add `AUTHENTICATION_AUTHORITY = POSTGRES` to CREATE statement |
| **Connection refused** | IP not in network policy — check with `DESCRIBE NETWORK POLICY` and add your IP |
| **Network policy not working** | Verify rule uses `MODE = POSTGRES_INGRESS` (not `INGRESS`) |
| **Instance stuck in STARTING** | Large instances can take a few minutes — check with `SHOW POSTGRES INSTANCES` |
| **SSL required error** | Add `?sslmode=require` to connection string, or enable SSL in GUI client |
| **Can't create instance** | Need ACCOUNTADMIN or CREATE POSTGRES INSTANCE privilege |

## Output

- A running Snowflake Postgres instance with network policy
- Connection credentials (host, port, user, password)
- Optionally: sample ecommerce schema with test data and queries

## References

- [Snowflake Postgres overview](https://docs.snowflake.com/en/user-guide/snowflake-postgres/about)
- [Getting started guide](https://www.snowflake.com/en/developers/guides/getting-started-with-snowflake-postgres/)
- [CREATE POSTGRES INSTANCE](https://docs.snowflake.com/en/sql-reference/sql/create-postgres-instance)
- [Network policies for Postgres](https://docs.snowflake.com/en/user-guide/snowflake-postgres/network-policies)
