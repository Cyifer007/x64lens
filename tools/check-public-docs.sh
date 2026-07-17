#!/usr/bin/env bash
# check-public-docs.sh
#
# Compatibility entry point for the shared public text/content policy.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec python3 "$ROOT_DIR/tools/check-public-content.py" "$@"
