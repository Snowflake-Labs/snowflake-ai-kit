#!/usr/bin/env python3
"""Get a fresh Snowflake session token for the MCP server.

Uses the Snowflake Python connector with externalbrowser auth.
The connector handles token lifecycle internally.

Usage:
    export CLOUD_AGENTS_SESSION_TOKEN=$(python3 get_token.py)
    node src/server.mjs
"""
import snowflake.connector
import os
import sys

ACCOUNT = os.environ.get("CLOUD_AGENTS_ACCOUNT", "")
USER = os.environ.get("CLOUD_AGENTS_USER")

def get_token():
    user = USER
    account = ACCOUNT
    if not account:
        account = input("Snowflake account (e.g. myorg-myaccount): ").strip()
        if not account:
            print("ERROR: Account is required.", file=sys.stderr)
            sys.exit(1)
    if not user:
        user = input("Snowflake username: ").strip()
        if not user:
            print("ERROR: Username is required.", file=sys.stderr)
            sys.exit(1)

    conn = snowflake.connector.connect(
        account=account,
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
