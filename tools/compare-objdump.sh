#!/usr/bin/env bash
# Compare discovered bytes and future gadget output against objdump disassembly.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <target-file>"
  exit 2
fi

TARGET="$1"
command -v objdump >/dev/null 2>&1 || { echo "error: objdump not found"; exit 127; }

objdump -d -Mintel "$TARGET"
