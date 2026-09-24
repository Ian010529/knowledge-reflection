"""Bookkeeping and consistency checks for assistant-authored judgments."""
import csv,json,hashlib,collections,datetime
from materialize import OUT,SRC,G,classes,ms,rr,cards,pairs,risk,assignments,decision,csvout,jwrite
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
manifest=json.loads((OUT/'input_manifest.json').read_text())
for n,meta in manifest['files'].items():
 assert hashlib.sha256((SRC/n).read_bytes()).hexdigest()==meta['sha256'],n
manifest['end_verification_utc']=now
manifest['initial_input_hashes_unchanged']=True
root=SRC.parents[1]
supp=[SRC/'historical_disagreements.csv',root/'stage2_reconstruction/v1/paper_coverage.csv',root/'stage2_reconstruction/v1/node_evidence.csv']
supp += [SRC/f'results/batches/{b}.json' for b in ['b00290a','b00290']]
manifest['supplemental_files']=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'hash_recorded':'end_of_review'} for p in supp]
jwrite(OUT/'input_manifest.json',manifest)

# This is the manually maintained list of full abstracts consulted, not a semantic filter.
tg='0253 0254 0192 0143 0111 0079 0247 0272 0319 0085 0090 0156 0173 0182 0204 0210 0221 0215 0104 0119'.split()
ite='0931 1503 1552 1221 1241 1712 0465 1263 0384 0409 0478 0508 0626 0688 0815 0858 1482 1666 0448 0507 1472 0949 0999 1490 1571 1883 0439 0481 0512 0717 0842 0876 1209 1708 0502 0515 0738 1090 1557 1565 1644 1692 1952 0687 1454 0377 0399 0518 0943 0944 0959 1071 1270 1359 1435 1599 1639 1686 1754 1772 1903 1964 0334 0345 0413 0446 0498 0547 0595 0660 0743 0768 0965 0988 1035 1210 1479 1676 1711 0533'.split()
keys={('TG','P'+x) for x in tg}|{('iTE','P'+x) for x in ite}
abstract_source=root/'stage2_reconstruction/v1/paper_coverage.csv'
abstracts=[]
for row in csv.DictReader(abstract_source.open(encoding='utf-8-sig')):
 if (row['domain'],row['paper_id']) in keys:
  abstracts.append({k:row[k] for k in ['domain','paper_id','title','doi','abstract','abstract_sha256','corpus_path','corpus_csv_row']})
  abstracts[-1]['source_locator']=str(abstract_source)+'::domain='+row['domain']+';paper_id='+row['paper_id']
assert len(abstracts)==len(keys),(len(abstracts),len(keys))
csvout('supplemental_abstract_evidence.csv',abstracts)

# Explicit judge ruling for the sole semantically conflicting duplicate.
pid='pair:f796dcff03115df7a583'
variants=[]
for b in ['b00290a','b00290']:
 p=SRC/f'results/batches/{b}.json'
 result=next(x for x in json.loads(p.read_text())['results'] if x['pair_id']==pid)
 variants.append({'batch_id':b,'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'result':result})
jwrite(OUT/'duplicate_conflict_judgment.json',{'pair_id':pid,'judge_relation':'related_to','judge_equivalence_decision':'reject','judge_reason':'P1062是材料热导率测量，P1481明确为晶格热导率kl。晶格热导是总热导的组成分量，整体—部分关系不能替换为is-a，也不是严格等价。b00290a的related_to判断成立；b00290的broader_than将分量误当下位概念。','variants':variants,'evidence':[cards[x] for x in ['iTE:P1062:n2','iTE:P1481:n2']],'judge_model':'gpt-6-astra','judge_reasoning_effort':'high','merge_applied':False,'formal_relation_applied':False})

index={m['mention_id']:(i,k) for i,c in enumerate(classes) for k,m in enumerate(ms[c['class_id']])}
assign={a['raw_mention_id']:a['draft_concept_id'] for a in assignments}
old_uncertain=list(csv.DictReader((SRC/'uncertain_list.csv').open()))
u=[]
for row in old_uncertain:
 d='uncertain';why='按授权保留原待定项；本轮未独立裁决该对，不进入接受边清单。';mode='retained_pending_without_new_pair_adjudication'
 if row['pair_id']=='pair:bf22258f47c01cfb6bde':
  d='accept';mode='individually_rechecked_with_full_abstracts'
  why='补读P0533全文摘要，electrical与ionic导电明确分列，前者对应电子输运；P0944为金属离子液体/SWCNT薄膜电子电导及功率因子，5029.86 S/cm。两者均为电子电导率，与group 1共同定义一致。'
 elif row['pair_id']=='pair:fec0b8d3a1f45d17cfd3':
  mode='individually_rechecked_with_group_definition'
  why='group 94的performance没有相同评价函数和指标范围，继续待定。'
 same=row['left_mention_id'] in assign and row['right_mention_id'] in assign and assign[row['left_mention_id']]==assign[row['right_mention_id']]
 assert not same or d=='accept',row['pair_id']
 u.append({'pair_id':row['pair_id'],'left_mention_id':row['left_mention_id'],'right_mention_id':row['right_mention_id'],'left_label':cards[row['left_mention_id']]['label'],'right_label':cards[row['right_mention_id']]['label'],'judge_decision':d,'judge_reason':why,'review_mode':mode,'dsh_reason':row['reason'],'left_evidence':row['left_evidence'],'right_evidence':row['right_evidence'],'source_locator':str(SRC/'uncertain_list.csv')+'::pair_id='+row['pair_id'],'merge_applied':False})
assert len(u)==138
csvout('original_uncertain_disposition.csv',u)
csvout('supplemental_accepted_pairs_draft.csv',[r for r in u if r['judge_decision']=='accept'])

# The secondary pass read all hierarchy rationales and 118 nonhierarchy rationales
# that contradicted a first-pass partition. Other rows expose inherited decisions.
queue=json.loads((OUT/'secondary_conflict_queue.json').read_text())
read_ids={r['pair_id'] for r in queue}|{r['pair_id'] for r in risk}
secondary=[]
for old in rr.values():
 a=index.get(old['left_mention_id']);b=index.get(old['right_mention_id'])
 if not a or not b or a[0]!=b[0] or old['relation']=='equivalent_to':continue
 d,why=decision(a[0],a[1],b[1])
 secondary.append({'pair_id':old['pair_id'],'group_index':a[0],'left_mention_id':old['left_mention_id'],'right_mention_id':old['right_mention_id'],'dsh_relation':old['relation'],'dsh_reason':old['reason'],'judge_equivalence_decision':d,'judge_reason':why,'secondary_rationale_read':old['pair_id'] in read_ids,'review_basis':'independent member evidence and explicit group definitions; targeted secondary rationale comparison','formal_relation_applied':False})
csvout('within_group_non_equivalent_review.csv',secondary)
for r in secondary:
 same=assign[r['left_mention_id']]==assign[r['right_mention_id']]
 assert same==(r['judge_equivalence_decision']=='accept'),r['pair_id']
group_rows=[]
for i,c in enumerate(classes):
 g=G[i];gp=[p for p in pairs if p['group_index']==i];counts=collections.Counter(p['judge_decision'] for p in gp)
 group_rows.append({'group_index':i,'class_id':c['class_id'],'original_members':len(ms[c['class_id']]),'original_equivalent_edges':len(gp),'priority_incomplete_or_inconsistent':i in manifest['priority_group_indices'],'judge_decision':g['judge_decision'],'draft_partitions':len(g['partitions']),'accepted_edges':counts['accept'],'rejected_edges':counts['reject'],'uncertain_edges':counts['uncertain'],'judge_reason':g['judge_reason'],'secondary_review_note':g.get('secondary_review_note',''),'status':'reviewed','merge_applied':False})
csvout('group_review.csv',group_rows)

hist=list(csv.DictReader((SRC/'historical_disagreements.csv').open()))
assert len(hist)==777
jwrite(OUT/'secondary_comparison_summary.json',{'mode':'targeted_rationale_comparison_after_complete_independent_semantic_pass','hierarchy_rationales_read':403,'nonhierarchy_conflicting_rationales_read':len(queue),'within_group_non_equivalent_rows':len(secondary),'original_equivalent_rationales':'preserved per pair for audit; not all 3268 rationales were separately reread in secondary pass','historical_disagreements':777,'historical_disagreements_disposition':'diagnostic_only_not_a_forced_queue_or_gold_standard','revised_groups':[0,3,10,11,21,32],'duplicate_conflicts_resolved':1})
progress=json.loads((OUT/'progress.json').read_text())
progress.update({'status':'completed_with_explicit_uncertainties','secondary_comparison_complete':True,'secondary_comparison_scope':'targeted: 403 hierarchy reasons + 118 conflicting nonhierarchy reasons; original 3268 equivalence reasons retained, not all reread','duplicate_conflict_complete':True,'original_uncertain_disposition':dict(collections.Counter(r['judge_decision'] for r in u)),'supplemental_accepted_pairs':1,'historical_disagreements_diagnostic_only':777,'merge_applied':False,'formal_graph_constructed':False,'timestamp_utc':now})
jwrite(OUT/'progress.json',progress)
coverage=json.loads((OUT/'coverage_check.json').read_text())
coverage.update({'priority_groups_reviewed':sum(r['priority_incomplete_or_inconsistent'] for r in group_rows),'other_groups_reviewed':sum(not r['priority_incomplete_or_inconsistent'] for r in group_rows),'original_uncertain_rows':len(u),'original_uncertain_mapping_contradictions':0,'within_group_non_equivalent_mapping_contradictions':0,'all_initial_source_hashes_unchanged':True,'supplemental_full_abstracts':len(abstracts),'draft_concepts':len(set(assign.values())),'nodes_in_non_singleton_draft_partitions':sum(a['partition_size']>1 for a in assignments),'human_accuracy_or_human_agreement_measured':False})
jwrite(OUT/'coverage_check.json',coverage)
print(json.dumps({'progress':progress,'coverage':coverage,'hierarchy':dict(collections.Counter(r['judge_risk_disposition'] for r in risk))},ensure_ascii=False,indent=2))
