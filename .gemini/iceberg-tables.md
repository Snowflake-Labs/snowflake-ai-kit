---
name: iceberg-tables
description: "Create and manage Apache Iceberg tables on Snowflake with Snowflake-managed or external catalogs. Use for: creating Iceberg tables, external volumes, catalog integrations, open table format, cross-engine interop. Triggers: iceberg, iceberg table, open table format, external volume, catalog integration, parquet, apache iceberg, snowflake managed iceberg."
---

# Iceberg Tables

Create and manage Apache Iceberg tables on Snowflake. Iceberg is an open table format that stores data as Parquet files with metadata, enabling cross-engine access from Spark, Trino, Flink, and other tools while Snowflake handles compute.

## When to Use

- User wants to create Iceberg tables on Snowflake
- User mentions open table format, Parquet, or cross-engine access
- User needs to set up external volumes for Iceberg storage
- User wants interoperability between Snowflake and Spark/Trino/Flink
- User asks about catalog integrations (REST, Polaris, Open Catalog)
- User wants to read existing Iceberg or Delta tables from object storage

## Tools Used

- `snowflake_sql_execute` -- Create external volumes, catalog integrations, Iceberg tables, verify data
- `ask_user_question` -- Choose catalog type, confirm targets, get approval at checkpoints
- `read` / `write` / `edit` -- Configure SQL templates with user-specific values

## Bundled Files

```
iceberg-tables/
├── SKILL.md                         # This file (agent instructions)
├── README.md                        # Human-facing docs
└── templates/
    ├── setup.sql                    # External volume + database setup
    ├── snowflake-managed.sql        # Snowflake-as-catalog Iceberg table
    └── external-catalog.sql         # REST catalog / object storage table
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User selects catalog type (Snowflake-managed vs external)
- Step 2: User confirms external volume configuration and updates IAM trust policy
- Step 4: User verifies Iceberg table created successfully

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Iceberg Tables -- What This Skill Does
>
> **Apache Iceberg** is an open table format that stores data as Parquet files with rich metadata. Snowflake supports Iceberg tables natively, letting you create, read, and write Iceberg data while other engines (Spark, Trino, Flink) can also access the same files.
>
> **Three catalog options:**
>
> 1. **Snowflake-managed** (simplest) -- Snowflake owns the catalog. Full read-write from Snowflake. External engines get read access via CATALOG_SYNC.
> 2. **REST catalog** (Polaris / Open Catalog) -- External catalog manages metadata. Snowflake reads and (depending on config) writes.
> 3. **Files in object storage** -- Point Snowflake at existing Iceberg/Delta files. Read-only.
>
> **What will happen (7 steps):**
>
> 1. **Choose catalog type** -- pick which approach fits your use case
> 2. **Create external volume** -- configure cloud storage (S3/GCS/Azure)
> 3. **Create catalog integration** -- if using external catalog
> 4. **Create Iceberg table** -- using the chosen approach
> 5. **Load sample data** -- insert or verify auto-refresh
> 6. **Query and verify** -- confirm data is accessible
> 7. **Cross-engine access** -- optional: set up CATALOG_SYNC
>
> **What this skill will NOT do:**
> - Modify your IAM roles automatically (you must update the trust policy)
> - Drop or alter existing objects not created by this workflow
> - Continue past any checkpoint without your approval

Ask the user: **"Shall I proceed with Step 1 (Choose Catalog Type)?"**

Do NOT proceed until the user confirms.

---

## Workflow

### Step 1: Choose Catalog Type

Ask the user which approach to use:

| Option | Best For | DML Support |
|--------|----------|-------------|
| **Snowflake-managed** | New tables, full Snowflake features | Full read-write |
| **REST catalog** | Polaris, Open Catalog, shared catalogs | Read-write (depends on catalog) |
| **Files in object storage** | Existing Iceberg/Delta files | Read-only |

Default recommendation: **Snowflake-managed** unless the user has a specific external catalog requirement.

Confirm the user's choice before proceeding.

---

### Step 2: Create External Volume

All Iceberg tables need an external volume that points to cloud storage.

Run `templates/setup.sql` after replacing placeholders. The user must provide:
- Cloud provider (S3, GCS, or Azure)
- Bucket/container name and path
- IAM role ARN (S3), service account (GCS), or tenant ID (Azure)

After creating the external volume, run:
```sql
DESCRIBE EXTERNAL VOLUME {{EXTERNAL_VOLUME_NAME}};
```

The user must update their IAM role trust policy with the values from:
- `STORAGE_AWS_IAM_USER_ARN`
- `STORAGE_AWS_EXTERNAL_ID`

Do NOT proceed until the user confirms the trust policy is updated.

**Alternative for demo/testing:** If the user just wants to try Iceberg tables and already has an external volume set at the account or database level, skip this step.

---

### Step 3: Create Catalog Integration (External Catalog Only)

Skip this step if the user chose Snowflake-managed.

For REST catalog:
```sql
CREATE OR REPLACE CATALOG INTEGRATION my_rest_catalog
    CATALOG_SOURCE = ICEBERG_REST
    TABLE_FORMAT = ICEBERG
    CATALOG_URI = 'https://my-catalog-host/api/v1'
    WAREHOUSE = 'my_catalog_warehouse'
    CATALOG_NAMESPACE = 'my_namespace'
    ENABLED = TRUE;
```

For files in object storage:
```sql
CREATE OR REPLACE CATALOG INTEGRATION my_files_catalog
    CATALOG_SOURCE = OBJECT_STORE
    TABLE_FORMAT = ICEBERG
    ENABLED = TRUE;
```

---

### Step 4: Create Iceberg Table

Route to the correct template based on Step 1:

**Snowflake-managed:** Run `templates/snowflake-managed.sql`
- Creates table with `CATALOG = 'SNOWFLAKE'`
- Inserts sample data
- Optionally creates a Dynamic Iceberg Table

**External catalog:** Run `templates/external-catalog.sql`
- REST catalog: `CATALOG_TABLE_NAME` + `AUTO_REFRESH = TRUE`
- Object storage files: `METADATA_FILE_PATH`

Verify:
```sql
SHOW ICEBERG TABLES IN SCHEMA {{DATABASE}}.{{SCHEMA}};
```

Confirm with the user that the table was created.

---

### Step 5: Load Sample Data

**Snowflake-managed:** Insert data directly (template includes sample inserts).

**REST catalog:** If the catalog supports writes from Snowflake, insert data. Otherwise, explain that data must be written from the external engine.

**Files in object storage:** Data already exists. Explain refresh:
```sql
ALTER ICEBERG TABLE my_table REFRESH 'path/to/new/metadata.json';
```

---

### Step 6: Query and Verify

```sql
SELECT COUNT(*) FROM {{DATABASE}}.{{SCHEMA}}.{{TABLE_NAME}};
SELECT * FROM {{DATABASE}}.{{SCHEMA}}.{{TABLE_NAME}} LIMIT 10;
SHOW ICEBERG TABLES LIKE '{{TABLE_NAME}}';
```

---

### Step 7: Cross-Engine Access (Optional)

For Snowflake-managed tables, enable CATALOG_SYNC to publish metadata to an external catalog:

```sql
ALTER ICEBERG TABLE my_table SET
    CATALOG_SYNC = 'my_open_catalog_integration';
```

This lets Spark/Trino read the table via the synced catalog while Snowflake remains the write engine.

---

## Patterns

### Snowflake-Managed with Partitioning

```sql
CREATE OR REPLACE ICEBERG TABLE partitioned_events (
    event_id INT,
    event_type STRING,
    event_date DATE,
    payload VARIANT
)
PARTITION BY (event_date)
CATALOG = 'SNOWFLAKE'
EXTERNAL_VOLUME = 'my_ext_vol'
BASE_LOCATION = 'events/';
```

### Dynamic Iceberg Table

```sql
CREATE OR REPLACE DYNAMIC ICEBERG TABLE sales_summary
    TARGET_LAG = '10 minutes'
    WAREHOUSE = compute_wh
    EXTERNAL_VOLUME = 'my_ext_vol'
    CATALOG = 'SNOWFLAKE'
    BASE_LOCATION = 'sales_summary/'
    AS
    SELECT region, DATE_TRUNC('day', sale_date) AS day, SUM(amount) AS total
    FROM raw_sales GROUP BY 1, 2;
```

### Enable Streams on Iceberg

```sql
ALTER ICEBERG TABLE my_table SET CHANGE_TRACKING = TRUE;
CREATE STREAM my_stream ON ICEBERG TABLE my_table;
```

### CTAS for Iceberg

```sql
CREATE OR REPLACE ICEBERG TABLE archive_2024
    CATALOG = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'my_ext_vol'
    BASE_LOCATION = 'archive_2024/'
    AS SELECT * FROM transactions WHERE year = 2024;
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| **Access Denied / 403** on external volume | IAM trust policy not configured | Run `DESCRIBE EXTERNAL VOLUME`, update IAM trust policy with Snowflake's ARN and external ID |
| **Object does not exist** (catalog integration) | Double-quoted identifier not preserved | Use `CATALOG = '"my_integration"'` (single quotes wrapping double quotes) |
| **Auto-refresh not picking up changes** | Event notification not configured | Set up SQS/SNS notifications for the S3 bucket, or use manual `ALTER ICEBERG TABLE ... REFRESH` |
| **Unsupported data type** | Iceberg type not mapped | Check Iceberg data type mapping in Snowflake docs; use compatible types |
| **Cannot write to table** | Externally managed table without write support | Only Snowflake-managed tables support full DML. External catalog tables may be read-only. |
| **ALLOW_WRITES error** | External volume missing write permission | Recreate volume with `ALLOW_WRITES = TRUE` |

---

## Architecture Notes

- **External volumes** define WHERE data is stored (S3/GCS/Azure). **Catalog integrations** define WHO manages the metadata.
- **Snowflake-managed Iceberg**: Snowflake owns the catalog metadata. Read-write from Snowflake, read-only from external engines via CATALOG_SYNC.
- **External catalog Iceberg**: External system (Polaris, Glue, etc.) owns the catalog. Snowflake reads and optionally writes.
- `BASE_LOCATION` is relative to the external volume's storage path. Each table should have its own base location.
- Iceberg tables support Time Travel, streams (with CHANGE_TRACKING), clustering, masking policies, and tagging -- same governance as regular Snowflake tables.
- Data files are stored as Parquet. Snowflake writes in its optimized format by default; set `STORAGE_SERIALIZATION_POLICY = 'COMPATIBLE'` for maximum interop.
- Default external volumes can be set at account, database, or schema level to avoid specifying them on every CREATE.

## Output

- External volume connected to cloud storage
- Iceberg table(s) with sample data
- Optional: catalog integration, Dynamic Iceberg Table, CATALOG_SYNC for cross-engine access
