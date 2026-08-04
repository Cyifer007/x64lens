#!/usr/bin/env python3
"""Recover an exact candidate source tree with archive and Git-tree custody.

The helper rejects unsafe, duplicate, linked, special, mode-mismatched, or
undeclared TAR members; requires every ancestor directory to be declared before
use; writes without following links; verifies exact bytes, Git blob IDs, modes,
and final membership; and derives the Git root tree from the recovered manifest
instead of trusting a printable ``candidate_tree`` label. The destination's
parent must already exist, so recovery never creates undeclared ancestors.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile
from typing import Any
class RecoveryError(RuntimeError): pass
def require(c:bool,m:str)->None:
    if not c: raise RecoveryError(m)
def strict(pairs:list[tuple[str,Any]])->dict[str,Any]:
    out={}
    for k,v in pairs: require(k not in out,f"duplicate JSON key: {k}"); out[k]=v
    return out
def safe(raw:str)->str:
    p=PurePosixPath(raw); require(raw and not p.is_absolute() and p.as_posix()==raw and "\\" not in raw and all(x not in {"",".",".."} for x in p.parts),f"unsafe member path: {raw!r}"); return raw
def parent(raw:str)->str:
    parts=PurePosixPath(raw).parts; return "/".join(parts[:-1])
def digest(path:Path)->tuple[str,int]:
    h=hashlib.sha256(); total=0
    with path.open("rb") as f:
        while True:
            b=f.read(1024*1024)
            if not b: break
            h.update(b); total+=len(b)
    return h.hexdigest(),total
def git_object(kind:bytes,payload:bytes)->str:
    return hashlib.sha1(kind+b" "+str(len(payload)).encode("ascii")+b"\0"+payload).hexdigest()
def load_manifest(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(),object_pairs_hook=strict)
    require(isinstance(value,dict) and set(value)=={"schema_id","candidate_tree","directories","files"},"source manifest shape changed")
    require(value["schema_id"]=="x64lens-candidate-source-tree-v1","wrong source manifest schema")
    require(isinstance(value["candidate_tree"],str) and len(value["candidate_tree"])==40 and all(c in "0123456789abcdef" for c in value["candidate_tree"]),"invalid candidate tree")
    require(isinstance(value["directories"],list) and isinstance(value["files"],list),"invalid manifest arrays")
    return value
def derive_tree(files:dict[str,dict[str,Any]],directories:set[str])->str:
    all_dirs={"",*directories}; children:dict[str,list[tuple[str,bool,str,str]]]={d:[] for d in all_dirs}
    for directory in directories:
        par=parent(directory); require(par in all_dirs,f"undeclared directory parent: {directory}")
    for path,item in files.items():
        par=parent(path); require(par in all_dirs,f"undeclared file parent: {path}")
        children[par].append((PurePosixPath(path).name,False,item["git_mode"],item["git_oid"]))
    tree_ids:dict[str,str]={}
    for directory in sorted(directories,key=lambda x:(-x.count("/"),os.fsencode(x))):
        par=parent(directory); name=PurePosixPath(directory).name
        payload_entries=children[directory]
        require(payload_entries,f"manifest contains an empty non-Git directory: {directory}")
        payload=b"".join(
            mode.encode("ascii")+b" "+name_b+b"\0"+bytes.fromhex(oid)
            for name_b,is_dir,mode,oid in sorted(
                ((os.fsencode(n)+(b"/" if d else b""),d,m,o) for n,d,m,o in payload_entries),
                key=lambda item:item[0],
            )
            for name_b in [name_b[:-1] if is_dir else name_b]
        )
        oid=git_object(b"tree",payload); tree_ids[directory]=oid
        children[par].append((name,True,"40000",oid))
    root_entries=children[""]; require(root_entries,"source manifest has no root entries")
    payload=b"".join(
        mode.encode("ascii")+b" "+name_b+b"\0"+bytes.fromhex(oid)
        for name_b,is_dir,mode,oid in sorted(
            ((os.fsencode(n)+(b"/" if d else b""),d,m,o) for n,d,m,o in root_entries),key=lambda item:item[0]
        )
        for name_b in [name_b[:-1] if is_dir else name_b]
    )
    return git_object(b"tree",payload)
def final_membership(destination:Path)->tuple[set[str],set[str]]:
    dirs=set(); files=set()
    for root,dirnames,filenames in os.walk(destination,topdown=True,followlinks=False):
        root_path=Path(root); rel_root=root_path.relative_to(destination)
        for name in dirnames:
            path=root_path/name; require(not path.is_symlink() and path.is_dir(),f"unsafe recovered directory: {path}"); dirs.add((rel_root/name).as_posix())
        for name in filenames:
            path=root_path/name; st=path.lstat(); require(stat.S_ISREG(st.st_mode) and st.st_nlink==1,f"unsafe recovered file: {path}"); files.add((rel_root/name).as_posix())
    return dirs,files
def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--archive",type=Path,required=True); ap.add_argument("--manifest",type=Path,required=True); ap.add_argument("--destination",type=Path,required=True); ns=ap.parse_args()
    m=load_manifest(ns.manifest); dir_modes={}; ordered_dirs=[]
    for item in m["directories"]:
        require(isinstance(item,dict) and set(item)=={"path","mode"},"invalid directory record"); path=safe(item["path"]); require(item["mode"]=="0755",f"noncanonical directory mode: {path}"); require(path not in dir_modes,f"duplicate directory: {path}"); dir_modes[path]=0o755; ordered_dirs.append(path)
    files={}
    for item in m["files"]:
        require(isinstance(item,dict) and set(item)=={"path","type","git_oid","git_mode","mode","sha256","size_bytes"},"invalid file record"); path=safe(item["path"]); require(path not in files and path not in dir_modes,f"duplicate source path: {path}")
        require(item["type"]=="blob",f"invalid source object type: {path}"); require(isinstance(item["git_oid"],str) and len(item["git_oid"])==40 and all(c in "0123456789abcdef" for c in item["git_oid"]),f"invalid Git object id: {path}")
        require(item["git_mode"] in {"100644","100755"} and item["mode"] in {"0644","0755"},f"invalid source mode: {path}"); require((item["git_mode"]=="100755")== (item["mode"]=="0755"),f"Git/recovery mode mismatch: {path}")
        require(isinstance(item["sha256"],str) and len(item["sha256"])==64 and all(c in "0123456789abcdef" for c in item["sha256"]),f"invalid digest: {path}"); require(type(item["size_bytes"]) is int and item["size_bytes"]>=0,f"invalid size: {path}"); files[path]=item
    require(ordered_dirs==sorted(ordered_dirs) and list(files)==sorted(files),"manifest paths must be sorted")
    for directory in dir_modes: require(parent(directory) in {"",*dir_modes},f"undeclared directory parent: {directory}")
    for path in files: require(parent(path) in {"",*dir_modes},f"undeclared file parent: {path}")
    derived_tree=derive_tree(files,set(dir_modes)); require(derived_tree==m["candidate_tree"],f"manifest candidate tree disagrees: derived={derived_tree} declared={m['candidate_tree']}")
    destination=Path(os.path.abspath(ns.destination)); require(not destination.exists(),"destination already exists"); require(destination.parent.is_dir() and not destination.parent.is_symlink(),"destination parent must already be a real directory")
    destination.mkdir(mode=0o755,parents=False); os.chmod(destination,0o755)
    seen_dirs=set(); seen_files=set()
    try:
        with tarfile.open(ns.archive,"r:*") as tf:
            for member in tf:
                raw=member.name[:-1] if member.name.endswith("/") else member.name; name=safe(raw)
                require(not member.issym() and not member.islnk() and not member.isdev() and not member.isfifo(),"linked or special source member rejected")
                target=destination/name
                if member.isdir():
                    require(name in dir_modes and name not in seen_dirs,f"undeclared/duplicate directory: {name}"); require(member.mode & 0o7777==dir_modes[name],f"TAR directory mode disagrees: {name}"); require(parent(name) in seen_dirs or parent(name)=="",f"directory parent not declared first: {name}")
                    target.mkdir(parents=False,exist_ok=False,mode=0o755); os.chmod(target,0o755); seen_dirs.add(name)
                elif member.isfile():
                    require(name in files and name not in seen_files,f"undeclared/duplicate file: {name}"); expected_mode=int(files[name]["mode"],8); require(member.mode & 0o7777==expected_mode,f"TAR file mode disagrees: {name}"); require(member.size==files[name]["size_bytes"],f"TAR file size disagrees: {name}"); require(parent(name) in seen_dirs or parent(name)=="",f"file parent not declared first: {name}")
                    src=tf.extractfile(member); require(src is not None,f"cannot read member: {name}"); fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o600)
                    try:
                        with os.fdopen(fd,"wb",closefd=False) as out: shutil.copyfileobj(src,out,1024*1024); out.flush(); os.fsync(out.fileno())
                        os.fchmod(fd,expected_mode)
                    finally: os.close(fd); src.close()
                    observed,size=digest(target); require(observed==files[name]["sha256"] and size==files[name]["size_bytes"],f"file bytes disagree: {name}")
                    raw_bytes=target.read_bytes(); require(git_object(b"blob",raw_bytes)==files[name]["git_oid"],f"Git object id disagrees: {name}"); seen_files.add(name)
                else: raise RecoveryError(f"unsupported TAR member: {name}")
        require(seen_dirs==set(dir_modes),f"directory membership mismatch: missing={sorted(set(dir_modes)-seen_dirs)}"); require(seen_files==set(files),f"file membership mismatch: missing={sorted(set(files)-seen_files)}")
        observed_dirs,observed_files=final_membership(destination); require(observed_dirs==set(dir_modes),"final directory membership changed"); require(observed_files==set(files),"final file membership changed")
        for name in sorted(dir_modes,key=lambda x:(-x.count("/"),x)): require(stat.S_IMODE((destination/name).stat().st_mode)==0o755,f"directory mode mismatch: {name}")
        for name,item in files.items(): require(stat.S_IMODE((destination/name).stat().st_mode)==int(item["mode"],8),f"file mode mismatch: {name}")
        require(derive_tree(files,set(dir_modes))==m["candidate_tree"],"final candidate tree derivation changed")
    except BaseException:
        shutil.rmtree(destination,ignore_errors=True); raise
    print(f"recover-candidate-source: ok tree={derived_tree} derived_tree=1 directories={len(dir_modes)} files={len(files)} destination={destination}"); return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except (RecoveryError,OSError,tarfile.TarError,json.JSONDecodeError,UnicodeDecodeError) as exc:
        print(f"recover-candidate-source: error: {exc}",file=sys.stderr); raise SystemExit(1)
