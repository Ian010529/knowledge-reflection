"""Bounded exploratory relation retrieval from frozen initial graphs; no re-encoding."""
import collections, csv, hashlib, json, random, time
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
D=Path(__file__).resolve().parent; H=D.parent; G=H/'initial_graph_v1'; R=H/'full_retrieval_rrf_v1'
CORE={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics'}
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,obj):(D/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def text(r):return f"{r['subject']} {r['predicate'].replace('_',' ')} {r['object']}"
def main():
 if (D/'freeze.json').exists():raise RuntimeError('Existing frozen exploration; do not overwrite')
 start=time.time(); papers={p['paper_id']:p for p in read(G/'papers.json')}; source={p['paper_id']:p for f in sorted((H/'full_extraction_v1/inputs').glob('*.json')) for p in read(f)}
 graphs={d:read(G/d/'graph.json') for d in ['iTE','TG']}
 # Membership exclusions only affect this exploration, never the source graphs.
 rows={d:[r for r in graphs[d]['edges'] if r['scope'] in CORE and papers[r['paper_id']]['source_membership']==d] for d in graphs}
 for d in rows:rows[d].sort(key=lambda r:r['claim_id'])
 A=rows['iTE'];B=rows['TG'];rng=random.Random(20260925)
 # Freeze 6 diverse query seeds/domain BEFORE looking at any similarity score.
 seeds={}
 for d in rows:
  selected=[];usedpapers=set()
  for scope in sorted(CORE)*2:
   pool=[r for r in rows[d] if r['scope']==scope and r['paper_id'] not in usedpapers]
   if pool:
    r=rng.choice(pool);selected.append(r['claim_id']);usedpapers.add(r['paper_id'])
   if len(selected)==6:break
  seeds[d]=selected
 write('query_seeds.json',seeds)
 z=np.load(next(R.glob('vectors_*.npz'))); V=z['vectors']; index={m:i for i,m in enumerate(z['mention_ids'].tolist())}
 def matrix(rs,side):return V[[index[r['domain']+':'+r[side+'_id']] for r in rs]]
 # Directional subject-to-subject and object-to-object evidence-context similarities.
 endpoint=(matrix(A,'subject')@matrix(B,'subject').T+matrix(A,'object')@matrix(B,'object').T)*.5
 tf=TfidfVectorizer(lowercase=True,ngram_range=(1,2),sublinear_tf=True)
 X=tf.fit_transform([text(r) for r in A+B]); lexical=(X[:len(A)]@X[len(A):].T).toarray().astype('float32')
 score=.7*endpoint+.3*lexical
 excluded=0
 for i,a in enumerate(A):
  for j,b in enumerate(B):
   if (a['doi'] and a['doi'].strip().lower()==b['doi'].strip().lower()) or a['paper_title'].strip().casefold()==b['paper_title'].strip().casefold():score[i,j]=-np.inf;excluded+=1
 # Save bidirectional top-3 candidates, but only inspect the bounded selection below.
 pairs=set()
 for i in range(len(A)):
  for j in np.argsort(-score[i],kind='stable')[:3]:
   if np.isfinite(score[i,j]):pairs.add((i,int(j)))
 for j in range(len(B)):
  for i in np.argsort(-score[:,j],kind='stable')[:3]:
   if np.isfinite(score[i,j]):pairs.add((int(i),j))
 ranked=sorted(pairs,key=lambda ij:(-float(score[ij]),A[ij[0]]['claim_id'],B[ij[1]]['claim_id']))
 def row(i,j):
  a,b=A[i],B[j]
  return dict(pair_id='X'+hashlib.sha256((a['claim_id']+'|'+b['claim_id']).encode()).hexdigest()[:12],iTE_claim=a['claim_id'],TG_claim=b['claim_id'],iTE_paper=a['paper_id'],TG_paper=b['paper_id'],score=float(score[i,j]),endpoint_similarity=float(endpoint[i,j]),relation_lexical_similarity=float(lexical[i,j]))
 candidates=[row(i,j) for i,j in ranked]
 with (D/'candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(candidates[0]));w.writeheader();w.writerows(candidates)
 picks=[];used=set();paperpairs=set();counts=collections.Counter()
 for i,j in ranked:
  a,b=A[i],B[j];pp=(a['paper_id'],b['paper_id'])
  if pp in paperpairs or counts[a['paper_id']]>=2 or counts[b['paper_id']]>=2:continue
  picks.append(dict(**row(i,j),selection='high_score_diverse'));used.add((i,j));paperpairs.add(pp);counts.update(pp)
  if len(picks)==12:break
 for d,ids in seeds.items():
  for cid in ids:
   if d=='iTE':
    i=next(i for i,r in enumerate(A) if r['claim_id']==cid); order=[(i,int(j)) for j in np.argsort(-score[i],kind='stable')]
   else:
    j=next(j for j,r in enumerate(B) if r['claim_id']==cid); order=[(int(i),j) for i in np.argsort(-score[:,j],kind='stable')]
   pair=next(((i,j) for i,j in order if (i,j) not in used and np.isfinite(score[i,j])),None)
   if pair:
    used.add(pair);picks.append(dict(**row(*pair),selection='fixed_query_'+d,query=cid))
 byid={r['claim_id']:r for rs in rows.values() for r in rs}; allbydomain={d:graphs[d]['edges'] for d in graphs}
 def packet(cid):
  r=byid[cid];neighbors=[e for e in allbydomain[r['domain']] if e['paper_id']==r['paper_id'] and e['claim_id']!=cid and ({e['source'],e['target']}&{r['source'],r['target']})]
  return dict(claim=r,abstract=source[r['paper_id']]['abstract'],same_paper_neighbor_claims=neighbors)
 rng.shuffle(picks)
 review=[dict(review_id=f'B{i+1:02}',pair_id=p['pair_id'],left=packet(p['iTE_claim']),right=packet(p['TG_claim'])) for i,p in enumerate(picks)]
 write('selection.json',picks);write('review_packets.json',review)
 metrics=dict(status='retrieval_complete_judgments_pending',eligible_core_relations={d:len(rs) for d,rs in rows.items()},excluded_shared_membership_papers=sum('|' in p['source_membership'] for p in papers.values()),same_document_pairs_excluded=excluded,candidates=len(candidates),selected_pairs=len(picks),query_seeds=seeds,weights={'cached_directional_endpoint':.7,'relation_tfidf':.3},new_embeddings=0,rrf_used=False,seconds=round(time.time()-start,2),seed=20260925)
 write('retrieval_summary.json',metrics)
 write('freeze.json',dict(created_at=time.time(),files={str(p.relative_to(H)):sha(p) for p in [G/'iTE/graph.json',G/'TG/graph.json',G/'node_mapping.json',R/'nodes.json',next(R.glob('vectors_*.npz')),D/'retrieve.py',D/'PROTOCOL.md',D/'query_seeds.json',D/'selection.json',D/'review_packets.json',D/'candidates.csv']}))
 print(json.dumps(metrics,ensure_ascii=False))
if __name__=='__main__':main()
