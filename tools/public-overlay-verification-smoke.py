#!/usr/bin/env python3
"""Regression-test authenticated public-overlay verification and self-tamper rejection."""
from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "tools" / "verify-public-overlay.py"
CHECKER = ROOT / "tools" / "check-public-content.py"
MANIFEST = "PATCH_TEST_PUBLIC_FILE_MANIFEST.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_zip(path: Path, files: dict[str, tuple[bytes, int]], *, manifest_payload: dict[str, object]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, (payload, mode) in files.items():
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload)
        info = zipfile.ZipInfo(MANIFEST)
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, json.dumps(manifest_payload, indent=2).encode() + b"\n")


def manifest_for(files: dict[str, tuple[bytes, int]]) -> dict[str, object]:
    records = []
    for member, (payload, mode) in sorted(files.items()):
        prefix = "changed-files/"
        assert member.startswith(prefix)
        records.append(
            {
                "path": member[len(prefix):],
                "sha256": digest(payload),
                "size": len(payload),
                "mode": f"0{mode:03o}",
            }
        )
    return {
        "artifact": "x64lens-public-overlay-smoke",
        "source_base_commit": "0" * 40,
        "file_count": len(records),
        "deleted_paths": [],
        "files": records,
    }


def run(bundle: Path, expected_hash: str, expected_exit: int, *, require_error: str | None = None) -> None:
    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--bundle", str(bundle), "--expected-sha256", expected_hash],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != expected_exit:
        raise RuntimeError(
            f"{bundle.name}: expected exit {expected_exit}, got {result.returncode}: "
            f"{result.stdout}{result.stderr}"
        )
    if require_error is not None and require_error not in result.stderr:
        raise RuntimeError(
            f"{bundle.name}: expected diagnostic containing {require_error!r}, got: "
            f"{result.stdout}{result.stderr}"
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-public-overlay-verify-") as temp:
        root = Path(temp)
        checker = CHECKER.read_bytes()
        clean_files = {
            "changed-files/README.md": (b"Repository-facing validation evidence.\n", 0o644),
            "changed-files/tools/check-public-content.py": (checker, 0o755),
        }
        clean = root / "clean.zip"
        clean_manifest = manifest_for(clean_files)
        write_zip(clean, clean_files, manifest_payload=clean_manifest)
        clean_hash = digest(clean.read_bytes())
        run(clean, clean_hash, 0)

        prohibited = ("Co" + "dex").encode()
        tampered_payload = checker + b"\n# " + prohibited + b"\n"
        tampered_files = dict(clean_files)
        tampered_files["changed-files/tools/check-public-content.py"] = (tampered_payload, 0o755)

        stale_hash = root / "tampered-stale-hash.zip"
        write_zip(stale_hash, tampered_files, manifest_payload=clean_manifest)
        run(stale_hash, clean_hash, 1)

        # Isolate internal-manifest reconciliation from the public-content
        # policy. Change a benign README payload, authenticate the resulting
        # archive externally, and retain the old clean manifest. The verifier
        # must reach the manifest layer and reject the stale digest there.
        stale_manifest = root / "benign-stale-manifest.zip"
        benign_changed_files = dict(clean_files)
        benign_changed_files["changed-files/README.md"] = (
            b"Repository-facing validation evidencf.\n",
            0o644,
        )
        write_zip(stale_manifest, benign_changed_files, manifest_payload=clean_manifest)
        stale_manifest_hash = digest(stale_manifest.read_bytes())
        run(stale_manifest, stale_manifest_hash, 1, require_error="SHA-256 mismatch for README.md")

        content_rejected = root / "tampered-authenticated.zip"
        write_zip(content_rejected, tampered_files, manifest_payload=manifest_for(tampered_files))
        content_rejected_hash = digest(content_rejected.read_bytes())
        run(content_rejected, content_rejected_hash, 1)

        invalid_deletion = root / "invalid-deletion-path.zip"
        invalid_manifest = manifest_for(clean_files)
        invalid_manifest["deleted_paths"] = ["../private-context.md"]
        invalid_manifest["deleted_count"] = 1
        write_zip(invalid_deletion, clean_files, manifest_payload=invalid_manifest)
        invalid_deletion_hash = digest(invalid_deletion.read_bytes())
        run(invalid_deletion, invalid_deletion_hash, 1)

    print("public-overlay-verification-smoke: ok cases=5 accepted=1 rejected=4")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"public-overlay-verification-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
