"""Single-pass corpus expansion of the frozen 40-paper revision workflow."""
import argparse,collections,concurrent.futures as cf,copy,datetime,hashlib,importlib.util,json,os,random,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent;DEV=H/'complete_revision_v1'
spec=importlib.util.spec_from_file_location('frozen_revision_workflow',DEV/'workflow.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
b=w.b;b.D=D;w.D=D
read,sha=b.read,b.sha;BASE=w.BASE;SRC=w.SRC

def write(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,path)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save_new(path,data):
 if path.exists():assert read(path)==data,'Refusing overwrite: '+str(path)
 else:write(path,data)

def histories():
 result={}
 paths=[H/'full_audit_v1/historical_exclusions.json']+list(H.glob('*/contacted_papers.json'))
 for p in paths:
  if p.parent==D:continue
  x=read(p);ids=x if isinstance(x,list) else x.get('paper_ids',[])
  if ids and all(isinstance(i,str) for i in ids):result[str(p.relative_to(H))]=set(ids)
 return result

def prepare():
 assert not (D/'freeze.json').exists(),'Already prepared'
 dev=read(DEV/'development_revised.json');dev_ids={p['paper_id'] for p in dev};assert len(dev_ids)==40
 assert len(BASE)==1971 and sum(len(p['records']) for p in BASE.values())==21115
 remaining=sorted(set(BASE)-dev_ids);assert len(remaining)==1931
 for pid in BASE:assert ''.join(s['text'] for s in SRC[pid]['segments'])==SRC[pid]['abstract']
 for phase in ['revision','reference']:
  (D/(phase+'_prompt.txt')).write_bytes((DEV/(phase+'_prompt.txt')).read_bytes());(D/(phase+'_schema.json')).write_bytes((DEV/(phase+'_schema.json')).read_bytes())
 items=[dict(**w.packet(pid),nodes=w.nodes(BASE[pid]),records=[dict(w.compact(r),subject_id=r['subject_id'],object_id=r['object_id']) for r in BASE[pid]['records']]) for pid in remaining]
 jobs=w.jobs('revision',items,4)
 assert {p['paper_id'] for j in jobs for p in read(D/'jobs/revision'/(j['id']+'.json'))}==set(remaining)
 hist=histories();doi=lambda p:SRC[p].get('doi','').strip().lower();dev_dois={doi(p) for p in dev_ids if doi(p)}
 exclude=dev_ids|{p for p in BASE if doi(p) and doi(p) in dev_dois}
 rng=random.Random(2026092508);recall=[]
 for domain in ['iTE','TG']:
  groups=collections.defaultdict(list)
  for pid in BASE:
   if pid not in exclude and BASE[pid]['domain']==domain:groups[b.year(pid)].append(pid)
  recall.extend(dict(domain=domain,**x,history=[k for k,v in hist.items() if x['id'] in v]) for x in b.allocate(groups,30,rng))
 save_new(D/'acceptance_reservation.json',dict(seed=2026092508,excluded_paper_ids=sorted(exclude),excluded_reason='40 development papers and matching nonempty DOI partners',recall=recall,precision_seed=2026092509,precision_rule='After final revision sample 100 accepted relations/domain by year x core/peripheral x evidence complexity, N/n weights; exclude development/DOI partners.',rejection_rule='Audit all rejected original relations if <=200; otherwise up to100/domain stratified by year, weighted N/n. Never repair using acceptance feedback.',history={k:sorted(v) for k,v in hist.items()},historical_exposure_is_not_independent_gold=True))
 w.jobs('reference',[w.packet(x['id']) for x in recall],4)
 save_new(D/'expansion_decision.json',dict(date=now(),user_authorization='那全库推进一下',basis='Same-ID 411/411 supported claims remained supported, 64 partial claims became supported, 74/78 additions supported, coverage improved in both domains; user explicitly authorized expansion after the denominator discussion.',original_development_gate_result_preserved=True,development_scores_sha256=sha(DEV/'development_scores.json'),development_prompt_sha256=sha(DEV/'revision_prompt.txt'),reused_papers=sorted(dev_ids),new_papers=remaining,each_paper_one_revision=True))
 sources=[H/'full_audit_v1/final/revised_all.json',DEV/'workflow.py',DEV/'development_revised.json',DEV/'change_log.json',DEV/'rejected.json',DEV/'reextract_queue.json',DEV/'description_changes.json',DEV/'concepts_description_revised.json',H/'full_audit_v1/pipeline.py',H/'full_audit_v1/materialize.py',H/'full_extraction_v1/run.py',H/'modality_guard.py',H/'initial_graph_v1/concepts.json',H/'initial_graph_v1/node_mapping.json']+list((H/'full_extraction_v1/inputs').glob('*.json'))
 sources += [D/'corpus.py',D/'protocol.md',D/'acceptance_reservation.json',D/'expansion_decision.json']+list(D.glob('*_prompt.txt'))+list(D.glob('*_schema.json'))+list(D.glob('*_jobs.json'))
 write(D/'freeze.json',dict(created_at=now(),model='gpt-6-astra',reasoning='medium',max_workers=4,files={str(p):sha(p) for p in sources}))
 write(D/'progress.json',dict(stage='prepared',completed_new_papers=0,reused_papers=40,total_papers=1971,revision_jobs=len(jobs),completed_jobs=0,failures=[],updated_at=now()))
 print(json.dumps(dict(new_papers=len(remaining),reused=40,jobs=len(jobs),reference_jobs=len(read(D/'reference_jobs.json')))),flush=True)

def check():
 for p,h in read(D/'freeze.json')['files'].items():assert sha(Path(p))==h,p

def materialize_paper(result,job_id):
 pid=result['paper_id'];src=SRC[pid];paper=copy.deepcopy(BASE[pid]);original={r['relation_id']:r for r in paper['records']};current={};index=w.mat.node_index(paper);logs=[];rejected=[];alerts=[];duplicates=[]
 for x in result['decisions']:
  rid=x['relation_id'];before=original[rid];after=copy.deepcopy(before);action=x['action']
  if action=='patch':
   body=w.body_of(before,src);body.update({k:v for k,v in x['patch'].items() if v is not None});after,a=w.mat.expand(body,src,rid,before['id'],index,before);alerts+=a
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
   after['status']='uncertain' if action=='uncertain' else 'accepted'
   after['review_status']='complete_abstract_revision_v1_not_independent_acceptance';after['decision_source']=dict(run='complete_revision_full_v1',job=job_id,action=action)
   current[rid]=after
  logs.append(dict(paper_id=pid,relation_id=rid,action=action,reason=x['reason'],changes={k:dict(before=before.get(k),after=after.get(k)) for k in set(before)|set(after) if before.get(k)!=after.get(k)} if after else {},original=before if after is None else None))
 for i,body in enumerate(result['additions'],1):
  short=f'cr{i:03}';rid=f'{pid}:complete_v1_{short}';assert rid not in original and rid not in current
  after,a=w.mat.expand(body,src,rid,short,index);alerts+=a
  for side in ['subject','object']:
   if ':audit_v1_' in after[side+'_id']:after[side+'_id']=after[side+'_id'].replace(':audit_v1_',':complete_v1_')
  exact=[r['relation_id'] for r in current.values() if all(after[k]==r[k] for k in w.FIELDS)]
  if exact:duplicates.append(dict(proposed_relation_id=rid,identical_to=exact,body=body,disposition='exact_duplicate_addition_not_materialized'));continue
  after.update(note='',review_status='complete_abstract_revision_v1_not_independent_acceptance',decision_source=dict(run='complete_revision_full_v1',job=job_id,action='add'))
  current[rid]=after;logs.append(dict(paper_id=pid,relation_id=rid,action='add',record=after))
 paper['records']=list(current.values());paper['review_status']='complete_abstract_revision_v1_not_independent_acceptance'
 # Mechanical protection: one node ID cannot represent two different label/role pairs.
 node_labels=collections.defaultdict(set)
 for r in paper['records']:
  for side in ['subject','object']:node_labels[r[side+'_id']].add((r[side],r[side+'_role']))
 for r in paper['records']:
  for side in ['subject','object']:
   old=r[side+'_id']
   if len(node_labels[old])>1:
    suffix=hashlib.sha256((r[side]+'\0'+r[side+'_role']).encode()).hexdigest()[:10];new=f'{pid}:complete_v1_disambiguated_{suffix}'
    # Keep original unchanged label ID whenever the old baseline unambiguously fixes that label.
    original_pairs={(rr[s],rr[s+'_role']) for rr in original.values() for s in ['subject','object'] if rr[s+'_id']==old}
    if original_pairs=={(r[side],r[side+'_role'])}:continue
    r[side+'_id']=new;alerts.append(dict(paper_id=pid,relation_id=r['relation_id'],side=side,old_id=old,new_id=new,reason='Mechanical separation of conflicting label/role reuse; new endpoint requires mapping review.'))
  for quotes,spans in [([r['quote']]+r['context_quotes'],r['evidence_spans']),(r['modality_evidence'],r['modality_spans'])]:
   assert len(quotes)==len(spans)
   for q,s in zip(quotes,spans):assert src['abstract'][s['start']:s['end']]==q
 # Refresh changed/new payloads after any mechanical ID disambiguation.
 for x in logs:
  rid=x['relation_id']
  if rid not in current:continue
  if x['action']=='add':x['record']=copy.deepcopy(current[rid])
  else:x['changes']={k:dict(before=original[rid].get(k),after=current[rid].get(k)) for k in set(original[rid])|set(current[rid]) if original[rid].get(k)!=current[rid].get(k)}
 assert {x['relation_id'] for x in logs if x['action']!='add'}==set(original)
 return dict(paper=paper,change_log=logs,rejected=rejected,alerts=alerts,duplicate_additions=duplicates,reextract=dict(paper_id=pid,reason=result['reextract_reason']) if result['reextract'] else None)

def run_job(job):
 result=b.run_job(job)
 if job['phase']=='revision':
  path=D/'runs'/job['id']/'materialized.json';raw=read(path.parent/'response.json')
  value=[materialize_paper(p,job['id']) for p in raw['papers']];save_new(path,value)
 return result

def run(phases):
 check();jobs=[j for ph in phases for j in read(D/(ph+'_jobs.json'))];errors=[];done=[];start=time.monotonic()
 # Reuse validated successful work without a new model invocation.
 pending=[]
 for j in jobs:
  if (D/'runs'/j['id']/'SUCCESS.json').exists():done.append(run_job(j))
  else:pending.append(j)
 def progress(active):
  newpapers=sum(len(read(D/'jobs/revision'/(r['id']+'.json'))) for r in done if r.get('phase','revision')=='revision' or r['id'].startswith('revision_'))
  write(D/'progress.json',dict(stage='running' if active else ('stopped_on_error' if errors else 'phase_complete'),phases=phases,completed_jobs=len(done),total_jobs=len(jobs),active_job_ids=[j['id'] for j in active.values()],completed_new_papers=newpapers,reused_papers=40,total_papers=1971,failures=errors,elapsed_seconds=round(time.monotonic()-start,1),updated_at=now()))
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  it=iter(pending);active={}
  for _ in range(4):
   j=next(it,None)
   if j:active[pool.submit(run_job,j)]=j
  progress(active)
  while active:
   ready,_=cf.wait(active,timeout=30,return_when=cf.FIRST_COMPLETED)
   completed=[]
   for f in ready:
    j=active.pop(f)
    try:r=f.result();done.append(r);completed.append(r);print(json.dumps(dict(event='complete',**r)),flush=True)
    except Exception as e:errors.append(dict(id=j['id'],error=str(e)));print(json.dumps(dict(event='failed',**errors[-1])),flush=True)
   # Stop new dispatch after ANY failure; other inflight calls may safely finish.
   if not errors:
    for _ in completed:
     j=next(it,None)
     if j:active[pool.submit(run_job,j)]=j
   progress(active)
 write(D/('errors_'+'_'.join(phases)+'.json'),errors)
 if errors:raise SystemExit(1)

def aggregate():
 check();papers=read(DEV/'development_revised.json');logs=read(DEV/'change_log.json');rejected=read(DEV/'rejected.json');queue=read(DEV/'reextract_queue.json');alerts=[];dups=[];seen={p['paper_id'] for p in papers}
 for j in read(D/'revision_jobs.json'):
  success=read(D/'runs'/j['id']/'SUCCESS.json');assert sha(D/'runs'/j['id']/'response.json')==success['response_sha256']
  for result in read(D/'runs'/j['id']/'materialized.json'):
   pid=result['paper']['paper_id'];assert pid not in seen;seen.add(pid);papers.append(result['paper']);logs+=result['change_log'];rejected+=result['rejected'];alerts+=result['alerts'];dups+=result['duplicate_additions']
   if result['reextract']:queue.append(result['reextract'])
 assert seen==set(BASE) and len(papers)==1971
 original_ids={r['relation_id'] for p in BASE.values() for r in p['records']};oldlogs=[x['relation_id'] for x in logs if x['action']!='add'];assert len(oldlogs)==len(set(oldlogs)) and set(oldlogs)==original_ids
 allids=[r['relation_id'] for p in papers for r in p['records']];assert len(allids)==len(set(allids))
 for name,value in {'revised_all.json':sorted(papers,key=lambda p:p['paper_id']),'change_log.json':logs,'rejected.json':rejected,'reextract_queue.json':queue,'uncertain.json':[dict(paper_id=p['paper_id'],record=r) for p in papers for r in p['records'] if r['status']=='uncertain'],'mechanical_alerts.json':alerts,'duplicate_additions.json':dups}.items():save_new(D/'revision_output'/name,value)
 write(D/'revision_summary.json',dict(papers=len(papers),reused_papers=40,new_papers=1931,old_relations=len(original_ids),new_relations=len(allids),actions=dict(collections.Counter(x['action'] for x in logs)),reextract_papers=len(queue),uncertain_relations=sum(r['status']=='uncertain' for p in papers for r in p['records']),semantic_acceptance=False))
 print(json.dumps(read(D/'revision_summary.json')),flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run','aggregate']);ap.add_argument('--phases',nargs='+',default=['revision']);a=ap.parse_args();{'prepare':prepare,'run':lambda:run(a.phases),'aggregate':aggregate}[a.action]()
