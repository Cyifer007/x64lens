#!/usr/bin/env python3
"""Promote Patch 075 review findings into durable adversarial regressions."""
from __future__ import annotations
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
from typing import Any

ROOT=Path(__file__).resolve().parent.parent
class Error(RuntimeError): pass
def require(c:bool,m:str)->None:
    if not c: raise Error(m)
def load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path); require(spec is not None and spec.loader is not None,f"cannot load {path}"); module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module
def run(argv:list[str],cwd:Path|None=None)->subprocess.CompletedProcess[bytes]: return subprocess.run(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
def init_repo(root:Path,relative:str)->Path:
    run(["git","init","-q"],root); run(["git","config","user.email","test@example.invalid"],root); run(["git","config","user.name","test"],root)
    path=root/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_text("tracked\n"); path.chmod(0o644); run(["git","add",relative],root); run(["git","update-index","--chmod=+x",relative],root); return path

def normalizer_tests()->tuple[int,int]:
    module=load("p076_normalizer",ROOT/"tools/normalize-tracked-permissions.py"); file_ok=parent_ok=0
    with tempfile.TemporaryDirectory(prefix="x64lens-p075-normalizer-file-") as td:
        repo=Path(td); target=init_repo(repo,"tool.sh"); displaced=repo/"owned-original"; real=module.os.fchmod; fired=False
        def hook(fd:int,mode:int):
            nonlocal fired
            if not fired and mode==0o755:
                fired=True; target.rename(displaced); target.write_text("foreign\n"); target.chmod(0o600)
            return real(fd,mode)
        module.os.fchmod=hook
        try:
            try: module.normalize(repo)
            except module.PermissionErrorContract: pass
            else: raise Error("normalizer accepted post-preflight file replacement")
        finally: module.os.fchmod=real
        require(fired and stat.S_IMODE(target.stat().st_mode)==0o600,"foreign replacement was modified")
        require(stat.S_IMODE(displaced.stat().st_mode)==0o644,"displaced tracked inode was not rolled back")
        file_ok=1
    with tempfile.TemporaryDirectory(prefix="x64lens-p075-normalizer-parent-") as td:
        repo=Path(td); target=init_repo(repo,"dir/tool.sh"); parent=target.parent; displaced=repo/"owned-dir"; real=module.os.fchmod; fired=False
        def hook(fd:int,mode:int):
            nonlocal fired
            if not fired and mode==0o755:
                fired=True; parent.rename(displaced); parent.mkdir(); foreign=parent/"tool.sh"; foreign.write_text("foreign\n"); foreign.chmod(0o600)
            return real(fd,mode)
        module.os.fchmod=hook
        try:
            try: module.normalize(repo)
            except module.PermissionErrorContract: pass
            else: raise Error("normalizer accepted post-preflight parent replacement")
        finally: module.os.fchmod=real
        require(fired and stat.S_IMODE((parent/"tool.sh").stat().st_mode)==0o600,"foreign parent member was modified")
        require(stat.S_IMODE((displaced/"tool.sh").stat().st_mode)==0o644,"displaced member was not rolled back")
        parent_ok=1
    return file_ok,parent_ok

def custody_tests()->tuple[int,int,int]:
    module=load("p076_custody",ROOT/"tools/verify-delivery-custody.py"); results=[]
    hooks=["_TEST_AFTER_MANIFEST_LINK_HOOK","_TEST_AFTER_MANIFEST_TEMP_UNLINK_HOOK","_TEST_BEFORE_MANIFEST_PARENT_FSYNC_HOOK"]
    for index,hook_name in enumerate(hooks):
        with tempfile.TemporaryDirectory(prefix=f"x64lens-p075-custody-{index}-") as td:
            root=Path(td)/"tree"; root.mkdir(); (root/"payload").write_text("x"); root.chmod(0o755); (root/"payload").chmod(0o644); manifest=root/"manifest.json"
            def explode(*_args:Any)->None: raise OSError("injected post-publication failure")
            setattr(module,hook_name,explode)
            try:
                try: module.create(root,manifest,"test")
                except (module.CustodyError,OSError): pass
                else: raise Error(f"custody publication accepted injected failure: {hook_name}")
            finally: setattr(module,hook_name,None)
            require(not manifest.exists(),f"published manifest residue after {hook_name}")
            require(not any(p.name.startswith(".custody.") for p in root.iterdir()),f"temporary manifest residue after {hook_name}")
            require((root/"payload").read_text()=="x",f"payload changed after {hook_name}")
            results.append(1)
    return tuple(results)  # type: ignore[return-value]

def tiny_manifest(raw:bytes,tree_override:str|None=None)->dict[str,Any]:
    recovery=load("p076_recovery_model",ROOT/"tools/recover-candidate-source.py")
    oid=recovery.git_object(b"blob",raw); payload=b"100644 a\0"+bytes.fromhex(oid); tree=recovery.git_object(b"tree",payload)
    return {"schema_id":"x64lens-candidate-source-tree-v1","candidate_tree":tree_override or tree,"directories":[],"files":[{"path":"a","type":"blob","git_oid":oid,"git_mode":"100644","mode":"0644","sha256":__import__("hashlib").sha256(raw).hexdigest(),"size_bytes":len(raw)}]}
def make_tar(path:Path,raw:bytes,mode:int)->None:
    with tarfile.open(path,"w:gz") as tf:
        info=tarfile.TarInfo("a"); info.size=len(raw); info.mode=mode; info.uid=0; info.gid=0; info.mtime=0; tf.addfile(info,io.BytesIO(raw))
def recovery_tests()->tuple[int,int,int,int]:
    helper=ROOT/"tools/recover-candidate-source.py"; raw=b"hello\n"; mode_reject=tree_reject=ancestor_reject=success=0
    with tempfile.TemporaryDirectory(prefix="x64lens-p075-recovery-") as td:
        root=Path(td); manifest=root/"manifest.json"; archive=root/"source.tar.gz"
        manifest.write_text(json.dumps(tiny_manifest(raw))); make_tar(archive,raw,0o755)
        cp=run([sys.executable,str(helper),"--archive",str(archive),"--manifest",str(manifest),"--destination",str(root/"bad-mode")]); require(cp.returncode!=0 and not (root/"bad-mode").exists(),"recovery accepted TAR mode disagreement"); mode_reject=1
        make_tar(archive,raw,0o644); manifest.write_text(json.dumps(tiny_manifest(raw,"0"*40)))
        cp=run([sys.executable,str(helper),"--archive",str(archive),"--manifest",str(manifest),"--destination",str(root/"bad-tree")]); require(cp.returncode!=0 and not (root/"bad-tree").exists(),"recovery accepted arbitrary candidate tree"); tree_reject=1
        manifest.write_text(json.dumps(tiny_manifest(raw))); cp=run([sys.executable,str(helper),"--archive",str(archive),"--manifest",str(manifest),"--destination",str(root/"missing-parent"/"tree")]); require(cp.returncode!=0 and not (root/"missing-parent").exists(),"recovery auto-created undeclared ancestor"); ancestor_reject=1
        cp=run([sys.executable,str(helper),"--archive",str(archive),"--manifest",str(manifest),"--destination",str(root/"ok")]); require(cp.returncode==0 and b"derived_tree=1" in cp.stdout and (root/"ok/a").read_bytes()==raw,"valid recovery failed"); success=1
    return mode_reject,tree_reject,ancestor_reject,success

def textrel_tests()->tuple[int,int,int,int]:
    module=load("p076_textrel",ROOT/"tools/sprint12-textrel-matrix-smoke.py"); authority=ROOT/"benchmarks/task-definitions/sprint12-textrel-private-evidence-v1.json"; module.load_authority(authority)
    aggregate_rejections=0; case=next(c for c in module.CASES if c.name=="null_only"); base=module.expected_facts(case)
    for key in ("carrier_count","textrel_tag_count","flags_count","flags_first_value","flags_and","flags_or","full_value_conflicts","textrel_conflicts","table_complete","textrel_state"):
        mutated=dict(base); mutated[key]=mutated[key]+1
        try: module.validate_probe(case,(json.dumps(mutated)+"\n").encode())
        except module.Error: aggregate_rejections+=1
        else: raise Error(f"textrel oracle accepted corrupted aggregate: {key}")
    extra=dict(base); extra["extra"]=0
    try: module.validate_probe(case,json.dumps(extra).encode())
    except module.Error: extra_reject=1
    else: raise Error("textrel oracle accepted extra probe key")
    auth=json.loads(authority.read_text())
    for mutate in (lambda x:x["state_values"].__setitem__("present",99),lambda x:x["public_commands"].reverse(),lambda x:x.__setitem__("schema_version","9.9.9")):
        value=json.loads(json.dumps(auth)); mutate(value)
        with tempfile.NamedTemporaryFile("w",delete=False) as f: json.dump(value,f); name=f.name
        try:
            try: module.load_authority(Path(name))
            except module.Error: pass
            else: raise Error("textrel authority mutation accepted")
        finally: os.unlink(name)
    authority_reject=3
    report={"schema_version":"0.2.0","command":"gadgets","target":{"path":"/tmp/path-containing-textrel.elf"}}
    module.validate_public_json(case,"gadgets",json.dumps(report).encode()); path_safe=1
    try: module.load_schema(ROOT/"schemas/does-not-exist.schema.json")
    except OSError: schema_consumed=1
    else: raise Error("nonexistent schema authority was not consumed")
    require(aggregate_rejections==10,"aggregate mutation denominator changed")
    return aggregate_rejections,extra_reject+authority_reject,path_safe,schema_consumed

def tracked_parity_test()->int:
    make=(ROOT/"Makefile").read_text(); script=(ROOT/"tools/sprint12-dynamic-metadata-environment-parity-smoke.py").read_text()
    require("sprint12-p076-acceptance-smoke" in make and "sprint12-dynamic-metadata-environment-parity-smoke" in make,"P076 acceptance omits dynamic parity")
    for token in ("matrix.validate_probe","private_records_compared","native_plane_mounted_into_container","SEARCH_PATH_AUTHORITY"):
        haystack = script if token != "SEARCH_PATH_AUTHORITY" else make
        require(token in haystack,f"dynamic parity omits {token}")
    for token in ("git_oid", "/authority/source-manifest.json:ro", "/output:rw", "verify_source(source_root, source)"):
        require(token in script,f"dynamic parity source or mount custody omits {token}")
    require("/exchange:rw" not in script,"dynamic parity exposes authority through a writable exchange mount")
    return 1

def main()->int:
    nf,np=normalizer_tests(); cl,ct,cf=custody_tests(); rm,rt,ra,rs=recovery_tests(); ta,tr,tp,ts=textrel_tests(); parity=tracked_parity_test()
    print("patch075-corrective-regression-smoke: ok "
          f"normalizer_file_identity={nf} normalizer_parent_identity={np} "
          f"custody_post_link={cl} custody_post_unlink={ct} custody_parent_fsync={cf} "
          f"recovery_tar_mode={rm} recovery_tree_derived={rt} recovery_ancestor={ra} recovery_success={rs} "
          f"textrel_aggregate_mutations={ta} textrel_authority_shape_rejections={tr} textrel_path_value_safe={tp} textrel_schema_consumed={ts} dynamic_parity_tracked={parity}")
    return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except (Error,OSError,subprocess.TimeoutExpired) as exc:
        print(f"patch075-corrective-regression-smoke: error: {exc}",file=sys.stderr); raise SystemExit(1)
