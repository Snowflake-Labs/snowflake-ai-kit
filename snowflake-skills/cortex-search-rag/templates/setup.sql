-- ============================================================
-- Cortex Search RAG — Setup
-- Creates a knowledge base table with sample documents
-- ============================================================

USE ROLE {{ROLE}};
USE WAREHOUSE {{WAREHOUSE}};

CREATE DATABASE IF NOT EXISTS {{DATABASE}};
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.{{SCHEMA}};
USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Grant Cortex Search access
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE {{ROLE}};

-- Create knowledge base table with change tracking
CREATE OR REPLACE TABLE KNOWLEDGE_BASE (
    ID          NUMBER AUTOINCREMENT,
    TITLE       VARCHAR,
    CATEGORY    VARCHAR,
    SOURCE_TYPE VARCHAR,
    BODY        VARCHAR,
    UPDATED_AT  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
CHANGE_TRACKING = TRUE;

-- Seed sample knowledge base articles
INSERT INTO KNOWLEDGE_BASE (TITLE, CATEGORY, SOURCE_TYPE, BODY)
VALUES
    ('Return Policy Overview', 'policies', 'faq',
     'Customers may return most items within 30 days of purchase for a full refund. Electronics have a 15-day return window. Opened laptops and custom-built PCs are subject to a 10% restocking fee. Items must be in original packaging with all accessories. Gift cards and downloadable software are non-refundable. Returns without a receipt may be issued store credit at the lowest price in the past 60 days.'),

    ('Shipping Options and Delivery', 'logistics', 'faq',
     'We offer three shipping tiers: Standard (5-7 business days, free over $50), Express (2-3 business days, $12.99), and Next-Day ($24.99, order by 2 PM local time). Rural and remote addresses may experience 1-2 additional days. Freight items (over 70 lbs) ship via LTL carrier with delivery appointment. International shipping is available to 40+ countries through our global logistics partner. Tracking numbers are emailed within 4 hours of shipment.'),

    ('Loyalty Program Guide', 'programs', 'article',
     'Our Rewards Plus program has three tiers: Silver (0-499 points), Gold (500-1999 points), and Platinum (2000+ points). Earn 1 point per dollar spent. Silver members get free standard shipping. Gold members earn 1.5x points and early sale access. Platinum members get 2x points, free express shipping, and a dedicated support line. Points expire after 12 months of account inactivity. Birthday month gives double points on all purchases.'),

    ('Product Warranty Information', 'policies', 'article',
     'All electronics carry a minimum 1-year manufacturer warranty. Extended warranty plans are available: 2-year ($49.99) and 3-year ($79.99). Warranty covers defects in materials and workmanship under normal use. Accidental damage, water damage, and unauthorized repairs void the warranty. To file a claim, contact support with your order number and description of the issue. Replacement or repair decisions are made within 48 hours.'),

    ('Account Security Best Practices', 'support', 'faq',
     'Enable two-factor authentication (2FA) in Account Settings > Security. We support authenticator apps (recommended), SMS codes, and email verification. Never share your password or one-time codes. Our team will never ask for your password via email or phone. If you suspect unauthorized access, change your password immediately and contact support. Session logs are available under Account Settings > Activity for the past 90 days.'),

    ('Payment Methods and Billing', 'billing', 'faq',
     'We accept Visa, Mastercard, American Express, Discover, PayPal, Apple Pay, and Google Pay. Corporate accounts can request NET-30 terms with approved credit. Subscriptions are billed on the anniversary of signup. Failed payments are retried 3 times over 7 days before service suspension. Invoices are available in Account Settings > Billing History. Tax-exempt organizations can upload certificates under Tax Settings.'),

    ('API Rate Limits and Usage', 'technical', 'docs',
     'Free tier: 100 requests/minute, 10,000 requests/day. Pro tier: 1,000 requests/minute, 100,000 requests/day. Enterprise tier: custom limits, contact sales. Rate limit headers (X-RateLimit-Remaining, X-RateLimit-Reset) are included in every response. Exceeding limits returns HTTP 429 with a Retry-After header. Batch endpoints (/v2/batch/*) have separate limits: 10 concurrent batches, 10,000 items per batch. WebSocket connections are limited to 50 per account.'),

    ('Data Retention and Privacy', 'policies', 'article',
     'Customer data is retained for the duration of the account plus 90 days after deletion. Backup data is purged within 30 days of account deletion. We comply with GDPR, CCPA, and SOC 2 Type II requirements. Data processing agreements (DPAs) are available upon request. Users can export all personal data via Account Settings > Privacy > Data Export. Deletion requests are processed within 30 days per applicable regulations.'),

    ('Troubleshooting Connection Issues', 'support', 'faq',
     'If you cannot connect: 1) Check our status page at status.example.com. 2) Clear browser cache and cookies. 3) Try a different browser or incognito mode. 4) Disable VPN or proxy temporarily. 5) Check firewall settings — we require ports 443 (HTTPS) and 8443 (WebSocket). If the issue persists, run a traceroute to api.example.com and share the output with support. Average resolution time for connection issues is under 2 hours.'),

    ('Enterprise Plan Features', 'billing', 'article',
     'Enterprise plans include: unlimited API calls, dedicated infrastructure, 99.99% SLA, SSO/SAML integration, custom data residency (US, EU, APAC), priority support with 15-minute response for P1 issues, quarterly business reviews, and a dedicated customer success manager. Minimum contract: 12 months. Volume discounts available for commitments over $100K annually. Includes up to 500 seats; additional seats at $15/user/month.'),

    ('Mobile App Features', 'products', 'docs',
     'The mobile app (iOS 16+ and Android 12+) supports: push notifications for order updates, barcode scanning for quick product lookup, saved payment methods with biometric auth, offline mode for viewing past orders, and dark mode. App size: ~45 MB. Auto-sync happens every 15 minutes when on WiFi. Force sync available via pull-to-refresh. Beta features can be enabled under Settings > Labs.'),

    ('Bulk Order Process', 'logistics', 'article',
     'Orders of 50+ units qualify for bulk pricing (10-25% discount depending on product and quantity). Submit bulk requests through the Business portal or email bulk-orders@example.com with: product SKUs, quantities, delivery address, and requested delivery date. Quotes are provided within 24 hours. Bulk orders ship via freight (5-10 business days). Split shipments available at no extra charge. Net-30 payment terms for approved business accounts.'),

    ('Integration Partners', 'technical', 'docs',
     'Native integrations available for: Salesforce, HubSpot, Slack, Microsoft Teams, Jira, Zendesk, Shopify, and QuickBooks. All integrations use OAuth 2.0 for secure authentication. Webhook support for real-time event notifications (order placed, shipped, delivered, returned). Custom integrations via REST API (OpenAPI 3.0 spec available). SDKs provided for Python, JavaScript, Ruby, Go, and Java. Average integration setup time: 2-4 hours.'),

    ('Holiday Season Policies', 'policies', 'article',
     'Extended returns: items purchased between November 1 and December 31 can be returned until January 31 with proof of purchase. Holiday shipping deadlines: Standard by Dec 10, Express by Dec 18, Next-Day by Dec 22 for Christmas delivery. Gift wrapping available for $4.99 per item. Gift receipts included automatically for items shipped to a different address. Holiday customer support hours: 7 AM - 11 PM EST, 7 days a week from Nov 15 through Jan 5.'),

    ('Subscription Management', 'billing', 'faq',
     'Manage subscriptions in Account Settings > Subscriptions. Upgrade or downgrade takes effect at the next billing cycle. Downgrades may result in feature loss — review the comparison page before confirming. Cancel anytime; service continues until the end of the paid period. Annual plans receive a 20% discount vs monthly. Pausing is available for up to 3 months (retains your data and settings). Reactivation within the pause period restores all configurations.');

-- Verify
SELECT
    COUNT(*) AS total_docs,
    COUNT(DISTINCT CATEGORY) AS categories,
    COUNT(DISTINCT SOURCE_TYPE) AS source_types
FROM KNOWLEDGE_BASE;
