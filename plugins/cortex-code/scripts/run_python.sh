#!/usr/bin/env bash
# Probe interpreters without consuming hook stdin, then run the command exactly once.
for candidate in python3 python; do
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' </dev/null >/dev/null 2>&1; then
        exec "$candidate" -u "$@"
    fi
done

printf '%s\n' 'Cortex Code plugin requires Python 3 on PATH (python3 preferred, python accepted only if Python 3).' >&2
exit 127