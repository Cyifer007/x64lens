#!/usr/bin/env python3
"""Regress confirmed Patch 074 correction and authority findings."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import stat
import subprocess
import sys
import tempfile
from types import ModuleType

ROOT=Path(__file__).resolve().parents[1]
class Error(RuntimeError): pass
def require(c:bool,m:str)->None:
    if not c: raise Error(m)
def load(name:str,path:Path)->ModuleType:
    spec=importlib.util.spec_from_file_location(name,path); require(spec is not None and spec.loader is not None,f'load {path}')
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
def run(*args:str,cwd:Path|None=None)->subprocess.CompletedProcess[str]:
    return subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
def new_repo(base:Path,name:str)->tuple[Path,Path]:
    repo=base/name; repo.mkdir(); require(run('git','init','-q',str(repo)).returncode==0,'git init')
    tracked=repo/'tracked.sh'; tracked.write_text('#!/bin/sh\nexit 0\n'); tracked.chmod(0o755)
    require(run('git','-C',str(repo),'add','tracked.sh').returncode==0,'git add'); tracked.chmod(0o644); repo.chmod(0o700)
    return repo,tracked

def main()->int:
    norm=load('p075_norm',ROOT/'tools/normalize-tracked-permissions.py')
    parity=load('p075_parity',ROOT/'tools/sprint12-role-property-environment-parity-smoke.py')
    closeout=load('p075_closeout',ROOT/'tools/sprint12-closeout-smoke.py')
    custody=load('p075_custody',ROOT/'tools/verify-delivery-custody.py')
    with tempfile.TemporaryDirectory(prefix='x64lens-p075-corrective-') as td:
        base=Path(td)
        # Hard-link aliases are rejected before chmod.
        repo,tracked=new_repo(base,'hardlink'); alias=repo/'ignored.bin'; os.link(tracked,alias)
        before=stat.S_IMODE(alias.stat().st_mode)
        try: norm.normalize(repo); raise Error('normalizer accepted untracked hardlink')
        except norm.PermissionErrorContract: pass
        require(stat.S_IMODE(alias.stat().st_mode)==before,'hardlink alias mutated')

        # Late verification failure rolls back every completed mode change.
        repo2,tracked2=new_repo(base,'rollback'); before_modes=(stat.S_IMODE(repo2.stat().st_mode),stat.S_IMODE(tracked2.stat().st_mode))
        real=norm.os.fchmod; fired=False; tracked_inode=tracked2.stat().st_ino
        def sabotage(fd,mode):
            nonlocal fired
            real(fd,mode)
            if not fired and os.fstat(fd).st_ino==tracked_inode and mode==0o755:
                fired=True; real(fd,0o644)
        norm.os.fchmod=sabotage
        try:
            try: norm.normalize(repo2); raise Error('late verification sabotage accepted')
            except norm.PermissionErrorContract: pass
        finally: norm.os.fchmod=real
        require(fired and (stat.S_IMODE(repo2.stat().st_mode),stat.S_IMODE(tracked2.stat().st_mode))==before_modes,'normalizer rollback incomplete')

        # Exactly five alternate mount spellings are rejected.
        mount_root=base/'mounts'; mount_root.mkdir(); inputs=mount_root/'inputs'; held=mount_root/'held'; output=mount_root/'output'; native=mount_root/'native'
        for p in (inputs,held,output,native): p.mkdir()
        baseline=parity.build_container_command(docker='docker',image='image',inputs=inputs,heldout=held,container_write_root=output)
        variants=[['--mount',f'type=bind,source={mount_root},target=/work,readonly'],[f'--mount=type=bind,source={mount_root},target=/work,readonly'],['--volume',f'{mount_root}:/work:ro'],[f'--volume={mount_root}:/work:ro'],[f'-v{mount_root}:/work:ro']]
        for extra in variants:
            cmd=list(baseline); i=cmd.index('image'); cmd[i:i]=extra
            try: parity.validate_container_mount_policy(cmd,native_result=native,inputs=inputs,heldout=held,container_write_root=output); raise Error(f'alternate mount accepted: {extra[0]}')
            except parity.ParityError: pass

        # Duplicate JSON keys and Boolean-as-integer values are rejected.
        original=closeout.CLOSEOUT; raw=original.read_text()
        dup=base/'dup.json'; dup.write_text(raw.replace('{\n','{\n  "status": "closed",\n',1)); closeout.CLOSEOUT=dup
        require(closeout.main()!=0,'duplicate JSON key accepted')
        value=json.loads(raw); value['diagnostic_evidence_boundary']['positive_coordinate_anchors']=False
        wrong=base/'bool.json'; wrong.write_text(json.dumps(value)); closeout.CLOSEOUT=wrong
        require(closeout.main()!=0,'Boolean accepted as integer zero'); closeout.CLOSEOUT=original

        # Root replacement after scanning is rejected and no manifest is published.
        parent=base/'root-race'; parent.mkdir(); tree=parent/'delivery'; tree.mkdir(); (tree/'payload').write_text('x')
        moved=parent/'owned-moved'; foreign=None
        def replace_root(_requested):
            nonlocal foreign
            os.rename(tree,moved); tree.mkdir(); foreign=tree
        custody._TEST_AFTER_TREE_SCAN_HOOK=replace_root
        try:
            try: custody.create(tree,tree/'manifest.json','label'); raise Error('replacement root accepted')
            except (custody.CustodyError,OSError): pass
        finally: custody._TEST_AFTER_TREE_SCAN_HOOK=None
        require(foreign is not None and not (foreign/'manifest.json').exists(),'manifest published through foreign root')

        # Rejected scans close all opened descriptors.
        leak=base/'fd-clean'; leak.mkdir()
        for i in range(20): (leak/f'{i:02d}').write_text('x')
        os.symlink('00',leak/'zz-link')
        before_fd=len(os.listdir('/proc/self/fd'))
        try: custody.create(leak,leak/'manifest.json','label'); raise Error('symlink accepted')
        except (custody.CustodyError,OSError): pass
        after_fd=len(os.listdir('/proc/self/fd')); require(after_fd==before_fd,f'FD leak: {before_fd}->{after_fd}')

        # Boundary: 511 payloads plus manifest succeeds; 512 fails without residue.
        cap511=base/'cap511'; cap511.mkdir()
        for i in range(511): (cap511/f'f{i:03d}').write_bytes(b'x')
        custody.create(cap511,cap511/'manifest.json','cap511'); custody.verify(cap511,cap511/'manifest.json')
        cap512=base/'cap512'; cap512.mkdir()
        for i in range(512): (cap512/f'f{i:03d}').write_bytes(b'x')
        try: custody.create(cap512,cap512/'manifest.json','cap512'); raise Error('512 payloads accepted')
        except custody.CustodyError: pass
        require(not (cap512/'manifest.json').exists(),'512-payload rejection left manifest residue')

        # FD capacity preflight accounts for the complete bounded transaction.
        soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
        low=min(128,hard)
        resource.setrlimit(resource.RLIMIT_NOFILE,(low,hard))
        try:
            try: custody.check_fd_capacity(cap511); raise Error('insufficient FD limit accepted')
            except custody.CustodyError: pass
        finally: resource.setrlimit(resource.RLIMIT_NOFILE,(soft,hard))

    print('patch074-corrective-regression-smoke: ok normalize_hardlink=1 normalize_rollback=1 alternate_mounts=5 duplicate_json=1 bool_int=1 custody_root_retained=1 custody_fd_cleanup=1 custody_capacity_511=1 custody_capacity_512=1 custody_fd_preflight=1')
    return 0
if __name__=='__main__':
    try: raise SystemExit(main())
    except (Error,OSError,subprocess.SubprocessError) as exc:
        print(f'patch074-corrective-regression-smoke: error: {exc}',file=sys.stderr); raise SystemExit(1)
