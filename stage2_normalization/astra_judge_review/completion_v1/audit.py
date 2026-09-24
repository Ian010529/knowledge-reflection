from work import *
def judge(i,status,reason,modality='as_reported',scope='intrinsic_material_mechanism',joint='',repair=''):
 a=sample[i];assert status in ('supported','qualify','reject','uncertain')
 append('relation_audit_judgments.jsonl',{'sample_index':i,'relation_id':a['relation_id'],'domain':a['domain'],'paper_id':a['paper_id'],'baseline_status':status,'strict_correct':status=='supported','reason':reason,'evidence_modality':modality,'analysis_scope':scope,'joint_factor_requirement':joint,'repair_instruction':repair,'judge_model':'gpt-6-astra','judge_reasoning_effort':'high'})
if __name__=='__main__':
 for i in range(int(sys.argv[1]),int(sys.argv[2])):
  a=sample[i];print('\nAUDIT',i,a['relation_id'],a['subject'],'|',a['predicate'],'|',a['object'],'|',a['assertion_type']);print('EVIDENCE',a['quote'])
