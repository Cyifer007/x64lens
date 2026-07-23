#!/usr/bin/env python3
"""Validate the complete Patch 060 30-condition diagnostic campaign plane.

The smoke uses the built x64lens binary and three controlled tool-compatible
baseline probes.  It validates complete condition accounting, native-row
retention, task-normalized relation derivation, runtime-closure evidence,
coordinate qualification, deterministic summaries, the engineering gap
register, checksums, no-replace publication, and the diagnostic claim boundary.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "benchmarks/scripts/sprint11-provisional-campaign.py"
PLAN = ROOT / "benchmarks/task-definitions/sprint11-p060-campaign-plan.json"
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint11-diagnostic-tasks.json"
CORPUS = ROOT / "benchmarks/corpus/generated/s11-p056-provisional-v1"
X64LENS = ROOT / "build/x64lens"


class SmokeError(RuntimeError):
    """Raised when the Patch 060 campaign contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def write_probe(path: Path, tool_id: str, version: str) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f"TOOL={tool_id!r}\n"
        f"VERSION={version!r}\n"
        "if sys.argv[1:] == ['--version']:\n"
        "    print(VERSION)\n"
        "    raise SystemExit(0)\n"
        "# One valid native return record exercises bounded parsing without\n"
        "# pretending that the controlled probe discovered the x64lens relation.\n"
        "print('0x0000000000000000: ret')\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def run(argv: list[str], timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def verify_checksum_manifest(root: Path) -> None:
    lines = (root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    require(lines, "Patch 060 checksum manifest is empty")
    seen: set[str] = set()
    for line in lines:
        digest, relative = line.split("  ", 1)
        require(relative not in seen, f"duplicate checksum member: {relative}")
        seen.add(relative)
        member = root / relative
        require(member.is_file() and not member.is_symlink(), f"checksum member is not a regular file: {relative}")
        require(sha256(member) == digest, f"checksum mismatch: {relative}")


def main() -> int:
    for path in (ORCHESTRATOR, PLAN, AUTHORITY, X64LENS, CORPUS / "corpus-manifest.json"):
        require(path.is_file() or path.is_dir(), f"missing Patch 060 smoke prerequisite: {path}")
    require(X64LENS.is_file() and not X64LENS.is_symlink(), "built x64lens binary is missing")

    local = ROOT / ".local"
    local.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="x64lens-s11-p060-campaign-", dir=local) as raw:
        base = Path(raw)
        tools = base / "tools"
        tools.mkdir()
        versions = {
            "ropgadget": "Version: ROPgadget v7.7",
            "ropper": "Version: Ropper 1.13.13",
            "ropr": "ropr 0.2.26",
        }
        paths: dict[str, Path] = {}
        for tool_id, version in versions.items():
            path = tools / tool_id
            write_probe(path, tool_id, version)
            paths[tool_id] = path

        output = base / "results"
        campaign_id = "s11-p060-complete-campaign-smoke"
        argv = [
            sys.executable,
            str(ORCHESTRATOR),
            "--plan", str(PLAN),
            "--task-authority", str(AUTHORITY),
            "--corpus-result", str(CORPUS),
            "--output-root", str(output),
            "--campaign-id", campaign_id,
            "--x64lens", str(X64LENS),
            "--ropgadget", str(paths["ropgadget"]),
            "--ropper", str(paths["ropper"]),
            "--ropr", str(paths["ropr"]),
            "--warmup-runs", "0",
            "--measured-runs", "1",
        ]
        result = run(argv)
        require(result.returncode == 0, f"Patch 060 campaign smoke failed: stdout={result.stdout!r} stderr={result.stderr!r}")
        require(result.stdout.startswith("sprint11-provisional-campaign: ok"), "unexpected Patch 060 campaign banner")
        root = output / campaign_id
        require(root.is_dir() and not root.is_symlink(), "Patch 060 campaign result was not published")

        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        accounting = json.loads((root / "condition-accounting.json").read_text(encoding="utf-8"))["conditions"]
        summary = json.loads((root / "summaries/task-summary.json").read_text(encoding="utf-8"))
        gap = json.loads((root / "engineering-gap-register.json").read_text(encoding="utf-8"))
        native = rows(root / "runner-results" / f"{campaign_id}-native" / "rows.tsv")

        require(manifest["campaign_id"] == campaign_id, "Patch 060 campaign identity changed")
        require(manifest["evidence_class"] == "diagnostic", "Patch 060 evidence class changed")
        require(manifest["frozen"] is False and manifest["publication_eligible"] is False, "Patch 060 claim boundary changed")
        require(len(accounting) == 30 and len({item["condition_id"] for item in accounting}) == 30, "30-condition accounting is incomplete")
        require(all(item["tool_available"] is True for item in accounting), "controlled all-tools campaign reported an unavailable tool")
        require(len(native) == 30 and all(row["phase"] == "measured" for row in native), "native row matrix is incomplete")
        require(all(row["process_outcome"] == "success" for row in native), "controlled native process failure was not retained as success")
        require(sum(1 for path in (root / "relations").glob("*.json")) == 24, "normalized relation artifact count changed")
        require(len(summary["runtime_closures"]) == 5, "task-path runtime closure count changed")
        require(summary["condition_totals"]["planned"] == 30 and summary["condition_totals"]["unavailable_tool"] == 0, "summary condition accounting changed")
        require(summary["coordinate_calibration"]["status"] != "unavailable", "complete relation inputs produced unavailable coordinate calibration")
        require(summary["factor_attribution"]["status"] == "not_identifiable_from_selected_screen", "selected-screen factor boundary changed")
        require(len(gap["selected_priorities"]) >= 1, "engineering gap register selected no evidence-backed priority")
        require(gap["evidence_class"] == "diagnostic" and gap["frozen"] is False and gap["publication_eligible"] is False, "gap-register evidence boundary changed")
        combined = json.dumps({"summary": summary, "gap": gap}, sort_keys=True)
        require("gadget_count" not in combined, "Patch 060 emitted a generic gadget count")
        require("publication_eligible\": true" not in combined.lower(), "Patch 060 generated publication-eligible evidence")
        verify_checksum_manifest(root)

        overwrite = run(argv, timeout=60)
        require(overwrite.returncode == 2 and "already exists" in overwrite.stderr, "Patch 060 campaign overwrite was accepted")
        require(not any(path.name.startswith(f".{campaign_id}.staging") for path in output.iterdir()), "Patch 060 staging residue remains")

    print(
        "sprint11-p060-campaign-smoke: ok "
        "conditions=30 native_rows=30 relations=24 runtime_closures=5 "
        "coordinate_qualified=1 gap_register=1 unavailable_tools=0 generic_counts=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, SmokeError, subprocess.SubprocessError) as exc:
        print(f"sprint11-p060-campaign-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
