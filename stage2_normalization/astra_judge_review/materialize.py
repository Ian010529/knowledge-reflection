import sys,json,csv,collections,hashlib,datetime
sys.argv=['review','none']
from review import OUT,SRC,classes,ms,ps,fs,eq,rr,cards,members,jwrite
G={x['group_index']:x for x in map(json.loads,(OUT/'group_judgments.jsonl').open())}
OV={}
p=OUT/'pair_overrides.jsonl'
for x in map(json.loads,p.open()):OV[(x['group_index'],frozenset(x['member_indices']))]=x

def decision(i,a,b):
 g=G[i]; ass={k:t for t,p in enumerate(g['partitions']) for k in p['members']}; pa,pb=g['partitions'][ass[a]],g['partitions'][ass[b]]
 if (i,frozenset([a,b])) in OV:
  o=OV[(i,frozenset([a,b]))];return o['judge_decision'],o['judge_reason']
 if ass[a]==ass[b]:return 'accept','共同定义：'+pa['definition']+'。'+g['judge_reason']
 if a in g.get('uncertain_cross_members',[]) or b in g.get('uncertain_cross_members',[]):return 'uncertain',g['uncertain_cross_reason']+'；左：'+pa['definition']+'；右：'+pb['definition']
 return g['cross_partition_decision'],'左：'+pa['definition']+'；右：'+pb['definition']+'。'+g['judge_reason']

def csvout(name,data,fields=None):
 if not data and not fields:return
 with (OUT/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(data[0]));w.writeheader();w.writerows(data)

pairs=[]; assignments=[]; evidence=[];risk=[]
for i,c in enumerate(classes):
 if i not in G:continue
 cid=c['class_id']; mm=ms[cid];idx={m['mention_id']:k for k,m in enumerate(mm)};g=G[i]
 ass={k:t for t,p in enumerate(g['partitions']) for k in p['members']}
 for k,m in enumerate(mm):
  p=g['partitions'][ass[k]]; assignments.append({'class_id':cid,'group_index':i,'raw_mention_id':m['mention_id'],'label':m['label'],'draft_concept_id':f'astra:g{i:03d}:p{ass[k]:03d}','judge_partition_definition':p['definition'],'partition_size':len(p['members']),'judge_status':'accepted_group_equivalence' if len(p['members'])>1 else 'retained_singleton','merge_applied':False,'reversible':True})
  ce=cards[m['mention_id']]
  evidence.append({'raw_mention_id':m['mention_id'],'class_id':cid,'paper_id':m['paper_id'],'source_file':str(SRC/'evidence_cards.jsonl'),'source_locator':'mention_id='+m['mention_id'],'quote':ce['quote'],'context':ce['context'],'source_quote_start':ce['quote_start'],'source_quote_end':ce['quote_end']})
 for p in ps[cid]:
  a,b=idx[p['left_mention_id']],idx[p['right_mention_id']];d,r=decision(i,a,b)
  pairs.append({'pair_id':p['pair_id'],'class_id':cid,'group_index':i,'domain':p['domain'],'left_mention_id':p['left_mention_id'],'right_mention_id':p['right_mention_id'],'left_label':p['left_label'],'right_label':p['right_label'],'judge_decision':d,'judge_relation':'equivalent_to' if d=='accept' else ('uncertain' if d=='uncertain' else 'not_equivalent'),'judge_reason':r,'left_evidence':p['left_evidence'],'right_evidence':p['right_evidence'],'left_evidence_locator':str(SRC/'evidence_cards.jsonl')+'::mention_id='+p['left_mention_id'],'right_evidence_locator':str(SRC/'evidence_cards.jsonl')+'::mention_id='+p['right_mention_id'],'judge_group_record':'group_judgments.jsonl::group_index='+str(i),'dsh_relation':'equivalent_to','dsh_reason':p['reason'],'judge_model':'gpt-6-astra','judge_reasoning_effort':'high','merge_applied':False})
 for flag in fs[cid]:
  old=rr[flag['detail_pair_id']];a,b=idx[old['left_mention_id']],idx[old['right_mention_id']];d,r=decision(i,a,b)
  risk.append({'class_id':cid,'group_index':i,'pair_id':old['pair_id'],'left_mention_id':old['left_mention_id'],'right_mention_id':old['right_mention_id'],'dsh_relation':old['relation'],'dsh_reason':old['reason'],'judge_equivalence_decision':d,'judge_risk_disposition':{'accept':'hierarchy_warning_rejected_by_shared_definition','reject':'keep_separate_hierarchy_direction_not_asserted','uncertain':'unresolved_do_not_merge'}[d],'judge_reason':r,'judge_hierarchy_direction':'not_adjudicated_as_formal_relation','source_locator':str(SRC/'review_results.csv')+'::pair_id='+old['pair_id']})

csvout('pair_judgments.csv',pairs);csvout('node_assignments_draft.csv',assignments);csvout('node_evidence.csv',evidence);csvout('hierarchy_flag_review.csv',risk)
csvout('accepted_pairs_draft.csv',[p for p in pairs if p['judge_decision']=='accept']);csvout('unresolved_equivalence_pairs.csv',[p for p in pairs if p['judge_decision']=='uncertain'])
count=collections.Counter(x['judge_decision'] for x in pairs)
report={'status':'independent_semantic_pass_complete' if len(G)==len(classes) else 'in_progress','model':'gpt-6-astra','reasoning_effort':'high','completed_groups':len(G),'remaining_groups':len(classes)-len(G),'completed_original_equivalent_pairs':len(pairs),'remaining_original_equivalent_pairs':len(eq)-len(pairs),'pair_decision_counts':dict(count),'reviewed_raw_nodes':len(evidence),'hierarchy_flags_materialized':len(risk),'secondary_comparison_complete':False,'duplicate_conflict_complete':False,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
jwrite(OUT/'progress.json',report)
assert len({p['pair_id'] for p in pairs})==len(pairs)
assert {p['pair_id'] for p in pairs}=={p['pair_id'] for p in eq}
assert len(G)==340 and len(evidence)==1522 and len(pairs)==3268 and len(risk)==403
# Never derive semantic decisions from labels: this checks consistency of the manually specified records.
conflicts=[]
assign={a['raw_mention_id']:a['draft_concept_id'] for a in assignments}
for p in pairs:
 if (p['judge_decision']=='accept')!=(assign[p['left_mention_id']]==assign[p['right_mention_id']]):conflicts.append(p['pair_id'])
assert not conflicts,conflicts
jwrite(OUT/'coverage_check.json',{'expected_pairs':3268,'unique_pairs':len(pairs),'missing_pairs':[],'extra_pairs':[],'duplicate_pairs':[],'groups':len(G),'raw_nodes':len(evidence),'risk_edges':len(risk),'assignment_pair_contradictions':conflicts,'structural_checks_passed':True,'semantic_accuracy_measured':False})
print(json.dumps(report,ensure_ascii=False))
