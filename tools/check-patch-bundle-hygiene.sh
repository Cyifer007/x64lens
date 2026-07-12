#!/usr/bin/env bash
# Public entry point for path-safe x64lens patch/source ZIP inspection.
#
# The policy implementation lives in Python so archive member normalization,
# case-folded path checks, symlink detection, and regression tests share one
# deterministic implementation. The helper never extracts the archive.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <patch-bundle.zip> [more.zip ...]" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "patch-bundle-hygiene: error: python3 is required" >&2
  exit 127
fi

script_dir="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
exec python3 "$script_dir/check-patch-bundle-hygiene.py" "$@"
