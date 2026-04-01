#!/usr/bin/env python3
"""Validate the Cortex Code MCP bridge by testing the JSON-RPC handshake.

Spawns `cortex mcp serve`, sends initialize + tools/list requests over
newline-delimited JSON-RPC, and prints the available tools.
Exits 0 on success, 1 on failure.

Requires: Cortex Code CLI (cortex) installed and in PATH.
No external Python dependencies — stdlib only.
"""

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time

# JSON-RPC message ID counter
_msg_id = 0


def _next_id() -> int:
    global _msg_id
    _msg_id += 1
    return _msg_id


def _make_request(method: str, params: dict | None = None) -> bytes:
    """Build a newline-delimited JSON-RPC 2.0 request."""
    body = {
        "jsonrpc": "2.0",
        "id": _next_id(),
        "method": method,
    }
    if params:
        body["params"] = params

    return (json.dumps(body) + "\n").encode()


def _make_notification(method: str) -> bytes:
    """Build a JSON-RPC 2.0 notification (no id)."""
    body = {
        "jsonrpc": "2.0",
        "method": method,
    }
    return (json.dumps(body) + "\n").encode()


def _read_response(fd: int, timeout: float = 30.0) -> dict | None:
    """Read a JSON-RPC response using non-blocking I/O.

    Cortex Code's MCP server uses newline-delimited JSON (not Content-Length framing).
    """
    buf = b""
    start = time.time()

    while time.time() - start < timeout:
        try:
            chunk = os.read(fd, 65536)
            if chunk:
                buf += chunk
                # Check for complete JSON lines
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except BlockingIOError:
            pass
        time.sleep(0.25)

    if buf.strip():
        try:
            return json.loads(buf.strip())
        except json.JSONDecodeError:
            pass

    return None


def validate_bridge(connection: str | None = None, timeout: float = 30.0) -> bool:
    """Test the MCP bridge by performing a full handshake.

    Args:
        connection: Optional Snowflake connection name.
        timeout: Max seconds to wait for each response.

    Returns:
        True if the bridge is working, False otherwise.
    """
    if not shutil.which("cortex"):
        print("ERROR: cortex CLI not found in PATH", file=sys.stderr)
        print("Install: curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | sh", file=sys.stderr)
        return False

    # Build command
    cmd = ["cortex", "mcp", "serve"]
    if connection:
        cmd.extend(["--connection", connection])

    print(f"Starting MCP server: {' '.join(cmd)}", file=sys.stderr)

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as e:
        print(f"ERROR: Failed to start cortex: {e}", file=sys.stderr)
        return False

    # Set stdout to non-blocking
    fd = process.stdout.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    # Give the server a moment to start
    time.sleep(2)

    # Check process is alive
    if process.poll() is not None:
        stderr_out = process.stderr.read().decode(errors="replace")
        print(f"ERROR: MCP server exited immediately", file=sys.stderr)
        if stderr_out:
            print(f"Server stderr: {stderr_out[:500]}", file=sys.stderr)
        return False

    try:
        # Step 1: Send initialize request
        print("Sending initialize request...", file=sys.stderr)
        process.stdin.write(_make_request("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {
                "name": "cortex-code-mcp-bridge-validator",
                "version": "1.0.0",
            },
        }))
        process.stdin.flush()

        init_resp = _read_response(fd, timeout)
        if not init_resp:
            print("ERROR: No response to initialize request", file=sys.stderr)
            return False

        if "error" in init_resp:
            print(f"ERROR: Initialize failed: {init_resp['error']}", file=sys.stderr)
            return False

        server_info = init_resp.get("result", {}).get("serverInfo", {})
        print(f"Connected to: {server_info.get('name', 'unknown')} v{server_info.get('version', '?')}", file=sys.stderr)

        # Step 2: Send initialized notification
        process.stdin.write(_make_notification("notifications/initialized"))
        process.stdin.flush()
        time.sleep(0.5)

        # Step 3: List tools
        print("Requesting tool list...", file=sys.stderr)
        process.stdin.write(_make_request("tools/list"))
        process.stdin.flush()

        tools_resp = _read_response(fd, timeout)
        if not tools_resp:
            print("ERROR: No response to tools/list request", file=sys.stderr)
            return False

        if "error" in tools_resp:
            print(f"ERROR: tools/list failed: {tools_resp['error']}", file=sys.stderr)
            return False

        tools = tools_resp.get("result", {}).get("tools", [])
        if not tools:
            print("WARNING: Server returned 0 tools", file=sys.stderr)
            return False

        # Print tool summary
        print(f"\nAvailable tools ({len(tools)}):", file=sys.stderr)
        print("-" * 60, file=sys.stderr)
        for tool in tools:
            name = tool.get("name", "?")
            desc = tool.get("description", "")
            if len(desc) > 70:
                desc = desc[:67] + "..."
            print(f"  {name:<30s} {desc}", file=sys.stderr)
        print("-" * 60, file=sys.stderr)

        # Output structured JSON to stdout
        output = {
            "status": "ok",
            "server": server_info,
            "tool_count": len(tools),
            "tools": [
                {"name": t.get("name"), "description": t.get("description", "")}
                for t in tools
            ],
        }
        print(json.dumps(output, indent=2))

        print(f"\nBridge validated successfully — {len(tools)} tools available.", file=sys.stderr)
        return True

    except BrokenPipeError:
        print("ERROR: MCP server process terminated unexpectedly", file=sys.stderr)
        stderr_out = process.stderr.read().decode(errors="replace")
        if stderr_out:
            print(f"Server stderr: {stderr_out[:500]}", file=sys.stderr)
        return False

    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def main():
    parser = argparse.ArgumentParser(
        description="Validate the Cortex Code MCP bridge"
    )
    parser.add_argument(
        "--connection", "-c",
        help="Snowflake connection name (uses default if omitted)",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=30.0,
        help="Timeout in seconds for each MCP request (default: 30)",
    )
    args = parser.parse_args()

    ok = validate_bridge(connection=args.connection, timeout=args.timeout)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
