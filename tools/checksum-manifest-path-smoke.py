#!/usr/bin/env python3
"""Prove checksum manifests resolve entries relative to their own directory."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "tools/verify-checksum-manifest.py"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(manifest: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFIER), str(manifest), "--quiet"],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-checksum-smoke-") as tmp_raw:
        tmp = Path(tmp_raw)
        delivery = tmp / "delivery"
        other = tmp / "other-cwd"
        delivery.mkdir()
        other.mkdir()
        one = b"one\n"
        two = b"two\n"
        (delivery / "one.bin").write_bytes(one)
        (delivery / "two.bin").write_bytes(two)
        manifest = delivery / "SHA256SUMS.txt"
        good_text = f"{sha(one)}  one.bin\n{sha(two)}  two.bin\n"
        manifest.write_text(good_text, encoding="utf-8")

        accepted = run(manifest, other)
        require(accepted.returncode == 0, f"manifest-relative positive control failed: {accepted.stderr}")

        (delivery / "one.bin").write_bytes(b"tampered\n")
        tampered = run(manifest, other)
        require(tampered.returncode != 0, "tampered payload was accepted")
        (delivery / "one.bin").write_bytes(one)

        manifest.write_text(f"{sha(one)}  ../one.bin\n", encoding="utf-8")
        traversal = run(manifest, other)
        require(traversal.returncode != 0, "traversal path was accepted")

        manifest.write_text(f"{sha(one)}  one.bin\n{sha(one)}  one.bin\n", encoding="utf-8")
        duplicate = run(manifest, other)
        require(duplicate.returncode != 0, "duplicate manifest entry was accepted")

    print("checksum-manifest-path-smoke: ok cases=4 accepted=1 rejected=3")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"checksum-manifest-path-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
