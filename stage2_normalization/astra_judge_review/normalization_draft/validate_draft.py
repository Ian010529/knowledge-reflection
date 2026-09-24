"""Verify lossless projection, reversibility, and semantic decision constraints."""
import collections
import json
from pathlib import Path
from build_draft import OUT, read, digest, save_json

manifest=json.loads((OUT/'input_manifest.json').read_text())
for item in manifest['inputs']:
    assert digest(Path(item['source_path']))==item['sha256'], item['source_path']
    assert digest(OUT/item['snapshot_path'])==item['sha256'], item['snapshot_path']

def same_original_rows(before,after,key):
    b={r[key]:r for r in before};a={r[key]:r for r in after}
    assert len(b)==len(before) and len(a)==len(after) and set(a)==set(b),key
    for rid,r in b.items():assert {k:a[rid][k] for k in r}==r,(key,rid)

rawnodes=read(OUT/'inputs/raw/node_evidence.csv');rawrels=read(OUT/'inputs/raw/relation_evidence.csv')
nodes=read(OUT/'node_evidence_projected.csv');rels=read(OUT/'concept_relations_v2_draft.csv')
assign=read(OUT/'normalization_assignments_v2_draft.csv');concepts=read(OUT/'concepts_v2_draft.csv')
same_original_rows(rawnodes,nodes,'mention_id');same_original_rows(rawrels,rels,'relation_id')
rollback=read(OUT/'rollback_assignments.csv');initial=read(OUT/'inputs/raw/initial_normalization_assignments.csv')
same_original_rows(initial,rollback,'mention_id')
am={r['mention_id']:r for r in assign};cm={r['concept_id']:r for r in concepts}
assert len(am)==4646 and len(cm)==3740 and len(rels)==2655
seen=[]
for c in concepts:
    mids=json.loads(c['source_mention_ids']);assert len(mids)==int(c['member_count'])
    seen+=mids
    for m in mids:assert am[m]['draft_concept_id']==c['concept_id'] and am[m]['domain']==c['domain']
assert len(seen)==len(set(seen))==len(am) and set(seen)==set(am)
judge=read(OUT/'inputs/judge/node_assignments_draft.csv')
jm={r['raw_mention_id']:r for r in judge};forward=collections.defaultdict(set);back=collections.defaultdict(set)
for m,r in jm.items():
    forward[r['draft_concept_id']].add(am[m]['draft_concept_id'])
    back[am[m]['draft_concept_id']].add(r['draft_concept_id'])
assert all(len(x)==1 for x in forward.values()) and all(len(x)==1 for x in back.values())
for m,r in am.items():
    if m not in jm:assert int(cm[r['draft_concept_id']]['member_count'])==1
for file,field in [('pair_judgments.csv','judge_decision'),('within_group_non_equivalent_review.csv','judge_equivalence_decision'),('original_uncertain_disposition.csv','judge_decision')]:
    for r in read(OUT/'inputs/judge'/file):
        same=am[r['left_mention_id']]['draft_concept_id']==am[r['right_mention_id']]['draft_concept_id']
        assert same==(r[field]=='accept'),r['pair_id']
dm={r['mention_id'] for r in read(OUT/'inputs/roles/role_deferred.csv')}
claims={r['claim_id'] for r in read(OUT/'inputs/raw/claim_evidence.csv')}
papers={(r['domain'],r['paper_id']) for r in read(OUT/'inputs/raw/paper_coverage.csv')}
for r in rels:
    s,o=r['subject_mention_id'],r['object_mention_id'];cs,co=r['draft_subject_concept_id'],r['draft_object_concept_id']
    assert cs==am[s]['draft_concept_id'] and co==am[o]['draft_concept_id']
    assert cm[cs]['domain']==cm[co]['domain']==r['domain']
    assert r['claim_id'] in claims and (r['domain'],r['paper_id']) in papers
    assert (r['deferred_endpoint']=='True')==(s in dm or o in dm)
    assert r['scientific_relation_validated']=='False'
for r in nodes:assert r['claim_id'] in claims and (r['domain'],r['paper_id']) in papers
eligible=read(OUT/'concept_relations_draft_eligible.csv')
assert {r['relation_id'] for r in eligible}=={r['relation_id'] for r in rels if r['projection_status']=='draft_projection_only'}
assert all(r['deferred_endpoint']=='False' and r['introduced_self_loop']=='False' for r in eligible)
group_ids=[rid for r in read(OUT/'relation_projection_groups.csv') for rid in json.loads(r['relation_ids'])]
assert len(group_ids)==len(set(group_ids))==2655
assert set(group_ids)=={r['relation_id'] for r in rawrels}
queue=read(OUT/'normalization_spotcheck_queue.csv')
assert len(queue)==len({r['group_index'] for r in queue})==50
assert all(not any(r[k] for k in ['human_decision','human_reason','reviewer','reviewed_at']) for r in queue)
context=read(OUT/'relation_context_review.csv')
flags=read(OUT/'relation_validation_flags.csv')
assert {r['flag_id'] for r in context}=={r['flag_id'] for r in flags if r['flag_type']!='deferred_role_endpoint'}
result={'status':'passed','raw_node_rows_preserved':4646,'raw_relation_rows_preserved':2655,
    'initial_assignments_roundtrip_exact':True,'cross_domain_merges':0,'lost_quotes_or_original_columns':0,
    'rejected_or_uncertain_pairs_indirectly_merged':0,'judge_partitions_changed':0,
    'deferred_nodes_kept_singleton':len(dm),'deferred_relations_held':len(rels)-len(eligible),
    'new_self_loops':sum(r['introduced_self_loop']=='True' for r in rels),
    'all_relation_and_paper_foreign_keys_valid':True,'source_and_snapshot_hashes_unchanged':True,
    'normalization_human_queue':50,'model_context_flags_reviewed':len(context),'human_reviews_completed':0,
    'semantic_accuracy_measured':False,'formal_graph_ready':False}
save_json('validation_report.json',result)
print(json.dumps(result,ensure_ascii=False,indent=2))
