"""Reproducible sampling only; no semantic selection or extraction."""
import csv, json, hashlib, random, re
from pathlib import Path
D = Path(__file__).resolve().parent
ROOT = D.parents[1]
def csvrows(p):
    return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
paths = [
 'stage2_review/v1/role_development_papers.csv',
 'stage2_review/v1/relation_audit_sample.csv',
 'stage2_review/v1/relation_model_review_pilot.csv',
 'stage2_review/batch02_v1/selection.json',
 'stage2_normalization/astra_judge_review/completion_v1/inputs/relation_audit_sample.csv',
 'stage2_normalization/astra_judge_review/completion_v1/inputs/abstract_gold_annotation_blank.csv',
 'stage2_normalization/astra_judge_review/completion_v1/challenge_cases.csv',
]
excluded = {}
for name in paths:
    p=ROOT/name
    for pid in sorted(set(re.findall(r'P\d{4}',p.read_text(encoding='utf-8-sig')))):
        excluded.setdefault(pid,[]).append(name)
papers=[]; missing=[]; files={}
for domain, name in [('iTE','ite_clean.csv'),('TG','tg_clean.csv')]:
    p=ROOT/'cleaned_ite_tg/data'/name; files[str(p.relative_to(ROOT))]=sha(p)
    for row in csvrows(p):
        if row['paper_id'] in excluded:continue
        if not row['摘要'].strip():missing.append(row['paper_id']);continue
        papers.append(dict(paper_id=row['paper_id'],domain=domain,title=row['文章名'],doi=row['DOI'],year=row['年份'],source_membership=row['source_membership'],abstract=row['摘要'],input_hash=hashlib.sha256(row['摘要'].encode()).hexdigest()))
rng=random.Random(20260924); selected=[]; strata=[]
for domain,source,n in [('iTE','iTE',6),('TG','TG',4),('TG','iTE|TG',2)]:
    pool=sorted([p for p in papers if p['domain']==domain and p['source_membership']==source],key=lambda p:p['paper_id'])
    sample=rng.sample(pool,n)
    for p in sample:p.update(stratum=source,inclusion_probability=n/len(pool))
    selected.extend(sample);strata.append(dict(domain=domain,source=source,eligible_N=len(pool),n=n))
def dump(name,v):
    p=D/name
    if p.exists():raise RuntimeError(f'Refusing overwrite {p}')
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
dump('input_papers.json',selected)
dump('selection.json',dict(seed=20260924,strata=strata,excluded=excluded,missing_abstracts=missing,source_hashes=files,protocol_sha256=sha(D/'protocol.md')))
dump('input_freeze.json',{name:sha(D/name) for name in ['protocol.md','prepare.py','input_papers.json','selection.json']})
print(json.dumps(dict(strata=strata,excluded_count=len(excluded),selected=[{k:p[k] for k in ['paper_id','domain','source_membership','title']} for p in selected]),ensure_ascii=False,indent=2))
