# Snowflake Docs Reference

Points AI coding agents at Snowflake's complete documentation via the `llms.txt` index — an LLM-optimized listing of every doc page.

## What It Does

This is a **reference skill**, not an action skill. It teaches your AI agent how to look up Snowflake documentation when other skills don't cover a topic.

## When to Use

- Unfamiliar SQL syntax or functions
- Platform features not covered by other skills
- API reference, configuration options, or edge cases
- "How does Snowflake handle X?" questions

## How It Works

The agent fetches `https://docs.snowflake.com/llms.txt`, searches for relevant sections, then fetches specific `.md` pages for detailed guidance.

## Links

- [Snowflake llms.txt](https://docs.snowflake.com/llms.txt)
- [Snowflake Documentation](https://docs.snowflake.com/)
