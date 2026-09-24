# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email [security@snowflake.com](mailto:security@snowflake.com) with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a timeline for a fix.

## Scope

This repository contains markdown skills, shell scripts, and a Claude Code plugin. Security concerns include:

- **Credential leakage** — skills, templates, and scripts must never contain real tokens, keys, or passwords
- **Supply chain** — the install script downloads files from this GitHub repo; verify you're using the official `Snowflake-Labs/snowflake-ai-kit` source
- **Code injection** — skills instruct AI agents to generate code; skill authors should avoid patterns that could lead to SQL injection, command injection, or XSS in generated code

## Best Practices for Contributors

- Never commit credentials, tokens, API keys, or `.env` files
- Use synthetic/example data in all templates and references
- Review generated code patterns for OWASP Top 10 vulnerabilities
- Use environment variables for any sensitive configuration in examples

## Remote MCP delegation

The optional remote backend delegates through the host's native MCP connection.
It does not enforce the local CLI's per-command security envelopes or audit remote
inner tool calls. Its consent and context-handling instructions are host-agent
workflow guidance, not a programmatic authorization boundary. Enforce access in
the host and Snowflake; organizations requiring local envelope controls should
not enable remote mode. See the [remote approval and data boundaries](plugins/cortex-code/REMOTE_MCP.md#approval-and-data-boundaries).
