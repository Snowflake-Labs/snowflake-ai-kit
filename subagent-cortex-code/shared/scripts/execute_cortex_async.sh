#!/bin/bash
# Async wrapper for Codex CLI - starts job and returns immediately.

set -euo pipefail

PROMPT=""
ENVELOPE="RO"
CONNECTION=""
OUTPUT_FILE=""
PID_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --prompt)
            PROMPT="$2"
            shift 2
            ;;
        --envelope)
            ENVELOPE="$2"
            shift 2
            ;;
        --connection|-c)
            CONNECTION="$2"
            shift 2
            ;;
        --output-file)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --pid-file)
            PID_FILE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

if [[ -z "$OUTPUT_FILE" ]]; then
    OUTPUT_FILE="$(mktemp "${TMPDIR:-/tmp}/codex-cortex.XXXXXX.json")"
fi
if [[ -z "$PID_FILE" ]]; then
    PID_FILE="${OUTPUT_FILE}.pid"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CMD=("python3" "$SCRIPT_DIR/execute_cortex.py" "--prompt" "$PROMPT" "--envelope" "$ENVELOPE" "--output-file" "$OUTPUT_FILE")

if [[ -n "$CONNECTION" ]]; then
    CMD+=("--connection" "$CONNECTION")
fi

python3 -c 'import json, sys, time; json.dump({"status":"running","started":int(time.time())}, open(sys.argv[1], "w"))' "$OUTPUT_FILE"

nohup "${CMD[@]}" </dev/null >/dev/null 2>&1 &
JOB_PID=$!
echo "$JOB_PID" > "$PID_FILE"
disown

echo "⏳ Cortex query started (PID: $JOB_PID)"
echo "📁 Results will be written to: $OUTPUT_FILE"
echo "📁 PID file: $PID_FILE"
echo "⏱️  Expected completion: 15-20 seconds"
echo ""
echo "To check results, run:"
echo "  cat '$OUTPUT_FILE' | python3 -c 'import sys, json; r=json.load(sys.stdin); print(r.get(\"final_result\", \"Still running...\"))'"
