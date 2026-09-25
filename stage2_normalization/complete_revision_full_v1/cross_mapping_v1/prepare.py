"""Current-graph lexical candidate mapping, with bounded source-grounded review."""
import collections,csv,hashlib,json,random,time
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
D=Path(__file__).resolve().parent;ROOT=D.parent;H=ROOT.parent;G=ROOT/'graph'
CORE={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics'}
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,x):(D/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvout(name,rows):
 with (D/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['pair_id']);w.writeheader();w.writerows(rows)
def text(e):return ' '.join([e['subject'],e['predicate'].replace('_',' '),e['object']])
def key(a,b,prefix):return prefix+hashlib.sha256((a+'|'+b).encode()).hexdigest()[:14]
def main():
 assert not (D/'freeze.json').exists(),'Already prepared'
 start=time.time();graphs={d:read(G/d/'graph.json') for d in ['iTE','TG']};papers={p['paper_id']:p for p in read(H/'initial_graph_v1/papers.json')};src={p['paper_id']:p for f in sorted((H/'full_extraction_v1/inputs').glob('*.json')) for p in read(f)}
 rows={d:sorted([e for e in g['edges'] if e['scope'] in CORE and papers[e['paper_id']]['source_membership']==d],key=lambda e:e['claim_id']) for d,g in graphs.items()}
 rng=random.Random(2026092501);seeds={}
 for d,rs in rows.items():
  chosen=[];used=set()
  for scope in sorted(CORE)*4:
   pool=[e for e in rs if e['scope']==scope and e['paper_id'] not in used]
   if pool:e=rng.choice(pool);chosen.append(e['claim_id']);used.add(e['paper_id'])
  seeds[d]=chosen
 write('query_seeds.json',seeds)
 nodes={d:{n['concept_id']:n for n in g['nodes']} for d,g in graphs.items()}
 eligible_nodes={d:{cid for e in graphs[d]['edges'] if papers[e['paper_id']]['source_membership']==d for cid in [e['source'],e['target']]} for d in graphs}
 N={d:[nodes[d][cid] for cid in sorted(eligible_nodes[d])] for d in graphs}
 def top_pairs(A,B,descriptions,compatible,prefix,idkey,exclude_docs=False):
  tf=TfidfVectorizer(lowercase=True,ngram_range=(1,2),sublinear_tf=True,dtype=np.float32)
  X=tf.fit_transform(descriptions);na=len(A);pairs={};best_b=[[] for _ in B];unmatched=[]
  for begin in range(0,na,128):
   sim=(X[begin:min(na,begin+128)]@X[na:].T).toarray()
   for off,a in enumerate(A[begin:begin+128]):
    i=begin+off;v=sim[off]
    for j in np.flatnonzero(v>0):
     b=B[j]
     if not compatible(a,b) or (exclude_docs and ((a['doi'] and a['doi'].strip().lower()==b['doi'].strip().lower()) or a['paper_title'].strip().casefold()==b['paper_title'].strip().casefold())):v[j]=0
    js=sorted(np.flatnonzero(v>0),key=lambda j:(-float(v[j]),B[j][idkey]))[:3]
    if not js:unmatched.append(a[idkey])
    for j in js:pairs[(i,int(j))]=float(v[j])
   # Reverse top-3 candidates must consider all left nodes, not just left top-3.
   for j,b in enumerate(B):
    ii=np.flatnonzero(sim[:,j]>0)
    if len(ii):
     ranked=sorted(ii,key=lambda off:(-float(sim[off,j]),A[begin+off][idkey]))[:3]
     best_b[j]=sorted(best_b[j]+[(float(sim[off,j]),begin+int(off)) for off in ranked],key=lambda t:(-t[0],A[t[1]][idkey]))[:3]
  for j,vs in enumerate(best_b):
   if not vs:unmatched.append(B[j][idkey])
   for value,i in vs:pairs[(i,j)]=value
  out=[dict(pair_id=key(A[i][idkey],B[j][idkey],prefix),left_id=A[i][idkey],right_id=B[j][idkey],retrieval_cosine=value,status='candidate_unreviewed') for (i,j),value in pairs.items()]
  out.sort(key=lambda x:(-x['retrieval_cosine'],x['left_id'],x['right_id']));return out,unmatched
 concept,cnone=top_pairs(N['iTE'],N['TG'],[' '.join(dict.fromkeys([n['label'],*n['aliases']])) for d in ['iTE','TG'] for n in N[d]],lambda a,b:bool(set(a['roles'])&set(b['roles'])),'C','concept_id')
 csvout('concept_candidates.csv',concept);write('concept_candidates.json',concept);write('concepts_without_candidate.json',cnone)
 relation,rnone=top_pairs(rows['iTE'],rows['TG'],[text(e) for d in ['iTE','TG'] for e in rows[d]],lambda a,b:a['subject_role']==b['subject_role'] and a['object_role']==b['object_role'],'R','claim_id',True)
 csvout('relation_candidates.csv',relation);write('relation_candidates.json',relation);write('relations_without_candidate.json',rnone)
 byid={e['claim_id']:e for d in rows for e in rows[d]};old={(p['iTE_claim'],p['TG_claim']) for p in read(H/'exploratory_match_v1/selection.json')};selected=[];used=set();paperpairs=set();counts=collections.Counter()
 for x in relation:
  a,b=byid[x['left_id']],byid[x['right_id']];pp=(a['paper_id'],b['paper_id'])
  if (x['left_id'],x['right_id']) in old or pp in paperpairs or max(counts[a['paper_id']],counts[b['paper_id']])>=2:continue
  selected.append(dict(x,basket='high_score_diverse'));used.add(x['pair_id']);paperpairs.add(pp);counts.update(pp)
  if len(selected)==32:break
 for d,ids in seeds.items():
  field='left_id' if d=='iTE' else 'right_id'
  for cid in ids:
   x=next((x for x in relation if x[field]==cid and x['pair_id'] not in used and (x['left_id'],x['right_id']) not in old),None)
   if x:selected.append(dict(x,basket='fixed_query_'+d));used.add(x['pair_id'])
 rng.shuffle(selected)
 def packet(cid):
  e=byid[cid];g=graphs[e['domain']];near=[x for x in g['edges'] if x['paper_id']==e['paper_id'] and x['claim_id']!=cid and ({x['source'],x['target']}&{e['source'],e['target']})]
  cons=[{k:nodes[e['domain']][x][k] for k in ['concept_id','label','definition','roles','aliases']} for x in dict.fromkeys([e['source'],e['target']])]
  return dict(claim=e,abstract=src[e['paper_id']]['abstract'],endpoint_concepts=cons,same_paper_neighbor_claims=near)
 review=[]
 for i,x in enumerate(selected,1):
  x['review_id']=f'M{i:03}';review.append(dict(review_id=x['review_id'],pair_id=x['pair_id'],left=packet(x['left_id']),right=packet(x['right_id'])))
 write('selection.json',selected);write('review_packets.json',review)
 summary=dict(eligible_concepts={d:len(ns) for d,ns in N.items()},eligible_core_relations={d:len(es) for d,es in rows.items()},concept_candidates=len(concept),relation_candidates=len(relation),concepts_without_candidate=len(cnone),relations_without_candidate=len(rnone),review_pairs=len(review),selection_baskets=dict(collections.Counter(x['basket'] for x in selected)),excluded_shared_membership_papers=sum('|' in p['source_membership'] for p in papers.values()),new_embeddings=0,retrieval_method='word unigram/bigram TF-IDF cosine; role-compatible bidirectional top-3; unvalidated retrieval baseline',semantic_probability=False,elapsed_seconds=time.time()-start)
 write('retrieval_summary.json',summary)
 paths=[G/d/'graph.json' for d in graphs]+[ROOT/'final/revised_all.json',H/'initial_graph_v1/papers.json',D/'PROTOCOL.md',Path(__file__),D/'query_seeds.json',D/'selection.json',D/'review_packets.json',D/'concept_candidates.json',D/'relation_candidates.json']
 write('freeze.json',dict(created_at=time.time(),files={str(p):sha(p) for p in paths}));print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
