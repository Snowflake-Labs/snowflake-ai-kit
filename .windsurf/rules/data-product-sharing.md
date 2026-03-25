---
name: data-product-sharing
description: "Share data products across Snowflake accounts using listings, shares, and the marketplace. Use for: data sharing, CREATE SHARE, CREATE LISTING, private listings, marketplace listings, cross-account sharing, secure data sharing, provider/consumer, application packages, data products, organization listings. Triggers: share data, data product, listing, marketplace, cross-account, share table, share view, provider studio, consumer, secure share, private share, auto-fulfillment."
---

# Data Product Sharing

Share tables, views, and other Snowflake objects with other accounts — privately or on the Snowflake Marketplace. No data copying, no ETL, real-time access.

## When to Use

- User wants to share data with another Snowflake account
- User mentions listings, marketplace, data products, or secure sharing
- User needs to set up provider/consumer data sharing
- User wants to publish to Snowflake Marketplace
- User needs cross-region or cross-cloud data sharing (auto-fulfillment)

## Tools Used

- `snowflake_sql_execute` — Create shares, grants, listings, verify access
- `ask_user_question` — Confirm sharing model, target accounts, access type
- `read` / `write` / `edit` — Configure SQL templates with user-specific values

## Bundled Files

```
data-product-sharing/
├── SKILL.md                         # This file (agent instructions)
├── README.md                        # Human-facing docs
└── templates/
    ├── setup.sql                    # Source data and provider setup
    ├── create-share.sql             # Secure share with grants
    ├── create-listing.sql           # Private and marketplace listings
    └── consumer-access.sql          # Consumer-side install and query
```

---

## Phase 0: Briefing

Present this to the user before starting:

> **Snowflake Data Sharing** lets you share live data with other Snowflake accounts — no copying, no ETL, no storage costs for consumers.
>
> Three sharing methods:
> - **Direct Share** — Point-to-point sharing with specific accounts. Simplest. Consumer gets a read-only database.
> - **Private Listing** — Like a direct share but with metadata, usage analytics, and support for paid access. Best for business partnerships.
> - **Marketplace Listing** — Publish publicly on Snowflake Marketplace. Best for broad distribution.
>
> I'll help you:
> 1. Prepare the data you want to share
> 2. Create a share or listing
> 3. Configure consumer access
> 4. Verify end-to-end

---

## Workflow

### Step 1: Gather Requirements

Ask the user:
- **What data?** Database, schema, specific tables/views to share
- **Who?** Target accounts (org.account format) or public marketplace
- **How?** Direct share, private listing, or marketplace listing
- **Access type?** Free, limited trial, or paid

**Decision guide:**

| Need | Method | Why |
|------|--------|-----|
| Quick share with one account | Direct Share | Simplest, no listing overhead |
| Share with metadata and analytics | Private Listing | Usage tracking, descriptions, sample queries |
| Broad distribution | Marketplace Listing | Publicly discoverable |
| Monetize data | Paid Listing | Stripe integration for payments |
| Internal org sharing | Organization Listing | Internal marketplace for business units |
| Share apps + data + agents | Application Package (TYPE=DATA) | Declarative sharing via manifest |

**For application packages (TYPE=DATA)** with agents, semantic views, or notebooks — use the `declarative-sharing` bundled skill instead. This skill covers share-based and listing-based sharing.

**Defaults if not specified:**
- Method: `direct share`
- Access type: `free`

### Step 2: Prepare Source Data

Load `templates/setup.sql` and customize:
- Replace `{{DATABASE}}`, `{{SCHEMA}}` with source database/schema
- Create or identify the tables/views to share
- Ensure objects are in a database the sharing role owns

**Key rule**: You share a database, then grant access to specific objects within it. You cannot share individual objects without a database context.

**Best practice**: Create secure views over raw tables to control what consumers see:
```sql
CREATE OR REPLACE SECURE VIEW share_ready_view AS
SELECT col1, col2, col3  -- only columns you want to expose
FROM raw_table
WHERE is_public = TRUE;  -- row-level filtering
```

**STOP**: Confirm which objects to share before proceeding.

### Step 3: Create Share or Listing

Based on Step 1 decision:

**Option A: Direct Share** — Load `templates/create-share.sql`
- Creates a share, grants usage on database/schema, grants SELECT on tables/views
- Adds consumer accounts

**Option B: Private Listing** — Load `templates/create-listing.sql`
- Creates a share first (same as Option A)
- Then wraps it in a listing with metadata

**Option C: Marketplace Listing** — Guide user to Provider Studio in Snowsight
- Requires a provider profile (one-time setup)
- Must accept Snowflake Provider and Consumer Terms
- Listing goes through approval process

Execute the appropriate SQL.

### Step 4: Consumer-Side Access

Share `templates/consumer-access.sql` with the consumer (or run it if testing in a second account):
- Creates a database from the share/listing
- Grants usage to consumer roles
- Verifies data is accessible

### Step 5: Verify End-to-End

**Provider side:**
```sql
SHOW SHARES;
DESCRIBE SHARE {{SHARE_NAME}};
-- For listings:
SHOW LISTINGS;
```

**Consumer side:**
```sql
SHOW AVAILABLE LISTINGS;
-- or
SHOW SHARES;
SELECT * FROM {{CONSUMER_DB}}.{{SCHEMA}}.{{TABLE}} LIMIT 10;
```

---

## Sharing Reference

### What Can Be Shared

| Object | Shareable | Notes |
|--------|-----------|-------|
| Tables | Yes | SELECT grant |
| Secure Views | Yes | Recommended over raw tables |
| Secure UDFs | Yes | Including UDTFs |
| Secure Materialized Views | Yes | Consumer sees materialized data |
| Schemas | Yes | Via USAGE grant |
| Databases | Yes | Required as container |

### Access Control

| Role | Privileges Needed |
|------|-------------------|
| Provider (share creator) | `CREATE SHARE` on account |
| Provider (listing creator) | `CREATE DATA EXCHANGE LISTING` on account |
| Consumer (access listing) | `CREATE DATABASE`, `IMPORT SHARE` |

### Key SQL Commands

```sql
-- Shares
CREATE SHARE ...                  -- Create empty share
GRANT USAGE ON DATABASE ... TO SHARE ...   -- Add database
GRANT USAGE ON SCHEMA ... TO SHARE ...     -- Add schema
GRANT SELECT ON TABLE ... TO SHARE ...     -- Add table
ALTER SHARE ... ADD ACCOUNTS = ...         -- Add consumers
DESCRIBE SHARE ...                         -- View share contents
REVOKE ... FROM SHARE ...                  -- Remove access

-- Consumer side
CREATE DATABASE ... FROM SHARE ...         -- Mount shared data
-- or
CREATE DATABASE ... FROM LISTING ...       -- Install from listing

-- Listings (SQL)
SHOW LISTINGS;
DESCRIBE LISTING ...;
```

### Auto-Fulfillment (Cross-Region)

When sharing with accounts in different regions, Snowflake automatically replicates data:
- Provider sets refresh frequency (default: 1 hour)
- Consumer sees data with slight lag
- Provider pays for replication compute and storage

---

## Stopping Points

- **Step 2**: Confirm which objects to share
- **Step 3**: Review share/listing before adding consumer accounts
- **Step 5**: Verify consumer can query the data

## Common Patterns

**Secure view with row-level filtering:**
```sql
CREATE OR REPLACE SECURE VIEW shared_orders AS
SELECT order_id, product, amount, region
FROM orders
WHERE region = CURRENT_ACCOUNT();  -- per-consumer filtering
```

**Reader accounts (for non-Snowflake consumers):**
```sql
CREATE MANAGED ACCOUNT consumer_reader
  ADMIN_NAME = 'admin'
  ADMIN_PASSWORD = 'ChangeMe123!'
  TYPE = READER;

ALTER SHARE my_share ADD ACCOUNTS = consumer_reader;
```

**Revoking access:**
```sql
ALTER SHARE my_share REMOVE ACCOUNTS = target_org.target_account;
-- or
DROP SHARE my_share;
```
