"""Held-out acceptance with frozen source-only references and design-weighted scoring."""
import argparse,collections,concurrent.futures as cf,copy,hashlib,importlib.util,json,random,time
from pathlib import Path
D=Path(__file__).resolve().parent;A=D/'acceptance';H=D.parent
s=importlib.util.spec_from_file_location('corpus_for_acceptance',D/'corpus.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
w,b=c.w,c.b;read,write,sha=c.read,c.write,c.sha
b.D=A;w.D=A
SOURCE=D/'final/revised_all.json'
S=b.S;obj=b.obj;arr=b.arr;enum=b.enum
SCHEMA={p:b.SCHEMAS[p] for p in ['precision','reference','coverage']}
SCHEMA['rejections']=obj(dict(judgments=arr(obj(dict(relation_id=S,verdict=enum(['correct_rejection','incorrect_rejection','uncertain']),retained_equivalent_ids=arr(S),reason=S)))))
PROMPTS={p:w.RULES+'\n'+b.PROMPTS[p] for p in ['precision','coverage']}
PROMPTS['reference']=w.PROMPTS['reference']
PROMPTS['rejections']=w.RULES+'''
TASK: Independently assess exclusion of each target OLD relation using full abstract and current retained records. No old reviewer reason is provided. correct_rejection means clearly unsupported/out_of_scope OR a true duplicate whose FULL meaning remains in a current accepted relationship; provide retained_equivalent_ids for the latter. A merely incomplete but supported relationship requiring a local correction is not a justified deletion if its meaning is now lost: incorrect_rejection. An explicit in-scope author hypothesis must not be rejected just because it is not an observed result. Source ambiguity is uncertain. Return every target ID once; do not alter any records or reference. Do not assume current accepted labels prove correctness.\n'''

def prepare():
 c.check();assert SOURCE.exists();assert not (A/'freeze.json').exists()
 data=read(SOURCE);base={p['paper_id']:p for p in data};reserved=read(D/'acceptance_reservation.json');excluded=set(reserved['excluded_paper_ids']);rng=random.Random(reserved['precision_seed']);picks=[]
 for domain in ['iTE','TG']:
  gs=collections.defaultdict(list)
  for p in data:
   if p['domain']!=domain or p['paper_id'] in excluded:continue
   for r in p['records']:
    if r['status']=='accepted':gs['|'.join([b.year(p['paper_id']),'core' if r['scope'] in b.CORE else 'peripheral','complex' if b.complex_r(r) else 'simple'])].append(r['relation_id'])
  picks.extend(dict(domain=domain,**x) for x in b.allocate(gs,100,rng))
 selection=dict(precision=picks,recall=reserved['recall'],challenge=[],excluded_count=len(excluded));write(A/'selection.json',selection)
 rels={r['relation_id']:(p['paper_id'],r) for p in data for r in p['records']}
 for phase in SCHEMA:
  write(A/(phase+'_schema.json'),SCHEMA[phase]);(A/(phase+'_prompt.txt')).write_text(PROMPTS[phase])
 bypaper=collections.defaultdict(list)
 for x in picks:
  pid,r=rels[x['id']];bypaper[pid].append(w.compact(r))
 w.jobs('precision',[dict(**w.packet(pid),targets=rs) for pid,rs in sorted(bypaper.items())],8)
 w.jobs('reference',[w.packet(x['id']) for x in reserved['recall']],4)
 rejected=read(D/'final/rejected.json');chosen=[]
 for domain in ['iTE','TG']:
  pool=[r for r in rejected if base[r['paper_id']]['domain']==domain]
  if not pool:continue
  gs=collections.defaultdict(list)
  for r in pool:gs[b.year(r['paper_id'])].append(r['relation_id'])
  n=len(pool) if len(rejected)<=200 else min(100,len(pool))
  chosen.extend(dict(domain=domain,**x) for x in b.allocate(gs,n,rng))
 write(A/'rejection_selection.json',chosen);rejectedmap={r['relation_id']:r for r in rejected};bp=collections.defaultdict(list)
 for x in chosen:
  r=rejectedmap[x['id']];bp[r['paper_id']].append(w.compact(r.get('record',r.get('original'))))
 w.jobs('rejections',[dict(**w.packet(pid),targets=rs,current_records=[w.compact(r) for r in base[pid]['records'] if r['status']=='accepted']) for pid,rs in sorted(bp.items())],4)
 # Expose historical contact per selected paper, not just the recall selection.
 ids=set(bypaper)|{x['id'] for x in reserved['recall']}|set(bp)
 write(A/'contacted_papers.json',dict(paper_ids=sorted(ids),history={pid:[name for name,pids in reserved['history'].items() if pid in pids] for pid in sorted(ids)},note='All papers underwent original extraction and current production revision; excluded from current rule development, not necessarily historically untouched.'))
 files=[SOURCE,D/'final/rejected.json',D/'acceptance_reservation.json',Path(__file__)]+list(A.glob('*_prompt.txt'))+list(A.glob('*_schema.json'))+list(A.glob('*_jobs.json'))+[A/'selection.json',A/'rejection_selection.json']
 write(A/'freeze.json',dict(created_at=c.now(),files={str(p):sha(p) for p in files}));print(json.dumps({p:len(read(A/(p+'_jobs.json'))) for p in ['precision','reference','rejections']}),flush=True)

def validate(phase,data,result):
 if phase=='reference':b.ex.validate_expand([c.SRC[p['paper_id']] for p in data],result);return
 if phase in ['precision','rejections']:
  expected={r['relation_id'] for p in data for r in p['targets']};ids=[j['relation_id'] for j in result['judgments']];assert len(ids)==len(set(ids)) and set(ids)==expected
  if phase=='rejections':
   lookup={r['relation_id']:{x['relation_id'] for x in p['current_records']} for p in data for r in p['targets']}
   for j in result['judgments']:assert set(j['retained_equivalent_ids'])<=lookup[j['relation_id']]
  return
 src={p['paper_id']:p for p in data};ids=[p['paper_id'] for p in result['papers']];assert len(ids)==len(set(ids)) and set(ids)==set(src)
 for p in result['papers']:
  x=src[p['paper_id']];ids=[c['reference_id'] for c in p['coverage']];assert len(ids)==len(set(ids)) and set(ids)=={r['relation_id'] for r in x['reference']}
  for row in p['coverage']:
   assert set(row['match_ids'])<={r['relation_id'] for r in x['candidates']};assert (row['coverage']=='missing')==(not row['match_ids'])
b.validate=validate

def check():
 for p,h in read(A/'freeze.json')['files'].items():assert sha(Path(p))==h,p

def run(phases):
 check();jobs=[j for phase in phases for j in read(A/(phase+'_jobs.json'))];errors=[];done=[];limit=min(12,read(D/'runtime_control.json')['workers'])
 with cf.ThreadPoolExecutor(max_workers=limit) as pool:
  it=iter(jobs);active={}
  for _ in range(limit):
   j=next(it,None)
   if j:active[pool.submit(b.run_job,j)]=j
  while active:
   ready,_=cf.wait(active,timeout=30,return_when=cf.FIRST_COMPLETED)
   n=0
   for f in ready:
    j=active.pop(f)
    try:r=f.result();done.append(r);n+=1;print(json.dumps(dict(event='complete',**r)),flush=True)
    except Exception as e:errors.append(dict(id=j['id'],error=str(e)))
   if not errors:
    for _ in range(n):
     j=next(it,None)
     if j:active[pool.submit(b.run_job,j)]=j
   write(A/'progress.json',dict(phases=phases,completed=len(done),total=len(jobs),active=[j['id'] for j in active.values()],errors=errors,updated_at=c.now()))
 write(A/('errors_'+'_'.join(phases)+'.json'),errors)
 if errors:raise SystemExit(1)

def coverage():
 check();assert not (A/'reference_freeze.json').exists();refs=[]
 for j in read(A/'reference_jobs.json'):
  raw=read(A/'runs'/j['id']/'response.json');pack=read(A/'jobs/reference'/(j['id']+'.json'));ps,_=b.ex.validate_expand([c.SRC[p['paper_id']] for p in pack],raw)
  for p in ps:
   labels={n['id']:n['label'] for rr in raw['papers'] if rr['paper_id']==p['paper_id'] for n in rr['nodes']}
   for r in p['records']:r['relation_id']=p['paper_id']+':g'+r['id'][1:];r['joint_factors']=[labels.get(v,v) for v in r['joint_factors']]
  refs+=ps
 write(A/'reference.json',refs);base={p['paper_id']:p for p in read(SOURCE)}
 w.jobs('coverage',[dict(**w.packet(p['paper_id']),reference=[w.compact(r) for r in p['records']],candidates=[w.compact(r) for r in base[p['paper_id']]['records'] if r['status']=='accepted']) for p in refs],4)
 write(A/'reference_freeze.json',dict(sha256=sha(A/'reference.json'),source_responses={j['id']:sha(A/'runs'/j['id']/'response.json') for j in read(A/'reference_jobs.json')}))

def score():
 check();assert sha(A/'reference.json')==read(A/'reference_freeze.json')['sha256']
 for phase in ['reference','precision','coverage','rejections']:
  for j in read(A/(phase+'_jobs.json')):
   root=A/'runs'/j['id'];meta=read(root/'SUCCESS.json');inp=A/'jobs'/phase/(j['id']+'.json')
   assert sha(root/'response.json')==meta['response_sha256'];assert sha(inp)==j['input_sha256']==meta['input_sha256']
   validate(phase,read(inp),read(root/'response.json'))
 s=importlib.util.spec_from_file_location('existing_audit_statistics',H/'full_audit_v1/score.py');stats=importlib.util.module_from_spec(s);s.loader.exec_module(stats)
 judgments=[r for j in read(A/'precision_jobs.json') for r in read(A/'runs'/j['id']/'response.json')['judgments']];cov=[p for j in read(A/'coverage_jobs.json') for p in read(A/'runs'/j['id']/'response.json')['papers']]
 base=read(SOURCE)
 for p in base:p['records']=[r for r in p['records'] if r['status']=='accepted']
 result=stats.compute(read(A/'selection.json'),base,read(A/'reference.json'),judgments,cov,set(read(D/'acceptance_reservation.json')['excluded_paper_ids']),repetitions=2000,enforce_sizes=False)
 result.pop('excluded_historical_papers',None)
 result.update(baseline=str(SOURCE),baseline_sha256=sha(SOURCE),excluded_current_development_papers=len(read(D/'acceptance_reservation.json')['excluded_paper_ids']),inference_population='Accepted relations and papers outside current 40-paper development set and matching DOI partners; historical exposure is recorded, not assumed absent. Not a guarantee for all 1,971 papers.',semantic_authority='Independent Astra contexts for reference and judgments; model acceptance, not human or external gold standard.')
 write(A/'scores.json',result);write(A/'precision_judgments.json',judgments);write(A/'coverage_judgments.json',cov)
 rejection=[x for j in read(A/'rejections_jobs.json') for x in read(A/'runs'/j['id']/'response.json')['judgments']];sel=read(A/'rejection_selection.json');jm={x['relation_id']:x for x in rejection};rs={}
 for domain in ['iTE','TG']:
  rows=[x for x in sel if x['domain']==domain];den=sum(x['weight'] for x in rows);num=sum(x['weight'] for x in rows if jm[x['id']]['verdict']=='correct_rejection');rs[domain]=dict(sampled=len(rows),verdict_counts=dict(collections.Counter(jm[x['id']]['verdict'] for x in rows)),weighted_correct=num,weighted_total=den,weighted_rate=num/den if den else None)
 write(A/'rejection_judgments.json',rejection);write(A/'rejection_scores.json',rs);print(json.dumps(result,ensure_ascii=False)[:18000],flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run','coverage','score']);ap.add_argument('--phases',nargs='+',default=['reference','precision','rejections']);a=ap.parse_args();{'prepare':prepare,'run':lambda:run(a.phases),'coverage':coverage,'score':score}[a.action]()
