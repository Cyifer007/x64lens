#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

mapfile -t FILES < <(
  find README.md CHANGELOG.md CONTRIBUTING.md SECURITY.md CODE_OF_CONDUCT.md \
       Dockerfile Makefile .github docs paper src include tests tools benchmarks schemas \
       -type f \
       ! -path 'benchmarks/results/*' \
       ! -path 'tests/bin/*' \
       ! -path 'tests/invalid/*' \
       ! -path 'tools/check-public-docs.sh' \
       \( -name '*.md' -o -name '*.asm' -o -name '*.inc' -o -name '*.sh' \
          -o -name '*.py' -o -name '*.yml' -o -name '*.yaml' -o -name '*.json' \
          -o -name '*.tex' -o -name '*.bib' -o -name 'Makefile' -o -name 'Dockerfile' \) \
       -print 2>/dev/null | sort
)

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "public-docs-check: no public text files discovered" >&2
  exit 2
fi

PATTERNS=(
  '/home/[A-Za-z0-9._-]+/'
  '/mnt/c/Users/'
  'x64lens_patch_[0-9]+'
  'user-created whole-repository zip snapshots'
  'in our (chat|conversation)'
  'the file you (uploaded|attached)'
  'as discussed in (chat|the conversation)'
)

failed=0
for pattern in "${PATTERNS[@]}"; do
  if grep -EnI "$pattern" "${FILES[@]}"; then
    echo "public-docs-check: prohibited repository-facing wording matched: $pattern" >&2
    failed=1
  fi
done

if (( failed != 0 )); then
  exit 1
fi

echo "public-docs-check: ok files=${#FILES[@]}"
