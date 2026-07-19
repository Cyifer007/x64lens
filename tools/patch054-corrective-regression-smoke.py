#!/usr/bin/env python3
"""Regression-test the two Patch 054 checker false negatives and source drift."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_CHECKER = "tools/research-roadmap-consistency-smoke.py"
CLOSEOUT_CHECKER = "tools/sprint10-closeout-smoke.py"


class SmokeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def copy_file(shadow: Path, relative: str) -> None:
    source = ROOT / relative
    require(source.is_file(), f"missing source file: {relative}")
    target = shadow / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def run_checker(shadow: Path, relative: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, relative],
        cwd=shadow,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def roadmap_cases() -> int:
    checker_globals = runpy.run_path(str(ROOT / ROADMAP_CHECKER))
    authority_paths = tuple(checker_globals["ACTIVE_AUTHORITY_PATHS"])
    path_claims = dict(checker_globals["FORBIDDEN_PATH_CLAIMS"])
    case_count = sum(len(values) for values in path_claims.values())

    with tempfile.TemporaryDirectory(prefix="x64lens-p054-roadmap-regression-") as raw:
        shadow = Path(raw)
        copy_file(shadow, ROADMAP_CHECKER)
        copy_file(shadow, "tests/expected/research-stage-gates.json")
        for relative in authority_paths:
            copy_file(shadow, relative)

        baseline = run_checker(shadow, ROADMAP_CHECKER)
        require(baseline.returncode == 0, f"roadmap baseline failed: {baseline.stderr}")

        for relative, literals in path_claims.items():
            path = shadow / relative
            original = path.read_text(encoding="utf-8")
            for literal in literals:
                path.write_text(original + f"\n{literal}\n", encoding="utf-8")
                result = run_checker(shadow, ROADMAP_CHECKER)
                require(result.returncode != 0, f"roadmap checker accepted stale claim {relative}: {literal!r}")
                require("stale path-specific chronology" in result.stderr, f"unexpected roadmap rejection: {result.stderr}")
                path.write_text(original, encoding="utf-8")

    return case_count


def observed_contract_counts(shadow: Path) -> dict[str, int]:
    catalog = json.loads((shadow / "tests/expected/sprint10-exact-pattern-catalog.json").read_text(encoding="utf-8"))
    family = json.loads((shadow / "tests/expected/sprint10-family-coverage.json").read_text(encoding="utf-8"))
    fixtures = json.loads((shadow / "tests/expected/sprint10-fixture-suite.json").read_text(encoding="utf-8"))
    patterns = catalog["patterns"]
    return {
        "semantic_family_contracts": len(family["families"]),
        "exact_patterns": len(patterns),
        "semantic_patterns": sum(item.get("semantic_class") != "unknown_candidate" for item in patterns),
        "exact_only_patterns": sum(item.get("semantic_class") == "unknown_candidate" for item in patterns),
        "scored_patterns": sum(item.get("score") is not None for item in patterns),
        "complete_effect_models": sum(item.get("effect_model_complete") is True for item in patterns),
        "partial_effect_models": sum(item.get("effect_model_complete") is False for item in patterns),
        "fixture_groups": len(fixtures["families"]),
    }


def closeout_cases() -> int:
    needed = (
        CLOSEOUT_CHECKER,
        "tests/expected/sprint10-closeout.json",
        "tests/expected/sprint10-exact-pattern-catalog.json",
        "tests/expected/sprint10-family-coverage.json",
        "tests/expected/sprint10-fixture-suite.json",
        "tests/expected/research-stage-gates.json",
        "tests/expected/x64lens-report-sprint10-effects-0.2.0.json",
        "include/constants.inc",
        "include/structs.inc",
        "docs/sprints/sprint-10-plan.md",
        "docs/sprints/sprint-11-plan.md",
        "docs/adr/0040-sprint10-closeout-and-diagnostic-benchmark-entry.md",
        "docs/sprints/sprint-10-patch-054-validation.md",
        "docs/sprints/sprint-10-retro.md",
        "Makefile",
    )

    with tempfile.TemporaryDirectory(prefix="x64lens-p054-closeout-regression-") as raw:
        shadow = Path(raw)
        for relative in needed:
            copy_file(shadow, relative)

        baseline = run_checker(shadow, CLOSEOUT_CHECKER)
        require(baseline.returncode == 0, f"closeout baseline failed: {baseline.stderr}")

        catalog_path = shadow / "tests/expected/sprint10-exact-pattern-catalog.json"
        closeout_path = shadow / "tests/expected/sprint10-closeout.json"
        catalog_original = catalog_path.read_text(encoding="utf-8")
        closeout_original = closeout_path.read_text(encoding="utf-8")
        catalog = json.loads(catalog_original)
        pattern = next(
            item for item in catalog["patterns"]
            if item.get("score") is not None and item.get("effect_model_complete") is True
        )
        pattern["score"] = None
        pattern["effect_model_complete"] = False
        catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
        closeout = json.loads(closeout_original)
        closeout["contract_counts"] = observed_contract_counts(shadow)
        closeout_path.write_text(json.dumps(closeout, indent=2) + "\n", encoding="utf-8")
        coordinated = run_checker(shadow, CLOSEOUT_CHECKER)
        require(coordinated.returncode != 0, "closeout checker accepted coordinated catalog/summary drift")
        require("catalog/canonical report count mismatch" in coordinated.stderr, f"unexpected coordinated rejection: {coordinated.stderr}")
        catalog_path.write_text(catalog_original, encoding="utf-8")
        closeout_path.write_text(closeout_original, encoding="utf-8")

        structs_path = shadow / "include/structs.inc"
        structs_original = structs_path.read_text(encoding="utf-8")
        require("%define GADGET_RECORD_SIZE          112" in structs_original, "record-size source probe cannot find authority")
        structs_path.write_text(
            structs_original.replace("%define GADGET_RECORD_SIZE          112", "%define GADGET_RECORD_SIZE          113", 1),
            encoding="utf-8",
        )
        source_drift = run_checker(shadow, CLOSEOUT_CHECKER)
        require(source_drift.returncode != 0, "closeout checker accepted source/profile drift")
        require("reference profile/source mismatch" in source_drift.stderr, f"unexpected source-drift rejection: {source_drift.stderr}")

    module = load_module(ROOT / CLOSEOUT_CHECKER, "x64lens_sprint10_closeout_smoke")
    synthetic = {
        "semantic_family_contracts": 11,
        "exact_patterns": 25,
        "semantic_patterns": 17,
        "exact_only_patterns": 8,
        "scored_patterns": 13,
        "complete_effect_models": 22,
        "partial_effect_models": 3,
        "fixture_groups": 5,
    }
    banner = module.format_success_banner(synthetic, patch_count=9, next_sprint=11)
    require("scored=13 model_complete=22 model_partial=3" in banner, f"success banner is not data-driven: {banner}")
    require("scored=14" not in banner, f"success banner retained a hardcoded count: {banner}")
    return 3


def main() -> int:
    roadmap = roadmap_cases()
    closeout = closeout_cases()
    print(f"patch054-corrective-regression-smoke: ok roadmap_cases={roadmap} closeout_cases={closeout}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, StopIteration, SmokeError, subprocess.SubprocessError) as exc:
        print(f"patch054-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
