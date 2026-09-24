from work import *
# Deliberately adversarial post-audit regression suite, not an independent accuracy sample.
cases={
'negation_boundary':[14,16,64,75,81,132,139,195],
'joint_factors':[17,23,24,39,43,68,69,70,86,91,110,126,136,137,143,152,166,192],
'computational_modality':[0,5,41,56,71,96,147,196,199],
'cross_sentence_and_symbols':[26,29,67,95,140],
'purpose_vs_observation':[94,122,170,176],
'conditions_sign_and_opposing_effects':[30,88,128,173,175,178]}
assert sum(map(len,cases.values()))==50
judges={r['sample_index']:r for r in map(json.loads,(OUT/'relation_audit_judgments.jsonl').read_text().splitlines())}
rows=[]
for typ,ids in cases.items():
 for i in ids:
  a=sample[i];j=judges[i]
  rows.append({'challenge_id':f'challenge:{i:03d}','sample_index':i,'relation_id':a['relation_id'],'domain':a['domain'],'challenge_type':typ,'expected_disposition':j['baseline_status'],'required_preservation':j['reason'],'required_repair':j['repair_instruction'],'joint_factor_requirement':j['joint_factor_requirement'],'quote':a['quote'],'overlaps_representative_audit':True})
assert len({r['relation_id'] for r in rows})==50
csvout('challenge_cases.csv',rows)
dump('challenge_design.json',{'count':50,'selection':'Astra-selected boundary cases from already-read representative audit; frozen before repair execution','purpose':'post-audit semantic regression, not unbiased performance estimate','all_overlap_relation_audit':True,'categories':{k:len(v) for k,v in cases.items()},'sha256':hashlib.sha256((OUT/'challenge_cases.csv').read_bytes()).hexdigest()})
