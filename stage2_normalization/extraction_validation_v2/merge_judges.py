"""Combine disjoint blind judgments without semantic alteration."""
import json,hashlib,datetime
from pathlib import Path
D=Path(__file__).resolve().parent
def load(n):return json.loads((D/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
alloc=load('judge_allocation.json')
assert sha(D/'blind/tail20.json')==alloc['tail_packet_sha256']
ite_tail=load('work/judge_tail/judgments_ite_tail.json')
tg_tail=load('work/judge_tg/judgments_tail.json')
tail=ite_tail+tg_tail
assert len(tail)==20 and len({x['paper_id'] for x in tail})==20
assert {x['paper_id'] for x in tail}=={x['paper_id'] for x in load('blind/tail20.json')}
provenance={}
for domain,folder in [('iTE','judge_ite'),('TG','judge_tg')]:
 head=load(f'work/{folder}/judgments_head.json');a=alloc['allocation'][domain]
 assert len(head)==20 and {x['paper_id'] for x in head}==set(a['head'])
 subset=[x for x in tail if x['paper_id'] in a['tail']];assert len(subset)==10
 combined=head+subset;assert len({x['paper_id'] for x in combined})==30
 out=D/f'work/{folder}/judgments.json';assert not out.exists(),out
 out.write_text(json.dumps(combined,ensure_ascii=False,indent=2)+'\n')
 for p in head:provenance[p['paper_id']]=dict(role=folder,source=f'work/{folder}/judgments_head.json')
 for p in subset:provenance[p['paper_id']]=dict(role='judge_tail' if domain=='iTE' else 'judge_tg',source='work/judge_tail/judgments_ite_tail.json' if domain=='iTE' else 'work/judge_tg/judgments_tail.json')
paths=['work/judge_ite/judgments_head.json','work/judge_tg/judgments_head.json','work/judge_tail/judgments_ite_tail.json','work/judge_tg/judgments_tail.json','work/judge_ite/judgments.json','work/judge_tg/judgments.json']
(D/'judge_provenance.json').write_text(json.dumps(dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),papers=provenance,files={p:sha(D/p) for p in paths}),ensure_ascii=False,indent=2)+'\n')
print('Merged60 unique paper judgments; head/tail source hashes preserved.')
