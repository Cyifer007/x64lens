#!/usr/bin/env bash
# Compare future x64lens gadget discovery against ROPgadget output.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <target-file>"
  exit 2
fi

TARGET="$1"
command -v ROPgadget >/dev/null 2>&1 || { echo "error: ROPgadget not found"; exit 127; }

ROPgadget --binary "$TARGET"
