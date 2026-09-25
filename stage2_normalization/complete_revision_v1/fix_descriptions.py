"""Apply exactly three evidence-reviewed description corrections, no regrouping."""
import copy,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=H/'initial_graph_v1/concepts.json';before=read(source);after=copy.deepcopy(before)
fixes={
'iTE:C3d9e7026fa6a4a':('Thermoelectric properties (ionic)','Properties characterizing the thermoelectric response of ionic thermoelectric materials or devices.','删除并非全部成员明确报告的离子重分布/扩散机制限定；保留已明示的离子热电语境。'),
'iTE:C3fb7e18a35b675':('High electrical conductivity','High ability to conduct electrical current.','P0937未说明载流机制；删除标签和定义中的electronic，不加入新的载流子判断。'),
'iTE:C835ef330237ca3':('Rapid self-healing','Rapid self-healing of a material after damage.','两篇均明确快速自愈，未共同报告无需外部触发；删除autonomous及不必要的共同性能恢复要求。')}
packets={c['concept_id']:c for p in (H/'post_revision_audit_v1/jobs/normalization').glob('*.json') for c in read(p) if c['concept_id'] in fixes}
logs=[]
for old,new in zip(before,after):
 if old['concept_id'] not in fixes:assert old==new;continue
 label,definition,reason=fixes[old['concept_id']];new.update(label=label,definition=definition)
 assert set(k for k in old if old[k]!=new[k])<={'label','definition'}
 assert {m['mention_id'] for m in packets[old['concept_id']]['members']}==set(old['mention_ids'])
 logs.append(dict(concept_id=old['concept_id'],before={k:old[k] for k in ['label','definition']},after={k:new[k] for k in ['label','definition']},reason=reason,review_type='current_assistant_source_evidence_review_not_human_gold',all_member_evidence=packets[old['concept_id']]['members']))
assert len(logs)==3
for name,value in {'description_changes.json':logs,'concepts_description_revised.json':after,'description_verification.json':dict(source_sha256=sha(source),mapping_sha256=sha(H/'initial_graph_v1/node_mapping.json'),exactly_three_concepts_changed=True,only_label_definition_changed=True,concept_ids_and_members_unchanged=True,old_graph_unchanged=True,all_member_evidence_reviewed=True,does_not_validate_all_merges=True)}.items():
 path=D/name;assert not path.exists();path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print('Exactly 3 descriptions corrected; all concept IDs and member mappings preserved.')
