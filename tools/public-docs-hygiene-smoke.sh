#!/usr/bin/env bash
# Regression probe for timestamped private attachment-name leakage.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CHECKER="$ROOT_DIR/tools/check-public-docs.sh"
tmp=$(mktemp -d "${TMPDIR:-/tmp}/x64lens-public-docs-smoke.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

printf '%s\n' 'Repository source archive and evidence bundle are generated artifacts.' > "$tmp/clean.md"
source_name="x64lens_${HEAD_TOKEN:-HEAD}_20260711_145537.zip"
evidence_name="x64lens_${EVIDENCE_TOKEN:-codex_evidence}_20260711_185352.tar.gz"
printf 'source: %s\n' "$source_name" > "$tmp/source-leak.md"
printf 'evidence: %s\n' "$evidence_name" > "$tmp/evidence-leak.md"

bash "$CHECKER" "$tmp/clean.md" >/dev/null
if bash "$CHECKER" "$tmp/source-leak.md" >/dev/null 2>&1; then
  echo 'public-docs-hygiene-smoke: timestamped source attachment escaped policy' >&2
  exit 1
fi
if bash "$CHECKER" "$tmp/evidence-leak.md" >/dev/null 2>&1; then
  echo 'public-docs-hygiene-smoke: timestamped evidence attachment escaped policy' >&2
  exit 1
fi

echo 'public-docs-hygiene-smoke: ok cases=3 accepted=1 rejected=2'
