#!/usr/bin/env python3
"""Run the exact, no-reroll Sprint 13 natural replay under pinned runtimes."""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-natural-frozen-replay-v2.json"
NATURAL = ROOT / "tools/sprint13-natural-coordinate-campaign.py"
ATTRIBUTION_V1 = ROOT / "tools/sprint13-natural-terminal-attribution-smoke.py"
ATTRIBUTION_V2 = ROOT / "tools/sprint13-natural-terminal-attribution-v2-smoke.py"
REMOVE = ROOT / "tools/remove-owned-tree.py"
TOOLS = ("x64lens", "ropgadget", "ropper", "ropr")
ROLES = ("et_exec", "pie_et_dyn", "shared_et_dyn")


class ReplayError(RuntimeError):
    pass


class CatchableTermination(ReplayError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ReplayError(message)


def fail(message: str) -> NoReturn:
    print(f"sprint13-natural-frozen-replay-v2-smoke: error: {message}", file=sys.stderr)
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
    require(spec is not None and spec.loader is not None, f"cannot load helper: {path}")
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
    guarded = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM}
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, guarded)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def rename_noreplace(source: Path, destination: Path) -> None:
    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    require(renameat2 is not None, "renameat2 unavailable")
    rc = renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    if rc != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), os.fspath(destination))


def safe_rel(raw: str) -> str:
    require(isinstance(raw, str) and raw, "empty predecessor checksum path")
    path = PurePosixPath(raw)
    require(not path.is_absolute() and "\\" not in raw, f"unsafe predecessor checksum path: {raw!r}")
    require(all(part not in {"", ".", ".."} for part in path.parts), f"unsafe predecessor checksum path: {raw!r}")
    return path.as_posix()


def validate_authority(value: Any) -> dict[str, Any]:
    attr = module("s13_p087_replay_attr_v2", ATTRIBUTION_V2)
    return attr.validate_authority(value)


def predecessor_authority(authority: dict[str, Any]) -> dict[str, Any]:
    """Project P088/P089 authority onto the exact P083 predecessor byte identity."""
    require("tool_identities" in authority["input_authority"],
            "predecessor tool identity authority is missing")
    projected = dict(authority)
    projected["tools"] = authority["input_authority"]["tool_identities"]
    return projected


def validate_adapters(authority: dict[str, Any]) -> None:
    require(len(authority["adapters"]) == 2, "adapter denominator changed")
    for item in authority["adapters"]:
        path = ROOT / item["path"]
        require(path.is_file() and not path.is_symlink() and sha(path) == item["sha256"],
                f"adapter authority changed: {item['path']}")


def resolve_symlink_chain(path: Path, *, maximum: int = 16) -> tuple[Path, list[dict[str, Any]]]:
    current = Path(os.path.abspath(path))
    chain: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for _ in range(maximum + 1):
        metadata = os.lstat(current)
        identity = (metadata.st_dev, metadata.st_ino)
        require(identity not in seen, f"symlink cycle rejected: {path}")
        seen.add(identity)
        if not stat.S_ISLNK(metadata.st_mode):
            require(stat.S_ISREG(metadata.st_mode), f"tool chain does not end at a regular file: {path}")
            return current, chain
        target = os.readlink(current)
        chain.append({
            "path_sha256": hashlib.sha256(os.fsencode(current)).hexdigest(),
            "target_sha256": hashlib.sha256(os.fsencode(target)).hexdigest(),
        })
        current = Path(target) if os.path.isabs(target) else current.parent / target
        current = Path(os.path.abspath(current))
    raise ReplayError(f"symlink chain exceeds {maximum} hops: {path}")


def strip_debug_projection(natural: Any, path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    payload, original = natural.read_regular_authority(path, 64 * 1024 * 1024)
    require(original["mode"] == expected["mode"], "x64lens source mode changed")
    objcopy_raw = shutil.which("objcopy")
    require(objcopy_raw is not None, "GNU objcopy is required for x64lens projection")
    objcopy = Path(objcopy_raw).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="x64lens-replay-projection-") as raw:
        root = Path(raw)
        source = root / "x64lens"
        output = root / "x64lens.projected"
        source.write_bytes(payload)
        source.chmod(0o755)
        completed = subprocess.run(
            [os.fspath(objcopy), "--strip-debug", os.fspath(source), os.fspath(output)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=30,
        )
        require(completed.returncode == 0 and len(completed.stderr) <= 65536,
                "GNU objcopy --strip-debug projection failed")
        projected_sha = sha(output)
        projected_size = output.stat().st_size
    require(projected_sha == expected["projection_sha256"], "x64lens strip-debug projection changed")
    require(projected_size == expected["projection_size_bytes"], "x64lens strip-debug size changed")
    return {
        "identity_policy": "strip_debug_projection",
        "source": original,
        "projection_sha256": projected_sha,
        "projection_size_bytes": projected_size,
        "objcopy_sha256": sha(objcopy),
    }


def tool_identity(natural: Any, path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    final, chain = resolve_symlink_chain(path)
    if expected.get("identity_policy") == "strip_debug_projection":
        require(not chain, "x64lens analyzer path may not be a symlink")
        return strip_debug_projection(natural, final, expected)
    current = natural.regular_identity(
        final,
        expected_mode=int(expected["mode"], 8),
        expected_sha256=expected["sha256"],
        require_single_link=False,
    )
    require(current["size_bytes"] == expected["size_bytes"] and bool(int(expected["mode"], 8) & 0o100),
            f"tool authority changed: {path}")
    return {**current, "symlink_chain": chain}

def copy_target(natural: Any, source: Path, destination: Path, expected: dict[str, Any]) -> dict[str, Any]:
    payload, identity = natural.read_regular_authority(source, 64 * 1024 * 1024)
    require(identity["sha256"] == expected["sha256"] and identity["size_bytes"] == expected["size_bytes"],
            f"frozen target changed: {expected['target_id']}")
    natural.write_regular(destination, payload, 0o444)
    return natural.regular_identity(
        destination,
        expected_mode=0o444,
        expected_sha256=expected["sha256"],
        require_single_link=True,
    )


def verify_predecessor_checksum(root: Path) -> int:
    manifest = root / "SHA256SUMS.txt"
    require(manifest.is_file() and not manifest.is_symlink(), "predecessor checksum manifest missing")
    declared: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        require(len(line) >= 67 and line[64:66] == "  ", "malformed predecessor checksum row")
        digest, rel = line[:64], safe_rel(line[66:])
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, "invalid predecessor checksum digest")
        require(rel != "SHA256SUMS.txt" and rel not in declared, "duplicate/self predecessor checksum row")
        declared[rel] = digest

    actual: dict[str, str] = {}
    for item in root.rglob("*"):
        relative = item.relative_to(root).as_posix()
        metadata = item.lstat()
        require(not stat.S_ISLNK(metadata.st_mode), f"linked predecessor evidence rejected: {relative}")
        if stat.S_ISREG(metadata.st_mode):
            require(metadata.st_nlink == 1, f"hard-linked predecessor evidence rejected: {relative}")
            if relative != "SHA256SUMS.txt":
                actual[relative] = sha(item)
        elif stat.S_ISDIR(metadata.st_mode):
            continue
        else:
            raise ReplayError(f"special predecessor evidence rejected: {relative}")
    require(declared == actual, "predecessor checksum membership or bytes changed")
    require(declared, "empty predecessor checksum manifest")
    return len(declared)


def launcher_interpreter(launcher: Path, expected: dict[str, Any], effective: dict[str, str], natural: Any) -> tuple[Path, dict[str, Any]]:
    launcher_file, launcher_chain = resolve_symlink_chain(launcher)
    first = launcher_file.read_bytes().splitlines()[0] if launcher_file.stat().st_size else b""
    require(first.startswith(b"#!"), "Python launcher lacks shebang")
    words = shlex.split(first[2:].decode("utf-8", "strict"))
    require(words, "empty Python launcher shebang")
    if Path(words[0]).name == "env":
        require(len(words) >= 2, "invalid env shebang")
        resolved = shutil.which(words[1], path=effective["PATH"])
        require(resolved is not None, "Python interpreter unavailable")
        invocation = Path(resolved)
    else:
        invocation = Path(words[0])
    require(invocation.is_absolute(), "Python interpreter path is not absolute")
    require(invocation.as_posix().endswith(expected["invocation_suffix"]), "Python launcher left its authenticated environment")
    target, interpreter_chain = resolve_symlink_chain(invocation)
    identity = natural.regular_identity(
        target,
        expected_mode=int(expected["resolved_interpreter"]["mode"], 8),
        expected_sha256=expected["resolved_interpreter"]["sha256"],
        require_single_link=False,
    )
    require(identity["size_bytes"] == expected["resolved_interpreter"]["size_bytes"],
            "resolved Python interpreter size changed")
    return invocation, {
        "invocation_suffix": expected["invocation_suffix"],
        "launcher_symlink_chain": launcher_chain,
        "interpreter_symlink_chain": interpreter_chain,
        "resolved_interpreter": identity,
    }

def package_closures(interpreter: Path, expected: list[dict[str, Any]], env: dict[str, str]) -> list[dict[str, Any]]:
    request = [{"distribution": item["distribution"], "package_root": item["package_root"]} for item in expected]
    script = r'''import base64,csv,hashlib,importlib.metadata,io,json,pathlib,stat,sys
requests=json.loads(sys.argv[1]); out=[]
for req in requests:
 d=importlib.metadata.distribution(req['distribution']); root=req['package_root']; records=[]; total=0
 record_text=d.read_text('RECORD'); assert record_text is not None
 record_sha=hashlib.sha256(record_text.encode()).hexdigest()
 for rel_raw,hash_spec,size_raw in csv.reader(io.StringIO(record_text)):
  rel=pathlib.PurePosixPath(rel_raw)
  if not rel.parts or rel.parts[0] != root or not hash_spec.startswith('sha256='): continue
  p=pathlib.Path(d.locate_file(rel_raw)); st=p.lstat()
  if not stat.S_ISREG(st.st_mode): continue
  payload=p.read_bytes(); encoded=hash_spec.split('=',1)[1]
  expected_digest=base64.urlsafe_b64decode(encoded+'='*((4-len(encoded)%4)%4)).hex()
  assert hashlib.sha256(payload).hexdigest()==expected_digest
  if size_raw: assert len(payload)==int(size_raw)
  records.append({'path':rel.as_posix(),'sha256':expected_digest,'size_bytes':len(payload),'mode':format(stat.S_IMODE(st.st_mode),'04o')})
  total+=len(payload)
 assert records and len(records)<=16384 and total<=1073741824
 canonical=(json.dumps(records,sort_keys=True,separators=(',',':'))+'\n').encode()
 out.append({'distribution':req['distribution'],'version':d.version,'package_root':root,'closure_policy':'importlib_metadata_record_sha256','files':len(records),'bytes':total,'closure_sha256':hashlib.sha256(canonical).hexdigest(),'record_sha256':record_sha})
print(json.dumps(out,sort_keys=True))'''
    cp = subprocess.run(
        [os.fspath(interpreter), "-c", script, json.dumps(request, sort_keys=True, separators=(",", ":"))],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, timeout=60, check=False,
    )
    require(cp.returncode == 0 and len(cp.stdout) <= 65536 and len(cp.stderr) <= 65536,
            "cannot authenticate RECORD-backed Python package closures")
    observed = json.loads(cp.stdout)
    require(len(observed) == len(expected), "Python package closure denominator changed")
    for requested, actual in zip(expected, observed):
        require(actual == requested,
                f"Python RECORD closure changed: {requested['distribution']}")
    return observed

def runtime_authority(
    natural: Any,
    paths: dict[str, Path],
    identities: dict[str, dict[str, Any]],
    authority: dict[str, Any],
    stage: Path,
) -> tuple[dict[str, Any], dict[str, str]]:
    state = stage / "runtime-state"
    home, cache, config = state / "home", state / "cache", state / "config"
    for path in (state, home, cache, config):
        path.mkdir(mode=0o700)
    effective = {
        "HOME": os.fspath(home),
        "XDG_CACHE_HOME": os.fspath(cache),
        "XDG_CONFIG_HOME": os.fspath(config),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    records: dict[str, Any] = {}
    launchers = authority["runtime_authority"]["python_launchers"]
    for name in TOOLS:
        record: dict[str, Any] = {"kind": "native", "executable": identities[name]}
        if name in launchers:
            expected = launchers[name]
            invocation, interpreter = launcher_interpreter(paths[name], expected, effective, natural)
            record = {
                "kind": "python_package_closure",
                "executable": identities[name],
                "interpreter": interpreter,
                "package_closures": package_closures(invocation, expected["package_closures"], effective),
            }
        records[name] = record
    normalized = {
        "HOME": "runtime-state/home",
        "XDG_CACHE_HOME": "runtime-state/cache",
        "XDG_CONFIG_HOME": "runtime-state/config",
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
    }
    require(normalized == authority["runtime_authority"]["environment"], "runtime environment policy changed")
    return {
        "schema": "x64lens-sprint13-natural-runtime-authority-v2",
        "environment": normalized,
        "tools": records,
        "cache_policy": "isolated_empty_before_replay",
        "inherited_home": False,
        "inherited_cache": False,
    }, effective


def checksum_write(natural: Any, stage: Path) -> int:
    files = sorted(
        (path for path in stage.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"),
        key=lambda path: os.fsencode(path.relative_to(stage).as_posix()),
    )
    natural.write_regular(
        stage / "SHA256SUMS.txt",
        "".join(f"{sha(path)}  {path.relative_to(stage).as_posix()}\n" for path in files).encode(),
    )
    return len(files)


def selection_summary(authority: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_count": len(authority["selection"]),
        "role_counts": {role: sum(item["role"] == role for item in authority["selection"]) for role in ROLES},
    }


def run_replay(args: argparse.Namespace, authority: dict[str, Any]) -> dict[str, Any]:
    natural = module("s13_p088_replay_natural", NATURAL)
    attr1 = module("s13_p088_replay_input", ATTRIBUTION_V1)
    remover = module("s13_p088_replay_remove", REMOVE)
    input_dir = args.input_dir.resolve(strict=True)
    try:
        attr1.validate_input(input_dir, predecessor_authority(authority))
    except BaseException as exc:
        if isinstance(exc, CatchableTermination):
            raise
        raise ReplayError(f"predecessor input authority rejected: {type(exc).__name__}") from None
    predecessor_checks = verify_predecessor_checksum(input_dir)
    validate_adapters(authority)
    try:
        source = natural.authenticate_source_authority(
            args.source_root, args.source_manifest, args.expected_candidate_tree
        )
    except BaseException as exc:
        if isinstance(exc, CatchableTermination):
            raise
        raise ReplayError(f"source authority rejected: {type(exc).__name__}") from None

    result_dir = Path(os.path.abspath(args.result_dir))
    require(not result_dir.exists() and not result_dir.is_symlink(), "replay result already exists")
    require(result_dir.parent.is_dir() and not result_dir.parent.is_symlink(), "replay result parent unavailable or linked")
    stage: Path | None = None
    identity = None
    current: Path | None = None
    paths = {
        "x64lens": Path(os.path.abspath(args.x64lens)),
        "ropgadget": Path(os.path.abspath(args.ropgadget)),
        "ropper": Path(os.path.abspath(args.ropper)),
        "ropr": Path(os.path.abspath(args.ropr)),
    }
    try:
        with defer_catchable_signals():
            stage = Path(tempfile.mkdtemp(prefix=f".{result_dir.name}.stage.", dir=result_dir.parent))
            identity = remover.parse_identity(remover.identify(stage))
            current = stage
        identities = {name: tool_identity(natural, path, authority["tools"][name]) for name, path in paths.items()}
        runtime, effective_env = runtime_authority(natural, paths, identities, authority, stage)
        natural.write_regular(stage / "runtime-authority.json", canonical(runtime))
        freeze = {
            "schema": "x64lens-sprint13-natural-selection-freeze-v2",
            "selection": authority["selection"],
            "summary": selection_summary(authority),
        }
        natural.write_regular(stage / "selection-freeze.json", canonical(freeze))

        target_root = stage / "targets"
        target_root.mkdir(mode=0o755)
        frozen_targets = {
            expected["target_id"]: copy_target(
                natural,
                input_dir / "targets" / expected["target_id"],
                target_root / expected["target_id"],
                expected,
            )
            for expected in authority["selection"]
        }

        outcomes: dict[str, Any] = {}
        execution_count = 0
        contract = authority["execution"]
        for expected in authority["selection"]:
            target = target_root / expected["target_id"]
            frozen = frozen_targets[expected["target_id"]]
            records: dict[str, Any] = {}
            for tool in TOOLS:
                require(natural.regular_identity(target, expected_mode=0o444, expected_sha256=expected["sha256"], require_single_link=True) == frozen,
                        f"target changed before replay: {expected['target_id']}/{tool}")
                require(tool_identity(natural, paths[tool], authority["tools"][tool]) == identities[tool],
                        f"tool changed before replay: {tool}")
                argv = natural.tool_commands(tool, paths[tool], target, 4)
                bounded = natural.run_bounded(
                    argv,
                    cwd=ROOT,
                    timeout=contract["timeout_seconds"],
                    stdout_limit=contract["stdout_limit_bytes"],
                    stderr_limit=contract["stderr_limit_bytes"],
                    env=effective_env,
                )
                require(natural.regular_identity(target, expected_mode=0o444, expected_sha256=expected["sha256"], require_single_link=True) == frozen,
                        f"target changed after replay: {expected['target_id']}/{tool}")
                require(tool_identity(natural, paths[tool], authority["tools"][tool]) == identities[tool],
                        f"tool changed after replay: {tool}")
                member = stage / "runs" / expected["target_id"] / tool
                stdout_path, stderr_path = member / "stdout", member / "stderr"
                stdout_desc = natural.write_regular(stdout_path, bounded.stdout)
                stderr_desc = natural.write_regular(stderr_path, bounded.stderr)
                record: dict[str, Any] = {
                    "argv": argv,
                    "exit_code": bounded.exit_code,
                    "signal": bounded.signal,
                    "timeout": bounded.timeout,
                    "output_limited": bounded.output_limited,
                    "wall_ns": bounded.wall_ns,
                    "stdout": {**stdout_desc, "path": stdout_path.relative_to(stage).as_posix()},
                    "stderr": {**stderr_desc, "path": stderr_path.relative_to(stage).as_posix()},
                    "relation_status": "unavailable",
                    "relation_addresses": [],
                }
                if bounded.exit_code == 0 and not bounded.timeout and not bounded.output_limited:
                    try:
                        if tool == "x64lens":
                            virtual, offsets = natural.relation_sets_x64lens(bounded.stdout)
                            record["relation_status"] = "observed" if virtual else "observed_zero"
                            record["virtual_addresses"] = sorted(virtual)
                            record["file_offsets"] = sorted(offsets)
                        else:
                            addresses = natural.relation_set_baseline(tool, bounded.stdout)
                            record["relation_status"] = "observed" if addresses else "observed_zero"
                            record["relation_addresses"] = sorted(addresses)
                    except Exception as exc:
                        record["relation_status"] = "parse_error"
                        record["parse_error"] = type(exc).__name__
                records[tool] = record
                execution_count += 1
            outcomes[expected["target_id"]] = {"target": expected, "tools": records}

        cells: list[dict[str, Any]] = []
        for baseline in natural.BASELINES:
            for role in natural.ROLES:
                observations = []
                for expected in [item for item in authority["selection"] if item["role"] == role]:
                    x64 = outcomes[expected["target_id"]]["tools"]["x64lens"]
                    base = outcomes[expected["target_id"]]["tools"][baseline]
                    observation: dict[str, Any] = {"target_id": expected["target_id"], "target_sha256": expected["sha256"]}
                    if x64["relation_status"] not in {"observed", "observed_zero"} or base["relation_status"] not in {"observed", "observed_zero"}:
                        observation["status"] = "unavailable"
                    else:
                        observation.update(natural.classify(set(base["relation_addresses"]), set(x64["virtual_addresses"]), set(x64["file_offsets"])))
                    observations.append(observation)
                cells.append(natural.cell_result(baseline, role, observations))

        result = {
            "schema": "x64lens-sprint13-natural-frozen-replay-result-v2",
            "sprint": 13,
            "patch": 88,
            "campaign_id": authority["campaign_id"],
            "predecessor_campaign_id": authority["predecessor_campaign_id"],
            "evidence_class": "diagnostic",
            "frozen": False,
            "publication_eligible": False,
            "authority_sha256": sha(args.authority.resolve(strict=True)),
            "predecessor_manifest_sha256": authority["input_authority"]["manifest_sha256"],
            "predecessor_checksum_entries": predecessor_checks,
            "source_authority": source,
            "tool_identities": identities,
            "runtime_authority_sha256": sha(stage / "runtime-authority.json"),
            "selection_freeze_sha256": sha(stage / "selection-freeze.json"),
            "selection_freeze": selection_summary(authority),
            "execution_count": execution_count,
            "complete_execution_denominator": 48,
            "outcomes": outcomes,
            "cells": cells,
            "cell_counts": {state: sum(cell["terminal_state"] == state for cell in cells) for state in ("qualified", "insufficient", "unavailable", "mismatch", "ambiguous")},
            "control_count": sum(len(cell["controls"]) for cell in cells),
            "raw_stream_count": 96,
            "target_file_count": 12,
            "claim_boundary": authority["claim_boundary"],
            "limitations": authority["limitations"],
        }
        natural.require_structural_complete(result)
        require(execution_count == 48 and result["raw_stream_count"] == 96 and result["control_count"] == 108,
                "replay denominator changed")
        require(natural.authenticate_source_authority(args.source_root, args.source_manifest, args.expected_candidate_tree) == source,
                "source authority changed during replay")
        require(stage is not None and identity is not None, "replay stage authority missing")
        natural.write_regular(stage / "manifest.json", canonical(result))
        checksum_count = checksum_write(natural, stage)
        require(checksum_count >= 111, "sealed replay membership is incomplete")
        with defer_catchable_signals():
            rename_noreplace(stage, result_dir)
            current = result_dir
        require(identity is not None, "replay identity authority missing")
        require(remover.identify(result_dir) == f"{remover.IDENTITY_VERSION}:{identity.device}:{identity.inode}:{identity.birth_ns}:{identity.mount_id}",
                "published replay identity changed")
        return result
    except BaseException as exc:
        try:
            if current is not None and current.exists() and identity is not None:
                remover.remove(current, identity)
        except BaseException as cleanup:
            raise ReplayError(f"replay failed and cleanup failed closed: {type(cleanup).__name__}") from None
        if isinstance(exc, (ReplayError, CatchableTermination)):
            raise
        raise ReplayError(f"replay dependency failure: {type(exc).__name__}") from None


def selftest(authority: dict[str, Any]) -> None:
    validate_adapters(authority)
    require(len(authority["selection"]) == 12 and authority["execution"]["execution_denominator"] == 48 and authority["result_contract"]["raw_streams"] == 96,
            "P088 replay selftest changed")
    require(selection_summary(authority) == {"selected_count": 12, "role_counts": {"et_exec": 4, "pie_et_dyn": 4, "shared_et_dyn": 4}},
            "selection-freeze summary changed")
    predecessor = predecessor_authority(authority)
    require(predecessor["tools"] == authority["input_authority"]["tool_identities"]
            and predecessor["tools"]["x64lens"]["sha256"]
            == "39f6af5c7991b6fd7d46b7ac1afb6340164cee14cfcec2d7cd0a2f014bf1222e",
            "predecessor byte-identity bridge changed")
    require(authority["runtime_authority"]["record_verified_package_closures"] == 5,
            "RECORD-backed Python closure denominator changed")
    for tool, expected in authority["runtime_authority"]["python_launchers"].items():
        require(tool in {"ropgadget", "ropper"} and expected["package_closures"], "missing Python package closure descriptor")
        for closure in expected["package_closures"]:
            require(set(closure) == {
                "distribution", "version", "package_root", "closure_policy",
                "files", "bytes", "closure_sha256", "record_sha256",
            } and closure["closure_policy"] == "importlib_metadata_record_sha256"
                    and closure["files"] > 0 and closure["bytes"] > 0
                    and re.fullmatch(r"[0-9a-f]{64}", closure["closure_sha256"])
                    and re.fullmatch(r"[0-9a-f]{64}", closure["record_sha256"]),
                    "invalid RECORD-backed Python package closure authority")
    with tempfile.TemporaryDirectory(prefix="x64lens-replay-symlink-selftest-") as raw:
        root = Path(raw)
        final = root / "launcher.py"
        final.write_text("#!/usr/bin/python3\n", encoding="utf-8")
        middle = root / "middle"
        leaf = root / "leaf"
        middle.symlink_to(final.name)
        leaf.symlink_to(middle.name)
        resolved, chain = resolve_symlink_chain(leaf)
        require(resolved == final and len(chain) == 2, "bounded symlink-chain resolution failed")
    remover = module("s13_p088_replay_selftest_remove", REMOVE)
    with tempfile.TemporaryDirectory(prefix="x64lens-replay-stage-signal-selftest-") as raw:
        parent = Path(raw)
        stage: Path | None = None
        current: Path | None = None
        identity = None
        try:
            with signal_guard("replay stage selftest"):
                try:
                    with defer_catchable_signals():
                        stage = Path(tempfile.mkdtemp(prefix=".stage.", dir=parent))
                        identity = remover.parse_identity(remover.identify(stage))
                        current = stage
                        os.kill(os.getpid(), signal.SIGTERM)
                except BaseException:
                    if current is not None and current.exists() and identity is not None:
                        remover.remove(current, identity)
                    raise
        except CatchableTermination:
            pass
        else:
            raise ReplayError("stage-creation signal was not delivered")
        require(stage is not None and not stage.exists(), "stage-creation signal left replay residue")
    with tempfile.TemporaryDirectory(prefix="x64lens-replay-publication-selftest-") as raw:
        parent = Path(raw)
        final = parent / "result"
        stage = Path(tempfile.mkdtemp(prefix=".result.stage.", dir=parent))
        identity = remover.parse_identity(remover.identify(stage))
        (stage / "owned").write_text("owned", encoding="utf-8")
        try:
            raise ReplayError("injected producer failure")
        except ReplayError:
            remover.remove(stage, identity)
        require(not stage.exists() and not final.exists(), "producer failure left a final or staging result")
    with tempfile.TemporaryDirectory(prefix="x64lens-replay-checksum-selftest-") as raw:
        root = Path(raw) / "input"
        root.mkdir()
        outside = root.parent / "outside"
        outside.write_text("outside")
        (root / "SHA256SUMS.txt").write_text(f"{sha(outside)}  ../outside\n", encoding="utf-8")
        try:
            verify_predecessor_checksum(root)
        except ReplayError:
            pass
        else:
            raise ReplayError("root-escaping predecessor checksum was accepted")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("selftest", "run"))
    parser.add_argument("--authority", type=Path, default=AUTHORITY)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--result-dir", type=Path)
    parser.add_argument("--x64lens", type=Path)
    parser.add_argument("--ropgadget", type=Path)
    parser.add_argument("--ropper", type=Path)
    parser.add_argument("--ropr", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--expected-candidate-tree")
    args = parser.parse_args()
    try:
        authority = validate_authority(load(args.authority.resolve(strict=True)))
        selftest(authority)
        if args.action == "selftest":
            print("sprint13-natural-frozen-replay-v2-smoke: ok targets=12 roles=3 tools=4 executions=48 raw_streams=96 reroll=0 isolated_cache=1 record_python_closures=5 run=deferred")
            return 0
        for name in ("input_dir", "result_dir", "x64lens", "ropgadget", "ropper", "ropr", "source_root", "source_manifest", "expected_candidate_tree"):
            require(getattr(args, name) is not None, f"--{name.replace('_', '-')} is required")
        with signal_guard("natural frozen replay"):
            result = run_replay(args, authority)
        print(f"sprint13-natural-frozen-replay-v2-smoke: ok targets=12 executions={result['execution_count']}/48 raw_streams=96 cells=9 controls={result['control_count']}/108 reroll=0 isolated_cache=1 record_python_closures=5 diagnostic=1")
        return 0
    except (OSError, ReplayError, subprocess.SubprocessError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        fail(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
