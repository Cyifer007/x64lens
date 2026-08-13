#!/usr/bin/env python3
"""Validate sealed P086 replay evidence and attribute terminal states by layer."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, stat, sys, tempfile
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

ROOT=Path(__file__).resolve().parents[1]
AUTHORITY=ROOT/'benchmarks/task-definitions/sprint13-natural-frozen-replay-v2.json'
EXPECTED=ROOT/'tests/expected/sprint13-natural-terminal-attribution-v2.json'
NATURAL=ROOT/'tools/sprint13-natural-coordinate-campaign.py'
TOOLS=('x64lens','ropgadget','ropper','ropr')
STATES=('qualified','insufficient','unavailable','mismatch','ambiguous')
class AttributionError(RuntimeError): pass
def require(ok:bool,msg:str)->None:
    if not ok: raise AttributionError(msg)
def fail(msg:str)->NoReturn:
    print(f'sprint13-natural-terminal-attribution-v2-smoke: error: {msg}',file=sys.stderr); raise SystemExit(1)
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

def safe_rel(value:str)->str:
    require(isinstance(value,str) and value!='','empty checksum path')
    p=PurePosixPath(value); require(not p.is_absolute() and '..' not in p.parts and '.' not in p.parts,'unsafe checksum path')
    return p.as_posix()

def checksum_map(root:Path)->dict[str,str]:
    path=root/'SHA256SUMS.txt'; require(path.is_file() and not path.is_symlink(),'replay checksum manifest missing')
    out={}
    for line in path.read_text(encoding='utf-8').splitlines():
        require(len(line)>=67 and line[64:66]=='  ','malformed replay checksum row')
        digest=line[:64]; rel=safe_rel(line[66:]); require(all(c in '0123456789abcdef' for c in digest),'invalid checksum digest')
        require(rel not in out and rel!='SHA256SUMS.txt','duplicate/self checksum path'); out[rel]=digest
    actual={}
    for item in root.rglob('*'):
        rel=item.relative_to(root).as_posix()
        st=item.lstat(); require(not stat.S_ISLNK(st.st_mode),'linked replay evidence rejected')
        if item.is_file():
            require(stat.S_ISREG(st.st_mode) and st.st_nlink==1,f'unsafe replay member: {rel}'); actual[rel]=sha(item)
        elif item.is_dir(): require(stat.S_ISDIR(st.st_mode),f'special replay member: {rel}')
        else: raise AttributionError(f'special replay member: {rel}')
    actual.pop('SHA256SUMS.txt',None)
    require(set(out)==set(actual),'replay checksum membership incomplete')
    for rel,digest in out.items(): require(actual[rel]==digest,f'replay checksum mismatch: {rel}')
    return out

def validate_authority(v:Any)->dict[str,Any]:
    keys={'schema','sprint','patch','campaign_id','predecessor_campaign_id','evidence_class','frozen','publication_eligible','input_authority','selection','tools','adapters','execution','runtime_authority','result_contract','terminal_attribution','claim_boundary','limitations'}
    require(isinstance(v,dict) and set(v)==keys,'P086 replay authority shape changed')
    require(v['schema']=='x64lens-sprint13-natural-frozen-replay-authority-v2' and v['sprint']==13 and v['patch']==86,'P086 replay authority identity changed')
    require(v['campaign_id']=='s13-p086-natural-frozen-replay-v2' and v['predecessor_campaign_id']=='s13-p083-natural-coordinate-v1','P086 replay lineage changed')
    require(v['evidence_class']=='diagnostic' and v['frozen'] is False and v['publication_eligible'] is False,'P086 replay evidence boundary changed')
    require(len(v['selection'])==12 and len({x['target_id'] for x in v['selection']})==12,'target denominator changed')
    require({x['role'] for x in v['selection']}=={'et_exec','pie_et_dyn','shared_et_dyn'},'role denominator changed')
    ex=v['execution']; require(ex['execution_denominator']==48 and ex['executions_per_target']==4 and ex['tools']==list(TOOLS) and ex['reroll'] is False,'execution authority changed')
    ia=v['input_authority']; require(type(ia['executions']) is int and ia['executions']==48 and ia['selected_targets']==12 and ia['cells']==9 and ia['controls']==108,'predecessor denominator authority changed')
    require(sum(ia['cell_counts'].values())==9,'predecessor cell counts changed')
    term=v['terminal_attribution']; require(term['execution_outcomes']==48 and term['relation_outcomes']==48 and term['observations']==36 and term['cells']==9 and term['precedence_mutations']==16,'terminal denominator changed')
    rc=v['result_contract']; require(rc=={'checksum_complete':True,'expected_result_required':True,'raw_streams':96,'run_records':48,'target_files':12},'result contract changed')
    return v

def execution_reason(record:dict[str,Any],tool:str)->str:
    if record.get('timeout') is True:return 'timeout'
    if record.get('output_limited') is True:return 'output_limit'
    if record.get('signal') is not None:return 'signal'
    if record.get('exit_code')==0:return 'success'
    if tool=='x64lens' and record.get('exit_code')==6:return 'unsupported'
    return 'nonzero_exit'

def precedence_selftest()->int:
    cases=[
      ({'timeout':True,'output_limited':True,'signal':9,'exit_code':0},'x64lens','timeout'),
      ({'timeout':True,'output_limited':False,'signal':None,'exit_code':6},'x64lens','timeout'),
      ({'timeout':False,'output_limited':True,'signal':9,'exit_code':0},'x64lens','output_limit'),
      ({'timeout':False,'output_limited':True,'signal':None,'exit_code':6},'x64lens','output_limit'),
      ({'timeout':False,'output_limited':False,'signal':9,'exit_code':0},'x64lens','signal'),
      ({'timeout':False,'output_limited':False,'signal':15,'exit_code':6},'x64lens','signal'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':0},'x64lens','success'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':0},'ropper','success'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':6},'x64lens','unsupported'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':6},'ropper','nonzero_exit'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':1},'x64lens','nonzero_exit'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':17},'ropr','nonzero_exit'),
      ({'timeout':True,'output_limited':True,'signal':None,'exit_code':None},'ropr','timeout'),
      ({'timeout':False,'output_limited':True,'signal':None,'exit_code':None},'ropr','output_limit'),
      ({'timeout':False,'output_limited':False,'signal':9,'exit_code':None},'ropr','signal'),
      ({'timeout':False,'output_limited':False,'signal':None,'exit_code':127},'ropgadget','nonzero_exit')]
    for record,tool,expected in cases: require(execution_reason(record,tool)==expected,f'precedence failure: {tool}/{expected}')
    return len(cases)

def validate_result(root:Path,authority:dict[str,Any],authority_sha256:str)->tuple[dict[str,Any],dict[str,str]]:
    checks=checksum_map(root)
    for name in ('manifest.json','selection-freeze.json','runtime-authority.json'):
        require(name in checks,f'missing sealed replay authority: {name}')
    result=load(root/'manifest.json'); freeze=load(root/'selection-freeze.json'); runtime=load(root/'runtime-authority.json')
    require(result['schema']=='x64lens-sprint13-natural-frozen-replay-result-v2' and result['patch']==86,'replay result identity changed')
    require(result['campaign_id']==authority['campaign_id'] and result['authority_sha256']==authority_sha256,'replay campaign or authority changed')
    require(freeze=={'schema':'x64lens-sprint13-natural-selection-freeze-v2','selection':authority['selection']},'selection freeze changed')
    require(runtime['schema']=='x64lens-sprint13-natural-runtime-authority-v1' and set(runtime['tools'])==set(TOOLS),'runtime authority changed')
    require(runtime['environment']==authority['runtime_authority']['environment'],'runtime environment authority changed')
    require(set(result['tool_identities'])==set(TOOLS),'result tool identity membership changed')
    for tool in TOOLS:
        expected=authority['tools'][tool]; current=result['tool_identities'][tool]; runtime_tool=runtime['tools'][tool]['executable']
        for key in ('sha256','size_bytes','mode'):
            require(current.get(key)==expected[key] and runtime_tool.get(key)==expected[key],f'tool/runtime authority changed: {tool}/{key}')
    expected={(x['target_id'],tool) for x in authority['selection'] for tool in TOOLS}
    observed=set(); raw=set()
    require(set(result['outcomes'])=={x['target_id'] for x in authority['selection']},'replay target membership changed')
    for target_id,outcome in result['outcomes'].items():
        require(set(outcome['tools'])==set(TOOLS),f'tool membership changed: {target_id}')
        for tool,record in outcome['tools'].items():
            observed.add((target_id,tool))
            for stream in ('stdout','stderr'):
                rel=safe_rel(record[stream]['path']); require(rel in checks,f'unsealed raw stream: {rel}')
                require(rel.startswith(f'runs/{target_id}/{tool}/'),f'raw stream path changed: {rel}'); raw.add(rel)
                path=root/rel; require(record[stream]['sha256']==sha(path) and record[stream]['size_bytes']==path.stat().st_size,f'raw stream descriptor changed: {rel}')
    require(observed==expected and len(raw)==96,'replay raw denominator changed')
    target_paths={f'targets/{x["target_id"]}' for x in authority['selection']}; require(target_paths<=set(checks),'target evidence missing')
    require(result['execution_count']==48 and result['complete_execution_denominator']==48 and len(result['cells'])==9 and result['control_count']==108,'replay manifest denominators changed')
    return result,checks

def attribute(result:dict[str,Any],authority:dict[str,Any])->dict[str,Any]:
    execution={k:0 for k in ('success','unsupported','timeout','output_limit','signal','nonzero_exit')}
    relation={k:0 for k in authority['terminal_attribution']['relation_reasons']}
    for outcome in result['outcomes'].values():
        for tool,record in outcome['tools'].items():
            execution[execution_reason(record,tool)]+=1; state=record['relation_status']; require(state in relation,f'unknown relation state: {state}'); relation[state]+=1
    observation={k:0 for k in authority['terminal_attribution']['observation_reasons']}; cells={k:0 for k in authority['terminal_attribution']['cell_reasons']}
    for cell in result['cells']:
        state=cell['terminal_state']; require(state in cells,f'unknown cell state: {state}'); cells[state]+=1
        for item in cell['observations']:
            state=item['status']; require(state in observation,f'unknown observation state: {state}'); observation[state]+=1
    out={'schema':'x64lens-sprint13-natural-terminal-attribution-result-v2','sprint':13,'patch':86,'campaign_id':result['campaign_id'],'execution_outcomes':sum(execution.values()),'execution_reasons':execution,'relation_outcomes':sum(relation.values()),'relation_reasons':relation,'observations':sum(observation.values()),'observation_reasons':observation,'cells':sum(cells.values()),'cell_reasons':cells,'precedence_mutations':precedence_selftest(),'raw_streams_verified':96,'target_files_verified':12,'checksum_complete':True,'decision':'sealed_terminal_layers_attributed_without_reinterpretation','public_fields_added':0,'semantic_changes':0,'score_changes':0,'schema_changed':False}
    require(out['execution_outcomes']==48 and out['relation_outcomes']==48 and out['observations']==36 and out['cells']==9,'attribution denominator changed')
    return out

def write_noreplace(path:Path,payload:bytes)->None:
    require(path.parent.is_dir() and not path.parent.is_symlink(),'output parent unavailable or linked')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o444)
    try:
        view=memoryview(payload)
        while view:
            n=os.write(fd,view); require(n>0,'short attribution write'); view=view[n:]
        os.fchmod(fd,0o444); os.fsync(fd)
    finally: os.close(fd)

def selftest(authority:dict[str,Any])->None:
    require(precedence_selftest()==16,'precedence denominator changed')
    mutated=json.loads(json.dumps(authority)); mutated['input_authority']['executions']=47
    try: validate_authority(mutated)
    except AttributionError: pass
    else: raise AttributionError('false replay denominator accepted')
    with tempfile.TemporaryDirectory(prefix='x64lens-attribution-raw-selftest-') as raw:
        root=Path(raw); (root/'runs/t/x').mkdir(parents=True)
        for name,payload in (('manifest.json',b'{}\n'),('selection-freeze.json',b'{}\n'),('runtime-authority.json',b'{}\n'),('runs/t/x/stdout',b'raw')):
            path=root/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(payload)
        paths=sorted(x for x in root.rglob('*') if x.is_file())
        (root/'SHA256SUMS.txt').write_text(''.join(f'{sha(x)}  {x.relative_to(root).as_posix()}\n' for x in paths),encoding='utf-8')
        checksum_map(root)
        (root/'runs/t/x/stdout').unlink()
        try: checksum_map(root)
        except AttributionError: pass
        else: raise AttributionError('missing raw replay member was accepted')

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('action',choices=('selftest','run')); ap.add_argument('--authority',type=Path,default=AUTHORITY); ap.add_argument('--expected',type=Path,default=EXPECTED); ap.add_argument('--input-dir',type=Path); ap.add_argument('--output',type=Path); args=ap.parse_args()
    try:
        authority_path=args.authority.resolve(strict=True); authority=validate_authority(load(authority_path)); selftest(authority)
        if args.action=='selftest':
            print('sprint13-natural-terminal-attribution-v2-smoke: ok precedence_mutations=16 execution_outcomes=48 relation_outcomes=48 observations=36 cells=9 raw_streams=96 expected_required=1 run=deferred'); return 0
        require(args.input_dir is not None and args.output is not None,'--input-dir and --output are required')
        result,_checks=validate_result(args.input_dir.resolve(strict=True),authority,sha(authority_path)); output=attribute(result,authority)
        require(args.expected is not None,'--expected is mandatory'); require(output==load(args.expected.resolve(strict=True)),'terminal attribution differs from mandatory expected result')
        write_noreplace(Path(os.path.abspath(args.output)),canonical(output))
        print('sprint13-natural-terminal-attribution-v2-smoke: ok precedence_mutations=16 execution_outcomes=48 relation_outcomes=48 observations=36 cells=9 raw_streams=96 expected_required=1 run=complete'); return 0
    except (OSError,json.JSONDecodeError,UnicodeDecodeError,AttributionError) as exc: fail(str(exc))
if __name__=='__main__': raise SystemExit(main())
