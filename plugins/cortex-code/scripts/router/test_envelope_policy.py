#!/usr/bin/env python3
"""Unit tests for envelope_policy.decide().

Run: python3 test_envelope_policy.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from envelope_policy import decide


def expect(envelope, tool, action, resource, want_behavior):
    behavior, reason = decide(envelope, tool, action, resource)
    ok = behavior == want_behavior
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {envelope:<8} {tool:<12} {resource!r:<60}  "
          f"got={behavior} want={want_behavior}")
    if not ok:
        print(f"       reason: {reason}")
    return ok


cases = [
    # RO: read-only SQL
    ("RO", "SQL", "execute_command", "SELECT 1",                       "allow"),
    ("RO", "SQL", "execute_command", "SHOW WAREHOUSES",                "allow"),
    ("RO", "SQL", "execute_command", "  select count(*) from t",       "allow"),
    ("RO", "SQL", "execute_command", "CREATE TABLE foo (x INT)",       "deny"),
    ("RO", "SQL", "execute_command", "DROP TABLE foo",                 "deny"),
    ("RO", "SQL", "execute_command", "INSERT INTO t VALUES (1)",       "deny"),
    # RO: file ops
    ("RO", "Read",  "file_read",  "/tmp/x",                            "allow"),
    ("RO", "Write", "file_write", "/tmp/x",                            "deny"),
    ("RO", "Edit",  "file_edit",  "/tmp/x",                            "deny"),
    # RO: bash -- redirect makes it a write
    ("RO", "Bash", "execute_command", "ls /tmp",                       "allow"),
    ("RO", "Bash", "execute_command", "cat /etc/hosts",                "allow"),
    ("RO", "Bash", "execute_command", "echo hi > /tmp/foo",            "deny"),
    ("RO", "Bash", "execute_command", "echo hi >> /tmp/foo",           "deny"),
    ("RO", "Bash", "execute_command", "ls && rm -rf /tmp/x",           "deny"),
    ("RO", "Bash", "execute_command", "cat $(echo /etc/passwd)",       "deny"),
    ("RO", "Bash", "execute_command", "sudo ls",                       "deny"),
    # RW: allow most, block destructive
    ("RW", "SQL",  "execute_command", "DROP TABLE prod",               "allow"),
    ("RW", "Write","file_write",      "/tmp/x",                        "allow"),
    ("RW", "Bash", "execute_command", "echo hi > /tmp/foo",            "allow"),
    ("RW", "Bash", "execute_command", "rm -rf /tmp/x",                 "deny"),
    ("RW", "Bash", "execute_command", "git push --force",              "deny"),
    ("RW", "Bash", "execute_command", "git reset --hard HEAD~1",       "deny"),
    ("RW", "Bash", "execute_command", "sudo dd if=/dev/zero of=/dev/sda", "deny"),
    # RESEARCH: read + web
    ("RESEARCH", "WebSearch", "web_access", "cortex docs",             "allow"),
    ("RESEARCH", "WebFetch",  "web_access", "https://example.com",     "allow"),
    ("RESEARCH", "Read",      "file_read",  "/tmp/x",                  "allow"),
    ("RESEARCH", "SQL",       "execute_command", "SELECT 1",           "allow"),
    ("RESEARCH", "SQL",       "execute_command", "CREATE TABLE t(x)",  "deny"),
    ("RESEARCH", "Write",     "file_write", "/tmp/x",                  "deny"),
    ("RESEARCH", "Bash",      "execute_command", "echo > /tmp/x",      "deny"),
    # DEPLOY: allow all except nuke
    ("DEPLOY", "SQL",  "execute_command", "DROP DATABASE prod",        "allow"),
    ("DEPLOY", "Bash", "execute_command", "rm -rf /",                  "deny"),
    ("DEPLOY", "Bash", "execute_command", "mkfs.ext4 /dev/sda1",       "deny"),
    ("DEPLOY", "Write","file_write",      "/etc/passwd",               "allow"),
]


def main():
    fails = 0
    for envelope, tool, action, resource, want in cases:
        if not expect(envelope, tool, action, resource, want):
            fails += 1
    print(f"\n{len(cases) - fails}/{len(cases)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
