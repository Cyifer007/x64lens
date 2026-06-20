#!/usr/bin/env bash
# Compatibility wrapper for the deterministic Sprint 7 hostile-input runner.
# The initial campaign is mutation-based and reproducible, not coverage-guided.

set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"
exec python3 tools/malformed-elf-smoke.py "$@"
