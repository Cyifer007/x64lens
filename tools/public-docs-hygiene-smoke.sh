#!/usr/bin/env bash
# Regression probe for private attachment-name and host-path leakage.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CHECKER="$ROOT_DIR/tools/check-public-docs.sh"
tmp=$(mktemp -d "${TMPDIR:-/tmp}/x64lens-public-docs-smoke.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

# Use unmistakably synthetic components. The tracked smoke must never retain a
# real attachment basename merely to prove that the public checker rejects it.
date_part=20991231
time_part=235959
stamp="${date_part}_${time_part}"
head_token=HEAD
evidence_token=codex_evidence
copy_token=copy
user_token=synthetic_user
host_token=Ubuntu-Test

printf '%s\n' 'Repository source archives and evidence bundles are generated artifacts.' > "$tmp/clean.md"
printf 'source: x64lens_%s_%s.zip\n' "$head_token" "$stamp" > "$tmp/source-standard.md"
printf 'source: x64lens_%s_%s(2).zip\n' "$head_token" "$stamp" > "$tmp/source-copy-number.md"
printf 'source: X64LENS_%s_%s_%s.zip\n' "$head_token" "$stamp" "$copy_token" > "$tmp/source-case-copy.md"
printf 'evidence: x64lens_%s_%s.tar.gz\n' "$evidence_token" "$stamp" > "$tmp/evidence-standard.md"
printf 'evidence: x64lens_%s_%s-%s.tar.gz\n' "$evidence_token" "$stamp" "$copy_token" > "$tmp/evidence-copy.md"
printf 'path: C:\\Users\\%s\\repo\\report.md\n' "$user_token" > "$tmp/windows-home.md"
printf 'path: \\\\wsl.localhost\\%s\\home\\%s\\repo\\report.md\n' "$host_token" "$user_token" > "$tmp/wsl-home.md"
printf 'path: /Users/%s/repo/report.md\n' "$user_token" > "$tmp/macos-home.md"
printf 'path: /home/%s/repo/report.md\n' "$user_token" > "$tmp/linux-home.md"
printf '%s@%s:~/repo$ make test\n' "$user_token" "$host_token" > "$tmp/shell-prompt.md"
cloud_word=cloud
environment_word=environment
authoritative_word=authoritative
local_word=local
acceptance_word=acceptance
mandatory_word=mandatory
platform_word=WSL2
private_word=private
handoff_word=handoff
verb_a=Attach
noun_r=report
direction_b=back
printf '%s %s may not provide the required compiler.\n' "$cloud_word" "$environment_word" > "$tmp/cloud-environment.md"
printf 'An %s %s %s decision is required.\n' "$authoritative_word" "$local_word" "$acceptance_word" > "$tmp/authoritative-local.md"
printf 'These checks remain %s in %s.\n' "$mandatory_word" "$platform_word" > "$tmp/wsl-follow-up.md"
printf 'This %s %s context governs the next patch.\n' "$private_word" "$handoff_word" > "$tmp/private-handoff.md"
printf '%s the %s %s to the review system.\n' "$verb_a" "$noun_r" "$direction_b" > "$tmp/report-handoff.md"

bash "$CHECKER" "$tmp/clean.md" >/dev/null

rejected=0
for fixture in \
  source-standard.md \
  source-copy-number.md \
  source-case-copy.md \
  evidence-standard.md \
  evidence-copy.md \
  windows-home.md \
  wsl-home.md \
  macos-home.md \
  linux-home.md \
  shell-prompt.md \
  cloud-environment.md \
  authoritative-local.md \
  wsl-follow-up.md \
  private-handoff.md \
  report-handoff.md; do
  if bash "$CHECKER" "$tmp/$fixture" >/dev/null 2>&1; then
    echo "public-docs-hygiene-smoke: prohibited fixture escaped policy: $fixture" >&2
    exit 1
  fi
  rejected=$((rejected + 1))
done

echo "public-docs-hygiene-smoke: ok cases=16 accepted=1 rejected=$rejected"
