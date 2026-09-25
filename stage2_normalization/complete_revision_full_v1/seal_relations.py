"""Seal complete, validated revisions without overwriting any previous release."""
import importlib.util,collections,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('corpus_seal',D/'corpus.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
c.check();c.aggregate()
queue=c.read(D/'revision_output/reextract_queue.json')
if queue:raise SystemExit(f'{len(queue)} papers require one source-only re-extraction before final sealing.')
files=['revised_all.json','change_log.json','rejected.json','uncertain.json','reextract_queue.json','mechanical_alerts.json','duplicate_additions.json']
for name in files:c.save_new(D/'final'/name,c.read(D/'revision_output'/name))
ps=c.read(D/'final/revised_all.json');seen=set();evidence=0;originalids={r['relation_id'] for p in c.BASE.values() for r in p['records']};nowids={r['relation_id'] for p in ps for r in p['records']};rejectids={r['relation_id'] for r in c.read(D/'final/rejected.json')}
assert originalids<=nowids|rejectids and not nowids&rejectids
for p in ps:
 assert p['paper_id'] not in seen;seen.add(p['paper_id']);src=c.SRC[p['paper_id']];nodepairs=collections.defaultdict(set)
 for r in p['records']:
  for side in ['subject','object']:nodepairs[r[side+'_id']].add((r[side],r[side+'_role']))
  for quotes,spans in [([r['quote']]+r['context_quotes'],r['evidence_spans']),(r['modality_evidence'],r['modality_spans'])]:
   assert len(quotes)==len(spans)
   for q,s in zip(quotes,spans):assert src['abstract'][s['start']:s['end']]==q;evidence+=1
 assert all(len(v)==1 for v in nodepairs.values()),p['paper_id']
assert seen==set(c.BASE)
c.save_new(D/'final/missing_abstracts.json',c.read(c.H/'full_extraction_v1/missing_abstracts.json'))
c.write(D/'final/manifest.json',dict(created_at=c.now(),papers=len(ps),relations=len(nowids),reused_development_papers=40,one_new_revision_per_remaining_paper=1931,evidence_positions_verified=evidence,files={name:c.sha(D/'final'/name) for name in files},source_sha256=c.sha(c.H/'full_audit_v1/final/revised_all.json'),status='corpus_revision_complete_pending_heldout_acceptance'))
print(json.dumps(c.read(D/'final/manifest.json')),flush=True)
