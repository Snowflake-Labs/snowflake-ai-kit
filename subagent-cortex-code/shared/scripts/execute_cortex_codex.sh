#!/bin/bash
# Wrapper for Codex CLI that waits for Cortex completion and prints the result.

set -euo pipefail

PROMPT=""
ENVELOPE="RO"
CONNECTION=""
OUTPUT_FILE="${TMPDIR:-/tmp}/codex-cortex.$$.json"
OUTPUT_FILE_PROVIDED=0

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
            OUTPUT_FILE_PROVIDED=1
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

if [[ $OUTPUT_FILE_PROVIDED -eq 0 ]]; then
    OUTPUT_FILE="$(mktemp "${TMPDIR:-/tmp}/codex-cortex.XXXXXX.json")"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CMD=("python3" "$SCRIPT_DIR/execute_cortex.py" "--prompt" "$PROMPT" "--envelope" "$ENVELOPE" "--output-file" "$OUTPUT_FILE")

if [[ -n "$CONNECTION" ]]; then
    CMD+=("--connection" "$CONNECTION")
fi

echo "⏳ Starting Cortex query (this takes 15-30 seconds)..."
"${CMD[@]}" </dev/null 2>/dev/null

echo "✓ Query completed, reading results..."
sleep 1

if [[ -f "$OUTPUT_FILE" ]]; then
    python3 -c 'import json, sys; r=json.load(open(sys.argv[1])); print(r.get("final_result", "No result"))' "$OUTPUT_FILE"
else
    echo "Error: Output file not created"
    exit 1
fi
