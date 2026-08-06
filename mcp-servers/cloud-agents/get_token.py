#!/usr/bin/env python3
"""Get a fresh Snowhouse session token for the MCP server.

Uses the Snowflake Python connector with externalbrowser auth.
The connector handles token lifecycle internally.

Usage:
    export CLOUD_AGENTS_SESSION_TOKEN=$(python3 get_token.py)
    node src/server.mjs
"""
import snowflake.connector
import os
import sys

ACCOUNT = os.environ.get("CLOUD_AGENTS_ACCOUNT", "snowhouse")
USER = os.environ.get("CLOUD_AGENTS_USER")

def get_token():
    user = USER
    if not user:
        user = input("Snowhouse username: ").strip()
        if not user:
            print("ERROR: Username is required.", file=sys.stderr)
            sys.exit(1)

    conn = snowflake.connector.connect(
        account=ACCOUNT,
        user=user,
        authenticator="externalbrowser",
        client_session_keep_alive=True,
    )
    token = conn.rest.token
    # Don't close — keep-alive means the token stays valid
    # Print to stdout for shell capture
    print(token, end="")
    return token

if __name__ == "__main__":
    get_token()
