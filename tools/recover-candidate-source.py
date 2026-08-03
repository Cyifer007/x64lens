#!/usr/bin/env python3
"""Recover an exact candidate source tree with manifest-authoritative modes.

The helper rejects unsafe, duplicate, linked, or special tar members; requires
exact file and directory membership; writes files without following links; and
sets canonical 0644/0755 file modes plus 0755 directory modes independently of
the caller's umask. It is a recovery path, not the preferred Git patch path.
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
    for k,v in pairs:
        require(k not in out,f'duplicate JSON key: {k}'); out[k]=v
    return out
def safe(raw:str)->str:
    p=PurePosixPath(raw); require(raw and not p.is_absolute() and p.as_posix()==raw and '\\' not in raw and all(x not in {'','.','..'} for x in p.parts),f'unsafe member path: {raw!r}'); return raw
def digest(path:Path)->tuple[str,int]:
    h=hashlib.sha256(); total=0
    with path.open('rb') as f:
        while True:
            b=f.read(1024*1024)
            if not b: break
            h.update(b); total+=len(b)
    return h.hexdigest(),total
def load_manifest(path:Path)->dict[str,Any]:
    v=json.loads(path.read_text(),object_pairs_hook=strict); require(isinstance(v,dict),'manifest must be object')
    require(v.get('schema_id')=='x64lens-candidate-source-tree-v1','wrong source manifest schema')
    require(isinstance(v.get('candidate_tree'),str) and len(v['candidate_tree'])==40,'invalid candidate tree')
    require(isinstance(v.get('directories'),list) and isinstance(v.get('files'),list),'invalid manifest arrays')
    return v
def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--archive',type=Path,required=True); ap.add_argument('--manifest',type=Path,required=True); ap.add_argument('--destination',type=Path,required=True); ns=ap.parse_args()
    m=load_manifest(ns.manifest)
    dirs=[]; dir_modes={}
    for item in m['directories']:
        require(isinstance(item,dict) and set(item)=={'path','mode'},'invalid directory record'); p=safe(item['path']); require(item['mode']=='0755',f'noncanonical directory mode: {p}'); require(p not in dir_modes,f'duplicate directory: {p}'); dir_modes[p]=0o755; dirs.append(p)
    files={}
    for item in m['files']:
        require(isinstance(item,dict) and set(item)=={'path','type','git_oid','git_mode','mode','sha256','size_bytes'},'invalid file record'); p=safe(item['path']); require(p not in files and p not in dir_modes,f'duplicate source path: {p}')
        require(item['type']=='blob',f'invalid source object type: {p}'); require(isinstance(item['git_oid'],str) and len(item['git_oid'])==40 and all(c in '0123456789abcdef' for c in item['git_oid']),f'invalid Git object id: {p}'); require(item['git_mode'] in {'100644','100755'} and item['mode'] in {'0644','0755'},f'invalid source mode: {p}'); require((item['git_mode']=='100755')==(item['mode']=='0755'),f'Git/recovery mode mismatch: {p}')
        require(isinstance(item['sha256'],str) and len(item['sha256'])==64 and all(c in '0123456789abcdef' for c in item['sha256']),f'invalid digest: {p}'); require(type(item['size_bytes']) is int and item['size_bytes']>=0,f'invalid size: {p}'); files[p]=item
    require(dirs==sorted(dirs) and list(files)==sorted(files),'manifest paths must be sorted')
    destination=Path(os.path.abspath(ns.destination)); require(not destination.exists(),'destination already exists')
    destination.mkdir(mode=0o755,parents=True); os.chmod(destination,0o755)
    seen_dirs=set(); seen_files=set()
    try:
        with tarfile.open(ns.archive,'r:*') as tf:
            for member in tf:
                name=safe(member.name.rstrip('/'))
                require(not member.issym() and not member.islnk() and not member.isdev() and not member.isfifo(),'linked or special source member rejected')
                target=destination/name
                if member.isdir():
                    require(name in dir_modes and name not in seen_dirs,f'undeclared/duplicate directory: {name}'); target.mkdir(parents=True,exist_ok=False); os.chmod(target,0o755); seen_dirs.add(name)
                elif member.isfile():
                    require(name in files and name not in seen_files,f'undeclared/duplicate file: {name}'); require(target.parent.exists(),f'file parent not declared first: {name}')
                    src=tf.extractfile(member); require(src is not None,f'cannot read member: {name}')
                    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
                    try:
                        with os.fdopen(fd,'wb',closefd=False) as out: shutil.copyfileobj(src,out,1024*1024); out.flush(); os.fsync(out.fileno())
                        os.fchmod(fd,int(files[name]['mode'],8))
                    finally: os.close(fd); src.close()
                    observed,size=digest(target); require(observed==files[name]['sha256'] and size==files[name]['size_bytes'],f'file bytes disagree: {name}')
                    raw=target.read_bytes(); git_oid=hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()
                    require(git_oid==files[name]['git_oid'],f'Git object id disagrees: {name}'); seen_files.add(name)
                else: raise RecoveryError(f'unsupported tar member: {name}')
        require(seen_dirs==set(dir_modes),f'directory membership mismatch: missing={sorted(set(dir_modes)-seen_dirs)}')
        require(seen_files==set(files),f'file membership mismatch: missing={sorted(set(files)-seen_files)}')
        for name in sorted(dir_modes,key=lambda x:(-x.count('/'),x)): require(stat.S_IMODE((destination/name).stat().st_mode)==0o755,f'directory mode mismatch: {name}')
        for name,item in files.items(): require(stat.S_IMODE((destination/name).stat().st_mode)==int(item['mode'],8),f'file mode mismatch: {name}')
    except BaseException:
        shutil.rmtree(destination,ignore_errors=True); raise
    print(f"recover-candidate-source: ok tree={m['candidate_tree']} directories={len(dir_modes)} files={len(files)} destination={destination}")
    return 0
if __name__=='__main__':
    try: raise SystemExit(main())
    except (RecoveryError,OSError,tarfile.TarError,json.JSONDecodeError,UnicodeDecodeError) as exc:
        print(f'recover-candidate-source: error: {exc}',file=sys.stderr); raise SystemExit(1)
