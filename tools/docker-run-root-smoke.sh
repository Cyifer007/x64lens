#!/usr/bin/env bash
# Prove that the immutable image's configured non-root user can recreate and
# execute inside the dedicated mutable run root without writing beneath /work.
set -euo pipefail

image=${1:?usage: docker-run-root-smoke.sh IMAGE_ID}
command -v docker >/dev/null 2>&1 || {
    printf 'docker-run-root-smoke: error: docker is required\n' >&2
    exit 127
}

for attempt in 1 2; do
    docker run --rm "$image" bash -lc '
        set -euo pipefail
        test "$(id -u)" -ne 0
        run=${X64LENS_RUN_ROOT:?}
        case "$run" in
            ${HOME:?}/*) ;;
            *) printf "unexpected mutable run root: %s\n" "$run" >&2; exit 1 ;;
        esac
        test -w "$(dirname "$run")"
        rm -rf "$run"
        mkdir "$run"
        cat > "$run/probe.sh" <<"PROBE"
#!/usr/bin/env bash
set -euo pipefail
printf "mutable-run-root-probe: ok\\n"
PROBE
        chmod 0755 "$run/probe.sh"
        test "$("$run/probe.sh")" = "mutable-run-root-probe: ok"
        python3 /work/tools/gitless-source-manifest.py verify \
            --root /work --manifest /x64lens-source-manifest.json >/dev/null
        test -z "$(find /work -type f -newer "$run/probe.sh" -print -quit)"
        rm -rf "$run"
        mkdir "$run"
        test -w "$run"
    '
done

printf 'docker-run-root-smoke: ok attempts=2 nonroot=1 writable_parent=1 executable_run_root=1 source_pristine=1\n'
