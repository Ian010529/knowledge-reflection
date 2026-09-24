import sys, json, datetime
sys.argv=['review','none']
from review import OUT,classes,ms
P=OUT/'group_judgments.jsonl'
def record(i,decision,definition,reason,partitions=None):
 mm=ms[classes[i]['class_id']]
 if partitions is None: partitions=[{'definition':definition,'members':list(range(len(mm)))}] if decision=='accept' else [{'definition':m['label'],'members':[k]} for k,m in enumerate(mm)]
 seen=[k for p in partitions for k in p['members']];assert sorted(seen)==list(range(len(mm)))
 x={'group_index':i,'class_id':classes[i]['class_id'],'judge_decision':decision,'concept_definition':definition,'judge_reason':reason,'partitions':[dict(p,raw_mention_ids=[mm[k]['mention_id'] for k in p['members']]) for p in partitions],'cross_partition_decision':'uncertain' if decision=='uncertain' else 'reject','review_scope':'all listed members and all proposed edges; equality within each partition justified by its shared definition, not graph closure','phase':'independent_evidence_first','timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 old=[json.loads(s) for s in P.read_text().splitlines()] if P.exists() else []
 assert i not in [a['group_index'] for a in old],i
 with P.open('a') as f:f.write(json.dumps(x,ensure_ascii=False)+'\n')
def revise(i,decision,definition,reason,source):
 old=[json.loads(s) for s in P.read_text().splitlines()]; previous=next(x for x in old if x['group_index']==i)
 with (OUT/'revision_history.jsonl').open('a') as f:f.write(json.dumps(previous,ensure_ascii=False)+'\n')
 P.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in old if x['group_index']!=i))
 record(i,decision,definition,reason)
 old=[json.loads(s) for s in P.read_text().splitlines()]; old[-1]['additional_evidence']=source
 P.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in old))
def override(i,a,b,decision,reason):
 with (OUT/'pair_overrides.jsonl').open('a') as f:f.write(json.dumps({'group_index':i,'member_indices':[a,b],'judge_decision':decision,'judge_reason':reason},ensure_ascii=False)+'\n')
def uncertain_members(i,indices,reason):
 old=[json.loads(s) for s in P.read_text().splitlines()]
 x=next(x for x in old if x['group_index']==i);x['uncertain_cross_members']=indices;x['uncertain_cross_reason']=reason
 P.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in old))
