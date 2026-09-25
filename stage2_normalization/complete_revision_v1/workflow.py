"""One complete-abstract revision, gated development evaluation; immutable old artifacts."""
import argparse, collections, concurrent.futures as cf, copy, datetime, hashlib, importlib.util, json, random, sys
from pathlib import Path
D=Path(__file__).resolve().parent; H=D.parent

def load_module(name,path):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
b=load_module('revision_backend',H/'full_audit_v1/pipeline.py'); b.D=D
mat=load_module('revision_materializer',H/'full_audit_v1/materialize.py')
read,write,sha=b.read,b.write,b.sha
BASE={p['paper_id']:p for p in read(H/'full_audit_v1/final/revised_all.json')}; SRC=b.SRC
S=b.S; arr=b.arr; obj=b.obj; enum=b.enum
FIELDS=['subject','subject_role','predicate','object','object_role','assertion','modality','conditions','joint_factors','scope','claim_scope','quote','context_quotes','modality_evidence']
PATCH_PROPS={k:dict(v) for k,v in b.BODY['properties'].items()}
for k,v in PATCH_PROPS.items(): PATCH_PROPS[k]={'anyOf':[v,{'type':'null'}]}
PATCH=obj(PATCH_PROPS)
SCHEMAS={
 'revision':obj(dict(papers=arr(obj(dict(paper_id=S,decisions=arr(obj(dict(relation_id=S,action=enum(['keep','patch','reject','uncertain']),patch={'anyOf':[PATCH,{'type':'null'}]},reason=S))),additions=arr(b.BODY),reextract={'type':'boolean'},reextract_reason=S))))),
 'reference':b.SCHEMAS['reference'],
 'evaluation':obj(dict(papers=arr(obj(dict(paper_id=S,judgments=arr(obj(dict(relation_id=S,verdict=enum(b.VERDICTS),issues=arr(S),reason=S))),coverage=arr(obj(dict(reference_id=S,validity=enum(['valid','uncertain','out_of_scope']),reason=S,versions=arr(obj(dict(version=S,coverage=enum(['complete','partial','missing']),match_ids=arr(S),reason=S)))))))))))
}
RULES=(H/'full_extraction_v1/PROMPT.md').read_text()+'''
Frozen interpretation for this development comparison: Concrete author-proposed applications are in scope as hypothesis; generic future promise is not. Explicit method-object or preparation-product relations are in measurement_method_model scope; a bare method/ingredient list is not a relation. Specific scientifically substantive background relations are allowed only when explicitly stated and marked background, never as own_work; generic topic/background introductions without a concrete relationship are excluded. This distinction applies equally to both versions and source references. Missing conditions are errors only if explicitly stated, meaning-bearing, and not already unambiguously bound in endpoints or other structured fields. Do not require duplicating qualifiers across fields. Mere presence in a quotation does not always bind sample/model/comparison to the structured claim. Default unspecified modality is valid unless explicit relationship-specific method information must be retained as a qualifier. No performance-number or modality completeness quota.
'''
PROMPTS={
 'revision':RULES+'''
TASK OVERRIDE: You receive the FULL original abstract (lossless numbered segments), ALL current records, and all endpoint IDs/names. Perform exactly ONE minimal revision pass, not fresh extraction. Review every existing relation_id exactly once: keep / patch / reject / uncertain. keep preserves correct content, patch changes only actual incorrect/missing fields, reject only clearly unsupported/out-of-scope/duplicate independent effects, uncertain only irreducible source ambiguity. No lengthy explanation; empty reason for keep. For patch, supply patch object with only changed fields non-null; null fields mean no change, empty strings/lists mean explicitly clear. For non-patch actions patch=null. e/me are source segment IDs and replace evidence lists only if needed. Preserve every old relation ID. Do not rewrite sound endpoints for style.
Bind material/sample, preparation vs measurement temperature, model assumptions, comparison and joint factors only to the relevant claim. Read the WHOLE abstract for ALL explicit uncovered in-scope relations, not an omission-hint list. Add only genuinely uncovered relationships, avoid duplicates and inferred intermediate/transitive mechanisms. Additions use BODY; program assigns new IDs. joint_factors uses readable labels, never opaque node IDs.
Mark reextract=true ONLY when referent/sample mixing or broad structural corruption makes local edits unable to recover faithful meaning; do not flag merely missing conditions or a few omitted relationships. When flagged, still dispose of each old ID conservatively, do not fabricate repairs; reason identifies structural fault. Corrupt/ambiguous abstract stays uncertain, not re-extraction. Return JSON only, no full copies of unchanged records.
''',
 'reference':RULES+'\nTASK: Build an independent source-only reference of explicit in-scope relationships, without any candidate results. Use the original compact extraction encoding. Human-readable joint factors, no opaque node IDs.\n',
 'evaluation':RULES+'''
TASK OVERRIDE: Independent blinded development assessment. Each paper has two anonymous versions and a FROZEN source reference. Version codes and relation IDs reveal no chronology. Evaluate every relation in both versions once. supported requires complete faithful meaning (all necessary qualifiers, assertion, scope, joint factors, endpoints and evidence). partial/unsupported/out_of_scope/uncertain are NOT strictly correct. Identical meaning-bearing content must receive consistent judgments across versions. Do not prefer longer or more elaborate records. Then evaluate every reference ID once: validity valid/uncertain/out_of_scope, and complete/partial/missing for EACH supplied version with matching IDs only from that version. Same reference validity for both; do not edit reference to reward a candidate. Claims may be covered across multiple records; a quote mentioning a claim does not automatically count as an extracted relation. Reasons concise, empty for supported/complete. Preserve reference disputes explicitly. No repairs, no access to former evaluations. Return JSON only.
'''}

def compact(r): return {k:r[k] for k in ['relation_id']+FIELDS}
def packet(pid): return b.packet(pid)
def nodes(p):
 ns={}
 for r in p['records']:
  for side in ['subject','object']:
   key=r[side+'_id']; val=dict(id=key,label=r[side],role=r[side+'_role'])
   ns.setdefault(key,[])
   if val not in ns[key]: ns[key].append(val)
 return [v for vs in ns.values() for v in vs]
def jobs(phase,items,size=4):
 out=[]; batch=[]
 for p in items:
  if batch and (len(batch)>=size or sum(len(json.dumps(x)) for x in batch)+len(json.dumps(p))>85000):
   out.append(batch); batch=[]
  batch.append(p)
 if batch: out.append(batch)
 js=[]
 for i,items in enumerate(out,1):
  jid=f'{phase}_{i:03}'; path=D/'jobs'/phase/(jid+'.json'); write(path,items); js.append(dict(id=jid,phase=phase,input_sha256=sha(path)))
 write(D/(phase+'_jobs.json'),js)
 return js

def prepare():
 assert not (D/'freeze.json').exists(), 'Already frozen'
 refs={}; ref_provenance={}
 for origin in ['full_audit_v1','post_revision_audit_v1']:
  for p in read(H/origin/'reference.json'):
   refs[p['paper_id']]=p; ref_provenance[p['paper_id']]=dict(path=str(H/origin/'reference.json'),sha256=sha(H/origin/'reference.json'))
 known=collections.defaultdict(set); bad=collections.defaultdict(list)
 oldbase=b.BASE
 for j in read(H/'full_audit_v1/precision_jobs.json'):
  for x in read(H/'full_audit_v1/runs'/j['id']/'response.json')['judgments']:
   pid=x['relation_id'].split(':')[0]; current={r['relation_id']:r for r in BASE[pid]['records']}; old={r['relation_id']:r for r in oldbase[pid]['records']}
   if x['verdict']=='supported' and x['relation_id'] in current and compact(current[x['relation_id']])==compact(old[x['relation_id']]):known[pid].add(x['relation_id'])
 for path in (H/'post_revision_audit_v1/runs').glob('precision_*/response.json'):
  for x in read(path)['judgments']:
   pid=x['relation_id'].split(':')[0]
   if x['verdict']=='supported':known[pid].add(x['relation_id'])
   else:bad[pid].append(x)
 selection=[]
 for domain in ['iTE','TG']:
  errors=[p for p in bad if BASE[p]['domain']==domain]
  errors.sort(key=lambda p:(-sum(bool(set(x['issues'])&{'conditions','scope','assertion','joint_factors'}) for x in bad[p]),-int(p in refs),p))
  chosen=errors[:10]; assert len(chosen)==10
  for p in chosen:selection.append(dict(paper_id=p,domain=domain,stratum='known_issue',issue_ids=[x['relation_id'] for x in bad[p]],known_correct_ids=sorted(known[p])))
  controls=[p for p in known if BASE[p]['domain']==domain and p not in chosen and p not in bad]
  controls.sort(key=lambda p:(-len(known[p]),-int(p in refs),p))
  assert len(controls)>=10
  for p in controls[:10]:selection.append(dict(paper_id=p,domain=domain,stratum='correct_relation_control',known_correct_ids=sorted(known[p])))
 write(D/'selection.json',selection)
 reused=[refs[x['paper_id']] for x in selection if x['paper_id'] in refs]; write(D/'reused_reference.json',reused)
 write(D/'reused_reference_provenance.json',{p['paper_id']:ref_provenance[p['paper_id']] for p in reused})
 for phase in SCHEMAS:
  write(D/(phase+'_schema.json'),SCHEMAS[phase]); (D/(phase+'_prompt.txt')).write_text(PROMPTS[phase])
 jobs('revision',[dict(**packet(x['paper_id']),nodes=nodes(BASE[x['paper_id']]),records=[dict(compact(r),subject_id=r['subject_id'],object_id=r['object_id']) for r in BASE[x['paper_id']]['records']]) for x in selection])
 jobs('reference',[packet(x['paper_id']) for x in selection if x['paper_id'] not in refs])
 sources=[H/'full_audit_v1/final/revised_all.json',H/'full_audit_v1/pipeline.py',H/'full_audit_v1/materialize.py',H/'full_extraction_v1/run.py',H/'full_extraction_v1/PROMPT.md',H/'modality_guard.py']+list((H/'full_extraction_v1/inputs').glob('*.json'))
 frozen=list(D.glob('*_prompt.txt'))+list(D.glob('*_schema.json'))+[D/'selection.json',D/'protocol.md',D/'reused_reference.json',D/'reused_reference_provenance.json']
 write(D/'freeze.json',dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),files={str(p):sha(p) for p in sources+frozen},baseline_papers=len(BASE),baseline_relations=sum(len(p['records']) for p in BASE.values()),gate=dict(strict_precision_each_domain=.90,no_correct_relation_harm=True,full_reference_coverage_nondecreasing=True)))
 print(json.dumps(dict(papers=len(selection),relations=sum(len(BASE[x['paper_id']]['records']) for x in selection),reused_references=len(reused),jobs={p:len(read(D/(p+'_jobs.json'))) for p in ['revision','reference']})))

def validate(phase,data,result):
 if phase=='reference': return b.ex.validate_expand([SRC[p['paper_id']] for p in data],result)
 expected={p['paper_id']:p for p in data}; got=[p['paper_id'] for p in result['papers']]; assert len(got)==len(set(got)) and set(got)==set(expected)
 for p in result['papers']:
  src=expected[p['paper_id']]
  if phase=='revision':
   ids=[x['relation_id'] for x in p['decisions']]; assert len(ids)==len(set(ids)) and set(ids)=={r['relation_id'] for r in src['records']}
   assert not p['reextract'] or p['reextract_reason'].strip()
   for x in p['decisions']:
    assert (x['action']=='patch')==(x['patch'] is not None)
    if x['patch'] is not None: assert any(v is not None for v in x['patch'].values())
   valid={s['id'] for s in SRC[p['paper_id']]['segments']}
   for body in p['additions']+[x['patch'] for x in p['decisions'] if x['patch']]:
    for k in ['e','me']:
     if body.get(k) is not None: assert set(body[k])<=valid and (k!='e' or body[k])
  elif phase=='evaluation':
   ids=[x['relation_id'] for x in p['judgments']]; assert len(ids)==len(set(ids)) and set(ids)=={r['relation_id'] for v in src['versions'] for r in v['records']}
   ids=[x['reference_id'] for x in p['coverage']]; assert len(ids)==len(set(ids)) and set(ids)=={r['relation_id'] for r in src['reference']}
   versions={v['version']:{r['relation_id'] for r in v['records']} for v in src['versions']}
   for c in p['coverage']:
    assert len(c['versions'])==len(versions) and {v['version'] for v in c['versions']}==set(versions)
    for v in c['versions']:
     assert set(v['match_ids'])<=versions[v['version']]
     assert v['coverage']!='missing' or not v['match_ids']
b.validate=validate

def check():
 for p,h in read(D/'freeze.json')['files'].items(): assert sha(Path(p))==h,p

def run(phases):
 check(); js=[j for phase in phases for j in read(D/(phase+'_jobs.json'))]; errors=[]
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  it=iter(js); active={}
  for _ in range(4):
   j=next(it,None)
   if j:active[pool.submit(b.run_job,j)]=j
  while active:
   done,_=cf.wait(active,return_when=cf.FIRST_COMPLETED)
   for f in done:
    j=active.pop(f)
    try:print(json.dumps(dict(event='complete',**f.result())),flush=True)
    except Exception as e:errors.append(dict(id=j['id'],error=str(e))); print(json.dumps(dict(event='failed',**errors[-1])),flush=True)
    if not errors:
     j=next(it,None)
     if j:active[pool.submit(b.run_job,j)]=j
 write(D/('errors_'+'_'.join(phases)+'.json'),errors)
 if errors:raise SystemExit(1)

def body_of(r,src):
 seg={s['text']:s['id'] for s in src['segments']}
 return dict(**{k:copy.deepcopy(r[k]) for k in b.BODY['properties'] if k not in ['e','me']},e=[seg[q] for q in [r['quote']]+r['context_quotes']],me=[seg[q] for q in r['modality_evidence']])

def materialize():
 check(); selected=[x['paper_id'] for x in read(D/'selection.json')]; out={pid:copy.deepcopy(BASE[pid]) for pid in selected}; logs=[]; rejected=[]; reextract=[]
 for j in read(D/'revision_jobs.json'):
  for p in read(D/'runs'/j['id']/'response.json')['papers']:
   pid=p['paper_id']; old={r['relation_id']:r for r in BASE[pid]['records']}; current={}; index=mat.node_index(BASE[pid])
   if p['reextract']:reextract.append(dict(paper_id=pid,reason=p['reextract_reason']))
   for x in p['decisions']:
    rid=x['relation_id']; before=old[rid]; after=copy.deepcopy(before); action=x['action']
    if action=='patch':
     body=body_of(before,SRC[pid]); body.update({k:v for k,v in x['patch'].items() if v is not None}); after,alerts=mat.expand(body,SRC[pid],rid,before['id'],index,before)
     for side in ['subject','object']:
      if (after[side],after[side+'_role'])!=(before[side],before[side+'_role']):after[side+'_id']=f'{pid}:complete_v1_{before["id"]}_{side}'
     for k,v in before.items():
      if k not in after:after[k]=copy.deepcopy(v)
     after['note']=''
     if x['patch'].get('e') is None:
      for k in ['quote','context_quotes','evidence_spans']:after[k]=copy.deepcopy(before[k])
     if x['patch'].get('me') is None and after['modality']==before['modality']:
      for k in ['modality_evidence','modality_spans']:after[k]=copy.deepcopy(before[k])
    if action=='reject':rejected.append(dict(paper_id=pid,relation_id=rid,record=before,reason=x['reason']));after=None
    else:
     if action in ['keep','patch']:after['status']='accepted'
     if action=='uncertain':after['status']='uncertain'
     after['review_status']='complete_abstract_revision_v1_not_independent_acceptance'; after['decision_source']=dict(run='complete_revision_v1',job=j['id'],action=action)
     current[rid]=after
    logs.append(dict(paper_id=pid,relation_id=rid,action=action,changes={k:dict(before=before.get(k),after=after.get(k)) for k in set(before)|set(after) if before.get(k)!=after.get(k)} if after else {},reason=x['reason']))
   for i,body in enumerate(p['additions'],1):
    short=f'cr{i:03}'; rid=f'{pid}:complete_v1_{short}'; assert rid not in old and rid not in current
    after,alerts=mat.expand(body,SRC[pid],rid,short,index)
    for side in ['subject','object']:
     if ':audit_v1_' in after[side+'_id']:after[side+'_id']=after[side+'_id'].replace(':audit_v1_',':complete_v1_')
    after.update(note='',review_status='complete_abstract_revision_v1_not_independent_acceptance',decision_source=dict(run='complete_revision_v1',job=j['id'],action='add'))
    assert not any(all(after[k]==r[k] for k in FIELDS) for r in current.values()),'Exact duplicate addition'
    current[rid]=after; logs.append(dict(paper_id=pid,relation_id=rid,action='add',record=after))
   out[pid]['records']=list(current.values())
 for p in out.values():
  for r in p['records']:
   for q,span in zip([r['quote']]+r['context_quotes'],r['evidence_spans']):assert SRC[p['paper_id']]['abstract'][span['start']:span['end']]==q
 write(D/'development_revised.json',list(out.values())); write(D/'change_log.json',logs);write(D/'rejected.json',rejected);write(D/'reextract_queue.json',reextract)
 write(D/'uncertain.json',[dict(paper_id=p['paper_id'],record=r) for p in out.values() for r in p['records'] if r['status']=='uncertain'])
 refs=read(D/'reused_reference.json')
 for j in read(D/'reference_jobs.json'):
  raw=read(D/'runs'/j['id']/'response.json'); ps=read(D/'jobs/reference'/(j['id']+'.json')); expanded,_=b.ex.validate_expand([SRC[p['paper_id']] for p in ps],raw)
  for p in expanded:
   labels={n['id']:n['label'] for rr in raw['papers'] if rr['paper_id']==p['paper_id'] for n in rr['nodes']}
   for r in p['records']:r['joint_factors']=[labels.get(v,v) for v in r['joint_factors']];r['relation_id']=p['paper_id']+':g'+r['id'][1:]
  refs+=expanded
 assert len(refs)==40 and len({p['paper_id'] for p in refs})==40
 write(D/'reference.json',refs); write(D/'reference_freeze.json',dict(sha256=sha(D/'reference.json'),sources={j['id']:sha(D/'runs'/j['id']/'response.json') for j in read(D/'reference_jobs.json')}))
 print(json.dumps(dict(actions=dict(collections.Counter(x['action'] for x in logs)),reextract=reextract)))

def evaluate_prepare():
 assert not read(D/'reextract_queue.json'),'Structural re-extractions must finish before evaluation'
 refs={p['paper_id']:p for p in read(D/'reference.json')}; new={p['paper_id']:p for p in read(D/'development_revised.json')}; rng=random.Random(2026092504); items=[]; decode={}
 for pid in new:
  versions=[]; order=['old','new'];rng.shuffle(order); mapping={}
  for i,version in enumerate(order):
   code=['A','B'][i]; mapping[code]=version; rs=[]
   for n,r in enumerate((BASE if version=='old' else new)[pid]['records'],1):
    x=compact(r); opaque=f'{pid}:{code}:{n:03}';decode[opaque]=dict(paper_id=pid,version=version,relation_id=r['relation_id']);x['relation_id']=opaque;rs.append(x)
   rng.shuffle(rs);versions.append(dict(version=code,records=rs))
  decode[pid]=mapping;items.append(dict(**packet(pid),versions=versions,reference=[compact(r) for r in refs[pid]['records']]))
 write(D/'blind_key.json',decode);jobs('evaluation',items,2);write(D/'evaluation_freeze.json',dict(reference_sha256=sha(D/'reference.json'),revised_sha256=sha(D/'development_revised.json'),blind_key_sha256=sha(D/'blind_key.json')))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run','materialize','evaluate']);ap.add_argument('--phases',nargs='+',default=['revision','reference']);a=ap.parse_args()
 {'prepare':prepare,'materialize':materialize,'evaluate':evaluate_prepare,'run':lambda:run(a.phases)}[a.action]()
