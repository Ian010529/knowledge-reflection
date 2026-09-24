"""Read-only final provenance and source-location checks; no semantic decisions."""
import json,hashlib,re
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
count=0
for directory in ['match_pilot_v1','extraction_sop_v1']:
 d=D.parent/directory;m=load(d/'DELIVERY_MANIFEST.json')
 for name,h in m['files'].items():assert sha(d/name)==h,(directory,name);count+=1
for path in [D/'input_freeze.json',D/'analysis_plan_freeze.json',D/'blind_freeze.json',D/'evaluation_freeze.json']:
 obj=load(path);files=obj.get('files',obj)
 for name,h in files.items():assert sha(D/name)==h,(path.name,name);count+=1
for path in D.glob('work/*/*.freeze.json'):
 m=load(path)
 for key in ['raw','output']:
  assert sha(Path(m[key+'_path']))==m[key+'_sha256'],path;count+=1
for name,h in load(D/'selection.json')['source_hashes'].items():assert sha(ROOT/name)==h,name;count+=1
P={p['paper_id']:p for p in load(D/'input_papers.json')}
assert len(P)==60 and not(set(P)&set(load(D/'selection.json')['excluded']))
assert len({p['doi'].strip().lower() for p in P.values()})==60
spans=0
for path in [D/'work/extract_ite/initial.json',D/'work/extract_ite/reviewed.json',D/'work/extract_tg/initial.json',D/'work/extract_tg/reviewed.json',D/'work/reference/reference.json']:
 for paper in load(path):
  pid=paper['paper_id'];assert paper['input_hash']==P[pid]['input_hash'];ids={}
  for r in paper['records']:
   for e in r['evidence_spans']:
    assert P[pid]['abstract'][e['start']:e['end']]==e['quote'];spans+=1
   for side in ['subject','object']:
    n=r[side+'_id'];value=(r[side],r[side+'_role']);assert n not in ids or ids[n]==value;ids[n]=value
if (D/'REPORT.md').exists():
 for target in re.findall(r'\]\(([^)]+)\)',(D/'REPORT.md').read_text()):
  if not target.startswith('http'):assert (D/target).exists(),target
print(json.dumps(dict(status='PASS',hashes_verified=count,exact_spans_verified=spans,papers=60,prior_experiment_files_unchanged=True,note='Technical checks do not establish scientific correctness.')))
