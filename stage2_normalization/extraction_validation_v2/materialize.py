"""Validate and serialize authored judgments; never decides semantic content."""
import json,hashlib,sys,datetime
from pathlib import Path
D=Path(__file__).resolve().parent
P={p['paper_id']:p for p in json.loads((D/'input_papers.json').read_text())}
ROLES={'material_entity','design_strategy','condition','interaction','mechanism_process','state_structure','quantity','descriptor','performance_function','application'}
SCOPES={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics','device_thermal_management','mechanical_environmental_stability','application_sensing','measurement_method_model'}
def main(raw_path,out_path):
 raw_path=Path(raw_path);out_path=Path(out_path)
 if out_path.exists() or out_path.with_suffix('.freeze.json').exists():raise RuntimeError('Refusing frozen output overwrite')
 raw=json.loads(raw_path.read_text());seen=set();count=0
 for paper in raw:
  pid=paper['paper_id'];assert pid in P and pid not in seen,pid;seen.add(pid)
  assert paper['article_role'] in {'research','review','other','uncertain'}
  paper['domain']=P[pid]['domain'];paper['input_hash']=P[pid]['input_hash'];ids=set();nodes={}
  for r in paper['records']:
   assert r['id'] not in ids,(pid,r['id']);ids.add(r['id']);count+=1
   for k in ['subject','predicate','object','quote']:assert isinstance(r[k],str) and r[k],(pid,k)
   assert r['subject_role'] in ROLES and r['object_role'] in ROLES
   assert r['scope'] in SCOPES
   assert r['assertion'] in {'author_claim','association','hypothesis','negated'}
   assert r['modality'] in {'experimental','computational','theoretical','mixed','unspecified'}
   assert r['status'] in {'accepted','uncertain'}
   assert isinstance(r['conditions'],str) and isinstance(r['joint_factors'],list)
   r['relation_id']=pid+':'+r['id'];r['evidence_spans']=[]
   for quote in [r['quote']]+r.get('context_quotes',[]):
    assert quote in P[pid]['abstract'],(pid,r['id'],'quote not in source',quote)
    start=P[pid]['abstract'].index(quote)
    r['evidence_spans'].append(dict(quote=quote,start=start,end=start+len(quote)))
   for side in ['subject','object']:
    key=(r[side],r[side+'_role'])
    if key not in nodes:nodes[key]=f'{pid}:n{len(nodes)+1:03}'
    r[side+'_id']=nodes[key]
  paper['schema_version']='validation_v2'
 out_path.parent.mkdir(parents=True,exist_ok=True)
 out_path.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n')
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 out_path.with_suffix('.freeze.json').write_text(json.dumps(dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw_path=str(raw_path.resolve()),raw_sha256=sha(raw_path),output_path=str(out_path.resolve()),output_sha256=sha(out_path),papers=len(raw),records=count),indent=2)+'\n')
 print(json.dumps(dict(papers=len(raw),records=count,output=str(out_path))))
if __name__=='__main__':main(*sys.argv[1:])
