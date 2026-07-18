#!/usr/bin/env python3
"""Regression-test public ZIP textual payload inspection."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "check-public-content.py"


def make_zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, text in members.items():
            archive.writestr(name, text)


def run(path: Path, expected: int) -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--zip", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != expected:
        raise RuntimeError(
            f"{path.name}: expected exit {expected}, got {result.returncode}: "
            f"{result.stdout}{result.stderr}"
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-public-artifact-content-") as temp:
        root = Path(temp)
        clean = root / "clean.zip"
        tampered_checker = root / "tampered-checker.zip"
        deleted_workspace = root / "deleted-workspace.zip"
        deleted_sandbox = root / "deleted-sandbox.zip"
        added_package = root / "added-package.zip"
        added_supply = root / "added-supply.zip"
        make_zip(
            clean,
            {
                "changed-files/README.md": "Repository-facing validation evidence.\n",
                # The real policy implementation must pass its own scan.
                "root/changed-files/tools/check-public-content.py": CHECKER.read_text(encoding="utf-8"),
            },
        )

        # Assemble negative phrases so this tracked regression does not itself
        # preserve the prohibited literals in a public text file.
        private_phrase = "private local " + "agent workspaces"
        sandbox_phrase = "restricted filesystem " + "sandbox"
        package_phrase = "self-" + "authenticating application and evidence package"
        supply_phrase = "artifact-" + "supply findings"
        make_zip(tampered_checker, {"changed-files/tools/check-public-content.py": CHECKER.read_text(encoding="utf-8") + "\n# " + ("Co" + "dex") + "\n"})
        make_zip(deleted_workspace, {"change.patch": f"-- Exclude {private_phrase}.\n"})
        make_zip(deleted_sandbox, {"change.patch": f"-- Validation ran outside the {sandbox_phrase}.\n"})
        make_zip(added_package, {"review.diff": f"+- Regenerate a complete, {package_phrase}.\n"})
        make_zip(added_supply, {"review.diff": f"+- Reconcile public documentation and {supply_phrase}.\n"})

        run(clean, 0)
        run(tampered_checker, 1)
        run(deleted_workspace, 1)
        run(deleted_sandbox, 1)
        run(added_package, 1)
        run(added_supply, 1)
    print("public-artifact-content-smoke: ok cases=6 accepted=1 rejected=5")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"public-artifact-content-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
