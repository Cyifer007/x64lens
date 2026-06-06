#!/usr/bin/env bash
# Compare x64lens mitigation output against checksec when checksec is available.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <target-file>"
  exit 2
fi

TARGET="$1"
command -v checksec >/dev/null 2>&1 || { echo "error: checksec not found"; exit 127; }

checksec --file="$TARGET"
