"""Deterministic pilot computation; semantic records/labels come from Astra files."""
import os
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import json,csv,hashlib,collections,time,random,sys,platform,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
D=Path(__file__).resolve().parent
REV='e9b6763023c676ca8431644204f50c2b100d9aab'
rows=json.loads((D/'extraction_reviewed.json').read_text()); papers={p['paper_id']:p for p in json.loads((D/'input_papers.json').read_text())}
main_scopes={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics'}
main=[r for r in rows if r['analysis_scope'] in main_scopes and r['review_status']=='accepted']
def dump(name,obj): (D/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvout(name,rs):
 if not rs:return
 with open(D/name,'w') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def doi(r):return papers[r['paper_id']]['doi'].lower().strip() or r['paper_id']
def text(r):return f"{r['subject']['canonical_label']} {r['canonical_predicate'].replace('_',' ')} {r['object']['canonical_label']}"
def stable(pair):return hashlib.sha256(('20260924|'+'|'.join(pair)).encode()).hexdigest()
for dom in ['iTE','TG']:
 rr=[r for r in main if r['domain']==dom]; nodes={v['concept_id']:{'id':v['concept_id'],'label':v['canonical_label'],'role':v['role']} for r in rr for v in [r['subject'],r['object']]}
 ed=collections.defaultdict(list)
 for r in rr:ed[(r['subject']['concept_id'],r['canonical_predicate'],r['object']['concept_id'])].append(r)
 edges=[dict(source=k[0],predicate=k[1],target=k[2],weight=len(set(doi(r) for r in rs)),relation_ids=[r['relation_id'] for r in rs],paper_ids=sorted(set(r['paper_id'] for r in rs))) for k,rs in ed.items()]
 dump(f'graph_{dom}.json',dict(status='development_only',nodes=list(nodes.values()),edges=edges))
 root=ET.Element('graphml',xmlns='http://graphml.graphdrawing.org/xmlns')
 for key,typ,where in [('label','string','node'),('role','string','node'),('predicate','string','edge'),('weight','int','edge'),('relation_ids','string','edge')]:ET.SubElement(root,'key',id=key,attrib={'for':where,'attr.name':key,'attr.type':typ})
 g=ET.SubElement(root,'graph',id=dom,edgedefault='directed')
 for id,v in nodes.items():
  n=ET.SubElement(g,'node',id=id)
  for k in ('label','role'):ET.SubElement(n,'data',key=k).text=v[k]
 for i,e in enumerate(edges):
  n=ET.SubElement(g,'edge',id=f'e{i}',source=e['source'],target=e['target'])
  for k in ('predicate','weight','relation_ids'):ET.SubElement(n,'data',key=k).text=str(e[k])
 ET.ElementTree(root).write(D/f'graph_{dom}.graphml',encoding='utf-8',xml_declaration=True)
 csvout(f'concept_stats_{dom}.csv',[dict(**v,supporting_papers=len(set(r['paper_id'] for r in rr if v['id'] in (r['subject']['concept_id'],r['object']['concept_id'])))) for v in nodes.values()])
 dump(f'peripheral_{dom}.json',[r for r in rows if r['domain']==dom and r not in main])
# All graph records are frozen before generating any matches.
inputs=sorted(set('clustering: '+x for r in main for x in [text(r),r['subject']['canonical_label'],r['object']['canonical_label']]))
fingerprint=hashlib.sha256(json.dumps([REV,inputs]).encode()).hexdigest();cache=D/'embeddings.npz'
started=time.time();device='mps' if torch.backends.mps.is_available() else 'cpu'; torch.set_num_threads(2)
if cache.exists():
 z=np.load(cache);assert z['fingerprint'].item()==fingerprint;vectors=z['vectors'];cached=True
else:
 model=SentenceTransformer('nomic-ai/nomic-embed-text-v1.5',revision=REV,device=device,trust_remote_code=False,local_files_only=True)
 model.max_seq_length=512
 assert max(len(model.tokenizer.encode(t)) for t in inputs)<=512
 vectors=model.encode(inputs,batch_size=8,normalize_embeddings=True,show_progress_bar=False)
 np.savez_compressed(cache,vectors=vectors,fingerprint=np.array(fingerprint));cached=False
assert np.isfinite(vectors).all() and np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-4)
V={t:vec for t,vec in zip(inputs,vectors)}
def vec(t):return V['clustering: '+t]
A=[r for r in main if r['domain']=='iTE'];B=[r for r in main if r['domain']=='TG']
rel=np.array([vec(text(r)) for r in A])@np.array([vec(text(r)) for r in B]).T
sub=np.array([vec(r['subject']['canonical_label']) for r in A])@np.array([vec(r['subject']['canonical_label']) for r in B]).T
obj=np.array([vec(r['object']['canonical_label']) for r in A])@np.array([vec(r['object']['canonical_label']) for r in B]).T
eligible={(i,j) for i,a in enumerate(A) for j,b in enumerate(B) if doi(a)!=doi(b)}
exact={(i,j) for i,j in eligible if all(A[i][k]['canonical_label']==B[j][k]['canonical_label'] for k in ('subject','object')) and A[i]['canonical_predicate']==B[j]['canonical_predicate']}
candidates=set(exact)
for i in range(len(A)):
 js=sorted([j for ii,j in eligible if ii==i],key=lambda j:(-float(rel[i,j]),stable((A[i]['relation_id'],B[j]['relation_id']))))[:20];candidates.update((i,j) for j in js)
for j in range(len(B)):
 ii=sorted([i for i,jj in eligible if jj==j],key=lambda i:(-float(rel[i,j]),stable((A[i]['relation_id'],B[j]['relation_id']))))[:20];candidates.update((i,j) for i in ii)
def sig(r,endpoint):
 cid=r[endpoint]['concept_id'];s=set()
 for e in main:
  if e['domain']!=r['domain'] or e['relation_id']==r['relation_id']:continue
  if e['subject']['concept_id']==cid:s.add(('out',e['canonical_predicate'],e['object']['role']))
  if e['object']['concept_id']==cid:s.add(('in',e['canonical_predicate'],e['subject']['role']))
 return s
def jac(x,y):return len(x&y)/len(x|y) if x|y else 0.
S={(r['relation_id'],k):sig(r,k) for r in main for k in ('subject','object')}
scored=[]
for i,j in sorted(candidates):
 a,b=A[i],B[j];sem=.5*float(rel[i,j])+.25*float(sub[i,j])+.25*float(obj[i,j]);role=sum(a[k]['role']==b[k]['role'] for k in ('subject','object'))/2;pred=float(a['canonical_predicate']==b['canonical_predicate']);cons=.65*sem+.2*role+.15*pred
 nei=sum(jac(S[a['relation_id'],k],S[b['relation_id'],k]) for k in ('subject','object'))/2
 scored.append(dict(pair_id='PAIR-'+stable((a['relation_id'],b['relation_id']))[:12],iTE_relation=a['relation_id'],TG_relation=b['relation_id'],iTE_paper=a['paper_id'],TG_paper=b['paper_id'],exact=int((i,j) in exact),semantic=sem,relation_constrained=cons,neighborhood=.8*cons+.2*nei,neighborhood_component=nei,role_component=role,predicate_component=pred,tie=stable((a['relation_id'],b['relation_id']))))
methods=['exact','semantic','relation_constrained','neighborhood']; rankings={m:sorted([s for s in scored if m!='exact' or s['exact']],key=lambda s:(-s[m],s['tie'])) for m in methods}
csvout('candidate_scores.csv',scored);dump('rankings.json',{m:[s['pair_id'] for s in rs] for m,rs in rankings.items()})
union={s['pair_id']:s for rs in rankings.values() for s in rs[:50]}; packet=list(union.values()); random.Random(20260924).shuffle(packet);byid={r['relation_id']:r for r in rows}
blind=[]
for k,s in enumerate(packet,1):
 a,b=byid[s['iTE_relation']],byid[s['TG_relation']]
 def item(r):return {k:r[k] for k in ['relation_id','paper_id','subject','predicate','object','quote','assertion','conditions','joint_factors','evidence_modality','note']}
 blind.append(dict(review_id=f'B{k:03d}',pair_id=s['pair_id'],left=item(a),right=item(b)))
dump('review_packet_blinded.json',blind)
with open(D/'review_packet_compact.txt','w') as f:
 for v in blind:
  f.write(f"{v['review_id']} ")
  for side in ['left','right']:
   r=v[side];f.write(f"{r['paper_id']} [{r['relation_id'].split('-')[-1]}] {r['subject']['canonical_label']} --{r['predicate']}--> {r['object']['canonical_label']} | ")
  f.write('\n')
report=dict(status='development_only_matching_completed_labels_pending',main_relations=collections.Counter(r['domain'] for r in main),total_relations=len(rows),input_papers=len(papers),same_doi_pairs_excluded=len(A)*len(B)-len(eligible),eligible_relation_pairs=len(eligible),candidate_count=len(scored),top50_union_count=len(blind),exact_returned=len(exact),embedding=dict(model='nomic-ai/nomic-embed-text-v1.5',revision=REV,dimension=vectors.shape[1],texts=len(inputs),device=device,cached=cached,seconds=time.time()-started,fingerprint=fingerprint),python=sys.version,platform=platform.platform(),torch=torch.__version__)
dump('run_metadata.json',report);dump('matching_freeze.json',{name:hashlib.sha256((D/name).read_bytes()).hexdigest() for name in ['candidate_scores.csv','rankings.json','review_packet_blinded.json','embeddings.npz','run_matching.py']});print(json.dumps(report,ensure_ascii=False))
