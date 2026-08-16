#!/usr/bin/env python3
"""Run and verify the bounded P089 opt-in split-debug packaging experiment.

The experiment consumes three-generation producer evidence but selects exactly
builds one and two.  It validates source/build independence, executes distinct
behavior profiles, packages a runtime tier plus debug companion, retains exact
member and mode authorities, and publishes complete-or-absent.  It remains a
diagnostic release experiment: post-link path redaction is still required on
current toolchains, path-stable DWARF is not established, and product adoption
is not authorized.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
from typing import Any, NoReturn
import zlib

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_TOOL = ROOT / "tools/sprint13-producer-authority-smoke.py"
AUTH_SCHEMA = "x64lens-sprint13-split-debug-packaging-v2"
RESULT_SCHEMA = "x64lens-sprint13-split-debug-packaging-result-v2"
MAX_JSON = 8 * 1024 * 1024
MAX_STREAM = 16 * 1024 * 1024
LOCAL_PREFIXES = (b"/tmp/", b"/home/", b"/mnt/")


class SplitDebugError(RuntimeError):
    pass


class CatchableTermination(SplitDebugError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SplitDebugError(message)


def fail(message: str) -> NoReturn:
    print(f"sprint13-split-debug-packaging-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def strict(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> Any:
    raw = path.read_bytes()
    require(len(raw) <= MAX_JSON, f"JSON exceeds bound: {path}")
    return json.loads(raw, object_pairs_hook=strict)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGHUP, signal.SIGINT, signal.SIGTERM})
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def safe_rel(raw: str) -> str:
    require(isinstance(raw, str) and raw, "empty path")
    path = PurePosixPath(raw)
    require(not path.is_absolute() and "\\" not in raw and all(part not in {"", ".", ".."} for part in path.parts),
            f"unsafe path: {raw!r}")
    require(path.as_posix() == raw, f"noncanonical path: {raw!r}")
    return raw


def resolve_tool(raw: str) -> Path:
    candidate = Path(raw)
    if "/" not in raw:
        value = shutil.which(raw)
        require(value is not None, f"required tool unavailable: {raw}")
        candidate = Path(value)
    candidate = candidate.resolve(strict=True)
    st = candidate.stat()
    require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and os.access(candidate, os.X_OK),
            f"tool is not one executable regular file: {candidate}")
    return candidate


def run(argv: list[str], *, cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, check=False, timeout=timeout)
    require(len(cp.stdout) <= MAX_STREAM and len(cp.stderr) <= MAX_STREAM, "command output exceeded bound")
    return cp


def tool_record(path: Path, version_args: list[str]) -> dict[str, Any]:
    cp = run([os.fspath(path), *version_args], cwd=path.parent)
    require(cp.returncode == 0, f"tool version command failed: {path}")
    st = path.stat()
    return {"sha256": sha(path), "size_bytes": st.st_size, "mode": f"{stat.S_IMODE(st.st_mode):04o}",
            "version_sha256": sha_bytes(cp.stdout + cp.stderr)}


def verify_member(root: Path, record: dict[str, Any], executable: bool) -> Path:
    require(isinstance(record, dict) and set(record) >= {"path", "sha256", "size_bytes", "mode"},
            "producer member descriptor is incomplete")
    path = root / safe_rel(record["path"])
    st = os.lstat(path)
    require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, f"unsafe producer member: {record['path']}")
    require(st.st_size == record["size_bytes"] and sha(path) == record["sha256"],
            f"producer member bytes changed: {record['path']}")
    require(f"{stat.S_IMODE(st.st_mode):04o}" == record["mode"], f"producer member mode changed: {record['path']}")
    require(bool(st.st_mode & 0o111) == executable, f"producer member executable state changed: {record['path']}")
    return path


def validate_authority(authority: dict[str, Any], expected: dict[str, Any]) -> None:
    required = {"schema", "sprint", "patch", "experiment_id", "evidence_class", "publication_eligible",
                "product_adoption_authorized", "builds", "producer_authority", "packaging", "behavior_profiles",
                "known_symbols", "required_denominators", "companion_controls", "public_boundary", "limitations"}
    require(isinstance(authority, dict) and set(authority) == required, "authority shape changed")
    require(authority["schema"] == AUTH_SCHEMA and authority["sprint"] == 13 and authority["patch"] == 89,
            "authority identity changed")
    require(authority["experiment_id"] == expected.get("experiment_id"), "experiment identity changed")
    require(authority["evidence_class"] == "diagnostic" and authority["publication_eligible"] is False
            and authority["product_adoption_authorized"] is False, "evidence boundary changed")
    require(authority["builds"] == expected.get("builds") == 2, "build denominator changed")
    producer = authority["producer_authority"]
    require(producer == {"schema": "x64lens-sprint13-producer-authority-v1", "generation_count": 3,
                         "selected_generations": [1, 2],
                         "build_commands": ["make clean", "make -j1", "make -j1 samples"]},
            "producer authority changed")
    profiles = authority["behavior_profiles"]
    require(isinstance(profiles, list) and len(profiles) == expected["behavior_profiles"] == 15,
            "behavior profile denominator changed")
    ids: list[str] = []
    signatures: list[str] = []
    for profile in profiles:
        require(isinstance(profile, dict) and set(profile) == {"id", "args", "target"},
                "behavior profile shape changed")
        require(isinstance(profile["id"], str) and profile["id"], "invalid behavior profile ID")
        require(isinstance(profile["args"], list) and profile["args"]
                and all(isinstance(item, str) and item for item in profile["args"]),
                f"invalid behavior command: {profile['id']}")
        require(profile["target"] in {None, "effects", "pairs"}, f"invalid behavior target: {profile['id']}")
        ids.append(profile["id"])
        signatures.append(json.dumps([profile["args"], profile["target"]], separators=(",", ":")))
    require(len(set(ids)) == 15 and len(set(signatures)) == 15,
            "behavior profile identities or semantics are not distinct")
    symbols = authority["known_symbols"]
    require(isinstance(symbols, list) and len(symbols) == 6 and len(set(symbols)) == 6
            and all(isinstance(item, str) and item for item in symbols), "known symbol authority changed")
    den = authority["required_denominators"]
    for key in ("behavior_executions", "behavior_pairs", "companion_controls", "symbol_resolutions"):
        require(den.get(key) == expected.get(key), f"denominator changed: {key}")
    controls = authority["companion_controls"]
    require(isinstance(controls, list) and len(controls) == 8 and len(set(controls)) == 8,
            "control denominator or uniqueness changed")
    packaging = authority["packaging"]
    require(packaging["minimum_runtime_size_reduction"] == expected["minimum_runtime_size_reduction"] == 0.5,
            "size threshold changed")
    require(packaging["build_id_policy"] == "must_be_absent_for_current_experiment"
            and packaging["post_link_path_redaction"] is True
            and packaging["path_stable_dwarf_required_for_adoption"] is True
            and packaging["total_transfer_reduction_required_for_adoption"] is True,
            "packaging policy changed")
    require(authority["public_boundary"] == {"public_fields_added": 0, "runtime_product_adoption": False,
            "schema_changed": False, "score_changes": 0, "semantic_changes": 0}, "public boundary changed")


def validate_producer(manifest_path: Path, root: Path, source_tree: str, authority: dict[str, Any]) -> dict[str, Any]:
    require(manifest_path.parent == root, "producer manifest must be rooted in the producer result directory")
    producer_tool = module("s13_p089_split_producer", PRODUCER_TOOL)
    producer = producer_tool.validate_manifest(manifest_path, source_tree)
    contract = authority["producer_authority"]
    require(producer["schema"] == contract["schema"] and producer["generation_count"] == contract["generation_count"],
            "producer schema or generation denominator changed")
    generations = producer["generations"]
    require(len({item["build_id"] for item in generations}) == contract["generation_count"],
            "producer build IDs are not independent")
    require(all(item["source_candidate_tree"] == source_tree for item in generations),
            "producer source trees disagree")
    require(all(item["source_manifest_sha256"] == producer["source_manifest_sha256"] for item in generations),
            "producer source manifests disagree")
    require(all(item["build_commands"] == contract["build_commands"] for item in generations),
            "producer build commands changed")
    selected = [item for item in generations if item["generation"] in contract["selected_generations"]]
    require([item["generation"] for item in selected] == contract["selected_generations"],
            "selected producer generations changed")
    return {**producer, "selected": selected}


def elf_sections(path: Path) -> dict[str, tuple[int, int]]:
    data = path.read_bytes()
    require(len(data) >= 64 and data[:6] == b"\x7fELF\x02\x01", f"unsupported ELF: {path}")
    shoff = struct.unpack_from("<Q", data, 0x28)[0]
    entsize = struct.unpack_from("<H", data, 0x3A)[0]
    count = struct.unpack_from("<H", data, 0x3C)[0]
    names_index = struct.unpack_from("<H", data, 0x3E)[0]
    require(entsize >= 64 and count > 0 and names_index < count, "unsupported section table")
    require(shoff <= len(data) and count <= (len(data) - shoff) // entsize, "section table out of range")
    names_entry = shoff + names_index * entsize
    names_off = struct.unpack_from("<Q", data, names_entry + 0x18)[0]
    names_size = struct.unpack_from("<Q", data, names_entry + 0x20)[0]
    require(names_off <= len(data) and names_size <= len(data) - names_off, "section names out of range")
    names = data[names_off:names_off + names_size]
    out: dict[str, tuple[int, int]] = {}
    for index in range(count):
        entry = shoff + index * entsize
        name_offset = struct.unpack_from("<I", data, entry)[0]
        section_type = struct.unpack_from("<I", data, entry + 4)[0]
        offset = struct.unpack_from("<Q", data, entry + 0x18)[0]
        size = struct.unpack_from("<Q", data, entry + 0x20)[0]
        require(name_offset < len(names), "section name offset out of range")
        end = names.find(b"\0", name_offset)
        require(end >= 0, "unterminated section name")
        name = names[name_offset:end].decode("ascii", "strict")
        if section_type != 8:
            require(offset <= len(data) and size <= len(data) - offset, f"section out of range: {name}")
            out[name] = (offset, size)
        else:
            out[name] = (offset, 0)
    return out


def parse_debuglink(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    offset, size = elf_sections(path)[".gnu_debuglink"]
    payload = data[offset:offset + size]
    end = payload.find(b"\0")
    require(end > 0, "malformed debuglink filename")
    crc_offset = (end + 4) & ~3
    require(crc_offset + 4 <= len(payload), "malformed debuglink CRC")
    return payload[:end].decode("ascii"), struct.unpack_from("<I", payload, crc_offset)[0]


def redact_paths(path: Path) -> int:
    data = bytearray(path.read_bytes())
    token = b"/x64lens/p089/redacted"
    count = 0
    for match in list(re.finditer(rb"[ -~]{4,}", data)):
        value = bytes(match.group())
        if any(prefix in value for prefix in LOCAL_PREFIXES):
            require(len(value) >= len(token), "path string shorter than redaction token")
            data[match.start():match.end()] = token + b"x" * (len(value) - len(token))
            count += 1
    path.write_bytes(data)
    require(not any(prefix in data for prefix in LOCAL_PREFIXES), "local path remained after redaction")
    return count


def package_once(analyzer: Path, destination: Path, objcopy: Path) -> dict[str, Any]:
    destination.mkdir(parents=True, mode=0o755)
    original = destination / "original.debug"
    debug = destination / "x64lens.debug"
    core = destination / "runtime.core"
    runtime = destination / "x64lens"
    cp = run([os.fspath(objcopy), "--only-keep-debug", os.fspath(analyzer), os.fspath(debug)], cwd=destination)
    require(cp.returncode == 0, "objcopy --only-keep-debug failed")
    shutil.copyfile(debug, original)
    redactions = redact_paths(debug)
    shutil.copyfile(analyzer, core)
    cp = run([os.fspath(objcopy), "--strip-all", os.fspath(core)], cwd=destination)
    require(cp.returncode == 0, "objcopy --strip-all failed")
    shutil.copyfile(core, runtime)
    cp = run([os.fspath(objcopy), "--add-gnu-debuglink=x64lens.debug", "x64lens"], cwd=destination)
    require(cp.returncode == 0, "objcopy --add-gnu-debuglink failed")
    runtime.chmod(0o755); core.chmod(0o755); debug.chmod(0o644); original.chmod(0o644)
    name, crc = parse_debuglink(runtime)
    require(name == "x64lens.debug" and crc == (zlib.crc32(debug.read_bytes()) & 0xffffffff),
            "debuglink filename/CRC mismatch")
    require(".gnu_debuglink" not in elf_sections(core), "runtime core already has debuglink")
    require(".note.gnu.build-id" not in elf_sections(analyzer), "unexpected GNU build ID")
    require(not any(prefix in runtime.read_bytes() + debug.read_bytes() for prefix in LOCAL_PREFIXES),
            "packaged output leaks a local path")
    return {"runtime": runtime, "debug": debug, "core": core, "original": original,
            "crc": crc, "redactions": redactions}


def symbol_addresses(analyzer: Path, nm: Path, symbols: list[str], cwd: Path) -> dict[str, str]:
    cp = run([os.fspath(nm), "-n", "--defined-only", os.fspath(analyzer)], cwd=cwd)
    require(cp.returncode == 0, "nm failed")
    found: dict[str, str] = {}
    for line in cp.stdout.decode("utf-8", "strict").splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[-1] in symbols:
            require(fields[-1] not in found, f"duplicate known symbol emitted: {fields[-1]}")
            found[fields[-1]] = "0x" + fields[0]
    require(set(found) == set(symbols), "known symbol set changed")
    return found


def resolve(addr2line: Path, cwd: Path, runtime: str, address: str) -> tuple[str, str]:
    cp = run([os.fspath(addr2line), "-f", "-e", runtime, address], cwd=cwd)
    require(cp.returncode == 0, "addr2line failed")
    lines = cp.stdout.decode("utf-8", "replace").splitlines()
    require(len(lines) >= 2, "addr2line output incomplete")
    return lines[0], lines[1]


def write_file(path: Path, data: bytes, mode: int) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)
    return {"sha256": sha_bytes(data), "size_bytes": len(data), "mode": f"{mode:04o}"}


def behavior(authority: dict[str, Any], build: int, unstripped: Path, runtime: Path,
             effects_source: Path, pairs_source: Path, retained: Path) -> tuple[int, int, dict[str, Any]]:
    work = runtime.parent
    effects = work / "effects"; pairs = work / "pairs"
    shutil.copyfile(effects_source, effects); shutil.copyfile(pairs_source, pairs)
    effects.chmod(0o444); pairs.chmod(0o444)
    targets = {"effects": effects.name, "pairs": pairs.name}
    executions = pairs_count = 0
    rows: list[dict[str, Any]] = []
    for profile in authority["behavior_profiles"]:
        args = list(profile["args"])
        if profile["target"] is not None:
            args.append(targets[profile["target"]])
        observed: dict[str, subprocess.CompletedProcess[bytes]] = {}
        for variant, binary in (("unstripped", unstripped), ("runtime", runtime)):
            cp = run([os.fspath(binary), *args], cwd=work)
            observed[variant] = cp
            raw_root = retained / "raw" / profile["id"]
            stdout = write_file(raw_root / f"{variant}.stdout", cp.stdout, 0o444)
            stderr = write_file(raw_root / f"{variant}.stderr", cp.stderr, 0o444)
            rows.append({"profile": profile["id"], "variant": variant, "args": args,
                         "exit_code": cp.returncode, "stdout": stdout, "stderr": stderr})
            executions += 1
        require(observed["unstripped"].returncode == observed["runtime"].returncode
                and observed["unstripped"].stdout == observed["runtime"].stdout
                and observed["unstripped"].stderr == observed["runtime"].stderr,
                f"behavior closure mismatch: build {build}/{profile['id']}")
        pairs_count += 1
    descriptor = write_file(retained / "behavior.json", canonical(rows), 0o444)
    descriptor["path"] = (retained / "behavior.json").name
    return executions, pairs_count, descriptor


def rename_noreplace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, "renameat2", None)
    require(function is not None, "renameat2 unavailable")
    rc = function(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    if rc != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), os.fspath(destination))


def descriptor(path: Path, root: Path) -> dict[str, Any]:
    st = os.lstat(path)
    require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, f"unsafe retained member: {path}")
    return {"path": path.relative_to(root).as_posix(), "sha256": sha(path), "size_bytes": st.st_size,
            "mode": f"{stat.S_IMODE(st.st_mode):04o}"}


def directory_authority(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), key=lambda item: item.relative_to(root).as_posix()):
        st = os.lstat(path)
        require(stat.S_ISDIR(st.st_mode), f"unsafe retained directory: {path}")
        rows.append({"path": path.relative_to(root).as_posix(), "mode": f"{stat.S_IMODE(st.st_mode):04o}"})
    return rows


def retained_authority(root: Path) -> list[dict[str, Any]]:
    return [descriptor(path, root) for path in sorted(
        (item for item in root.rglob("*") if item.is_file() and item.name not in {"manifest.json", "SHA256SUMS.txt"}),
        key=lambda item: item.relative_to(root).as_posix())]


def checksums(root: Path) -> None:
    rows = [f"{sha(path)}  {path.relative_to(root).as_posix()}" for path in sorted(
        (item for item in root.rglob("*") if item.is_file() and item.name != "SHA256SUMS.txt"),
        key=lambda item: item.relative_to(root).as_posix())]
    write_file(root / "SHA256SUMS.txt", ("\n".join(rows) + "\n").encode(), 0o444)


def verify_result_tree(result_dir: Path, result: dict[str, Any]) -> None:
    root_stat = os.lstat(result_dir)
    require(stat.S_ISDIR(root_stat.st_mode) and stat.S_IMODE(root_stat.st_mode) == 0o755,
            "result root mode or type changed")
    declared_dirs = {row["path"]: row for row in result["retained_directories"]}
    declared_files = {row["path"]: row for row in result["retained_members"]}
    require(len(declared_dirs) == len(result["retained_directories"]), "duplicate retained directory")
    require(len(declared_files) == len(result["retained_members"]), "duplicate retained member")
    actual_dirs: set[str] = set()
    actual_files: set[str] = set()
    inode_keys: set[tuple[int, int]] = set()
    for path in result_dir.rglob("*"):
        rel = path.relative_to(result_dir).as_posix()
        st = os.lstat(path)
        require(not stat.S_ISLNK(st.st_mode), f"linked result member rejected: {rel}")
        if stat.S_ISDIR(st.st_mode):
            actual_dirs.add(rel)
            require(rel in declared_dirs and f"{stat.S_IMODE(st.st_mode):04o}" == declared_dirs[rel]["mode"],
                    f"result directory authority changed: {rel}")
        elif stat.S_ISREG(st.st_mode):
            require(st.st_nlink == 1, f"hard-linked result member rejected: {rel}")
            key = (st.st_dev, st.st_ino)
            require(key not in inode_keys, f"duplicate inode topology in result: {rel}")
            inode_keys.add(key)
            if rel not in {"manifest.json", "SHA256SUMS.txt"}:
                actual_files.add(rel)
                require(rel in declared_files, f"undeclared result member: {rel}")
                record = declared_files[rel]
                require(st.st_size == record["size_bytes"] and sha(path) == record["sha256"]
                        and f"{stat.S_IMODE(st.st_mode):04o}" == record["mode"],
                        f"result member authority changed: {rel}")
            else:
                require(stat.S_IMODE(st.st_mode) == 0o444, f"result authority mode changed: {rel}")
        else:
            raise SplitDebugError(f"special result member rejected: {rel}")
    require(actual_dirs == set(declared_dirs) and actual_files == set(declared_files),
            "result membership changed")
    checksum_path = result_dir / "SHA256SUMS.txt"
    declared: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        require(len(line) >= 67 and line[64:66] == "  ", "malformed result checksum row")
        digest, raw = line[:64], safe_rel(line[66:])
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None and raw not in declared
                and raw != "SHA256SUMS.txt", "invalid/duplicate result checksum row")
        declared[raw] = digest
    actual = {path.relative_to(result_dir).as_posix(): sha(path) for path in result_dir.rglob("*")
              if path.is_file() and path.name != "SHA256SUMS.txt"}
    require(declared == actual, "result checksum closure changed")


def validate_result(result: dict[str, Any], expected: dict[str, Any], tree: str) -> None:
    required = {"schema", "sprint", "patch", "experiment_id", "evidence_class", "publication_eligible",
                "product_adoption_authorized", "source_candidate_tree", "producer_manifest_sha256",
                "producer_source_manifest_sha256", "tools", "build_results", "companion_controls", "summary",
                "retained_directories", "retained_members", "public_boundary", "limitations"}
    require(isinstance(result, dict) and set(result) == required, "result shape changed")
    require(result["schema"] == RESULT_SCHEMA and result["sprint"] == 13 and result["patch"] == 89
            and result["source_candidate_tree"] == tree, "result identity changed")
    require(result["evidence_class"] == "diagnostic" and result["publication_eligible"] is False
            and result["product_adoption_authorized"] is False, "result evidence boundary changed")
    builds = result["build_results"]
    require(isinstance(builds, list) and len(builds) == 2 and [item["generation"] for item in builds] == [1, 2]
            and len({item["producer_build_id"] for item in builds}) == 2,
            "result build independence changed")
    for item in builds:
        require(item["source_candidate_tree"] == tree
                and item["source_manifest_sha256"] == result["producer_source_manifest_sha256"]
                and item["build_commands"] == ["make clean", "make -j1", "make -j1 samples"],
                "result source/build provenance changed")
        require(len(item["symbol_resolutions"]) == 6
                and len({row["symbol"] for row in item["symbol_resolutions"]}) == 6,
                "result symbol denominator or uniqueness changed")
        require(item["behavior_executions"] == 30 and item["behavior_pairs"] == 15,
                "result behavior denominator changed")
    summary = result["summary"]
    for key in ("builds", "behavior_executions", "behavior_pairs", "companion_controls",
                "symbol_resolutions", "local_path_leaks"):
        require(summary.get(key) == expected.get(key), f"result denominator changed: {key}")
    require(summary["minimum_runtime_size_reduction"] >= expected["minimum_runtime_size_reduction"],
            "runtime reduction below threshold")
    require(summary["build_id_present"] is False
            and summary["runtime_bytes_equal_between_builds"] is True
            and summary["companion_bytes_equal_between_builds"] is True,
            "packaging equivalence changed")
    require(summary["path_stable_dwarf"] is expected["path_stable_dwarf"] is False
            and summary["post_link_redaction_used"] is expected["post_link_redaction_used"] is True
            and summary["total_transfer_reduction"] is expected["total_transfer_reduction"] is False,
            "adoption prerequisite state changed")
    require(result["public_boundary"] == {"public_fields_added": 0, "runtime_product_adoption": False,
            "schema_changed": False, "score_changes": 0, "semantic_changes": 0}, "public boundary changed")


def safe_remove_stage(stage: Path, opened: tuple[int, int] | None) -> None:
    if not stage.exists():
        return
    st = os.lstat(stage)
    require(opened is not None and stat.S_ISDIR(st.st_mode) and (st.st_dev, st.st_ino) == opened,
            "split-debug stage identity changed; residue preserved")
    shutil.rmtree(stage)


def run_experiment(authority_path: Path, expected_path: Path, producer_root: Path,
                   producer_manifest_path: Path, result_dir: Path, source_tree: str,
                   objcopy_raw: str, nm_raw: str, addr2line_raw: str) -> dict[str, Any]:
    authority = load(authority_path); expected = load(expected_path)
    validate_authority(authority, expected)
    producer = validate_producer(producer_manifest_path, producer_root, source_tree, authority)
    require(not result_dir.exists(), "result already exists")
    result_dir.parent.mkdir(parents=True, exist_ok=True)
    objcopy = resolve_tool(objcopy_raw); nm = resolve_tool(nm_raw); addr2line = resolve_tool(addr2line_raw)
    stage: Path | None = None
    stage_identity: tuple[int, int] | None = None
    try:
        with signal_guard("split-debug experiment"):
            with defer_catchable_signals():
                stage = Path(tempfile.mkdtemp(prefix=".p089-split-debug-stage.", dir=result_dir.parent))
                st = os.lstat(stage)
                stage_identity = (st.st_dev, st.st_ino)
            with tempfile.TemporaryDirectory(prefix="x64lens-p089-split-debug-") as raw:
                workspace = Path(raw)
                build_results: list[dict[str, Any]] = []
                packages: list[dict[str, Any]] = []
                original_debugs: list[Path] = []
                cores: list[Path] = []
                total_exec = total_pairs = total_symbols = 0
                controls: list[str] = []
                for index, generation in enumerate(producer["selected"], 1):
                    analyzer = verify_member(producer_root, generation["analyzer"], True)
                    effects = verify_member(producer_root, generation["effects_fixture"], False)
                    pairs = verify_member(producer_root, generation["ordered_pairs_fixture"], False)
                    first = package_once(analyzer, workspace / f"build-{index}/a", objcopy)
                    second = package_once(analyzer, workspace / f"build-{index}/b", objcopy)
                    for key in ("runtime", "debug", "core"):
                        require(first[key].read_bytes() == second[key].read_bytes(),
                                f"nondeterministic {key}: build {index}")
                    retained = stage / f"build-{index}"
                    retained.mkdir(mode=0o755)
                    runtime = retained / "x64lens"; debug = retained / "x64lens.debug"
                    shutil.copyfile(first["runtime"], runtime); shutil.copyfile(first["debug"], debug)
                    runtime.chmod(0o555); debug.chmod(0o444)
                    unstripped = workspace / f"build-{index}/unstripped"
                    shutil.copyfile(analyzer, unstripped); unstripped.chmod(0o755)
                    executed, paired, behavior_descriptor = behavior(
                        authority, index, unstripped, first["runtime"], effects, pairs, retained)
                    total_exec += executed; total_pairs += paired
                    addresses = symbol_addresses(unstripped, nm, authority["known_symbols"], first["runtime"].parent)
                    resolutions: list[dict[str, str]] = []
                    for symbol in authority["known_symbols"]:
                        name, location = resolve(addr2line, first["runtime"].parent, "x64lens", addresses[symbol])
                        require(name == symbol and not any(prefix.decode() in location for prefix in LOCAL_PREFIXES),
                                f"symbol resolution failed: build {index}/{symbol}")
                        resolutions.append({"symbol": symbol, "address": addresses[symbol], "location": location})
                        total_symbols += 1
                    controls.extend([f"build{index}_debuglink_name_crc", f"build{index}_symbol_resolution"])
                    unstripped_size = analyzer.stat().st_size
                    runtime_size = runtime.stat().st_size
                    companion_size = debug.stat().st_size
                    reduction = (unstripped_size - runtime_size) / unstripped_size
                    total_reduction = (unstripped_size - runtime_size - companion_size) / unstripped_size
                    require(reduction >= 0.5, f"runtime reduction below threshold: build {index}")
                    packages.append(first); original_debugs.append(first["original"]); cores.append(first["core"])
                    build_results.append({"build": index, "generation": generation["generation"],
                        "producer_build_id": generation["build_id"],
                        "source_candidate_tree": generation["source_candidate_tree"],
                        "source_manifest_sha256": generation["source_manifest_sha256"],
                        "build_commands": generation["build_commands"],
                        "unstripped_sha256": sha(analyzer), "unstripped_size_bytes": unstripped_size,
                        "runtime": {"sha256": sha(runtime), "size_bytes": runtime_size, "mode": "0555"},
                        "companion": {"sha256": sha(debug), "size_bytes": companion_size, "mode": "0444"},
                        "behavior": behavior_descriptor, "runtime_size_reduction": reduction,
                        "total_transfer_reduction": total_reduction, "debuglink_crc32": first["crc"],
                        "redacted_local_path_strings": first["redactions"], "symbol_resolutions": resolutions,
                        "behavior_executions": executed, "behavior_pairs": paired, "build_id_present": False})
                first = packages[0]; work = first["runtime"].parent; debug = work / "x64lens.debug"
                saved = debug.read_bytes(); absent = work / "x64lens.debug.absent"; debug.rename(absent)
                name, _ = resolve(addr2line, work, "x64lens", build_results[0]["symbol_resolutions"][0]["address"])
                require(name == "??", "missing companion accepted"); absent.rename(debug)
                controls.append("companion_absent_rejected")
                corrupt = bytearray(saved); require(len(corrupt) > 128, "debug companion too small")
                corrupt[128] ^= 1; debug.write_bytes(corrupt)
                name, _ = resolve(addr2line, work, "x64lens", build_results[0]["symbol_resolutions"][0]["address"])
                require(name == "??", "CRC-mismatched companion accepted"); debug.write_bytes(saved)
                controls.append("companion_crc_mismatch_rejected")
                cross = workspace / "cross"; cross.mkdir(); runtime_orig = cross / "runtime"; canonical_debug = cross / "x64lens.debug"
                shutil.copyfile(cores[0], runtime_orig); shutil.copyfile(original_debugs[0], canonical_debug)
                cp = run([os.fspath(objcopy), "--add-gnu-debuglink=x64lens.debug", "runtime"], cwd=cross)
                require(cp.returncode == 0, "cross-build control setup failed")
                shutil.copyfile(original_debugs[1], canonical_debug)
                name, _ = resolve(addr2line, cross, "runtime", build_results[0]["symbol_resolutions"][0]["address"])
                require(name == "??", "cross-build pre-normalization companion accepted")
                controls.append("cross_build_substitution_rejected_before_normalization")
                require(".gnu_debuglink" not in elf_sections(cores[0]), "runtime core contains debuglink")
                controls.append("runtime_core_has_no_debuglink")
                require(len(controls) == 8 and set(controls) == set(authority["companion_controls"]),
                        "companion-control closure changed")
                runtime_equal = packages[0]["runtime"].read_bytes() == packages[1]["runtime"].read_bytes()
                debug_equal = packages[0]["debug"].read_bytes() == packages[1]["debug"].read_bytes()
                require(runtime_equal and debug_equal, "normalized artifacts differ across builds")
                path_stable = all(item["redacted_local_path_strings"] == 0 for item in build_results)
                total_transfer_reduction = all(item["total_transfer_reduction"] > 0 for item in build_results)
                result = {"schema": RESULT_SCHEMA, "sprint": 13, "patch": 89,
                    "experiment_id": authority["experiment_id"], "evidence_class": "diagnostic",
                    "publication_eligible": False, "product_adoption_authorized": False,
                    "source_candidate_tree": source_tree, "producer_manifest_sha256": sha(producer_manifest_path),
                    "producer_source_manifest_sha256": producer["source_manifest_sha256"],
                    "tools": {"objcopy": tool_record(objcopy, ["--version"]), "nm": tool_record(nm, ["--version"]),
                              "addr2line": tool_record(addr2line, ["--version"])},
                    "build_results": build_results,
                    "companion_controls": [{"id": item, "passed": True} for item in controls],
                    "summary": {"builds": 2, "behavior_executions": total_exec, "behavior_pairs": total_pairs,
                        "companion_controls": len(controls), "symbol_resolutions": total_symbols,
                        "minimum_runtime_size_reduction": min(item["runtime_size_reduction"] for item in build_results),
                        "build_id_present": False, "local_path_leaks": 0,
                        "runtime_bytes_equal_between_builds": runtime_equal,
                        "companion_bytes_equal_between_builds": debug_equal,
                        "path_stable_dwarf": path_stable, "post_link_redaction_used": not path_stable,
                        "total_transfer_reduction": total_transfer_reduction},
                    "retained_directories": [], "retained_members": [],
                    "public_boundary": authority["public_boundary"], "limitations": authority["limitations"]}
                # Freeze final retained topology before writing the self-describing manifest.
                result["retained_directories"] = directory_authority(stage)
                result["retained_members"] = retained_authority(stage)
                validate_result(result, expected, source_tree)
                write_file(stage / "manifest.json", canonical(result), 0o444)
                checksums(stage)
                verify_result_tree(stage, result)
                with defer_catchable_signals():
                    rename_noreplace(stage, result_dir)
                    stage = None
                published = load(result_dir / "manifest.json")
                validate_result(published, expected, source_tree)
                verify_result_tree(result_dir, published)
                return published
    finally:
        if stage is not None and stage.exists():
            safe_remove_stage(stage, stage_identity)


def verify(authority_path: Path, expected_path: Path, result_dir: Path, source_tree: str) -> dict[str, Any]:
    authority = load(authority_path); expected = load(expected_path); validate_authority(authority, expected)
    result = load(result_dir / "manifest.json")
    validate_result(result, expected, source_tree)
    verify_result_tree(result_dir, result)
    return result


def selftest(authority_path: Path, expected_path: Path) -> None:
    authority = load(authority_path); expected = load(expected_path); validate_authority(authority, expected)
    mutations = 0
    mutators = [
        lambda value: value.__setitem__("builds", 1),
        lambda value: value.__setitem__("publication_eligible", True),
        lambda value: value.__setitem__("product_adoption_authorized", True),
        lambda value: value["required_denominators"].__setitem__("behavior_executions", 59),
        lambda value: value["public_boundary"].__setitem__("score_changes", 1),
        lambda value: value["known_symbols"].__setitem__(1, value["known_symbols"][0]),
        lambda value: value["behavior_profiles"].__setitem__(1, {**value["behavior_profiles"][1],
            "args": list(value["behavior_profiles"][0]["args"]), "target": value["behavior_profiles"][0]["target"]}),
        lambda value: value["producer_authority"].__setitem__("generation_count", 2),
        lambda value: value["packaging"].__setitem__("path_stable_dwarf_required_for_adoption", False),
        lambda value: value["companion_controls"].__setitem__(1, value["companion_controls"][0]),
    ]
    for mutator in mutators:
        changed = json.loads(json.dumps(authority))
        mutator(changed)
        try:
            validate_authority(changed, expected)
        except SplitDebugError:
            mutations += 1
        else:
            raise SplitDebugError("authority mutation accepted")
    require(mutations == len(mutators), "mutation denominator changed")
    with tempfile.TemporaryDirectory(prefix="x64lens-split-stage-signal-") as raw:
        parent = Path(raw)
        stage: Path | None = None
        identity: tuple[int, int] | None = None
        try:
            with signal_guard("split stage selftest"):
                with defer_catchable_signals():
                    stage = Path(tempfile.mkdtemp(prefix=".p089-split-debug-stage.", dir=parent))
                    st = os.lstat(stage); identity = (st.st_dev, st.st_ino)
                os.kill(os.getpid(), signal.SIGTERM)
        except CatchableTermination:
            if stage is not None and stage.exists():
                safe_remove_stage(stage, identity)
        else:
            raise SplitDebugError("split-debug signal selftest was not delivered")
        require(stage is not None and not stage.exists(), "split-debug signal left staging residue")
    print("sprint13-split-debug-packaging-smoke: ok mode=selftest builds=2 producer_generations=3 "
          "behavior_profiles=15 behavior_executions=60 behavior_pairs=30 companion_controls=8 "
          "symbol_resolutions=12 minimum_reduction=0.50 path_stable_required=1 "
          f"product_adoption=0 mutation_rejections={mutations} signal_cleanup=1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("selftest", "run", "verify"):
        item = sub.add_parser(action)
        item.add_argument("--authority", type=Path, required=True)
        item.add_argument("--expected", type=Path, required=True)
        if action != "selftest":
            item.add_argument("--result-dir", type=Path, required=True)
            item.add_argument("--expected-source-tree", required=True)
        if action == "run":
            item.add_argument("--producer-root", type=Path, required=True)
            item.add_argument("--producer-manifest", type=Path, required=True)
            item.add_argument("--objcopy", default="objcopy")
            item.add_argument("--nm", default="nm")
            item.add_argument("--addr2line", default="addr2line")
    args = parser.parse_args()
    if args.action == "selftest":
        selftest(args.authority, args.expected)
    elif args.action == "run":
        result = run_experiment(args.authority, args.expected, args.producer_root.resolve(strict=True),
            args.producer_manifest.resolve(strict=True), args.result_dir, args.expected_source_tree,
            args.objcopy, args.nm, args.addr2line)
        print("sprint13-split-debug-packaging-smoke: ok mode=run builds=2 behavior_executions="
              f"{result['summary']['behavior_executions']} behavior_pairs=30 companion_controls=8 "
              f"symbol_resolutions=12 minimum_reduction={result['summary']['minimum_runtime_size_reduction']:.6f} "
              "path_stable_dwarf=0 product_adoption=0")
    else:
        result = verify(args.authority, args.expected, args.result_dir, args.expected_source_tree)
        print("sprint13-split-debug-packaging-smoke: ok mode=verify builds=2 behavior_executions="
              f"{result['summary']['behavior_executions']} companion_controls=8 symbol_resolutions=12 "
              "retained_members_verified=1 product_adoption=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SplitDebugError, CatchableTermination, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        fail(str(exc))
