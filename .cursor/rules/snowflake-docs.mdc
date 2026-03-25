---
name: snowflake-docs
description: "Snowflake documentation reference via llms.txt index. Use when other skills do not cover a topic, looking up unfamiliar Snowflake features, or needing authoritative docs on SQL syntax, APIs, platform capabilities, or configuration. Triggers: snowflake docs, documentation, look up, reference, sql syntax, how does snowflake, what is, api reference, llms.txt."
---

# Snowflake Documentation Reference

This skill provides access to the complete Snowflake documentation index via llms.txt. Use it as a **reference resource** to supplement other skills.

## Role of This Skill

This is a **reference skill**, not an action skill. Use it to:

## When to Use

- Other skills don't cover the topic the user is asking about
- Looking up unfamiliar SQL syntax, functions, or DDL commands
- Finding authoritative guidance on platform features and configuration
- Needing API reference details, error code explanations, or edge cases
- Answering "How does Snowflake handle X?" questions

**Always prefer using specific skills for workflows** (cortex-agents, dynamic-tables-pipeline, etc.). Use this skill when you need reference documentation that no other skill covers.

## How to Use

Fetch the llms.txt documentation index:

**URL:** `https://docs.snowflake.com/llms.txt`

Use `web_fetch` to retrieve the index, then:

1. Search for relevant sections/links in the index
2. Fetch specific `.md` pages for detailed guidance (each link in the index points to an LLM-optimized `.md` version of the page)
3. Apply what you learn

## Documentation Structure

The llms.txt file is organized by category:

| Section | Coverage |
|---------|----------|
| **General** | Overview, getting started, tutorials |
| **SQL Reference** | Every SQL command, function, data type, class method |
| **User Guide** | Data loading, querying, security, account management |
| **Developer Guide** | Snowpark, UDFs, stored procedures, Streamlit, Native Apps |
| **Connectors & Drivers** | Python, JDBC, ODBC, Node.js, Go, .NET |
| **Collaboration & Marketplace** | Data sharing, listings, Snowflake Marketplace |
| **Migrations** | Oracle, Teradata, and other platform migrations |
| **Programmatic Access** | REST APIs, Snowflake CLI |

## Example Usage

**Scenario:** User asks about an unfamiliar SQL function

1. Fetch `https://docs.snowflake.com/llms.txt`
2. Search for the function name in the index
3. Fetch the specific `.md` page for full syntax and examples
4. Use `snowflake_sql_execute` to run the query

**Scenario:** User needs details on a feature another skill covers broadly

1. Use the specific skill for the workflow (e.g., `cortex-search-rag` for RAG)
2. Fetch the llms.txt index for deeper documentation on a sub-topic
3. Read the specific doc page for configuration details or edge cases

## Related Skills

All other Snowflake skills in this repo cover specific workflows. This skill fills the gaps when you need raw documentation:

- **cortex-agents** — Cortex Agent creation and orchestration
- **cortex-ai-pipeline** — AI enrichment with Cortex AI Functions
- **cortex-search-rag** — RAG with Cortex Search
- **dynamic-tables-pipeline** — Declarative data pipelines
- **iceberg-tables** — Apache Iceberg on Snowflake
- **ml-model-registry** — ML model lifecycle
- **streamlit-in-snowflake** — Streamlit app deployment
- **data-product-sharing** — Secure sharing and listings
