"""Mechanically anonymize frozen outputs and select audits BEFORE evaluation."""
import json,random,hashlib,datetime
from pathlib import Path
D=Path(__file__).resolve().parent
def load(p):return json.loads((D/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
 p=D/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError(f'Refusing overwrite {p}')
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def check(p):
 f=load(str(Path(p).with_suffix('.freeze.json')))
 assert sha(D/p)==f['output_sha256'],p
 assert sha(Path(f['raw_path']))==f['raw_sha256'],p
 return f
FIELDS=['subject','subject_role','predicate','object','object_role','quote','assertion','modality','conditions','joint_factors','scope','context_quotes']
def content(r):return {k:r[k] for k in FIELDS if k in r}
P={p['paper_id']:p for p in load('input_papers.json')}
check('work/reference/reference.json')
REF={p['paper_id']:p for p in load('work/reference/reference.json')};assert set(REF)==set(P)
keys={};audit=[];packages=[];rng=random.Random(2026092403);sources={}
for domain,folder in [('iTE','extract_ite'),('TG','extract_tg')]:
 paper_ids={pid for pid,p in P.items() if p['domain']==domain};byversion={};unique={};originals=[]
 for ver in ['initial','reviewed']:
  path=f'work/{folder}/{ver}.json';check(path);sources[path]=sha(D/path)
  papers=load(path);assert {p['paper_id'] for p in papers}==paper_ids
  byversion[ver]={p['paper_id']:p for p in papers};items=[]
  for paper in papers:
   for row in paper['records']:
    pid=paper['paper_id'];c=content(row);c['article_role']=paper['article_role'];identity=(pid,json.dumps(c,sort_keys=True,ensure_ascii=False))
    unique[identity]=c;items.append(dict(paper_id=pid,original_id=row['id'],version=ver,identity=identity))
  chosen=rng.sample(items,min(100,len(items)))
  selected={(x['paper_id'],x['original_id']) for x in chosen}
  for x in items:
   x['audit_selected']=(x['paper_id'],x['original_id']) in selected
   x['relation_inclusion_probability']=min(100,len(items))/len(items) if items else 1
  originals+=items
  audit.append(dict(domain=domain,version=ver,N=len(items),n=len(chosen),seed=2026092403))
 identities=list(unique);rng.shuffle(identities)
 cmap={identity:f'C{domain}-{i+1:04}' for i,identity in enumerate(identities)}
 for x in originals:
  x['candidate_id']=cmap[x.pop('identity')];x['domain']=domain
  p=P[x['paper_id']];x['paper_inclusion_probability']=p['inclusion_probability'];x['design_weight']=p['design_weight']/x['relation_inclusion_probability']
 keys[domain]=originals
 packet=[];paper_order=sorted(paper_ids);rng.shuffle(paper_order)
 refkeys={}
 for pid in paper_order:
  p=P[pid];cand=[dict(candidate_id=cmap[k],**unique[k]) for k in identities if k[0]==pid];refs=[]
  rawrefs=REF[pid]['records'][:];rng.shuffle(rawrefs)
  for i,r in enumerate(rawrefs):
   rid=f'G{pid}-{i+1:03}';refs.append(dict(reference_id=rid,article_role=REF[pid]['article_role'],**content(r)));refkeys[rid]=dict(paper_id=pid,original_id=r['id'],original_status=r['status'])
  packet.append(dict(paper_id=pid,domain=domain,title=p['title'],abstract=p['abstract'],candidates=cand,references=refs))
 out=f'blind/{domain}.json';put(out,packet);packages.append(out);put(f'private/{domain}_reference_key.json',refkeys)
put('private/version_key.json',keys);put('private/precision_sampling.json',audit)
sources['work/reference/reference.json']=sha(D/'work/reference/reference.json')
for name in packages+['private/version_key.json','private/precision_sampling.json','private/iTE_reference_key.json','private/TG_reference_key.json']:
 sources[name]=sha(D/name)
put('blind_freeze.json',dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=sources))
print(json.dumps(dict(audits=audit,blind_packets=packages),ensure_ascii=False))
