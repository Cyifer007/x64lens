#!/usr/bin/env bash
# Prepare local release artifacts.
#
# Sprint 1 creates unsigned checksummed artifacts only. Future releases
# should add signing, SBOM generation, and release-note validation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
BIN="$ROOT/build/x64lens"

mkdir -p "$DIST"

if [[ ! -x "$BIN" ]]; then
  echo "error: build/x64lens not found. Run make first."
  exit 1
fi

cp "$BIN" "$DIST/x64lens"
(
  cd "$DIST"
  sha256sum x64lens > x64lens.sha256
)

echo "release artifacts written to $DIST"
