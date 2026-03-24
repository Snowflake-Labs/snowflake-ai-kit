-- =============================================================================
-- Create a Listing
-- =============================================================================
-- Wraps a share in a listing for enhanced metadata, analytics, and access.
-- Supports private listings and marketplace listings.
--
-- Replace these placeholders:
--   {{DATABASE}}         — Source database
--   {{SCHEMA}}           — Source schema
--   {{SHARE_NAME}}       — Existing share (create via create-share.sql first)
--   {{LISTING_NAME}}     — Name for the listing
--   {{CONSUMER_ACCOUNT}} — Target account for private listings (ORG.ACCOUNT)
-- =============================================================================

-- =============================================================================
-- OPTION A: Private Listing (SQL — share with specific accounts)
-- =============================================================================
-- Prerequisites:
--   1. CREATE DATA EXCHANGE LISTING privilege
--   2. An existing share (create-share.sql)

USE ROLE ACCOUNTADMIN;

-- Ensure the share exists and has objects
DESCRIBE SHARE {{SHARE_NAME}};

-- Private listings are typically created in Provider Studio (Snowsight UI):
--   1. Navigate to Marketplace > Provider Studio
--   2. Create Listing > Specified Consumers
--   3. Enter listing title
--   4. Click + Select and choose your share or database objects
--   5. Add consumer accounts (ORG.ACCOUNT format)
--   6. Publish

-- To find your organization name:
SELECT CURRENT_ORGANIZATION_NAME();

-- =============================================================================
-- OPTION B: Organization Listing (Internal Marketplace)
-- =============================================================================
-- Share within your organization across accounts.
-- Requires Enterprise Edition or higher.

-- Prerequisites:
--   1. ORGADMIN role must enable Internal Marketplace
--   2. CREATE ORGANIZATION LISTING privilege

-- Grant listing privileges to a role:
-- USE ROLE ACCOUNTADMIN;
-- GRANT CREATE SHARE ON ACCOUNT TO ROLE data_provider_role;
-- GRANT CREATE ORGANIZATION LISTING ON ACCOUNT TO ROLE data_provider_role;

-- Create via Provider Studio > Internal Marketplace:
--   1. Navigate to Marketplace > Provider Studio
--   2. Create Listing > Internal Marketplace
--   3. Set listing title
--   4. Select a provider profile
--   5. Click Add Data Product > + Select > choose objects
--   6. Generate data dictionary (optional but recommended)
--   7. Publish

-- Consumers access via the Universal Listing Locator (ULL):
-- SELECT * FROM ORGDATACLOUD${{PROFILE}}${{LISTING_NAME}}.{{SCHEMA}}.{{TABLE}};

-- =============================================================================
-- OPTION C: Marketplace Listing (Public)
-- =============================================================================
-- One-time setup (if not done before):
--   1. Accept Provider and Consumer Terms in Snowsight
--   2. Create a provider profile in Provider Studio > Profiles
--   3. (For paid listings) Set up Stripe integration

-- Create via Provider Studio:
--   1. Navigate to Marketplace > Provider Studio
--   2. Create Listing > Snowflake Marketplace
--   3. Choose: Free, Limited Trial, or Paid
--   4. Add data product (share or application package)
--   5. Fill in listing metadata:
--      - Title, subtitle, description
--      - Sample SQL queries
--      - Business needs / use cases
--      - Data dictionary
--   6. Submit for approval (marketplace listings require approval)

-- =============================================================================
-- Verify listings
-- =============================================================================
SHOW LISTINGS;
-- DESCRIBE LISTING {{LISTING_NAME}};
