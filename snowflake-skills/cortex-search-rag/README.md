# Cortex Search RAG

Build a Retrieval-Augmented Generation (RAG) pipeline using Snowflake Cortex Search and Cortex AI Functions — semantic search over your documents with LLM-powered answers.

## What It Does

This skill guides your AI coding agent through building an end-to-end RAG system:

1. **Setup** — Create a knowledge base table with sample documents
2. **Index** — Create a Cortex Search Service (vector + keyword hybrid search)
3. **Query** — Search for relevant documents with semantic understanding
4. **Generate** — Feed retrieved context to AI_COMPLETE for grounded answers
5. **Verify** — Test answer quality and citation accuracy

## Prerequisites

- Snowflake account with Cortex Search enabled
- `SNOWFLAKE.CORTEX_USER` database role granted to your role
- A warehouse (XS is fine for indexing small datasets)

## Quick Start

Ask your AI coding agent:

> "Build a RAG pipeline using Cortex Search to answer questions about my docs"

Or for a demo:

> "Set up a demo RAG system with Cortex Search and sample knowledge base articles"

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions and workflow |
| `templates/setup.sql` | Create DB, knowledge base table, seed sample docs |
| `templates/search-service.sql` | Create Cortex Search Service + test queries |
| `templates/rag-query.sql` | Full RAG pattern: search → context → AI_COMPLETE |
