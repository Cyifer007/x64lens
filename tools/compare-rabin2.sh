#!/usr/bin/env bash
# Compare x64lens mitigation output against rabin2 metadata when rabin2 is available.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <target-file> [x64lens-binary]"
  exit 2
fi

TARGET="$1"
TOOL="${2:-./build/x64lens}"
command -v rabin2 >/dev/null 2>&1 || { echo "error: rabin2 not found"; exit 127; }
if [[ ! -x "$TOOL" ]]; then
  echo "error: x64lens binary is not executable: $TOOL" >&2
  exit 1
fi

printf '\n== x64lens mitigations ==\n'
"$TOOL" mitigations "$TARGET"

printf '\n== rabin2 -I ==\n'
rabin2 -I "$TARGET"
