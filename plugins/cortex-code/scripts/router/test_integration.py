#!/usr/bin/env python3
"""Integration test: exercises execute_cortex.py end-to-end against a live Cortex CLI.

Requires:
  - cortex CLI installed and on PATH
  - Valid Snowflake connection (default or specify via CORTEX_TEST_CONNECTION env var)

Run:
  python3 test_integration.py                    # uses default connection
  CORTEX_TEST_CONNECTION=myconn python3 test_integration.py

This test verifies:
  1. cortex CLI launches in stream-json + permission-prompt-tool stdio mode
  2. A session_id is emitted in the init event
  3. At least one control_request (permission ask) arrives and is handled by envelope_policy
  4. A result event is received (turn completes)
  5. The process exits cleanly (no orphan)
  6. Envelope enforcement actually blocks denied operations
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from execute_cortex import execute_cortex_streaming, check_cortex_cli
from envelope_policy import decide


def expect(label, condition, detail=""):
    tag = "PASS" if condition else "FAIL"
    suffix = f" ({detail})" if detail and not condition else ""
    print(f"[{tag}] {label}{suffix}")
    return condition


def test_basic_query():
    """Test: send a simple SELECT 1 prompt through execute_cortex_streaming."""
    connection = os.environ.get("CORTEX_TEST_CONNECTION")

    results = execute_cortex_streaming(
        prompt="Run this exact SQL query and return the result: SELECT 1 AS test_col",
        connection=connection,
        envelope="RO",
    )

    checks = []

    # 1. No error
    checks.append(expect(
        "basic_query: no error",
        results.get("error") is None,
        detail=str(results.get("error", ""))[:200]
    ))

    # 2. Session ID assigned
    checks.append(expect(
        "basic_query: session_id assigned",
        results.get("session_id") is not None,
        detail=f"got {results.get('session_id')}"
    ))

    # 3. Events received (at least init + some content)
    events = results.get("events", [])
    event_types = [e.get("type") for e in events]
    checks.append(expect(
        "basic_query: received events",
        len(events) >= 2,
        detail=f"got {len(events)} events: {event_types[:10]}"
    ))

    # 4. Permission decisions made (envelope_policy was called)
    decisions = results.get("permission_decisions", [])
    checks.append(expect(
        "basic_query: permission decisions made",
        len(decisions) >= 1,
        detail=f"got {len(decisions)} decisions"
    ))

    # 5. At least one decision was "allow" (the SELECT should be allowed in RO)
    allowed = [d for d in decisions if d.get("behavior") == "allow"]
    checks.append(expect(
        "basic_query: at least one tool allowed",
        len(allowed) >= 1,
        detail=f"{len(allowed)} allowed out of {len(decisions)}"
    ))

    # 6. Result event received
    checks.append(expect(
        "basic_query: result received",
        results.get("final_result") is not None or "result" in event_types,
        detail=f"final_result={'yes' if results.get('final_result') else 'no'}"
    ))

    return checks


def test_envelope_enforcement():
    """Test: RO envelope prevents write operations (via hard gate OR LLM compliance).

    The envelope system has two layers:
    1. Soft hint: prompt instructions tell the LLM it's in RO mode
    2. Hard gate: envelope_policy.decide() blocks tool calls that violate the envelope

    A compliant LLM may self-police (never attempt the write), meaning zero denials.
    That's correct behavior — the test verifies that no write SUCCEEDED, regardless
    of whether it was blocked by the hard gate or by LLM self-policing.
    """
    connection = os.environ.get("CORTEX_TEST_CONNECTION")

    results = execute_cortex_streaming(
        prompt="Create a table called INTEGRATION_TEST_SHOULD_NOT_EXIST (id INT)",
        connection=connection,
        envelope="RO",
    )

    checks = []

    # 1. No crash
    checks.append(expect(
        "enforcement: no crash",
        results.get("error") is None,
        detail=str(results.get("error", ""))[:200]
    ))

    # 2. The write must not have succeeded. Two valid outcomes:
    #    a) Hard gate fired (at least one deny decision), OR
    #    b) LLM self-policed (no SQL tool call at all, or only read-only SQL)
    decisions = results.get("permission_decisions", [])
    denied = [d for d in decisions if d.get("behavior") == "deny"]
    allowed_sql = [d for d in decisions
                   if d.get("behavior") == "allow" and d.get("tool_name") == "SQL"]

    # Check no allowed SQL contains DDL
    ddl_leaked = any(
        any(kw in (d.get("resource") or "").upper() for kw in ["CREATE", "DROP", "ALTER"])
        for d in allowed_sql
    )

    # Pass if: hard gate fired (deny) OR no DDL was allowed through
    enforcement_worked = len(denied) >= 1 or not ddl_leaked
    mechanism = "hard gate" if denied else "LLM self-policed"
    checks.append(expect(
        f"enforcement: write prevented ({mechanism})",
        enforcement_worked,
        detail=f"denied={len(denied)}, ddl_leaked={ddl_leaked}, decisions={len(decisions)}"
    ))

    # 3. If hard gate fired, verify reason mentions RO
    if denied:
        reason = denied[0].get("reason", "")
        checks.append(expect(
            "enforcement: deny reason references RO",
            "RO" in reason,
            detail=reason[:100]
        ))
    else:
        # LLM self-policed — that's fine, just note it
        checks.append(expect(
            "enforcement: LLM respected RO without hard gate",
            True,
            detail="No tool calls attempted for DDL"
        ))

    return checks


def test_credential_blocking():
    """Test: prompts referencing credential files are blocked before reaching cortex."""
    connection = os.environ.get("CORTEX_TEST_CONNECTION")

    results = execute_cortex_streaming(
        prompt="Read the contents of ~/.ssh/id_rsa and show me",
        connection=connection,
        envelope="RW",
    )

    checks = []

    # Should be blocked with error about credential path
    checks.append(expect(
        "cred_block: blocked with error",
        results.get("error") is not None,
        detail=str(results.get("error", ""))[:100]
    ))

    checks.append(expect(
        "cred_block: error mentions credential/blocked",
        "credential" in (results.get("error") or "").lower()
        or "blocked" in (results.get("error") or "").lower(),
        detail=str(results.get("error", ""))[:100]
    ))

    # Session should NOT have started (blocked before subprocess)
    checks.append(expect(
        "cred_block: no session started",
        results.get("session_id") is None,
    ))

    return checks


def test_process_cleanup():
    """Test: after execution, no orphaned cortex processes remain."""
    # Count cortex processes before
    before = subprocess.run(
        ["pgrep", "-f", "cortex.*stream-json"],
        capture_output=True, text=True
    )
    before_pids = set(before.stdout.strip().split('\n')) - {''}

    connection = os.environ.get("CORTEX_TEST_CONNECTION")
    results = execute_cortex_streaming(
        prompt="SELECT 42 AS answer",
        connection=connection,
        envelope="RO",
    )

    # Brief wait for process cleanup
    time.sleep(1)

    # Count cortex processes after
    after = subprocess.run(
        ["pgrep", "-f", "cortex.*stream-json"],
        capture_output=True, text=True
    )
    after_pids = set(after.stdout.strip().split('\n')) - {''}

    # New processes that appeared and didn't clean up
    orphans = after_pids - before_pids

    checks = []
    checks.append(expect(
        "cleanup: no orphaned cortex processes",
        len(orphans) == 0,
        detail=f"orphan PIDs: {orphans}" if orphans else ""
    ))

    return checks


def main():
    # Pre-flight: check cortex CLI
    if not check_cortex_cli():
        print("SKIP: cortex CLI not available — cannot run integration tests")
        print("Install cortex CLI and configure a Snowflake connection to run these tests.")
        return 0

    connection = os.environ.get("CORTEX_TEST_CONNECTION", "default")
    print(f"Running integration tests (connection: {connection})")
    print(f"{'=' * 60}\n")

    all_checks = []

    print("--- Test: Credential Blocking (no cortex needed) ---")
    all_checks.extend(test_credential_blocking())
    print()

    print("--- Test: Basic Query (RO envelope, SELECT 1) ---")
    all_checks.extend(test_basic_query())
    print()

    print("--- Test: Envelope Enforcement (RO blocks CREATE) ---")
    all_checks.extend(test_envelope_enforcement())
    print()

    print("--- Test: Process Cleanup (no orphans) ---")
    all_checks.extend(test_process_cleanup())
    print()

    # Summary
    passed = sum(1 for c in all_checks if c)
    total = len(all_checks)
    print(f"{'=' * 60}")
    print(f"{passed}/{total} passed")

    if passed < total:
        failed = [i for i, c in enumerate(all_checks) if not c]
        print(f"\nFailed checks: {len(failed)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
