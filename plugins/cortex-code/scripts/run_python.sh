#!/usr/bin/env bash
# Probe interpreters without consuming hook stdin, then run the command exactly once.
# Order: python3 (standard), python (if Python 3), py -3 (Windows launcher).
for candidate in python3 python; do
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' </dev/null >/dev/null 2>&1; then
        exec "$candidate" -u "$@"
    fi
done
if command -v py >/dev/null 2>&1 && py -3 -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' </dev/null >/dev/null 2>&1; then
    exec py -3 -u "$@"
fi

printf '%s\n' 'Cortex Code plugin requires Python 3 on PATH (python3 preferred, python accepted, py -3 on Windows).' >&2
exit 127