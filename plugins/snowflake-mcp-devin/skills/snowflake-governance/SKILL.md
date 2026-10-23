---
name: snowflake-governance
description: >-
  Audit data access, inspect masking and row access policies, review
  tags and classification, and analyze role hierarchies and grants
  in Snowflake.
---

# Snowflake Governance

Audit access, inspect policies, and review security configuration.

## When to use

- User asks "who can access this table", "what policies are applied"
- User wants to audit access history or login activity
- User asks about tags, data classification, or PII
- User wants to understand the role hierarchy or grant structure

## Access control and grants

**Grants on a specific object:**
```sql
SHOW GRANTS ON TABLE my_db.my_schema.customers;
```

**What a role can access:**
```sql
SHOW GRANTS TO ROLE analyst_role;
```

**Who has a role:**
```sql
SHOW GRANTS OF ROLE analyst_role;
```

**Role hierarchy (what roles does a role inherit):**
```sql
SHOW GRANTS TO ROLE analyst_role;
-- Look for USAGE grants on other roles
```

## Masking policies

```sql
-- List masking policies
SHOW MASKING POLICIES IN ACCOUNT;

-- See where a policy is applied
SELECT *
FROM TABLE(INFORMATION_SCHEMA.POLICY_REFERENCES(
  POLICY_NAME => 'my_db.my_schema.mask_pii'
));
```

If data appears as `***` or `NULL` unexpectedly, a masking policy is likely applied. Tell the user which policy is active and what role would see unmasked data.

## Row access policies

```sql
-- List row access policies
SHOW ROW ACCESS POLICIES IN ACCOUNT;

-- See where applied
SELECT *
FROM TABLE(INFORMATION_SCHEMA.POLICY_REFERENCES(
  POLICY_NAME => 'my_db.my_schema.row_filter'
));
```

Row access policies filter rows based on the querying role. Different users may see different result sets from the same table.

## Tags and classification

```sql
-- List tags
SHOW TAGS IN ACCOUNT;

-- See what's tagged
SELECT *
FROM TABLE(INFORMATION_SCHEMA.TAG_REFERENCES(
  'my_db.my_schema.customers', 'TABLE'
));

-- Find all objects with a specific tag
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
WHERE TAG_NAME = 'PII'
  AND TAG_VALUE = 'true';
```

## Access history (who accessed what)

```sql
SELECT user_name, query_start_time, direct_objects_accessed
FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
WHERE query_start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
ORDER BY query_start_time DESC
LIMIT 50;
```

## Login history

```sql
SELECT user_name, client_ip, first_authentication_factor, is_success, error_message
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE event_timestamp >= DATEADD(day, -7, CURRENT_TIMESTAMP())
ORDER BY event_timestamp DESC
LIMIT 50;
```

## Network policies

```sql
SHOW NETWORK POLICIES;
DESCRIBE NETWORK POLICY my_policy;
```

## Important

- ACCOUNT_USAGE views have up to 45-minute latency. They are not real-time.
- Some views require ACCOUNTADMIN or specific grants on the SNOWFLAKE database.
- Never attempt to bypass governance — if data is masked or filtered, explain that to the user.
