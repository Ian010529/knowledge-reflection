from work import *
pending_original=[r for r in read(OUT/'inputs/original_uncertain_disposition.csv') if r['judge_decision']=='uncertain']
pending_groups=[r for r in read(OUT/'inputs/pair_judgments.csv') if r['judge_decision']=='uncertain']
def pair(i,decision,reason,relation=None):
 r=pending_original[i];record(r,decision,reason,relation,source='original_uncertain',index=i)
def record(r,decision,reason,relation=None,**extra):
 assert decision in ('accept','reject','uncertain')
 append('equivalence_followup.jsonl',{'pair_id':r['pair_id'],'left_mention_id':r['left_mention_id'],'right_mention_id':r['right_mention_id'],'decision':decision,'semantic_relation':relation or {'accept':'equivalent_to','reject':'distinct_from','uncertain':'uncertain'}[decision],'reason':reason,'review_status':'astra_adjudicated','human_review_required':False,'judge_model':'gpt-6-astra',**extra})
if __name__=='__main__':
 for i in range(int(sys.argv[1]),int(sys.argv[2])):
  r=pending_original[i];print('\nPAIR',i,r['left_mention_id'],r['left_label'],'|',r['right_mention_id'],r['right_label']);print('L',r['left_evidence']);print('R',r['right_evidence'])
