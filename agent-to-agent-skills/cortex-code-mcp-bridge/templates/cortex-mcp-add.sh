#!/usr/bin/env bash
# Add Cortex Code as an MCP server to another Cortex Code instance.
# Replace {{CONNECTION_NAME}} with your Snowflake connection name.

cortex mcp add cortex-code-bridge cortex -- mcp serve --connection "{{CONNECTION_NAME}}"
