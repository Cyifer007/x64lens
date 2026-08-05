#!/usr/bin/env bash
# Prove that the generated exact Docker context excludes untracked env files
# and that the final image-owned /work tree matches the staged Git authority.
set -euo pipefail

IMAGE="${1:-x64lens-dev-context-hygiene}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_BIN="${DOCKER:-docker}"
TMPROOT="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$TMPROOT/x64lens-docker-context.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
CTX="$WORK/context"

python3 "$ROOT/tools/gitless-source-manifest.py" create-context \
  --repo "$ROOT" --context "$CTX"

# These sentinels are in the transport context but outside authenticated
# source/. The Dockerfile copies only source/ and its detached manifest.
printf 'sentinel only; not a secret\n' > "$CTX/.env"
printf 'sentinel only; not a secret\n' > "$CTX/.env.local"
printf 'sentinel only; not a secret\n' > "$CTX/.env.production"

"$DOCKER_BIN" build -f "$CTX/Dockerfile.transport" -t "$IMAGE" "$CTX" >/dev/null
"$DOCKER_BIN" run --rm -e HOME=/tmp "$IMAGE" bash -lc '
  test ! -e /work/.env &&
  test ! -e /work/.env.local &&
  test ! -e /work/.env.production &&
  python3 /work/tools/gitless-source-manifest.py verify \
    --root /work --manifest /x64lens-source-manifest.json
'

echo "docker-context-hygiene-smoke: ok image=$IMAGE exact_source=1 sentinel_excluded=3"
