from work import *
ROLES={'m':'material_entity','d':'design_strategy','c':'condition','i':'interaction','p':'mechanism_process','s':'state_structure','q':'quantity','e':'descriptor','f':'performance_function','a':'application'}
def role(i,code,reason,definition='context_scoped'):
 r=deferred[i];assert code in ROLES
 append('role_judgments.jsonl',{'index':i,'mention_id':r['mention_id'],'domain':r['domain'],'raw_phrase':r['raw_phrase'],'accepted_role':ROLES[code],'reason':reason,'definition_status':definition,'role_review_status':'astra_accepted','human_review_required':False,'normalization_policy':'retain_singleton_unless_explicit_equivalence_approved','judge_model':'gpt-6-astra'})
if __name__=='__main__':
 for i in range(int(sys.argv[1]),int(sys.argv[2])):
  r=deferred[i];print('\nROLE',i,r['mention_id'],r['raw_phrase']);print(r['quote'])
