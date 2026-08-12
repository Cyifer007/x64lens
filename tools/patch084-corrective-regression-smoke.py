#!/usr/bin/env python3
"""Discriminate every P084 finding promoted into the P085 correction."""
from __future__ import annotations
import errno
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
GITLESS=ROOT/'tools/gitless-source-manifest.py'
RECOVERY=ROOT/'tools/recover-candidate-source.py'
ABI=ROOT/'tools/sprint13-abi-role-query-smoke.py'
NATURAL=ROOT/'tools/sprint13-natural-coordinate-campaign.py'
LIFECYCLE=ROOT/'tools/sprint13-lifecycle-denominator-smoke.py'
ATTRIBUTION=ROOT/'tools/sprint13-natural-terminal-attribution-smoke.py'
REPLAY=ROOT/'tools/sprint13-natural-frozen-replay-smoke.py'

class RegressionError(RuntimeError): pass
def require(ok:bool,msg:str)->None:
    if not ok: raise RegressionError(msg)
def run(argv:list[str],*,cwd:Path|None=None,expected:int|None=0,env:dict[str,str]|None=None)->subprocess.CompletedProcess[bytes]:
    cp=subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=180)
    if expected is not None: require(cp.returncode==expected,f'command failed ({cp.returncode}, expected {expected}): {argv}\n{cp.stderr[-3000:]!r}')
    return cp
def load_module(name:str,path:Path)->Any:
    spec=importlib.util.spec_from_file_location(name,path); require(spec is not None and spec.loader is not None,f'cannot load {path}')
    value=importlib.util.module_from_spec(spec); sys.modules[name]=value; spec.loader.exec_module(value); return value
def git_blob(payload:bytes)->str:return hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()
def git_tree(mode:str,name:str,oid:str)->str:
    body=mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(oid); return hashlib.sha1(b'tree '+str(len(body)).encode()+b'\0'+body).hexdigest()

def init_source_repo(path:Path,files:dict[str,tuple[bytes,int]])->str:
    path.mkdir(); run(['git','init','-q','-b','main'],cwd=path); run(['git','config','user.name','regression'],cwd=path); run(['git','config','user.email','regression@example.invalid'],cwd=path)
    for raw,(payload,mode) in files.items():
        target=path/raw; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(payload); target.chmod(mode)
    run(['git','add','.'],cwd=path); run(['git','commit','-qm','source'],cwd=path)
    return run(['git','write-tree'],cwd=path).stdout.decode().strip()

def lifecycle_probe()->tuple[int,int,int]:
    module=load_module('p085_lifecycle',LIFECYCLE); authority=module.load(ROOT/'benchmarks/task-definitions/sprint13-lifecycle-denominator-authority-v1.json')
    module.validate(authority)
    require([item['patch'] for item in authority['successor_deltas']]==[80,81,82,83,84],'P084 successor delta missing')
    rejected=0
    for key in sorted(authority['denominator_floors']):
        changed=json.loads(json.dumps(authority)); changed['denominator_floors'][key]-=1
        try: module.validate(changed)
        except module.LifecycleError: rejected+=1
        else: raise RegressionError(f'lifecycle floor mutation accepted: {key}')
    require(rejected==24,'all 24 lifecycle floors were not enforced')
    require(module.mutation_rejections(authority)==13,'lifecycle mutation suite changed')
    return 24,1,13

def abi_disjoint_probe()->int:
    module=load_module('p085_abi_disjoint',ABI); authority=module.load(ROOT/'benchmarks/task-definitions/sprint13-abi-role-query-v1.json')
    module.validate_authority(authority)
    development=next(item for item in authority['queries'] if item['split']=='development')
    confirmation=next(index for index,item in enumerate(authority['queries']) if item['split']=='confirmation')
    changed=json.loads(json.dumps(authority)); replacement=dict(development); replacement['id']=changed['queries'][confirmation]['id']; replacement['split']='confirmation'; changed['queries'][confirmation]=replacement
    try: module.validate_authority(changed)
    except module.QueryError: return 1
    raise RegressionError('ABI development/confirmation semantic overlap was accepted')

def abi_publication_probe(tmp:Path)->int:
    module=load_module('p085_abi_publish',ABI); source=tmp/'abi-stage'; destination=tmp/'abi-result'; source.mkdir(); destination.mkdir(); (source/'owned').write_text('owned'); (destination/'foreign').write_text('foreign')
    try: module.rename_noreplace(source,destination)
    except OSError as exc: require(exc.errno==errno.EEXIST,'ABI no-replace failed with wrong error')
    else: raise RegressionError('ABI result publication replaced a raced destination')
    require((destination/'foreign').read_text()=='foreign' and source.is_dir(),'ABI no-replace did not preserve both objects')
    return 1

def manifest_and_archive(tmp:Path,payload:bytes=b'good\n')->tuple[Path,Path]:
    oid=git_blob(payload); tree=git_tree('100644','a.txt',oid)
    manifest={'schema_id':'x64lens-candidate-source-tree-v1','candidate_tree':tree,'directories':[],'files':[{'path':'a.txt','type':'blob','git_oid':oid,'git_mode':'100644','mode':'0644','sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload)}]}
    manifest_path=tmp/'manifest.json'; manifest_path.write_text(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n')
    archive=tmp/'source.tar.gz'; info=tarfile.TarInfo('a.txt'); info.size=len(payload); info.mode=0o644
    with tarfile.open(archive,'w:gz') as tar: tar.addfile(info,io.BytesIO(payload))
    return manifest_path,archive

def recovery_initial_open_probe(tmp:Path)->int:
    module=load_module('p085_recovery_open',RECOVERY); manifest,archive=manifest_and_archive(tmp); destination=tmp/'open-result'
    original=module.os.open; injected=False
    def hooked(path:Any,flags:int,*args:Any,**kwargs:Any)->int:
        nonlocal injected
        if not injected and isinstance(path,str) and path.startswith('.x64lens-recovery-stage.') and flags & module.O_DIRECTORY:
            injected=True; raise OSError(errno.EIO,'injected first-open failure')
        return original(path,flags,*args,**kwargs)
    module.os.open=hooked
    try:
        try: module.recover(archive,manifest,destination)
        except OSError as exc: require(exc.errno==errno.EIO,'first-open failure changed class')
        else: raise RegressionError('first-open recovery fault was accepted')
    finally: module.os.open=original
    require(not destination.exists() and not list(tmp.glob('.x64lens-recovery-*')),'first-open recovery left staging residue')
    return 1

def recovery_posthash_probe(tmp:Path)->int:
    module=load_module('p085_recovery_posthash',RECOVERY); manifest,archive=manifest_and_archive(tmp); destination=tmp/'posthash-result'
    original=module.hash_fd; injected=False
    def hooked(fd:int)->tuple[str,int,bytes|None]:
        nonlocal injected
        result=original(fd)
        if not injected:
            injected=True; os.fchmod(fd,0o600)
        return result
    module.hash_fd=hooked
    try:
        try: module.recover(archive,manifest,destination)
        except module.RecoveryError as exc: require('metadata changed while hashing' in str(exc),'post-hash recovery mutation produced wrong diagnostic')
        else: raise RegressionError('post-hash recovery topology mutation was accepted')
    finally: module.hash_fd=original
    require(not destination.exists() and not list(tmp.glob('.x64lens-recovery-*')),'post-hash recovery left residue')
    return 1

def gitless_topology_probe(tmp:Path)->tuple[int,int]:
    module=load_module('p085_gitless_topology',GITLESS); repo=tmp/'gitless-repo'; tree=init_source_repo(repo,{'Dockerfile':(b'FROM scratch\n',0o644),'a.txt':(b'payload\n',0o644)})
    root=tmp/'gitless-root'; manifest_path=tmp/'gitless-manifest.json'; manifest=module.create(repo,root,manifest_path,tree)
    target=root/'a.txt'; original=module.hash_stream; mode_rejected=0; link_rejected=0
    injected=False
    def mode_hook(handle:Any)->tuple[str,int,str]:
        nonlocal injected
        result=original(handle)
        if not injected and Path(os.readlink(f'/proc/self/fd/{handle.fileno()}')).name=='a.txt': injected=True; os.chmod(target,0o600)
        return result
    module.hash_stream=mode_hook
    try:
        try: module.verify(root,manifest)
        except module.SourceError: mode_rejected=1
        else: raise RegressionError('Git-less chmod drift was accepted')
    finally: module.hash_stream=original; os.chmod(target,0o644)
    injected=False; alias=root/'a.alias'
    def link_hook(handle:Any)->tuple[str,int,str]:
        nonlocal injected
        result=original(handle)
        if not injected and Path(os.readlink(f'/proc/self/fd/{handle.fileno()}')).name=='a.txt': injected=True; os.link(target,alias)
        return result
    module.hash_stream=link_hook
    try:
        try: module.verify(root,manifest)
        except module.SourceError: link_rejected=1
        else: raise RegressionError('Git-less hard-link drift was accepted')
    finally: module.hash_stream=original; alias.unlink(missing_ok=True)
    return mode_rejected,link_rejected

def natural_structural_probe(tmp:Path)->tuple[int,int]:
    natural=load_module('p085_natural_structural',NATURAL)
    targets={}; outcomes={}
    for role in natural.ROLES:
        for slot in range(4):
            tid=f'{role}-{slot}'; target={'target_id':tid,'role':role,'sha256':hashlib.sha256(tid.encode()).hexdigest()}; targets[tid]=target; outcomes[tid]={'target':target,'tools':{name:{} for name in ('x64lens',*natural.BASELINES)}}
    cells=[]
    for baseline in natural.BASELINES:
        for role in natural.ROLES:
            observations=[{'target_id':tid,'target_sha256':targets[tid]['sha256'],'status':'unavailable'} for tid in targets if targets[tid]['role']==role]
            cells.append(natural.cell_result(baseline,role,observations))
    result={'selection_freeze':{'selected_count':12,'role_counts':{role:4 for role in natural.ROLES}},'execution_count':48,'complete_execution_denominator':48,'outcomes':outcomes,'cells':cells,'cell_counts':{state:sum(cell['terminal_state']==state for cell in cells) for state in ('qualified','insufficient','unavailable','mismatch','ambiguous')},'control_count':108}
    natural.require_structural_complete(result)
    mutations=[]
    changed=json.loads(json.dumps(result)); changed['execution_count']=47; mutations.append(changed)
    changed=json.loads(json.dumps(result)); changed['cell_counts']['unavailable']=8; mutations.append(changed)
    changed=json.loads(json.dumps(result)); changed['cells'][1]['cell_id']=changed['cells'][0]['cell_id']; mutations.append(changed)
    changed=json.loads(json.dumps(result)); changed['cells'][0]['observations'][0]['target_id']='foreign'; mutations.append(changed)
    changed=json.loads(json.dumps(result)); first=next(iter(changed['outcomes'])); changed['outcomes'][first]['tools'].pop('ropr'); mutations.append(changed)
    rejected=0
    for mutation in mutations:
        try: natural.require_structural_complete(mutation)
        except natural.CampaignError: rejected+=1
        else: raise RegressionError('natural structural mutation was accepted')
    path=tmp/'natural-target'; path.write_bytes(b'ELF'); path.chmod(0o444); identity=natural.regular_identity(path,expected_mode=0o444,expected_sha256=hashlib.sha256(b'ELF').hexdigest(),require_single_link=True); os.chmod(path,0o600)
    try: natural.regular_identity(path,expected_mode=0o444,expected_sha256=identity['sha256'],require_single_link=True)
    except natural.CampaignError: target_rejected=1
    else: raise RegressionError('natural target mode mutation was accepted')
    return rejected,target_rejected

def abi_execution_probe(tmp:Path)->tuple[int,int]:
    module=load_module('p085_abi_execution',ABI); repo=tmp/'abi-source-repo'; tree=init_source_repo(repo,{'Dockerfile':(b'FROM scratch\n',0o644)})
    gitless=load_module('p085_abi_gitless',GITLESS); source_root=tmp/'abi-source'; source_manifest=tmp/'abi-source.json'; gitless.create(repo,source_root,source_manifest,tree)
    analyzer=tmp/'fake-analyzer'; analyzer.write_text('#!/usr/bin/env python3\nimport json,sys\ncmd=sys.argv[1]\nif "--format" in sys.argv: print(json.dumps({"schema_version":"0.2.0","command":cmd}))\nelse: print("ok")\n'); analyzer.chmod(0o755)
    authority=module.validate_authority(module.load(ROOT/'benchmarks/task-definitions/sprint13-abi-role-query-v1.json')); contract=module.contract_result(authority)
    def attempt(label:str,mutate_analyzer:bool)->int:
        result=tmp/f'abi-{label}'; args=type('A',(),{'analyzer':analyzer,'result_dir':result,'source_root':source_root,'source_manifest':source_manifest,'expected_candidate_tree':tree,'authority':ROOT/'benchmarks/task-definitions/sprint13-abi-role-query-v1.json','expected':ROOT/'tests/expected/sprint13-abi-role-query-v1.json'})()
        original=module.subprocess.run; injected=False
        def hooked(argv:Any,*a:Any,**kw:Any)->Any:
            nonlocal injected
            cp=original(argv,*a,**kw)
            if not injected and isinstance(argv,list) and argv and Path(argv[0]).name=='analyzer':
                injected=True
                if mutate_analyzer:
                    path=Path(argv[0]); payload=path.read_bytes(); replacement=path.with_name('replacement'); replacement.write_bytes(payload); replacement.chmod(0o555); os.replace(replacement,path)
                else:
                    Path(argv[-1]).chmod(0o600)
            return cp
        module.subprocess.run=hooked
        try:
            try: module.run_closures(args,authority,contract)
            except module.QueryError: return 1
            raise RegressionError(f'ABI {label} mutation was accepted')
        finally: module.subprocess.run=original
    return attempt('target',False),attempt('analyzer',True)

def make_authority_probe()->tuple[int,int]:
    text=(ROOT/'Makefile').read_text(encoding='utf-8')
    require('sprint13-p084-acceptance-smoke: S13_EXPECTED_CANDIDATE_TREE := 178f1d1c93a5a05fba5a77af2c378e63e5dc017b' in text,'P084 acceptance lacks fixed source authority')
    relevant=text[text.index('sprint13-producer-authority-smoke:'):text.index('sprint13-ordered-two-pop-role-task-value-smoke:')]+text[text.index('sprint13-natural-coordinate-campaign-run:'):text.index('patch083-corrective-regression-smoke:')]+text[text.index('sprint13-abi-role-query-smoke:'):text.index('patch080-corrective-regression-smoke:')]+text[text.index('docker-build:'):text.index('docker-image-authority-smoke:')]
    require('expected_tree="$$(git write-tree)"' not in relevant,'acceptance dependencies still self-authenticate the caller tree')
    require(relevant.count('an authenticated expected candidate tree is required')>=4,'fixed-tree requirement is incomplete')
    return 1,1

def gitless_source_state_probe(tmp:Path)->int:
    module=load_module('p085_p083_regression',ROOT/'tools/patch083-corrective-regression-smoke.py'); repo=tmp/'gitless-state-repo'; tree=init_source_repo(repo,{'.gitignore':(b'/tests/toy-src/gadgets_sprint13_ordered_pairs\n',0o644),'Dockerfile':(b'FROM scratch\n',0o644)})
    gitless=load_module('p085_state_gitless',GITLESS); source=tmp/'gitless-state'; manifest=tmp/'gitless-state.json'; gitless.create(repo,source,manifest,tree)
    old_root,old_gitless=module.ROOT,module.GITLESS; old_manifest=os.environ.get('X64LENS_SOURCE_MANIFEST'); old_source=os.environ.get('X64LENS_SOURCE_AUTHORITY_ROOT')
    module.ROOT=source; module.GITLESS=GITLESS; os.environ['X64LENS_SOURCE_MANIFEST']=os.fspath(manifest); os.environ['X64LENS_SOURCE_AUTHORITY_ROOT']=os.fspath(source)
    try: return module.source_state_probe()
    finally:
        module.ROOT=old_root; module.GITLESS=old_gitless
        if old_manifest is None: os.environ.pop('X64LENS_SOURCE_MANIFEST',None)
        else: os.environ['X64LENS_SOURCE_MANIFEST']=old_manifest
        if old_source is None: os.environ.pop('X64LENS_SOURCE_AUTHORITY_ROOT',None)
        else: os.environ['X64LENS_SOURCE_AUTHORITY_ROOT']=old_source

def strategic_tools_probe()->tuple[int,int]:
    run([sys.executable,os.fspath(ATTRIBUTION),'selftest']); run([sys.executable,os.fspath(REPLAY),'selftest']); return 16,48

def main()->int:
    floors,delta,lifecycle_mutations=lifecycle_probe(); disjoint=abi_disjoint_probe(); make_fixed,make_no_fallback=make_authority_probe(); precedence,replay=strategic_tools_probe()
    with tempfile.TemporaryDirectory(prefix='x64lens-p085-corrective-') as raw:
        tmp=Path(raw); abi_publish=abi_publication_probe(tmp); initial_open=recovery_initial_open_probe(tmp); recovery_posthash=recovery_posthash_probe(tmp); gitless_mode,gitless_link=gitless_topology_probe(tmp); natural_mutations,natural_target=natural_structural_probe(tmp); abi_target,abi_analyzer=abi_execution_probe(tmp); gitless_state=gitless_source_state_probe(tmp)
    print('patch084-corrective-regression-smoke: ok '
          f'lifecycle_floors={floors} lifecycle_p084_delta={delta} lifecycle_mutations={lifecycle_mutations} '
          f'abi_semantic_disjoint={disjoint} abi_no_replace={abi_publish} abi_target_reauth={abi_target} abi_analyzer_pinned={abi_analyzer} '
          f'recovery_first_open_cleanup={initial_open} recovery_posthash={recovery_posthash} '
          f'gitless_mode_drift={gitless_mode} gitless_link_drift={gitless_link} gitless_source_state={gitless_state} '
          f'natural_structural_mutations={natural_mutations} natural_target_reauth={natural_target} '
          f'make_p084_fixed_tree={make_fixed} make_no_tree_fallback={make_no_fallback} '
          f'terminal_precedence={precedence} frozen_replay_executions={replay} loose_delivery=delivery_gate evidence_seal=delivery_gate')
    return 0
if __name__=='__main__':
    try: raise SystemExit(main())
    except (RegressionError,OSError,subprocess.SubprocessError,json.JSONDecodeError) as exc:
        print(f'patch084-corrective-regression-smoke: error: {exc}',file=sys.stderr); raise SystemExit(1)
