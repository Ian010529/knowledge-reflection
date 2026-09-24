"""Carry explicit context judgments forward and add model modality annotations."""
from build_draft import OUT,read,write,save_json
import shutil,json
old=OUT.parent/'normalization_draft'
prior={r['flag_id']:r for r in read(old/'relation_context_review.csv')}
flags=read(OUT/'relation_validation_flags.csv')
rows=[]
for f in flags:
 if f['flag_type']=='deferred_role_endpoint':continue
 assert f['flag_id'] in prior,('new flag requires semantic review',f['flag_id'])
 r=dict(prior[f['flag_id']])
 assert r['relation_ids']==f['relation_ids']
 r['human_review_status']='not_required_user_selected_astra'
 r['resolution_status']='model_context_review_completed'
 if f['flag_id']=='flag:cd92f548e49308bead68':
  r['resolution_status']='model_review_complete_independence_uncertain'
  r['judge_reason']+='；模型验收结论为来源独立性未证实，保留两条出处并标记禁止按两次独立验证计权，不另设人工门槛。'
 if f['flag_id']=='flag:1127e629f737df492d08':
  r['judge_disposition']='computational_prediction_modality_annotated'
  r['judge_reason']='两篇摘要均明确计算/预测n型掺杂提高功率因子。模型在新投影中为两条关系增加computational_prediction限定；保留原author_claim/hypothesis字段以便回滚，不将author_claim解释为实验验证。'
 rows.append(r)
write('relation_context_review.csv',rows)
shutil.copyfile(old/'context_review_supplemental_abstracts.csv',OUT/'context_review_supplemental_abstracts.csv')
annotations=[]
for name in ['concept_relations_v2_draft.csv','concept_relations_draft_eligible.csv']:
 rr=read(OUT/name)
 for r in rr:
  rid=r['relation_id']
  r['judge_evidence_modality']='computational_prediction' if rid in ['iTE:P1510:r001','iTE:P1516:r001'] else 'not_reclassified'
  r['judge_evidence_independence']='undetermined_do_not_double_count' if rid in ['iTE:P1371:r001','iTE:P1440:r001'] else 'not_assessed'
  if name=='concept_relations_v2_draft.csv' and (r['judge_evidence_modality']!='not_reclassified' or r['judge_evidence_independence']!='not_assessed'):
   annotations.append({k:r[k] for k in ['relation_id','assertion_type','raw_predicate','quote','judge_evidence_modality','judge_evidence_independence','relation_evidence_locator']})
 write(name,rr)
write('relation_model_annotations.csv',annotations)
save_json('context_review_summary.json',{'active_flags_reviewed':len(rows),'prior_flags_reviewed':21,
 'one_temperature_gradient_collision_removed_by_partition_revision':True,
 'computational_prediction_annotations':2,'source_independence_uncertain_annotations':2,
 'required_human_review':False,'original_assertion_columns_preserved':True,
 'scope':'model review of structural flags, not the planned full extraction audit'})
print('20 active context flags reviewed; prediction and source-dependence limits recorded.')
