#!/usr/bin/env python3
"""Token provider that keeps a Snowhouse session alive and writes the token to a file.

The MCP server reads the token from this file on each request.
Run this in the background before starting the MCP server.

Usage:
    python3 token_provider.py &
    # Token is written to /tmp/cloud-agents-token.txt
    # Then start the MCP server:
    CLOUD_AGENTS_SESSION_TOKEN=$(cat /tmp/cloud-agents-token.txt) node src/server.mjs
"""
import snowflake.connector
import time
import sys
import os
import signal

TOKEN_FILE = os.environ.get("CLOUD_AGENTS_TOKEN_FILE", "/tmp/cloud-agents-token.txt")
REFRESH_INTERVAL = 60  # seconds between heartbeats

ACCOUNT = os.environ.get("CLOUD_AGENTS_ACCOUNT", "snowhouse")
USER = os.environ.get("CLOUD_AGENTS_USER")  # None = auto-detect from SSO

def main():
    connect_args = {
        "account": ACCOUNT,
        "authenticator": "externalbrowser",
        "client_session_keep_alive": True,
    }
    if USER:
        connect_args["user"] = USER

    conn = snowflake.connector.connect(**connect_args)

    token = conn.rest.token
    with open(TOKEN_FILE, "w") as f:
        f.write(token)

    print(f"Token provider running. Token written to {TOKEN_FILE}", file=sys.stderr)
    print(f"Token length: {len(token)}", file=sys.stderr)

    def cleanup(sig, frame):
        print("\nShutting down token provider...", file=sys.stderr)
        try:
            os.unlink(TOKEN_FILE)
        except OSError:
            pass
        conn.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Keep session alive with periodic heartbeats
    while True:
        time.sleep(REFRESH_INTERVAL)
        try:
            conn.cursor().execute("SELECT 1")
            # Refresh token file in case it rotated
            new_token = conn.rest.token
            if new_token != token:
                token = new_token
                with open(TOKEN_FILE, "w") as f:
                    f.write(token)
                print("Token refreshed", file=sys.stderr)
        except Exception as e:
            print(f"Heartbeat failed: {e}", file=sys.stderr)
            break

    cleanup(None, None)

if __name__ == "__main__":
    main()
