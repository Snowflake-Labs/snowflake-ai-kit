# Data Product Sharing

Share Snowflake data with other accounts via secure shares, private listings, or the Snowflake Marketplace. Zero-copy, real-time, no ETL.

## What It Does

This skill helps your AI coding agent:

1. **Prepare data** — Create secure views and organize objects for sharing
2. **Create shares** — Direct account-to-account sharing
3. **Create listings** — Private or marketplace listings with metadata and analytics
4. **Consumer access** — Install and verify shared data on the consumer side

## When to Use

- Sharing tables or views with another Snowflake account
- Publishing data to the Snowflake Marketplace
- Setting up provider/consumer data sharing patterns
- Creating private or organization listings

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions and workflow |
| `templates/setup.sql` | Source data and provider infrastructure |
| `templates/create-share.sql` | Direct share with grants |
| `templates/create-listing.sql` | Private and marketplace listing patterns |
| `templates/consumer-access.sql` | Consumer-side install and verification |

## Prerequisites

- Provider: `CREATE SHARE` privilege (ACCOUNTADMIN by default)
- Listings: `CREATE DATA EXCHANGE LISTING` privilege
- Consumer: `CREATE DATABASE` + `IMPORT SHARE` privileges
- Marketplace: Provider profile + terms acceptance

## Quick Start

```sql
-- Create and populate a share
CREATE SHARE product_data_share;
GRANT USAGE ON DATABASE analytics_db TO SHARE product_data_share;
GRANT USAGE ON SCHEMA analytics_db.public TO SHARE product_data_share;
GRANT SELECT ON TABLE analytics_db.public.products TO SHARE product_data_share;
ALTER SHARE product_data_share ADD ACCOUNTS = target_org.target_account;
```

## Links

- [About listings](https://docs.snowflake.com/en/collaboration/collaboration-listings-about)
- [CREATE SHARE reference](https://docs.snowflake.com/en/sql-reference/sql/create-share)
- [Create and publish a listing](https://docs.snowflake.com/en/collaboration/provider-listings-creating-publishing)
- [Secure Data Sharing overview](https://docs.snowflake.com/en/user-guide/data-sharing-intro)
