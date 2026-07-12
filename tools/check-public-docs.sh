#!/usr/bin/env bash
# check-public-docs.sh
#
# Purpose:
#   Scan public, repository-facing text files for private local paths, hostnames,
#   attachment references, and dialogue-style wording that should not ship in
#   the public x64lens repository.
#
# Boundary:
#   This check intentionally scans tracked and untracked public source
#   files. Generated and ignored evidence artifacts under tests/results, benchmarks/results, .local,
#   and private agent workspaces are not public documentation and must not make
#   aggregate validation cleanup-sensitive.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

public_paths=(
  README.md
  CHANGELOG.md
  CONTRIBUTING.md
  SECURITY.md
  CODE_OF_CONDUCT.md
  Dockerfile
  Makefile
  .github
  docs
  paper
  src
  include
  tests
  tools
  benchmarks
  schemas
)

is_text_candidate() {
  case "$1" in
    *.md|*.asm|*.inc|*.sh|*.py|*.yml|*.yaml|*.json|*.tex|*.bib|Makefile|Dockerfile)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_public_candidate() {
  case "$1" in
    tools/check-public-docs.sh)
      return 1
      ;;
    tests/bin/*|tests/results/*|tests/invalid/*|benchmarks/results/*)
      return 1
      ;;
    .local/*|.codex/*|.codex-log/*|.agents/*)
      return 1
      ;;
    *)
      is_text_candidate "$1"
      ;;
  esac
}

collect_with_git() {
  local path
  git ls-files --cached --others --exclude-standard -- "${public_paths[@]}" | while IFS= read -r path; do
    if is_public_candidate "$path"; then
      printf '%s\n' "$path"
    fi
  done
}

collect_with_find() {
  local path
  find "${public_paths[@]}" \
       -type f \
       ! -path 'benchmarks/results/*' \
       ! -path 'tests/bin/*' \
       ! -path 'tests/results/*' \
       ! -path 'tests/invalid/*' \
       ! -path '.local/*' \
       ! -path '.codex/*' \
       ! -path '.codex-log/*' \
       ! -path '.agents/*' \
       -print 2>/dev/null | while IFS= read -r path; do
    if is_public_candidate "$path"; then
      printf '%s\n' "$path"
    fi
  done
}

if (( $# > 0 )); then
  FILES=("$@")
else
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    mapfile -t FILES < <(collect_with_git | sort -u)
  else
    mapfile -t FILES < <(collect_with_find | sort -u)
  fi
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "public-docs-check: no public text files discovered" >&2
  exit 2
fi

PATTERNS=(
  '/mnt/data/'
  'cyifer007@'
  'DESKTOP-[A-Z0-9-]+'
  'x64lens_patch_[0-9]+'
  'user-created whole-repository zip snapshots'
  'in our (chat|conversation)'
  'the file you (uploaded|attached)'
  'as discussed in (chat|the conversation)'
  'Codex'
  'CODEX_LOCAL_MISSION'
)

CASE_INSENSITIVE_PATTERNS=(
  'x64lens[_ -]*(HEAD|source)[_ -]*[0-9]{8}[_ -]*[0-9]{6}([_ (.-]*(copy|[0-9]+)[) ]*)?[.]zip'
  'x64lens[_ -]*(codex[_ -]*evidence|evidence)[_ -]*[0-9]{8}[_ -]*[0-9]{6}([_ (.-]*(copy|[0-9]+)[) ]*)?[.]tar[.]gz'
  '[.]local/codex/reports/'
)

HOME_PATH_PATTERNS=(
  '/home/[A-Za-z0-9._-]+(/|$)'
  '/Users/[A-Za-z0-9._-]+(/|$)'
  '/mnt/[A-Za-z]/Users/[A-Za-z0-9._-]+/'
  '[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9._-]+[\\/]'
  '\\\\wsl([.]localhost)?\\[^\\]+\\home\\[A-Za-z0-9._-]+\\'
)

failed=0
for pattern in "${PATTERNS[@]}"; do
  if grep -E -n -I "$pattern" "${FILES[@]}"; then
    echo "public-docs-check: prohibited repository-facing wording matched: $pattern" >&2
    failed=1
  fi
done

for pattern in "${CASE_INSENSITIVE_PATTERNS[@]}"; do
  if grep -E -i -n -I "$pattern" "${FILES[@]}"; then
    echo "public-docs-check: prohibited repository-facing wording matched: $pattern" >&2
    failed=1
  fi
done

# Docker's public development image intentionally uses a generic container
# home. Host-path checks therefore scan every other public text file while
# preserving that reproducible Dockerfile setting.
HOME_FILES=()
for path in "${FILES[@]}"; do
  [[ "$path" == "Dockerfile" ]] || HOME_FILES+=("$path")
done
for pattern in "${HOME_PATH_PATTERNS[@]}"; do
  if (( ${#HOME_FILES[@]} > 0 )) && grep -E -i -n -I "$pattern" "${HOME_FILES[@]}"; then
    echo "public-docs-check: prohibited repository-facing host path matched: $pattern" >&2
    failed=1
  fi
done

if (( failed != 0 )); then
  exit 1
fi

echo "public-docs-check: ok files=${#FILES[@]}"
