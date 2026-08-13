#!/usr/bin/env python3
"""Execute and seal the P086 no-reroll natural-coordinate replay."""
from __future__ import annotations
import argparse, ctypes, hashlib, importlib.util, json, os, re, shutil, signal, stat, subprocess, sys, tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NoReturn

ROOT=Path(__file__).resolve().parents[1]
AUTHORITY=ROOT/'benchmarks/task-definitions/sprint13-natural-frozen-replay-v2.json'
NATURAL=ROOT/'tools/sprint13-natural-coordinate-campaign.py'
ATTRIBUTION_V1=ROOT/'tools/sprint13-natural-terminal-attribution-smoke.py'
ATTRIBUTION_V2=ROOT/'tools/sprint13-natural-terminal-attribution-v2-smoke.py'
REMOVE=ROOT/'tools/remove-owned-tree.py'
TOOLS=('x64lens','ropgadget','ropper','ropr')
class ReplayError(RuntimeError): pass
class CatchableTermination(ReplayError): pass
def require(ok:bool,msg:str)->None:
    if not ok: raise ReplayError(msg)
def fail(msg:str)->NoReturn:
    print(f'sprint13-natural-frozen-replay-v2-smoke: error: {msg}',file=sys.stderr); raise SystemExit(1)
def strict(items:list[tuple[str,Any]])->dict[str,Any]:
    out={}
    for k,v in items: require(k not in out,f'duplicate JSON key: {k}'); out[k]=v
    return out
def load(path:Path)->Any:return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=strict)
def canonical(v:Any)->bytes:return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode()
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def module(name:str,path:Path)->Any:
    spec=importlib.util.spec_from_file_location(name,path); require(spec is not None and spec.loader is not None,f'cannot load {path}')
    value=importlib.util.module_from_spec(spec); sys.modules[name]=value; spec.loader.exec_module(value); return value
@contextmanager
def signal_guard(label:str):
    guarded=(signal.SIGHUP,signal.SIGINT,signal.SIGTERM); previous={s:signal.getsignal(s) for s in guarded}
    def handler(signum,_frame):
        for s in guarded: signal.signal(s,signal.SIG_IGN)
        raise CatchableTermination(f'{label} interrupted by {signal.Signals(signum).name}')
    for s in guarded: signal.signal(s,handler)
    try: yield
    finally:
        for s,old in previous.items(): signal.signal(s,old)

def rename_noreplace(source:Path,destination:Path)->None:
    libc=ctypes.CDLL(None,use_errno=True);fn=getattr(libc,'renameat2',None);require(fn is not None,'renameat2 is unavailable')
    fn.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];fn.restype=ctypes.c_int
    if fn(-100,os.fsencode(source),-100,os.fsencode(destination),1)!=0:
        err=ctypes.get_errno();raise OSError(err,os.strerror(err),destination)

def validate_authority(v:Any)->dict[str,Any]:
    attr=module('s13_p086_replay_attr_v2',ATTRIBUTION_V2); return attr.validate_authority(v)
def validate_adapters(authority:dict[str,Any])->None:
    require(len(authority['adapters'])==2,'adapter denominator changed')
    for item in authority['adapters']:
        p=ROOT/item['path']; require(p.is_file() and not p.is_symlink() and sha(p)==item['sha256'],f'adapter authority changed: {item["path"]}')
def tool_identity(natural:Any,path:Path,expected:dict[str,Any])->dict[str,Any]:
    current=natural.regular_identity(path,expected_mode=int(expected['mode'],8),expected_sha256=expected['sha256'],require_single_link=True)
    require(current['size_bytes']==expected['size_bytes'] and bool(int(expected['mode'],8)&0o100),f'tool authority changed: {path}')
    return current
def copy_target(natural:Any,source:Path,destination:Path,expected:dict[str,Any])->dict[str,Any]:
    payload,identity=natural.read_regular_authority(source,64*1024*1024)
    require(identity['sha256']==expected['sha256'] and identity['size_bytes']==expected['size_bytes'],f'frozen target changed: {expected["target_id"]}')
    natural.write_regular(destination,payload,0o444)
    return natural.regular_identity(destination,expected_mode=0o444,expected_sha256=expected['sha256'],require_single_link=True)

def verify_predecessor_checksum(root:Path)->int:
    path=root/'SHA256SUMS.txt'; require(path.is_file() and not path.is_symlink(),'predecessor checksum manifest missing')
    seen=set(); count=0
    for line in path.read_text(encoding='utf-8').splitlines():
        require(len(line)>=67 and line[64:66]=='  ','malformed predecessor checksum row'); digest=line[:64]; rel=line[66:]
        require(re.fullmatch(r'[0-9a-f]{64}',digest) is not None and rel not in seen,'invalid predecessor checksum row'); seen.add(rel)
        p=root/rel; require(p.is_file() and not p.is_symlink() and sha(p)==digest,f'predecessor checksum mismatch: {rel}'); count+=1
    require(count>0,'empty predecessor checksum manifest'); return count

def distribution_closure(interpreter:Path,distribution:str,env:dict[str,str])->dict[str,Any]:
    script=r'''import hashlib,importlib.metadata,json,os,pathlib,stat,sys
name=sys.argv[1]; d=importlib.metadata.distribution(name); records=[]; total=0
for item in sorted(d.files or [],key=lambda x:os.fsencode(str(x))):
 p=pathlib.Path(d.locate_file(item))
 try: st=p.lstat()
 except FileNotFoundError: continue
 if not stat.S_ISREG(st.st_mode) or st.st_nlink<1: continue
 h=hashlib.sha256(p.read_bytes()).hexdigest(); total+=st.st_size
 records.append({'path':str(item),'sha256':h,'size_bytes':st.st_size,'mode':format(stat.S_IMODE(st.st_mode),'04o')})
assert len(records)<=16384 and total<=1073741824
payload=(json.dumps(records,sort_keys=True,separators=(',',':'))+'\n').encode()
print(json.dumps({'distribution':name,'version':d.version,'files':len(records),'bytes':total,'closure_sha256':hashlib.sha256(payload).hexdigest()},sort_keys=True))'''
    cp=subprocess.run([os.fspath(interpreter),'-c',script,distribution],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=60,check=False)
    require(cp.returncode==0 and len(cp.stdout)<=65536 and len(cp.stderr)<=65536,f'cannot authenticate Python distribution {distribution}: {cp.stderr[:256]!r}')
    return json.loads(cp.stdout)

def runtime_authority(natural:Any,paths:dict[str,Path],identities:dict[str,dict[str,Any]],authority:dict[str,Any],stage:Path)->tuple[dict[str,Any],dict[str,str]]:
    state=stage/'runtime-state'; home=state/'home'; cache=state/'cache'; config=state/'config'
    for p in (state,home,cache,config): p.mkdir(mode=0o700)
    effective={'HOME':os.fspath(home),'XDG_CACHE_HOME':os.fspath(cache),'XDG_CONFIG_HOME':os.fspath(config),'LANG':'C','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','PATH':os.environ.get('PATH','/usr/bin:/bin')}
    records={}
    distributions=authority['runtime_authority']['python_distributions']
    for name in TOOLS:
        record={'kind':'native','executable':identities[name]}
        if name in distributions:
            first=paths[name].read_bytes().splitlines()[0] if paths[name].stat().st_size else b''
            require(first.startswith(b'#!'),'Python launcher lacks shebang')
            shebang=first[2:].decode('utf-8','strict').strip().split()
            if shebang and Path(shebang[0]).name=='env':
                require(len(shebang)>=2,'invalid env shebang'); resolved=shutil.which(shebang[1],path=effective['PATH'])
                require(resolved is not None,'Python interpreter unavailable'); interpreter=Path(resolved).resolve(strict=True)
            else: interpreter=Path(shebang[0]).resolve(strict=True)
            interpreter_identity=natural.regular_identity(interpreter,require_single_link=False)
            record={'kind':'python_distribution','executable':identities[name],'interpreter':interpreter_identity,'distribution_closure':distribution_closure(interpreter,distributions[name],effective)}
        records[name]=record
    normalized={'HOME':'runtime-state/home','XDG_CACHE_HOME':'runtime-state/cache','XDG_CONFIG_HOME':'runtime-state/config','LANG':'C','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'}
    require(normalized==authority['runtime_authority']['environment'],'runtime environment policy changed')
    return {'schema':'x64lens-sprint13-natural-runtime-authority-v1','environment':normalized,'tools':records,'cache_policy':'isolated_empty_before_replay','inherited_home':False,'inherited_cache':False},effective

def checksum_write(natural:Any,stage:Path)->int:
    lines=[]
    for path in sorted((x for x in stage.rglob('*') if x.is_file() and x.name!='SHA256SUMS.txt'),key=lambda x:os.fsencode(x.relative_to(stage).as_posix())):
        lines.append(f'{sha(path)}  {path.relative_to(stage).as_posix()}\n')
    natural.write_regular(stage/'SHA256SUMS.txt',''.join(lines).encode()); return len(lines)

def run_replay(args:argparse.Namespace,authority:dict[str,Any])->dict[str,Any]:
    natural=module('s13_p086_replay_natural',NATURAL); attr1=module('s13_p086_replay_input',ATTRIBUTION_V1); remover=module('s13_p086_replay_remove',REMOVE)
    input_dir=args.input_dir.resolve(strict=True); predecessor=attr1.validate_input(input_dir,authority); predecessor_checks=verify_predecessor_checksum(input_dir)
    validate_adapters(authority); source=natural.authenticate_source_authority(args.source_root,args.source_manifest,args.expected_candidate_tree)
    result_dir=Path(os.path.abspath(args.result_dir)); require(not result_dir.exists() and not result_dir.is_symlink(),'replay result already exists'); require(result_dir.parent.is_dir() and not result_dir.parent.is_symlink(),'replay result parent unavailable or linked')
    stage=Path(tempfile.mkdtemp(prefix=f'.{result_dir.name}.stage.',dir=result_dir.parent)); identity=remover.parse_identity(remover.identify(stage)); current=stage
    paths={'x64lens':args.x64lens.resolve(strict=True),'ropgadget':args.ropgadget.resolve(strict=True),'ropper':args.ropper.resolve(strict=True),'ropr':args.ropr.resolve(strict=True)}
    try:
        identities={name:tool_identity(natural,path,authority['tools'][name]) for name,path in paths.items()}
        runtime,effective_env=runtime_authority(natural,paths,identities,authority,stage); natural.write_regular(stage/'runtime-authority.json',canonical(runtime))
        freeze={'schema':'x64lens-sprint13-natural-selection-freeze-v2','selection':authority['selection']}; natural.write_regular(stage/'selection-freeze.json',canonical(freeze))
        target_root=stage/'targets'; target_root.mkdir(mode=0o755); frozen_targets={}
        for expected in authority['selection']: frozen_targets[expected['target_id']]=copy_target(natural,input_dir/'targets'/expected['target_id'],target_root/expected['target_id'],expected)
        outcomes={}; execution_count=0; contract=authority['execution']
        for expected in authority['selection']:
            target=target_root/expected['target_id']; frozen=frozen_targets[expected['target_id']]; records={}
            for tool in TOOLS:
                require(natural.regular_identity(target,expected_mode=0o444,expected_sha256=expected['sha256'],require_single_link=True)==frozen,f'target changed before replay: {expected["target_id"]}/{tool}')
                require(tool_identity(natural,paths[tool],authority['tools'][tool])==identities[tool],f'tool changed before replay: {tool}')
                argv=natural.tool_commands(tool,paths[tool],target,4)
                result=natural.run_bounded(argv,cwd=ROOT,timeout=contract['timeout_seconds'],stdout_limit=contract['stdout_limit_bytes'],stderr_limit=contract['stderr_limit_bytes'],env=effective_env)
                require(natural.regular_identity(target,expected_mode=0o444,expected_sha256=expected['sha256'],require_single_link=True)==frozen,f'target changed after replay: {expected["target_id"]}/{tool}')
                require(tool_identity(natural,paths[tool],authority['tools'][tool])==identities[tool],f'tool changed after replay: {tool}')
                member=stage/'runs'/expected['target_id']/tool; stdout_path=member/'stdout'; stderr_path=member/'stderr'
                stdout_desc=natural.write_regular(stdout_path,result.stdout); stderr_desc=natural.write_regular(stderr_path,result.stderr)
                record={'argv':argv,'exit_code':result.exit_code,'signal':result.signal,'timeout':result.timeout,'output_limited':result.output_limited,'wall_ns':result.wall_ns,'stdout':{**stdout_desc,'path':stdout_path.relative_to(stage).as_posix()},'stderr':{**stderr_desc,'path':stderr_path.relative_to(stage).as_posix()},'relation_status':'unavailable','relation_addresses':[]}
                if result.exit_code==0 and not result.timeout and not result.output_limited:
                    try:
                        if tool=='x64lens':
                            virtual,offsets=natural.relation_sets_x64lens(result.stdout); record['relation_status']='observed' if virtual else 'observed_zero'; record['virtual_addresses']=sorted(virtual); record['file_offsets']=sorted(offsets)
                        else:
                            addresses=natural.relation_set_baseline(tool,result.stdout); record['relation_status']='observed' if addresses else 'observed_zero'; record['relation_addresses']=sorted(addresses)
                    except Exception as exc: record['relation_status']='parse_error'; record['parse_error']=f'{type(exc).__name__}: {exc}'
                records[tool]=record; execution_count+=1
            outcomes[expected['target_id']]={'target':expected,'tools':records}
        cells=[]
        for baseline in natural.BASELINES:
            for role in natural.ROLES:
                observations=[]
                for expected in [x for x in authority['selection'] if x['role']==role]:
                    x=outcomes[expected['target_id']]['tools']['x64lens']; b=outcomes[expected['target_id']]['tools'][baseline]; observation={'target_id':expected['target_id'],'target_sha256':expected['sha256']}
                    if x['relation_status'] not in {'observed','observed_zero'} or b['relation_status'] not in {'observed','observed_zero'}: observation['status']='unavailable'
                    else: observation.update(natural.classify(set(b['relation_addresses']),set(x['virtual_addresses']),set(x['file_offsets'])))
                    observations.append(observation)
                cells.append(natural.cell_result(baseline,role,observations))
        result={'schema':'x64lens-sprint13-natural-frozen-replay-result-v2','sprint':13,'patch':86,'campaign_id':authority['campaign_id'],'predecessor_campaign_id':authority['predecessor_campaign_id'],'evidence_class':'diagnostic','frozen':False,'publication_eligible':False,'authority_sha256':sha(args.authority.resolve(strict=True)),'predecessor_manifest_sha256':authority['input_authority']['manifest_sha256'],'predecessor_checksum_entries':predecessor_checks,'source_authority':source,'tool_identities':identities,'runtime_authority_sha256':sha(stage/'runtime-authority.json'),'selection_freeze_sha256':sha(stage/'selection-freeze.json'),'execution_count':execution_count,'complete_execution_denominator':48,'outcomes':outcomes,'cells':cells,'cell_counts':{s:sum(c['terminal_state']==s for c in cells) for s in ('qualified','insufficient','unavailable','mismatch','ambiguous')},'control_count':sum(len(c['controls']) for c in cells),'raw_stream_count':96,'target_file_count':12,'claim_boundary':authority['claim_boundary'],'limitations':authority['limitations']}
        natural.require_structural_complete(result); require(execution_count==48 and result['raw_stream_count']==96 and result['control_count']==108,'replay denominator changed')
        require(natural.authenticate_source_authority(args.source_root,args.source_manifest,args.expected_candidate_tree)==source,'source authority changed during replay')
        natural.write_regular(stage/'manifest.json',canonical(result)); checksum_count=checksum_write(natural,stage); require(checksum_count>=111,'sealed replay membership is incomplete')
        rename_noreplace(stage,result_dir); current=result_dir
        require(remover.identify(result_dir)==f'{remover.IDENTITY_VERSION}:{identity.device}:{identity.inode}:{identity.birth_ns}:{identity.mount_id}','published replay identity changed')
        return result
    except BaseException:
        try:
            if current.exists(): remover.remove(current,identity)
        except BaseException as cleanup:
            raise ReplayError(f'replay failed and cleanup failed closed: {cleanup}')
        raise

def selftest(authority:dict[str,Any])->None:
    validate_adapters(authority)
    require(len(authority['selection'])==12 and authority['execution']['execution_denominator']==48 and authority['result_contract']['raw_streams']==96,'P086 replay selftest changed')
    remover=module('s13_p086_replay_selftest_remove',REMOVE)
    with tempfile.TemporaryDirectory(prefix='x64lens-replay-publication-selftest-') as raw:
        parent=Path(raw); final=parent/'result'; stage=Path(tempfile.mkdtemp(prefix='.result.stage.',dir=parent))
        identity=remover.parse_identity(remover.identify(stage)); (stage/'owned').write_text('owned',encoding='utf-8')
        try:
            raise ReplayError('injected producer failure')
        except ReplayError:
            remover.remove(stage,identity)
        require(not stage.exists() and not final.exists(),'producer failure left a final or staging result')

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('action',choices=('selftest','run')); ap.add_argument('--authority',type=Path,default=AUTHORITY); ap.add_argument('--input-dir',type=Path); ap.add_argument('--result-dir',type=Path); ap.add_argument('--x64lens',type=Path); ap.add_argument('--ropgadget',type=Path); ap.add_argument('--ropper',type=Path); ap.add_argument('--ropr',type=Path); ap.add_argument('--source-root',type=Path); ap.add_argument('--source-manifest',type=Path); ap.add_argument('--expected-candidate-tree'); args=ap.parse_args()
    try:
        authority=validate_authority(load(args.authority.resolve(strict=True))); selftest(authority)
        if args.action=='selftest': print('sprint13-natural-frozen-replay-v2-smoke: ok targets=12 roles=3 tools=4 executions=48 raw_streams=96 reroll=0 isolated_cache=1 run=deferred'); return 0
        for name in ('input_dir','result_dir','x64lens','ropgadget','ropper','ropr','source_root','source_manifest','expected_candidate_tree'): require(getattr(args,name) is not None,f'--{name.replace("_","-")} is required')
        with signal_guard('natural frozen replay'): result=run_replay(args,authority)
        print(f'sprint13-natural-frozen-replay-v2-smoke: ok targets=12 executions={result["execution_count"]}/48 raw_streams=96 cells=9 controls={result["control_count"]}/108 reroll=0 isolated_cache=1 diagnostic=1'); return 0
    except Exception as exc: fail(f'{type(exc).__name__}: {exc}')
if __name__=='__main__': raise SystemExit(main())
