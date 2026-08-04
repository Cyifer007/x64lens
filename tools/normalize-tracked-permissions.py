#!/usr/bin/env python3
"""Normalize only Git-tracked modes through identity-bound transactions.

Git index modes are the authority. Every parent directory and tracked object is
preflighted without following links. Objects that require mutation are reopened
through authenticated directory descriptors, mutated with ``fchmod``, retained
through final verification, and rolled back through those same descriptors on
any failure. A post-preflight pathname or parent replacement is therefore never
chmod'd as though it were the tracked object.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from typing import NamedTuple

O_CLOEXEC=getattr(os,"O_CLOEXEC",0); O_NOFOLLOW=getattr(os,"O_NOFOLLOW",0); O_DIRECTORY=getattr(os,"O_DIRECTORY",0)
class PermissionErrorContract(RuntimeError): pass
class Identity(NamedTuple):
    device:int; inode:int; file_type:int; uid:int; gid:int; nlink:int
@dataclass(frozen=True)
class IndexRecord:
    path:str; expected_mode:int; file_type:int
@dataclass
class Mutation:
    path:str; fd:int; original_mode:int; expected_identity:Identity

def require(c:bool,m:str)->None:
    if not c: raise PermissionErrorContract(m)
def identity(st:os.stat_result)->Identity:
    return Identity(st.st_dev,st.st_ino,stat.S_IFMT(st.st_mode),st.st_uid,st.st_gid,st.st_nlink)
def run_git(repo:Path,*args:str)->bytes:
    cp=subprocess.run(["git","-C",str(repo),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    require(cp.returncode==0,f"git {' '.join(args)} failed: {cp.stderr.decode(errors='replace').strip()}"); return cp.stdout
def safe_path(raw:str)->str:
    p=PurePosixPath(raw); require(raw and not p.is_absolute() and p.as_posix()==raw and "\\" not in raw and all(x not in {"",".",".."} for x in p.parts),f"unsafe tracked path: {raw!r}"); return raw
def index_records(repo:Path)->list[IndexRecord]:
    out=[]
    for item in run_git(repo,"ls-files","-s","-z").split(b"\0"):
        if not item: continue
        header,path_raw=item.split(b"\t",1); fields=header.split(); require(len(fields)==3,"unexpected git index record")
        mode=fields[0].decode("ascii"); path=safe_path(os.fsdecode(path_raw))
        if mode=="100644": out.append(IndexRecord(path,0o644,stat.S_IFREG))
        elif mode=="100755": out.append(IndexRecord(path,0o755,stat.S_IFREG))
        elif mode=="120000": out.append(IndexRecord(path,0,stat.S_IFLNK))
        else: raise PermissionErrorContract(f"unsupported tracked index mode {mode}: {path}")
    require(out,"repository has no tracked paths"); return out

def parent_path(path:str)->str:
    parts=PurePosixPath(path).parts
    return "/".join(parts[:-1])
def open_directory(root_fd:int,relative:str,expected:dict[str,Identity])->int:
    fd=os.dup(root_fd); current=""
    try:
        require(identity(os.fstat(fd))==expected[""],"repository root identity changed")
        if not relative: return fd
        for component in PurePosixPath(relative).parts:
            nxt=component if not current else current+"/"+component
            child=os.open(component,os.O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW,dir_fd=fd)
            observed=identity(os.fstat(child)); require(observed==expected.get(nxt),f"tracked parent identity changed: {nxt}")
            os.close(fd); fd=child; current=nxt
        return fd
    except BaseException:
        os.close(fd); raise

def open_regular(root_fd:int,path:str,expected_dirs:dict[str,Identity],expected_identity:Identity)->int:
    parent=open_directory(root_fd,parent_path(path),expected_dirs)
    try:
        name=PurePosixPath(path).name
        fd=os.open(name,os.O_RDONLY|O_CLOEXEC|O_NOFOLLOW,dir_fd=parent)
        observed=identity(os.fstat(fd)); require(observed==expected_identity,f"tracked file identity changed: {path}")
        return fd
    finally: os.close(parent)
def lstat_bound(root_fd:int,path:str,expected_dirs:dict[str,Identity])->os.stat_result:
    parent=open_directory(root_fd,parent_path(path),expected_dirs)
    try: return os.stat(PurePosixPath(path).name,dir_fd=parent,follow_symlinks=False)
    finally: os.close(parent)

def normalize(repo:Path)->tuple[int,int]:
    repo=Path(os.path.abspath(repo)); require(repo.is_dir() and not repo.is_symlink(),f"repository root is not a real directory: {repo}")
    records=index_records(repo); owner=os.geteuid()
    root_fd=os.open(repo,os.O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW)
    mutations:list[Mutation]=[]; open_mutation_fds:set[int]=set()
    try:
        root_st=os.fstat(root_fd); root_id=identity(root_st); require(root_id.file_type==stat.S_IFDIR,"repository root changed type")
        require(root_id.uid==owner or owner==0,"repository root is not owned by current user")
        expected_dirs:{str:Identity}={"":root_id}
        directory_modes:{str:int}={"":stat.S_IMODE(root_st.st_mode)}
        required_dirs=set()
        for record in records:
            parent=parent_path(record.path)
            while parent:
                required_dirs.add(parent); parent=parent_path(parent)
        for directory in sorted(required_dirs,key=lambda x:(x.count("/"),os.fsencode(x))):
            parent=open_directory(root_fd,parent_path(directory),expected_dirs)
            try:
                fd=os.open(PurePosixPath(directory).name,os.O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW,dir_fd=parent)
                try:
                    st=os.fstat(fd); ident=identity(st)
                    require(ident.file_type==stat.S_IFDIR,f"tracked parent changed type: {directory}")
                    require(ident.uid==owner or owner==0,f"tracked parent is not owned by current user: {directory}")
                    expected_dirs[directory]=ident; directory_modes[directory]=stat.S_IMODE(st.st_mode)
                finally: os.close(fd)
            finally: os.close(parent)

        expected_files:dict[str,Identity]={}; file_modes:dict[str,int]={}; tracked_inodes:dict[tuple[int,int],str]={}
        for record in records:
            st=lstat_bound(root_fd,record.path,expected_dirs); ident=identity(st)
            require(ident.file_type==record.file_type,f"tracked path type disagrees with Git index: {record.path}")
            expected_files[record.path]=ident
            if record.file_type==stat.S_IFREG:
                require(ident.uid==owner or owner==0,f"tracked file is not owned by current user: {record.path}")
                require(ident.nlink==1,f"tracked file has hard-link aliases: {record.path}")
                key=(ident.device,ident.inode); require(key not in tracked_inodes,f"tracked files share one inode: {tracked_inodes.get(key)} and {record.path}")
                tracked_inodes[key]=record.path; file_modes[record.path]=stat.S_IMODE(st.st_mode)

        changed_files=sum(record.file_type==stat.S_IFREG and file_modes[record.path]!=record.expected_mode for record in records)
        changed_dirs=sum(mode!=0o755 for mode in directory_modes.values())
        try:
            for directory in sorted(directory_modes,key=lambda x:(x.count("/"),os.fsencode(x))):
                original=directory_modes[directory]
                if original==0o755: continue
                fd=open_directory(root_fd,directory,expected_dirs); open_mutation_fds.add(fd)
                os.fchmod(fd,0o755); mutations.append(Mutation(directory or ".",fd,original,expected_dirs[directory]))
            for record in sorted(records,key=lambda r:os.fsencode(r.path)):
                if record.file_type!=stat.S_IFREG or file_modes[record.path]==record.expected_mode: continue
                fd=open_regular(root_fd,record.path,expected_dirs,expected_files[record.path]); open_mutation_fds.add(fd)
                os.fchmod(fd,record.expected_mode); mutations.append(Mutation(record.path,fd,file_modes[record.path],expected_files[record.path]))

            # Verify caller-visible bindings only after every mutation. Replaced
            # objects fail the transaction; rollback still targets retained FDs.
            final_inodes:dict[tuple[int,int],str]={}
            for record in records:
                st=lstat_bound(root_fd,record.path,expected_dirs); ident=identity(st)
                require(ident==expected_files[record.path],f"tracked path identity changed after normalization: {record.path}")
                if record.file_type==stat.S_IFREG:
                    require(ident.nlink==1,f"tracked file gained a hard-link alias: {record.path}")
                    key=(ident.device,ident.inode); require(key not in final_inodes,f"tracked files share one inode after normalization: {final_inodes.get(key)} and {record.path}")
                    final_inodes[key]=record.path
                    require(stat.S_IMODE(st.st_mode)==record.expected_mode,f"tracked file mode normalization failed: {record.path}")
            for directory,ident_expected in expected_dirs.items():
                fd=open_directory(root_fd,directory,expected_dirs)
                try:
                    st=os.fstat(fd); require(identity(st)==ident_expected,f"tracked directory identity changed after normalization: {directory or '.'}")
                    require(stat.S_IMODE(st.st_mode)==0o755,f"tracked directory mode normalization failed: {directory or '.'}")
                finally: os.close(fd)
        except BaseException as exc:
            errors=[]
            for mutation in reversed(mutations):
                try:
                    require(identity(os.fstat(mutation.fd))==mutation.expected_identity,f"retained mutation descriptor changed identity: {mutation.path}")
                    os.fchmod(mutation.fd,mutation.original_mode)
                    if stat.S_IMODE(os.fstat(mutation.fd).st_mode)!=mutation.original_mode: errors.append(f"mode verification failed: {mutation.path}")
                except BaseException as rollback_exc: errors.append(f"{mutation.path}: {rollback_exc}")
            suffix=f"; rollback failures: {errors}" if errors else ""
            raise PermissionErrorContract(f"permission normalization failed: {exc}{suffix}") from exc
        return changed_files,changed_dirs
    finally:
        for fd in list(open_mutation_fds):
            try: os.close(fd)
            except OSError: pass
        os.close(root_fd)

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--repo",type=Path,default=Path.cwd()); args=parser.parse_args()
    files,dirs=normalize(args.repo); print(f"normalize-tracked-permissions: ok files_changed={files} directories_changed={dirs} untracked_touched=0 descriptor_bound=1")
    return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except (PermissionErrorContract,OSError,ValueError) as exc:
        print(f"normalize-tracked-permissions: error: {exc}",file=sys.stderr); raise SystemExit(1)
