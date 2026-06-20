#!/usr/bin/env bash
# Inspect a patch ZIP for generated, private, or local-only repository state.
#
# Purpose:
#   Patch/release bundles should be reproducible public source artifacts. They
#   must not include Git internals, build outputs, generated sample binaries,
#   local-only context files, benchmark result dumps, or private/course files.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <patch-bundle.zip>" >&2
  exit 2
fi

bundle="$1"
if [[ ! -f "$bundle" ]]; then
  echo "patch-bundle-hygiene: error: not a file: $bundle" >&2
  exit 1
fi

if ! command -v unzip >/dev/null 2>&1; then
  echo "patch-bundle-hygiene: error: unzip is required" >&2
  exit 127
fi

mapfile -t entries < <(unzip -Z1 "$bundle")
if [[ "${#entries[@]}" -eq 0 ]]; then
  echo "patch-bundle-hygiene: error: bundle is empty" >&2
  exit 1
fi

bad=0
for entry in "${entries[@]}"; do
  case "$entry" in
    /*|*../*|../*)
      echo "patch-bundle-hygiene: forbidden unsafe path: $entry" >&2
      bad=1
      ;;
  esac

  case "$entry" in
    x64lens/.git/*|x64lens/.git|*/.git/*|*/.git)
      echo "patch-bundle-hygiene: forbidden Git internals: $entry" >&2
      bad=1
      ;;
    x64lens/.local/*|x64lens/.local|*/.local/*|*/.local)
      echo "patch-bundle-hygiene: forbidden local-only context: $entry" >&2
      bad=1
      ;;
    x64lens/build/*|x64lens/build|*/build/*|*/build)
      echo "patch-bundle-hygiene: forbidden build output: $entry" >&2
      bad=1
      ;;
    x64lens/tests/bin/*|x64lens/tests/bin)
      echo "patch-bundle-hygiene: forbidden generated test binary: $entry" >&2
      bad=1
      ;;
    x64lens/tests/results/*|x64lens/tests/results)
      echo "patch-bundle-hygiene: forbidden generated test result: $entry" >&2
      bad=1
      ;;
    x64lens/benchmarks/results/*)
      if [[ "$entry" != "x64lens/benchmarks/results/.gitkeep" ]]; then
        echo "patch-bundle-hygiene: forbidden generated benchmark result: $entry" >&2
        bad=1
      fi
      ;;
    x64lens/tests/toy-src/minimal_nopie|x64lens/tests/toy-src/minimal_pie_canary|x64lens/tests/toy-src/minimal_execstack|x64lens/tests/toy-src/gadgets|x64lens/tests/toy-src/gadgets_capacity_exact|x64lens/tests/toy-src/gadgets_capacity)
      echo "patch-bundle-hygiene: forbidden generated toy binary: $entry" >&2
      bad=1
      ;;
    *.o|*.pyc|*__pycache__*|*.docx|*.pdf|*.zip)
      echo "patch-bundle-hygiene: forbidden generated/private file type: $entry" >&2
      bad=1
      ;;
  esac

done

if [[ "$bad" -ne 0 ]]; then
  exit 1
fi

echo "patch-bundle-hygiene: ok $bundle"
