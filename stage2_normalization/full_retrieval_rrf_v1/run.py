"""Apply the existing BM25/short-context/RRF recipe to revised extraction nodes.
Local encoding and retrieval only. No semantic merging or generative calls.
"""
import csv, hashlib, json, math, os, re, sys, time
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
D=Path(__file__).resolve().parent; H=D.parent
sys.path.insert(0,str(H))
from compare_keyword_semantic import tokenize, K1, B, TOP, RRF_K
from compare_embedding_inputs import focused_context, MODEL, REVISION
from generate_semantic_candidates import short_context
SOURCE=H/'full_audit_v1/final/revised_all.json'
NAMES=['bm25','vector','rrf']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,obj): (D/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvout(name,rows):
 with (D/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 started=time.perf_counter();source_hash=sha(SOURCE)
 if (D/'summary.json').exists(): raise RuntimeError('Completed output already exists; inspect rather than overwrite.')
 papers=json.loads(SOURCE.read_text()); pool={}; deferred=[]
 for p in papers:
  for r in p['records']:
   if r['status']!='accepted': deferred.append(r['relation_id']);continue
   for side in ('subject','object'):
    mid=p['domain']+':'+r[side+'_id']; label=r[side];role=r[side+'_role']
    node=pool.setdefault(mid,dict(mention_id=mid,domain=p['domain'],paper_id=p['paper_id'],label=label,role=role,relation_ids=[],evidence=[]))
    assert (node['label'],node['role'])==(label,role)
    node['relation_ids'].append(r['relation_id'])
    for q in [r['quote']]+r['context_quotes']:
     if q not in node['evidence']:node['evidence'].append(q)
 nodes=[pool[k] for k in sorted(pool)]; mids=[n['mention_id'] for n in nodes]
 for n in nodes:
  quote=next((q for q in n['evidence'] if re.search(re.escape(n['label']),q,re.I)),n['evidence'][0])
  context,a,b,method=short_context(n['label'],quote)
  if re.search(re.escape(n['label']),quote,re.I):
   context,a,b,method=focused_context(dict(label=n['label'],quote=quote,context=context,context_start=a,context_end=b))
  n.update(quote=quote,context=context,context_start=a,context_end=b,context_method=method,
           embedding_text='clustering: '+n['label']+'. Context: '+' '.join(context.split()))
  assert quote[a:b]==context and any(context in q for q in n['evidence'])
 dump('nodes.json',nodes);dump('deferred_relation_ids.json',deferred)
 rng=np.random.default_rng(20260925)
 sample=sorted(int(i) for d in ('iTE','TG') for i in rng.choice([i for i,n in enumerate(nodes) if n['domain']==d],12,replace=False))
 dump('sample_queries.json',[mids[i] for i in sample])
 spec=dict(source_sha256=source_hash,model=MODEL,revision=REVISION,max_seq_length=512,normalized=True,inputs=[(n['mention_id'],n['embedding_text']) for n in nodes])
 fp=hashlib.sha256(json.dumps(spec,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 cache=D/('vectors_'+fp[:20]+'.npz');cache_reused=cache.exists();tick=time.perf_counter()
 torch.set_num_threads(2);device='mps' if torch.backends.mps.is_available() else 'cpu'
 if device=='mps':torch.mps.set_per_process_memory_fraction(.35)
 print(json.dumps(dict(stage='prepared',nodes=len(nodes),domains=dict(Counter(n['domain'] for n in nodes)),context_methods=dict(Counter(n['context_method'] for n in nodes)))),flush=True)
 if cache_reused:
  with np.load(cache) as z: assert z['mention_ids'].tolist()==mids;vec=z['vectors']
 else:
  model=SentenceTransformer(MODEL,revision=REVISION,device=device,trust_remote_code=False,local_files_only=True);model.max_seq_length=512
  texts=[n['embedding_text'] for n in nodes]
  lengths=[len(model.tokenizer.encode(t)) for t in texts]
  assert max(lengths)<=512, 'Unexpected input truncation; inspect before encoding'
  vec=np.empty((len(nodes),768),dtype=np.float32)
  for a in range(0,len(nodes),2048):
   part=D/f'part_{fp[:20]}_{a:06}.npy';b=min(a+2048,len(nodes))
   if part.exists(): chunk=np.load(part)
   else:
    chunk=model.encode(texts[a:b],batch_size=16,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False);np.save(part,chunk)
   assert chunk.shape==(b-a,768);vec[a:b]=chunk
   print(json.dumps(dict(stage='embedding',done=b,total=len(nodes),seconds=round(time.perf_counter()-tick,1))),flush=True)
  np.savez_compressed(cache,mention_ids=np.array(mids),vectors=vec)
 assert vec.shape==(len(nodes),768) and np.isfinite(vec).all() and np.allclose(np.linalg.norm(vec,axis=1),1,atol=1e-4)
 encoding=time.perf_counter()-tick;tick=time.perf_counter()
 neighbors={m:np.full((len(nodes),TOP),-1,dtype=np.int32) for m in NAMES}
 scores={m:np.full((len(nodes),TOP),np.nan) for m in NAMES}
 tokens=[Counter(tokenize(n['label'])) for n in nodes];assert all(tokens)
 maxdiff=0.;checked=0
 for domain in ('TG','iTE'):
  ids=np.array([i for i,n in enumerate(nodes) if n['domain']==domain]);ts=[tokens[i] for i in ids]
  dl=np.array([sum(t.values()) for t in ts]);avg=float(dl.mean());post=defaultdict(list)
  for j,t in enumerate(ts):
   for term,tf in t.items():post[term].append((j,tf))
  lookup={}
  for term,items in post.items():
   js=np.array([j for j,tf in items]);tf=np.array([tf for j,tf in items])
   lookup[term]=(js,math.log1p((len(ids)-len(items)+.5)/(len(items)+.5))*tf*(K1+1)/(tf+K1*(1-B+B*dl[js]/avg)))
  matrix=vec[ids];check_queries={sample_i for sample_i in sample if nodes[sample_i]['domain']==domain};check_queries=set(sorted(check_queries)[:3])
  for a in range(0,len(ids),128):
   similarities=np.clip(matrix[a:a+128]@matrix.T,-1,1)
   for offset,dense in enumerate(similarities):
    q=a+offset;src=ids[q];lex=np.zeros(len(ids))
    for term in sorted(ts[q]):
     js,values=lookup[term];lex[js]+=values
    if src in check_queries:
     ref=np.array([sum(math.log1p((len(ids)-len(post[t])+.5)/(len(post[t])+.5))*c[t]*(K1+1)/(c[t]+K1*(1-B+B*sum(c.values())/avg)) for t in sorted(ts[q]) if c.get(t,0)) for c in ts])
     diff=float(np.max(np.abs(ref-lex)));maxdiff=max(maxdiff,diff);assert diff<1e-10;checked+=1
    lex[q]=dense[q]=-np.inf
    lo=np.argsort(-lex,kind='stable')[:TOP];lo=[j for j in lo if lex[j]>0]
    vo=np.argsort(-dense,kind='stable')[:TOP].tolist();fusion=defaultdict(float)
    for order in (lo,vo):
     for rank,j in enumerate(order,1):fusion[j]+=1/(RRF_K+rank)
    fo=sorted(fusion,key=lambda j:(-fusion[j],mids[ids[j]]))[:TOP]
    for name,order,vals in [('bm25',lo,lex),('vector',vo,dense),('rrf',fo,fusion)]:
     neighbors[name][src,:len(order)]=ids[order];scores[name][src,:len(order)]=[vals[j] for j in order]
  print(json.dumps(dict(stage='retrieval',domain=domain,done=len(ids))),flush=True)
 retrieval=time.perf_counter()-tick
 metrics={};sets={};examples=[]
 for name,arr in neighbors.items():
  pairs=set();same_label=0;same_role=0;same_paper=0;directed=0
  for i,row in enumerate(arr):
   valid=[int(j) for j in row if j>=0];assert len(valid)==len(set(valid)) and i not in valid
   for rank,j in enumerate(valid,1):
    assert nodes[i]['domain']==nodes[j]['domain'];directed+=1;pairs.add(tuple(sorted((i,j))))
    same_label+=nodes[i]['label'].casefold()==nodes[j]['label'].casefold();same_role+=nodes[i]['role']==nodes[j]['role'];same_paper+=nodes[i]['paper_id']==nodes[j]['paper_id']
    if i in sample:examples.append(dict(method=name,source=mids[i],source_label=nodes[i]['label'],source_role=nodes[i]['role'],target=mids[j],target_label=nodes[j]['label'],target_role=nodes[j]['role'],rank=rank,score=float(scores[name][i,rank-1]),source_context=nodes[i]['context'],target_context=nodes[j]['context']))
  sets[name]=pairs;metrics[name]=dict(unordered_pairs=len(pairs),directed_neighbors=directed,queries_under_top10=int(np.sum(np.sum(arr>=0,axis=1)<10)),same_label_neighbors=same_label,same_role_neighbors=same_role,same_paper_neighbors=same_paper,
      pairs_by_domain=dict(Counter(nodes[i]['domain'] for i,j in pairs)))
 for i in range(len(nodes)):
  f=defaultdict(float)
  for m in ('bm25','vector'):
   for rank,j in enumerate(neighbors[m][i],1):
    if j>=0:f[int(j)]+=1/(RRF_K+rank)
  expected=sorted(f,key=lambda j:(-f[j],mids[j]))[:TOP]
  assert expected==neighbors['rrf'][i].tolist()
 candidate_rows=[]
 for i,j in sorted(sets['rrf']):
  candidate_rows.append(dict(left=mids[i],right=mids[j],domain=nodes[i]['domain'],left_label=nodes[i]['label'],right_label=nodes[j]['label'],left_role=nodes[i]['role'],right_role=nodes[j]['role'],same_paper=nodes[i]['paper_id']==nodes[j]['paper_id'],in_bm25=(i,j) in sets['bm25'],in_vector=(i,j) in sets['vector'],status='unreviewed_retrieval_candidate'))
 csvout('rrf_candidates.csv',candidate_rows);csvout('sample_top10.csv',examples)
 np.savez_compressed(D/'all_top10.npz',mention_ids=np.array(mids),**neighbors,**{m+'_scores':s for m,s in scores.items()})
 assert sha(SOURCE)==source_hash
 summary=dict(status='retrieval_trial_complete_not_normalization',source_sha256=source_hash,papers=len(papers),accepted_relations=sum(len(p['records']) for p in papers)-len(deferred),deferred_relations=len(deferred),nodes=len(nodes),nodes_by_domain=dict(Counter(n['domain'] for n in nodes)),model=MODEL,revision=REVISION,device=device,embedding_input_fingerprint=fp,cache_reused=cache_reused,embedding_seconds=encoding,retrieval_seconds=retrieval,total_seconds=time.perf_counter()-started,
   parameters=dict(bm25_k1=K1,bm25_b=B,channel_top_k=TOP,rrf_k=RRF_K,final_top_k=TOP,domain_local=True,role_filter=False,self_excluded=True,same_paper_allowed=True),context_methods=dict(Counter(n['context_method'] for n in nodes)),metrics=metrics,
   rrf_added_vs_bm25=len(sets['rrf']-sets['bm25']),rrf_dropped_vs_bm25=len(sets['bm25']-sets['rrf']),rrf_added_vs_vector=len(sets['rrf']-sets['vector']),rrf_dropped_vs_vector=len(sets['vector']-sets['rrf']),
   validation=dict(source_unchanged=True,finite_unit_vectors=True,bm25_scalar_queries=checked,bm25_max_error=maxdiff,rrf_all_queries_reconstructed=True,no_self_cross_domain_duplicate_neighbors=True),semantic_recall_measured=False,semantic_precision_measured=False,new_generative_model_calls=0,merges_applied=0,script_sha256=sha(Path(__file__)))
 dump('summary.json',summary);print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
