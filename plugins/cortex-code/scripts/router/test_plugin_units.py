#!/usr/bin/env python3
"""Unit tests for plugin modules: session_state, check_credential_paths, build_envelope_prompt.

Run: python3 test_plugin_units.py

Complements test_envelope_policy.py (which covers decide()). These tests
cover the other pure/near-pure functions in the plugin router.
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import session_state
from execute_cortex import (
    CREDENTIAL_PATTERNS,
    ENVELOPE_INSTRUCTIONS,
    build_envelope_prompt,
    check_credential_paths,
)


def expect(label, got, want):
    ok = got == want
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {label}")
    if not ok:
        print(f"       got={got!r}  want={want!r}")
    return ok


# ── check_credential_paths ────────────────────────────────────────

def test_credential_paths():
    cases = [
        # (prompt, expected_match_or_None)
        ("Read the file at ~/.ssh/id_rsa", ".ssh/"),
        ("Show me .snowflake/connections.toml", ".snowflake/"),
        ("Load the .env file", ".env"),
        ("Open credentials.json", "credentials.json"),
        ("Use the _key.p8 file", "_key.p8"),
        ("Check .aws/credentials", ".aws/credentials"),
        ("Read .kube/config", ".kube/config"),
        ("Show me private_key contents", "private_key"),
        ("Upload secret_key to S3", "secret_key"),
        ("Read api_key_file from disk", "api_key_file"),
        ("Read token.json from disk", "token.json"),
        # Safe prompts — no match
        ("Show me the weather", None),
        ("SELECT * FROM my_table", None),
        ("List files in /tmp", None),
        ("Explain how envelopes work", None),
        ("What is the .env.example format?", ".env"),  # substring match — intentional
    ]
    results = []
    for prompt, want in cases:
        got = check_credential_paths(prompt)
        results.append(expect(f"cred_check: {prompt[:50]}", got, want))
    return results


# ── build_envelope_prompt ─────────────────────────────────────────

def test_build_envelope_prompt():
    results = []
    prompt = "Do something"

    # Known envelopes prepend instructions
    for env in ("RO", "RW", "RESEARCH", "DEPLOY"):
        built = build_envelope_prompt(prompt, env)
        has_prefix = built.startswith(ENVELOPE_INSTRUCTIONS[env])
        has_prompt = prompt in built
        results.append(expect(f"envelope_{env}: starts with instructions", has_prefix, True))
        results.append(expect(f"envelope_{env}: contains user prompt", has_prompt, True))

    # Unknown envelope returns prompt unchanged
    built = build_envelope_prompt(prompt, "UNKNOWN")
    results.append(expect("envelope_UNKNOWN: returns raw prompt", built, prompt))

    # Empty envelope returns prompt unchanged
    built = build_envelope_prompt(prompt, "")
    results.append(expect("envelope_empty: returns raw prompt", built, prompt))

    return results


# ── session_state ─────────────────────────────────────────────────

def test_session_state():
    results = []

    # Use a temp directory so we don't touch real state
    original_dir = session_state.STATE_DIR
    original_file = session_state.STATE_FILE_NAME

    tmpdir = Path(tempfile.mkdtemp(prefix="test_session_"))
    session_state.STATE_DIR = tmpdir

    try:
        # 1. load returns None when no state file exists
        result = session_state.load_active_session()
        results.append(expect("session: load returns None when empty", result, None))

        # 2. save then load round-trips
        session_state.save_active_session("test-session-abc123")
        result = session_state.load_active_session()
        results.append(expect("session: save/load round-trip", result is not None, True))
        if result:
            results.append(expect("session: correct session_id", result["session_id"], "test-session-abc123"))
            results.append(expect("session: has timestamp", "timestamp" in result, True))

        # 3. save empty string is a no-op
        session_state.save_active_session("")
        result = session_state.load_active_session()
        results.append(expect("session: save('') is no-op, old session preserved",
                              result["session_id"] if result else None, "test-session-abc123"))

        # 4. clear removes state
        session_state.clear_active_session()
        result = session_state.load_active_session()
        results.append(expect("session: clear removes state", result, None))

        # 5. stale session returns None
        session_state.save_active_session("stale-session")
        state_path = tmpdir / session_state.STATE_FILE_NAME
        data = json.loads(state_path.read_text())
        data["timestamp"] = time.time() - session_state.STALE_AFTER_SECONDS - 1
        state_path.write_text(json.dumps(data))
        result = session_state.load_active_session()
        results.append(expect("session: stale session returns None", result, None))

        # 6. corrupt JSON returns None
        state_path.write_text("NOT VALID JSON{{{")
        result = session_state.load_active_session()
        results.append(expect("session: corrupt JSON returns None", result, None))

        # 7. missing session_id returns None
        state_path.write_text(json.dumps({"timestamp": time.time()}))
        result = session_state.load_active_session()
        results.append(expect("session: missing session_id returns None", result, None))

        # 8. clear on already-cleared is a no-op (no crash)
        session_state.clear_active_session()
        session_state.clear_active_session()
        results.append(expect("session: double-clear is safe", True, True))

    finally:
        session_state.STATE_DIR = original_dir
        # Clean up
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    return results


# ── _send_control_response format ─────────────────────────────────

def test_control_response_format():
    """Verify _send_control_response writes valid JSON with expected schema."""
    import io
    from execute_cortex import _send_control_response

    results = []

    buf = io.StringIO()
    _send_control_response(buf, "req-123", "allow", "test reason")
    raw = buf.getvalue()
    try:
        payload = json.loads(raw.strip())
        results.append(expect("ctrl_resp: valid JSON", True, True))
        results.append(expect("ctrl_resp: type=control_response",
                              payload.get("type"), "control_response"))
        resp = payload.get("response", {})
        results.append(expect("ctrl_resp: request_id round-trips",
                              resp.get("request_id"), "req-123"))
        inner = resp.get("response", {})
        results.append(expect("ctrl_resp: behavior=allow",
                              inner.get("behavior"), "allow"))
        results.append(expect("ctrl_resp: message set",
                              inner.get("message"), "test reason"))
    except json.JSONDecodeError:
        results.append(expect("ctrl_resp: valid JSON", False, True))

    # Deny case
    buf2 = io.StringIO()
    _send_control_response(buf2, "req-456", "deny", "blocked")
    payload2 = json.loads(buf2.getvalue().strip())
    inner2 = payload2["response"]["response"]
    results.append(expect("ctrl_resp_deny: behavior=deny",
                          inner2.get("behavior"), "deny"))

    return results


# ── Main ──────────────────────────────────────────────────────────

def main():
    all_results = []
    all_results.extend(test_credential_paths())
    all_results.extend(test_build_envelope_prompt())
    all_results.extend(test_session_state())
    all_results.extend(test_control_response_format())

    passed = sum(1 for r in all_results if r)
    total = len(all_results)
    print(f"\n{passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
