import csv,json,random,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(name,obj):
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError(f'Cannot overwrite {p}')
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
prior=ROOT/'stage2_normalization/extraction_sop_v1'
ex=json.loads((prior/'selection.json').read_text())['excluded']
for p in json.loads((prior/'input_papers.json').read_text()):ex[p['paper_id']]=['extraction_sop_v1/input_papers.json']
allpapers=[];sources={};missing=[]
for domain,file in [('iTE','ite_clean.csv'),('TG','tg_clean.csv')]:
 path=ROOT/'cleaned_ite_tg/data'/file;sources[str(path.relative_to(ROOT))]=sha(path)
 for r in csv.DictReader(path.open(encoding='utf-8-sig')):
  if r['paper_id'] in ex:continue
  if not r['摘要'].strip():missing.append(r['paper_id']);continue
  allpapers.append(dict(paper_id=r['paper_id'],domain=domain,title=r['文章名'],doi=r['DOI'],year=r['年份'],source_membership=r['source_membership'],abstract=r['摘要'],input_hash=hashlib.sha256(r['摘要'].encode()).hexdigest()))
rng=random.Random(2026092402);chosen=[];strata=[]
for domain,source,n in [('iTE','iTE',30),('TG','TG',25),('TG','iTE|TG',5)]:
 pool=sorted([p for p in allpapers if p['domain']==domain and p['source_membership']==source],key=lambda p:p['paper_id'])
 selected=rng.sample(pool,n)
 for p in selected:p.update(stratum=source,inclusion_probability=n/len(pool),design_weight=len(pool)/n)
 chosen+=selected;strata.append(dict(domain=domain,stratum=source,N=len(pool),n=n))
assert len(chosen)==60 and len({p['paper_id'] for p in chosen})==60
assert len({p['doi'].strip().lower() for p in chosen})==60
put('input_papers.json',chosen)
put('selection.json',dict(seed=2026092402,strata=strata,excluded=ex,missing_abstracts=missing,source_hashes=sources))
for domain in ['iTE','TG']:put('inputs/'+domain+'.json',[p for p in chosen if p['domain']==domain])
put('inputs/reference_all.json',chosen)
for role in ['extract_ite','extract_tg','reference','judge_ite','judge_tg']:(D/'work'/role).mkdir(parents=True,exist_ok=True)
files=['protocol.md','schema.md','prepare.py','materialize.py','input_papers.json','selection.json','inputs/iTE.json','inputs/TG.json','inputs/reference_all.json']
put('input_freeze.json',{n:sha(D/n) for n in files})
print(json.dumps(dict(strata=strata,excluded=len(ex),selected=[p['paper_id'] for p in chosen]),ensure_ascii=False))
