#!/usr/bin/env python3
"""Join explicitly recorded Codex pilot decisions to immutable source evidence."""
import argparse,csv,json,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'stage2_review';OUT=BASE/'v1';SOURCE=ROOT/'stage2_reconstruction'/'v1'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=OUT)
OUT=parser.parse_args().output.resolve()
OUT.mkdir(parents=True,exist_ok=True)
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(name,rows):
 p=OUT/name
 assert not p.exists(),p
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
nodes=read(SOURCE/'node_evidence.csv');nb={r['mention_id']:r for r in nodes}
papers={r['paper_id']:r for r in read(SOURCE/'paper_coverage.csv')}
rd=json.loads((BASE/'pilot_role_decisions.json').read_text())
ed=json.loads((BASE/'pilot_relation_reviews.json').read_text())
nd=json.loads((BASE/'pilot_normalization_decisions.json').read_text())
roles={'material_entity','design_strategy','condition','interaction','mechanism_process','state_structure','quantity','descriptor','performance_function','application'}
rows=[]
for pid,decisions in rd['papers'].items():
 source=[n for n in nodes if n['paper_id']==pid]
 assert len(source)==len(decisions),pid
 for i,(n,d) in enumerate(zip(source,decisions),1):
  assert n['local_node_id']==f'n{i}' and d[0] in roles
  rows.append(dict(mention_id=n['mention_id'],paper_id=pid,domain=n['domain'],raw_phrase=n['raw_phrase'],
   legacy_role=n['legacy_role'],proposed_semantic_role=d[0],role_detail=d[1],role_flags=d[2],
   model_reason=d[3],quote=n['quote'],claim_id=n['claim_id'],
   annotation_author='Codex current session',proposal_status='model_proposed_pending_human',
   human_decision='',human_role='',human_reason=''))
write('role_model_proposals_pilot.csv',rows)
edge_rows=[]
for r in read(SOURCE/'relation_evidence.csv'):
 if r['paper_id'] not in ed['papers']:continue
 d=ed['papers'][r['paper_id']]
 a=d.get('overrides',{}).get(r['relation_id'].split(':')[-1],d)
 edge_rows.append(dict(relation_id=r['relation_id'],domain=r['domain'],paper_id=r['paper_id'],
  subject=nb[r['subject_mention_id']]['raw_phrase'],predicate=r['raw_predicate'],object=nb[r['object_mention_id']]['raw_phrase'],
  assertion_type=r['assertion_type'],model_assessment=a['assessment'],model_reason=a['reason'],
  quote=r['quote'],source_limitations=r['limitations'],proposal_status='model_proposed_pending_human',human_decision='',human_reason=''))
write('relation_model_review_pilot.csv',edge_rows)
pair_rows=[]
for left,right,decision,reason in nd['pairs']:
 a,b=nb[left],nb[right];assert a['domain']==b['domain']
 pair_rows.append(dict(proposal_id='pilot:'+hashlib.sha256((left+'|'+right).encode()).hexdigest()[:14],
  domain=a['domain'],left_mention_id=left,right_mention_id=right,left_label=a['raw_phrase'],right_label=b['raw_phrase'],
  proposed_relation=decision,model_reason=reason,left_quote=a['quote'],right_quote=b['quote'],
  left_full_abstract=papers[a['paper_id']]['abstract'],right_full_abstract=papers[b['paper_id']]['abstract'],
  selection='purposive_development_comparison_not_random_evaluation',proposal_status='model_proposed_pending_human',
  merge_applied=False,human_decision='',human_reason=''))
write('normalization_model_review_pilot.csv',pair_rows)
summary=dict(role_proposals=len(rows),role_distribution=dict(Counter(r['proposed_semantic_role'] for r in rows)),
 relation_reviews=len(edge_rows),relation_assessments=dict(Counter(r['model_assessment'] for r in edge_rows)),
 normalization_proposals=len(pair_rows),normalization_distribution=dict(Counter(r['proposed_relation'] for r in pair_rows)),
 human_reviewed=0,concepts_merged=0)
(OUT/'pilot_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
