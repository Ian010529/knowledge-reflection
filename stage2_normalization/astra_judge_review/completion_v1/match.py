from work import *
refs=[json.loads(s) for s in (OUT/'abstract_reference.jsonl').read_text().splitlines()]
def match(i,decisions):
 r=refs[i];assert len(decisions)==len(r['reference_claims']),(i,len(decisions),len(r['reference_claims']))
 for c,(status,ids,reason) in zip(r['reference_claims'],decisions):
  rr=[f"{r['domain']}:{r['paper_id']}:r{x:03d}" for x in ids];assert all(x in rm for x in rr)
  append('abstract_recall_judgments.jsonl',{'sample_index':i,'domain':r['domain'],'paper_id':r['paper_id'],'reference_id':c['reference_id'],'baseline_coverage':status,'matched_relation_ids':rr,'reason':reason,'judge_model':'gpt-6-astra'})
if __name__=='__main__':
 for r in refs[int(sys.argv[1]):int(sys.argv[2])]:
  print('\nPAPER',r['sample_index'],r['domain'],r['paper_id'])
  for c in r['reference_claims']:print('REF',c['reference_id'].rsplit('_',1)[1],c['subject'],'|',c['predicate'],'|',c['object'])
  for x in relations:
   if (x['domain'],x['paper_id'])==(r['domain'],r['paper_id']):print('RAW',x['relation_id'],nm[x['subject_mention_id']]['raw_phrase'],'|',x['raw_predicate'],'|',nm[x['object_mention_id']]['raw_phrase'],'|',x['assertion_type'],'|',x['quote'])
