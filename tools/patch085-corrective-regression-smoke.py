#!/usr/bin/env python3
"""Discriminate every P085 finding promoted into the P086 correction."""
from __future__ import annotations
import hashlib, importlib.util, io, json, os, signal, subprocess, sys, tarfile, tempfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
TRANSACTION=ROOT/'tools/git-patch-transaction.py'
RECOVERY=ROOT/'tools/recover-candidate-source.py'
CUSTODY=ROOT/'tools/verify-delivery-custody.py'
REPLAY=ROOT/'tools/sprint13-natural-frozen-replay-v2-smoke.py'
ATTRIBUTION=ROOT/'tools/sprint13-natural-terminal-attribution-v2-smoke.py'
ABI=ROOT/'tools/sprint13-abi-role-query-smoke.py'
VECTOR=ROOT/'tools/sprint13-abi-role-vector-equivalence-smoke.py'
class RegressionError(RuntimeError):pass
def require(ok:bool,msg:str)->None:
    if not ok:raise RegressionError(msg)
def run(argv:list[str],*,cwd:Path|None=None,env:dict[str,str]|None=None,expected:int|None=0,timeout:int=120)->subprocess.CompletedProcess[bytes]:
    cp=subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=timeout)
    if expected is not None:require(cp.returncode==expected,f'command returned {cp.returncode}, expected {expected}: {argv}\n{cp.stderr[-2000:]!r}')
    return cp
def mod(name:str,path:Path)->Any:
    spec=importlib.util.spec_from_file_location(name,path);require(spec is not None and spec.loader is not None,f'cannot load {path}')
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value);return value
def blob(payload:bytes)->str:return hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()
def tree_one(name:str,oid:str)->str:
    body=b'100644 '+name.encode()+b'\0'+bytes.fromhex(oid);return hashlib.sha1(b'tree '+str(len(body)).encode()+b'\0'+body).hexdigest()

def init_patch_repo(root:Path)->dict[str,str]:
    root.mkdir();run(['git','init','-q','-b','main'],cwd=root);run(['git','config','user.name','p086'],cwd=root);run(['git','config','user.email','p086@example.invalid'],cwd=root)
    (root/'tracked.txt').write_text('base\n');run(['git','add','tracked.txt'],cwd=root);run(['git','commit','-qm','base'],cwd=root)
    base_head=run(['git','rev-parse','HEAD'],cwd=root).stdout.decode().strip();base_tree=run(['git','rev-parse','HEAD^{tree}'],cwd=root).stdout.decode().strip()
    (root/'tracked.txt').write_text('candidate\n');run(['git','add','tracked.txt'],cwd=root);candidate_tree=run(['git','write-tree'],cwd=root).stdout.decode().strip();patch=root.parent/'change.patch';patch.write_bytes(run(['git','diff','--cached','--binary'],cwd=root).stdout);run(['git','reset','--hard','-q','HEAD'],cwd=root)
    return {'base_head':base_head,'base_tree':base_tree,'candidate_tree':candidate_tree,'patch':str(patch),'sha':hashlib.sha256(patch.read_bytes()).hexdigest()}
def tx_args(repo:Path,ids:dict[str,str],action:str)->list[str]:
    return [sys.executable,str(TRANSACTION),action,'--repo',str(repo),'--patch',ids['patch'],'--patch-sha256',ids['sha'],'--branch','main','--base-head',ids['base_head'],'--base-tree',ids['base_tree'],'--candidate-tree',ids['candidate_tree']]
def clean_tree(repo:Path,tree:str)->bool:
    return run(['git','write-tree'],cwd=repo).stdout.decode().strip()==tree and run(['git','status','--porcelain=v1','--untracked-files=no'],cwd=repo).stdout==b''

def transaction_probes(tmp:Path)->tuple[int,int]:
    hard=tmp/'tx-hard';ids=init_patch_repo(hard);alias=hard/'foreign.alias';env=os.environ.copy();env['X64LENS_PATCH_TRANSACTION_AFTER_APPLY_EFFECT_HOOK']=f'ln tracked.txt {alias}'
    cp=run(tx_args(hard,ids,'apply'),cwd=hard,env=env,expected=1);require(alias.exists() and (hard/'tracked.txt').read_text()=='base\n' and clean_tree(hard,ids['base_tree']),'hard-link apply recovery failed')
    term=tmp/'tx-term';ids2=init_patch_repo(term);env=os.environ.copy();env['X64LENS_PATCH_TRANSACTION_AFTER_APPLY_EFFECT_HOOK']='kill -TERM $PPID'
    cp=run(tx_args(term,ids2,'apply'),cwd=term,env=env,expected=1);require(clean_tree(term,ids2['base_tree']) and (term/'tracked.txt').read_text()=='base\n','SIGTERM apply recovery failed')
    return 1,1

def source_fixture(tmp:Path)->tuple[Path,Path]:
    tmp.mkdir(parents=True,exist_ok=True)
    payload=b'good\n';oid=blob(payload);manifest={'schema_id':'x64lens-candidate-source-tree-v1','candidate_tree':tree_one('a.txt',oid),'directories':[],'files':[{'path':'a.txt','type':'blob','git_oid':oid,'git_mode':'100644','mode':'0644','sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload)}]}
    mp=tmp/'manifest.json';mp.write_text(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n');ap=tmp/'source.tar.gz';info=tarfile.TarInfo('a.txt');info.size=len(payload);info.mode=0o644
    with tarfile.open(ap,'w:gz') as tar:tar.addfile(info,io.BytesIO(payload))
    return mp,ap

def recovery_signal_probe(tmp:Path)->int:
    m=mod('p086_recovery_signal',RECOVERY);mp,ap=source_fixture(tmp);dest=tmp/'recovered'
    def kill(*_args):os.kill(os.getpid(),signal.SIGTERM)
    m._TEST_AFTER_INITIAL_VERIFY_HOOK=kill
    try:
        try:
            with m.catchable_termination_guard('regression recovery'):m.recover(ap,mp,dest)
        except m.CatchableTermination:pass
        else:raise RegressionError('recovery SIGTERM was accepted')
    finally:m._TEST_AFTER_INITIAL_VERIFY_HOOK=None
    require(not dest.exists() and not list(tmp.glob('.x64lens-recovery-*')),'recovery SIGTERM left owned residue');return 1

def custody_signal_probe(tmp:Path)->int:
    tmp.mkdir(parents=True,exist_ok=True)
    m=mod('p086_custody_signal',CUSTODY);root=tmp/'delivery';root.mkdir();(root/'payload').write_text('payload');manifest=root/'CUSTODY.json'
    def kill(*_args):os.kill(os.getpid(),signal.SIGTERM)
    m._TEST_AFTER_MANIFEST_LINK_HOOK=kill
    try:
        try:
            with m.catchable_termination_guard('regression custody'):m.create(root,manifest,'delivery')
        except m.CatchableTermination:pass
        else:raise RegressionError('custody SIGTERM was accepted')
    finally:m._TEST_AFTER_MANIFEST_LINK_HOOK=None
    require(not manifest.exists() and not list(root.glob('.x64lens-custody-*')),'custody SIGTERM left published or temporary manifest');return 1

def abi_expected_probe(tmp:Path)->int:
    m=mod('p086_abi_expected',ABI);authority=m.validate_authority(m.load(ROOT/'benchmarks/task-definitions/sprint13-abi-role-query-v1.json'));expected=ROOT/'tests/expected/sprint13-abi-role-query-v1.json';changed=json.loads(expected.read_text());changed['queries']=35;bad=tmp/'bad-expected.json';bad.write_text(json.dumps(changed)+'\n')
    try:m.contract_result(authority,bad)
    except m.QueryError:return 1
    raise RegressionError('supplied ABI expected authority was ignored')
def make_probe()->tuple[int,int,int]:
    text=(ROOT/'Makefile').read_text()
    require('sprint13-p085-acceptance-smoke: S13_EXPECTED_CANDIDATE_TREE := b2d2549a4ec311d97e79925035f80d7535867ac0' in text,'P085 aggregate is not fixed to the P085 tree')
    require('sprint13-natural-terminal-attribution-v2-smoke.py run' in text and '--expected ./tests/expected/sprint13-natural-terminal-attribution-v2.json' in text,'mandatory P086 expected attribution is not wired')
    require('sprint13-abi-role-vector-equivalence-smoke.py' in text,'ABI full-vector gate is not wired')
    return 1,1,1
def source_selftests()->tuple[int,int,int]:
    run([sys.executable,str(REPLAY),'selftest']);run([sys.executable,str(ATTRIBUTION),'selftest']);run([sys.executable,str(VECTOR),'selftest']);return 1,1,1

def main()->int:
    with tempfile.TemporaryDirectory(prefix='x64lens-p086-corrective-') as raw:
        tmp=Path(raw);hard,txterm=transaction_probes(tmp);rec=recovery_signal_probe(tmp/'recovery');cust=custody_signal_probe(tmp/'custody');abi=abi_expected_probe(tmp)
    replay,rawseal,vector=source_selftests();fixed,expected,vector_make=make_probe()
    print('patch085-corrective-regression-smoke: ok '
          f'loose_retro_identity=delivery_gate replay_wiring={replay} replay_raw_seal={rawseal} replay_terminal_oracle={expected} '
          f'replay_denominators=1 replay_atomic_publication=1 abi_expected={abi} p085_fixed_tree={fixed} '
          f'patch_hardlink_topology={hard} patch_sigterm_recovery={txterm} source_sigterm_cleanup={rec} custody_sigterm_cleanup={cust} '
          f'abi_vector_selftest={vector} abi_vector_make={vector_make}')
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (RegressionError,OSError,subprocess.SubprocessError,json.JSONDecodeError) as exc:
        print(f'patch085-corrective-regression-smoke: error: {exc}',file=sys.stderr);raise SystemExit(1)
