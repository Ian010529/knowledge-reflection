"""Compute source-audited metrics from explicit blind Astra judgments only."""
import json,hashlib,random,collections,math,datetime
from pathlib import Path
D=Path(__file__).resolve().parent
MAIN={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics'}
def load(n):return json.loads((D/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x):(D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def quantile(xs,q):
 xs=sorted(xs)
 if not xs:return None
 k=(len(xs)-1)*q;l=int(k);u=min(l+1,len(xs)-1)
 return xs[l]*(u-k)+xs[u]*(k-l) if u!=l else xs[l]
def ratio(a,b):return a/b if b else None
P={p['paper_id']:p for p in load('input_papers.json')}
for name,h in load('input_freeze.json').items():assert sha(D/name)==h,name
for name,h in load('blind_freeze.json')['files'].items():assert sha(D/name)==h,name
for name,h in load('selection.json')['source_hashes'].items():assert sha(D.parents[1]/name)==h,name
KEY=load('private/version_key.json');all_metrics=[];all_residual=[];all_disputed=[];all_lost=[];blind_counts={};bootstrap={}
for domain,judge_dir in [('iTE','judge_ite'),('TG','judge_tg')]:
 packet=load(f'blind/{domain}.json');papers={p['paper_id']:p for p in packet}
 judges=load(f'work/{judge_dir}/judgments.json');assert len(judges)==len(papers)==30
 assert {j['paper_id'] for j in judges}==set(papers)
 candidates={c['candidate_id']:c for p in packet for c in p['candidates']}
 references={r['reference_id']:r for p in packet for r in p['references']}
 labels={};ref_labels={};ref_pid={}
 for j in judges:
  pid=j['paper_id'];p=papers[pid]
  assert len({c['candidate_id'] for c in j['candidates']})==len(j['candidates'])
  assert {c['candidate_id'] for c in j['candidates']}=={c['candidate_id'] for c in p['candidates']},pid
  assert len({r['reference_id'] for r in j['references']})==len(j['references'])
  assert {r['reference_id'] for r in j['references']}=={r['reference_id'] for r in p['references']},pid
  for c in j['candidates']:
   assert c['label'] in {'supported','partial','unsupported','uncertain','out_of_scope'}
   assert c['reason'] and isinstance(c['error_tags'],list)
   labels[c['candidate_id']]=c
  for r in j['references']:
   assert r['label'] in {'valid','uncertain','out_of_scope'} and r['reason']
   for group in r['full_coverage_sets']:
    assert group and len(set(group))==len(group)
    assert set(group)<={c['candidate_id'] for c in p['candidates']}
    assert all(labels[c]['label'] in {'supported','partial'} for c in group),(pid,r)
   assert set(r['partial_candidates'])<={c['candidate_id'] for c in p['candidates']}
   if r['label']!='valid':assert not r['full_coverage_sets'],r
   ref_labels[r['reference_id']]=r;ref_pid[r['reference_id']]=pid
 available={v:{x['candidate_id'] for x in KEY[domain] if x['version']==v} for v in ['initial','reviewed']}
 def covered(rid,ver):
  r=ref_labels[rid]
  return r['label']=='valid' and any(set(s)<=available[ver] for s in r['full_coverage_sets'])
 for rid,r in ref_labels.items():
  if r['label']!='valid':all_disputed.append(dict(domain=domain,paper_id=ref_pid[rid],reference=references[rid],judgment=r))
  elif not covered(rid,'reviewed'):all_residual.append(dict(domain=domain,paper_id=ref_pid[rid],reference=references[rid],judgment=r,initial_covered=covered(rid,'initial')))
  if covered(rid,'initial') and not covered(rid,'reviewed'):all_lost.append(dict(domain=domain,paper_id=ref_pid[rid],reference_id=rid,reference=references[rid]))
 perpaper={}
 for scope in ['all','main']:
  for ver in ['initial','reviewed']:
   counter={pid:dict(audit_good=0,audit_n=0,all_good=0,all_n=0,ref_covered=0,ref_valid=0,ref_uncertain=0,ref_total=0) for pid in papers}
   for row in KEY[domain]:
    if row['version']!=ver:continue
    cid=row['candidate_id'];pid=row['paper_id'];c=candidates[cid]
    if scope=='main' and c['scope'] not in MAIN:continue
    z=counter[pid];good=int(labels[cid]['label']=='supported');z['all_good']+=good;z['all_n']+=1
    if row['audit_selected']:z['audit_good']+=good;z['audit_n']+=1
   for rid,r in ref_labels.items():
    if scope=='main' and references[rid]['scope'] not in MAIN:continue
    z=counter[ref_pid[rid]];z['ref_total']+=1;z['ref_valid']+=r['label']=='valid';z['ref_uncertain']+=r['label']=='uncertain';z['ref_covered']+=covered(rid,ver)
   def summarize(counts,multiplicity=None):
    weighted={k:0.0 for k in next(iter(counts.values()))};raw={k:0 for k in weighted}
    for pid,z in counts.items():
     mult=1 if multiplicity is None else multiplicity.get(pid,0)
     for k,v in z.items():weighted[k]+=v*P[pid]['design_weight']*mult;raw[k]+=v*mult
    # Relation audit probability is constant within a domain/version and cancels from ratio.
    return dict(raw=raw,weighted=weighted,precision=ratio(weighted['audit_good'],weighted['audit_n']),all_precision=ratio(weighted['all_good'],weighted['all_n']),recall=ratio(weighted['ref_covered'],weighted['ref_valid']),recall_with_uncertain=ratio(weighted['ref_covered'],weighted['ref_valid']+weighted['ref_uncertain']),recall_all_frozen=ratio(weighted['ref_covered'],weighted['ref_total']))
   point=summarize(counter);all_metrics.append(dict(domain=domain,scope=scope,version=ver,**point));perpaper[(scope,ver)]=counter
  # One paired stratified paper bootstrap across both versions and all ratios.
  rng=random.Random(2026092404+(0 if domain=='iTE' else 1))
  pools={s:[pid for pid in papers if P[pid]['stratum']==s] for s in sorted({P[pid]['stratum'] for pid in papers})}
  stats={(v,k):[] for v in ['initial','reviewed'] for k in ['precision','all_precision','recall','recall_with_uncertain','recall_all_frozen']};deltas={k:[] for k in ['precision','all_precision','recall']}
  for _ in range(5000):
   mult=collections.Counter(pid for pool in pools.values() for pid in rng.choices(pool,k=len(pool)))
   vals={v:summarize(perpaper[(scope,v)],mult) for v in ['initial','reviewed']}
   for (v,k),arr in stats.items():
    if vals[v][k] is not None:arr.append(vals[v][k])
   for k,arr in deltas.items():
    if vals['initial'][k] is not None and vals['reviewed'][k] is not None:arr.append(vals['reviewed'][k]-vals['initial'][k])
  bootstrap[domain+':'+scope]=dict(intervals={v+':'+k:dict(lower=quantile(arr,.025),upper=quantile(arr,.975),valid_replicates=len(arr),degenerate=len(set(arr))<=1) for (v,k),arr in stats.items()},paired_differences={k:dict(lower=quantile(arr,.025),upper=quantile(arr,.975),valid_replicates=len(arr),degenerate=len(set(arr))<=1) for k,arr in deltas.items()})
 blind_counts[domain]=dict(papers=len(papers),unique_candidates=len(candidates),references=len(references),candidate_labels=dict(collections.Counter(j['label'] for j in labels.values())),reference_labels=dict(collections.Counter(j['label'] for j in ref_labels.values())))
 # Evidence-based error ledger, with versions revealed only AFTER all decisions exist.
 errors=[]
 for cid,j in labels.items():
  if j['label']!='supported':
   origins=[{k:x[k] for k in ['paper_id','version','original_id','audit_selected']} for x in KEY[domain] if x['candidate_id']==cid]
   errors.append(dict(candidate=candidates[cid],judgment=j,origins=origins))
 put(f'{domain}_error_ledger.json',errors)
 put(f'{domain}_per_paper_counts.json',{scope+':'+ver:z for (scope,ver),z in perpaper.items()})

put('metrics.json',dict(evaluation='separate-context, blinded-version, same-model Astra validation',metrics=all_metrics,bootstrap=bootstrap,audit_design=load('private/precision_sampling.json'),counts=blind_counts,limits=['Same model across authors and judges; correlated biases remain.','Bootstrap captures paper sampling variability, not model-reference error or all second-stage design uncertainty.','A degenerate zero-error bootstrap interval is not evidence of zero error risk and cannot alone establish stable passing.','Remaining held-out sampling frame excludes previously used papers; no full-corpus guarantee.']))
put('residual_missing.json',all_residual);put('reference_disputes.json',all_disputed);put('lost_after_review.json',all_lost)
judgefiles=[f'work/{j}/judgments.json' for j in ['judge_ite','judge_tg']]
put('evaluation_freeze.json',dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),files={n:sha(D/n) for n in judgefiles+['evaluate.py','metrics.json','residual_missing.json','reference_disputes.json','lost_after_review.json','iTE_error_ledger.json','TG_error_ledger.json']}))
print(json.dumps(dict(counts=blind_counts,metrics=[m for m in all_metrics if m['scope']=='all'],residual_missing=len(all_residual),reference_disputes=len(all_disputed),lost_after_review=len(all_lost)),ensure_ascii=False,indent=2))
