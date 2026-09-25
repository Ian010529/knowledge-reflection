"""Read-only verification of frozen inputs, all jobs, IDs and evidence mappings."""
import importlib.util,json,hashlib,collections
from pathlib import Path
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('delivery_workflow',D/'workflow.py');w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
w.check();counts=collections.Counter()
for phase in ['revision','reference','evaluation']:
 for j in w.read(D/(phase+'_jobs.json')):
  data=D/'jobs'/phase/(j['id']+'.json');response=D/'runs'/j['id']/'response.json';success=w.read(response.parent/'SUCCESS.json')
  assert w.sha(data)==j['input_sha256']==success['input_sha256'];assert w.sha(response)==success['response_sha256'];w.validate(phase,w.read(data),w.read(response));counts[phase]+=1
for k,p in [('reference_sha256','reference.json'),('revised_sha256','development_revised.json'),('blind_key_sha256','blind_key.json')]:assert w.sha(D/p)==w.read(D/'evaluation_freeze.json')[k]
for p in w.read(D/'development_revised.json'):
 seen=set();src=w.SRC[p['paper_id']]
 for r in p['records']:
  assert r['relation_id'] not in seen;seen.add(r['relation_id'])
  for quotes,spans in [([r['quote']]+r['context_quotes'],r['evidence_spans']),(r['modality_evidence'],r['modality_spans'])]:
   assert len(quotes)==len(spans)
   for q,s in zip(quotes,spans):assert src['abstract'][s['start']:s['end']]==q
original=w.read(D/'implementation_freeze.json');amend=w.read(D/'scoring_implementation_amendment.json')
for filename,h in original.items():assert w.sha(D/filename)==(amend['after_sha256'] if filename=='score.py' else h)
fix=w.read(D/'description_verification.json');assert w.sha(w.H/'initial_graph_v1/concepts.json')==fix['source_sha256'];assert w.sha(w.H/'initial_graph_v1/node_mapping.json')==fix['mapping_sha256']
result=dict(status='PASS_program_integrity_only',jobs=dict(counts),all_input_hashes_unchanged=True,all_job_outputs_valid=True,blinded_inputs_and_reference_unchanged=True,evidence_positions_valid=True,old_concepts_and_mapping_unchanged=True,semantic_gate_separate='development_scores.json')
w.write(D/'verification.json',result);print(json.dumps(result))
