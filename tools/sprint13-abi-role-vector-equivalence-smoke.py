#!/usr/bin/env python3
"""Compare production private role vectors with an independent fixture oracle."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-abi-role-vector-equivalence-v1.json"
EXPECTED = ROOT / "tests/expected/sprint13-abi-role-vector-equivalence-v1.json"
ABI_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-abi-role-query-v1.json"
ABI_EXPECTED = ROOT / "tests/expected/sprint13-abi-role-query-v1.json"
ABI_TOOL = ROOT / "tools/sprint13-abi-role-query-smoke.py"


class VectorError(RuntimeError):
    pass


class CatchableTermination(VectorError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise VectorError(message)


def fail(message: str) -> NoReturn:
    print(f"sprint13-abi-role-vector-equivalence-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def strict(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


@contextmanager
def signal_guard(label: str):
    guarded = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    previous = {sig: signal.getsignal(sig) for sig in guarded}

    def handler(signum: int, _frame: object) -> None:
        for candidate in guarded:
            signal.signal(candidate, signal.SIG_IGN)
        raise CatchableTermination(f"{label} interrupted by {signal.Signals(signum).name}")

    for sig in guarded:
        signal.signal(sig, handler)
    try:
        yield
    finally:
        for sig, old in previous.items():
            signal.signal(sig, old)


@contextmanager
def defer_catchable_signals():
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGHUP, signal.SIGINT, signal.SIGTERM})
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def rename_noreplace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    require(renameat2 is not None, "renameat2 unavailable")
    rc = renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    if rc != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), os.fspath(destination))


def validate_authority(value: Any) -> dict[str, Any]:
    keys = {
        "schema", "sprint", "patch", "evidence_class", "publication_eligible",
        "purpose", "internal_dispositions", "vector_contract", "valid_pop_cases",
        "non_pop_pattern_ids", "guard_cases", "targets", "claim_boundary", "limitations",
    }
    require(isinstance(value, dict) and set(value) == keys, "vector authority shape changed")
    require(value["schema"] == "x64lens-sprint13-abi-role-vector-equivalence-authority-v1"
            and value["sprint"] == 13 and value["patch"] == 88,
            "vector authority identity changed")
    require(value["internal_dispositions"] == {
        "valid": 16,
        "pattern_register_contradictions": 16,
        "non_pop_zero_mask": 10,
        "pointer_count_capacity_guards": 6,
        "total": 48,
    }, "internal denominator changed")
    require(value["vector_contract"] == {
        "candidate_capacity": 4096,
        "controlled_targets": 24,
        "expected_public_closures": 96,
        "expected_queries": 36,
        "maximum_occupied_indices": 98304,
    }, "vector contract changed")
    require(len(value["valid_pop_cases"]) == 16 and len(value["non_pop_pattern_ids"]) == 10
            and len(value["guard_cases"]) == 6 and len(value["targets"]) == 24,
            "vector member denominator changed")
    require(len({item["id"] for item in value["targets"]}) == 24, "duplicate controlled target")
    return value


def vector_run(probe: Path, records: list[tuple[int, int, int]], work: Path) -> tuple[int, list[int]]:
    source = work / f"in-{os.urandom(8).hex()}"
    output = work / f"out-{os.urandom(8).hex()}"
    payload = bytearray(b"X64R" + struct.pack("<II", len(records), len(records)))
    for pattern, count, order in records:
        payload += struct.pack("<III", pattern, count, order)
    source.write_bytes(payload)
    source.chmod(0o444)
    cp = subprocess.run(
        [os.fspath(probe), "--vector", os.fspath(source), os.fspath(output)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    require(cp.returncode == 0, f"role probe failed: {cp.stderr[-512:]!r}")
    raw = output.read_bytes()
    require(len(raw) == 12 + 8 * len(records) and raw[:4] == b"X64O", "role probe output malformed")
    status, count = struct.unpack_from("<II", raw, 4)
    require(count == len(records), "role probe count changed")
    masks = list(struct.unpack_from(f"<{count}Q", raw, 12)) if count else []
    return status, masks


def internal_dispositions(probe: Path, authority: dict[str, Any], work: Path) -> dict[str, int]:
    valid = [(item["pattern_id"], 1, item["reg_id"]) for item in authority["valid_pop_cases"]]
    status, masks = vector_run(probe, valid, work)
    require(status == 0 and masks == [item["expected_role_mask"] for item in authority["valid_pop_cases"]],
            "valid role masks disagree")
    rejected = 0
    for item in authority["valid_pop_cases"]:
        status, _ = vector_run(probe, [(item["pattern_id"], 1, (item["reg_id"] + 1) % 16)], work)
        require(status == 7, "pattern/register contradiction accepted")
        rejected += 1
    status, masks = vector_run(probe, [(item, 0, 0) for item in authority["non_pop_pattern_ids"]], work)
    require(status == 0 and masks == [0] * 10, "non-pop role mask changed")
    guards = 0
    for name, expected in authority["guard_cases"].items():
        cp = subprocess.run([os.fspath(probe), "--guard", name], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=10, check=False)
        require(cp.returncode == 0 and int(cp.stdout.strip()) == expected, f"guard case changed: {name}")
        guards += 1
    return {
        "valid_masks": len(valid),
        "contradiction_rejections": rejected,
        "non_pop_zero_masks": len(masks),
        "guard_dispositions": guards,
    }


def full_vectors(probe: Path, authority: dict[str, Any], abi_root: Path, work: Path) -> tuple[int, int]:
    occupied = matches = 0
    for target in authority["targets"]:
        report = abi_root / "outputs" / target["id"] / "gadgets_json" / "stdout"
        require(report.is_file(), f"missing public closure: {target['id']}")
        value = load(report)
        gadgets = value["gadgets"]
        require(len(gadgets) == 1, f"controlled target candidate denominator changed: {target['id']}")
        gadget = gadgets[0]
        require(gadget["pattern"] == target["public_pattern"]
                and gadget.get("stack_pop_order", []) == target["stack_pop_order"],
                f"controlled target exact facts changed: {target['id']}")
        status, masks = vector_run(
            probe,
            [(target["pattern_id"], target["pattern_reg_count"], target["pattern_reg_order"])],
            work,
        )
        require(status == 0 and masks == [target["expected_role_mask"]],
                f"candidate role vector disagrees: {target['id']}")
        occupied += 1
        matches += 1
    require(occupied <= authority["vector_contract"]["maximum_occupied_indices"],
            "occupied candidate cap exceeded")
    return occupied, matches


def selftest(authority: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory(prefix="x64lens-abi-stage-signal-selftest-") as raw:
        parent = Path(raw)
        stage: Path | None = None
        try:
            with signal_guard("ABI stage signal selftest"):
                try:
                    with defer_catchable_signals():
                        stage = Path(tempfile.mkdtemp(prefix=".abi.stage.", dir=parent))
                    os.kill(os.getpid(), signal.SIGTERM)
                except BaseException:
                    if stage is not None and stage.exists():
                        shutil.rmtree(stage, ignore_errors=True)
                    raise
        except CatchableTermination:
            pass
        else:
            raise VectorError("ABI stage signal selftest did not terminate")
        require(stage is not None and not stage.exists(), "ABI signal left staging residue")
    allowed = 0x3F3F01
    for item in authority["valid_pop_cases"]:
        require(item["expected_role_mask"] & ~allowed == 0, "oracle mask exceeds allowed role domain")
    require(next(item for item in authority["valid_pop_cases"] if item["register"] == "rcx")["expected_role_mask"] & (1 << 11),
            "rcx SysV arg4 missing")
    require(next(item for item in authority["valid_pop_cases"] if item["register"] == "r10")["expected_role_mask"] & (1 << 19),
            "r10 syscall arg4 missing")
    with tempfile.TemporaryDirectory(prefix="x64lens-abi-publication-selftest-") as raw:
        parent = Path(raw)
        stage = parent / "stage"
        final = parent / "final"
        stage.mkdir()
        final.mkdir()
        try:
            rename_noreplace(stage, final)
        except OSError:
            pass
        else:
            raise VectorError("replace-capable ABI publication accepted")
        require(stage.is_dir() and final.is_dir(), "ABI no-replace selftest changed either directory")
    with tempfile.TemporaryDirectory(prefix="x64lens-abi-checksum-selftest-") as raw:
        stage = Path(raw)
        (stage / "retained").write_text("retained", encoding="utf-8")
        work = stage / "work"
        work.mkdir()
        (work / "transient").write_text("transient", encoding="utf-8")
        shutil.rmtree(work)
        count = write_checksums(stage)
        require(count == 1 and "work/" not in (stage / "SHA256SUMS.txt").read_text(encoding="utf-8"),
                "ABI checksum includes deleted work members")


def write_checksums(stage: Path) -> int:
    files = sorted(
        (path for path in stage.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"),
        key=lambda path: os.fsencode(path.relative_to(stage).as_posix()),
    )
    (stage / "SHA256SUMS.txt").write_text(
        "".join(f"{sha(path)}  {path.relative_to(stage).as_posix()}\n" for path in files),
        encoding="utf-8",
    )
    (stage / "SHA256SUMS.txt").chmod(0o444)
    return len(files)


def run(args: argparse.Namespace, authority: dict[str, Any]) -> dict[str, Any]:
    abi = module("s13_p087_vector_abi", ABI_TOOL)
    abi_authority = abi.validate_authority(load(args.abi_authority.resolve(strict=True)))
    contract = abi.contract_result(abi_authority, args.abi_expected)
    result_dir = Path(os.path.abspath(args.result_dir))
    require(not result_dir.exists() and result_dir.parent.is_dir() and not result_dir.parent.is_symlink(),
            "vector result path unavailable")
    stage: Path | None = None
    current: Path | None = None
    try:
        with defer_catchable_signals():
            stage = Path(tempfile.mkdtemp(prefix=f".{result_dir.name}.stage.", dir=result_dir.parent))
            current = stage
        work = stage / "work"
        work.mkdir(mode=0o700)
        abi_root = stage / "abi-closures"
        namespace = SimpleNamespace(
            analyzer=args.analyzer,
            result_dir=abi_root,
            source_root=args.source_root,
            source_manifest=args.source_manifest,
            expected_candidate_tree=args.expected_candidate_tree,
            authority=args.abi_authority,
            expected=args.abi_expected,
        )
        abi_manifest = abi.run_closures(namespace, abi_authority, contract)
        require(abi_manifest["public_closure_count"] == 96, "ABI public closure denominator changed")
        probe = args.probe.resolve(strict=True)
        metadata = probe.stat()
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_mode & 0o100 and metadata.st_nlink == 1,
                "role probe is not an executable single-link authority")
        internal = internal_dispositions(probe, authority, work)
        occupied, matches = full_vectors(probe, authority, abi_root, work)
        result = {
            "schema": "x64lens-sprint13-abi-role-vector-equivalence-result-v1",
            "sprint": 13,
            "patch": 88,
            "internal_dispositions": sum(internal.values()),
            **internal,
            "controlled_targets": 24,
            "occupied_indices": occupied,
            "vector_matches": matches,
            "queries": 36,
            "public_closures": 96,
            "decision": "private_full_vector_equivalent",
            "public_fields_added": 0,
            "semantic_changes": 0,
            "score_changes": 0,
            "schema_changed": False,
        }
        require(result == load(args.expected.resolve(strict=True)),
                "ABI vector result differs from expected authority")
        manifest = {
            "result": result,
            "authority_sha256": sha(args.authority.resolve(strict=True)),
            "probe_sha256": sha(probe),
            "abi_closure_manifest_sha256": sha(abi_root / "manifest.json"),
            "source_authority": abi_manifest["source_authority"],
            "analyzer_source": abi_manifest["analyzer_source"],
            "executed_analyzer": abi_manifest["executed_analyzer"],
            "claim_boundary": authority["claim_boundary"],
        }
        (stage / "manifest.json").write_bytes(canonical(manifest))
        (stage / "manifest.json").chmod(0o444)
        shutil.rmtree(work)
        count = write_checksums(stage)
        retained = [path for path in stage.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"]
        require(count == len(retained), "ABI checksum membership does not match retained members")
        with defer_catchable_signals():
            rename_noreplace(stage, result_dir)
            current = result_dir
        require((result_dir / "manifest.json").is_file(), "published ABI result is incomplete")
        return result
    except BaseException:
        if current is not None and current.exists():
            shutil.rmtree(current, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("selftest", "run"))
    parser.add_argument("--authority", type=Path, default=AUTHORITY)
    parser.add_argument("--expected", type=Path, default=EXPECTED)
    parser.add_argument("--abi-authority", type=Path, default=ABI_AUTHORITY)
    parser.add_argument("--abi-expected", type=Path, default=ABI_EXPECTED)
    parser.add_argument("--analyzer", type=Path)
    parser.add_argument("--probe", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--expected-candidate-tree")
    parser.add_argument("--result-dir", type=Path)
    args = parser.parse_args()
    try:
        authority = validate_authority(load(args.authority.resolve(strict=True)))
        selftest(authority)
        if args.action == "selftest":
            print("sprint13-abi-role-vector-equivalence-smoke: ok internal_dispositions=48 targets=24 max_indices=98304 queries=36 public_closures=96 candidate_source_bound=1 no_replace=1 run=deferred")
            return 0
        for name in ("analyzer", "probe", "source_root", "source_manifest", "expected_candidate_tree", "result_dir"):
            require(getattr(args, name) is not None, f"--{name.replace('_', '-')} is required")
        with signal_guard("ABI role vector equivalence"):
            result = run(args, authority)
        print(f"sprint13-abi-role-vector-equivalence-smoke: ok internal_dispositions={result['internal_dispositions']} vectors={result['vector_matches']}/{result['occupied_indices']} targets=24 queries=36 public_closures=96 candidate_source_bound=1 no_replace=1 public_fields_added=0 semantic_changes=0 score_changes=0 schema_changed=0")
        return 0
    except (OSError, VectorError, subprocess.SubprocessError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
