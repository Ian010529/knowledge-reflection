"""Deterministic, reversible projection of reviewed partitions; no semantic inference."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import shutil

OUT = Path(__file__).resolve().parent
JUDGE = OUT.parent / 'astra_model_acceptance'
SOURCE = Path('/Users/chl/Desktop/my_project/knowledge_reflection')
RAW = SOURCE / 'stage2_reconstruction/v1'
DSH = SOURCE / 'stage2_normalization/dsh_flash_review'

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write(name, rows, fields=None):
    with (OUT / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def js(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def identifier(kind, parts):
    return kind + ':' + hashlib.sha256(js(parts).encode()).hexdigest()[:20]

def save_json(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

def build():
    inputs = {
        **{f'raw/{n}': RAW/n for n in ['node_evidence.csv','relation_evidence.csv','paper_coverage.csv','claim_evidence.csv','initial_concepts.csv','initial_normalization_assignments.csv']},
        **{f'judge/{n}': JUDGE/n for n in ['node_assignments_draft.csv','pair_judgments.csv','group_judgments.jsonl','group_review.csv','hierarchy_flag_review.csv','within_group_non_equivalent_review.csv','original_uncertain_disposition.csv','duplicate_conflict_judgment.json','input_manifest.json','progress.json','METHOD_CHANGE.md','group_acceptance.csv','role_mixture_disposition.csv']},
        'roles/evidence_cards.jsonl': DSH/'evidence_cards.jsonl',
        'roles/role_deferred.csv': SOURCE/'stage2_normalization/semantic_candidates_v2/role_deferred.csv',
    }
    hashes = {key:digest(path) for key,path in inputs.items()}
    prior = json.loads((JUDGE/'input_manifest.json').read_text())
    # Do not silently project judgments onto changed upstream evidence.
    for name, metadata in prior['files'].items():
        assert digest(DSH/name) == metadata['sha256'], ('changed judge input', name)
    for metadata in prior['supplemental_files']:
        assert digest(Path(metadata['path'])) == metadata['sha256'], metadata['path']
    run_id = identifier('normalization_draft', hashes)
    for key,path in inputs.items():
        dest=OUT/'inputs'/key
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert digest(dest)==hashes[key], ('snapshot already exists with different input; create a new draft version', key)
        else:
            shutil.copyfile(path,dest)

    nodes=read(RAW/'node_evidence.csv'); relations=read(RAW/'relation_evidence.csv')
    old=read(RAW/'initial_normalization_assignments.csv')
    reviewed=read(JUDGE/'node_assignments_draft.csv'); group_rows=read(JUDGE/'group_review.csv')
    deferred=read(inputs['roles/role_deferred.csv'])
    cards=[json.loads(line) for line in inputs['roles/evidence_cards.jsonl'].read_text().splitlines()]
    nm={r['mention_id']:r for r in nodes}; oldmap={r['mention_id']:r for r in old}
    rm={r['raw_mention_id']:r for r in reviewed}; dm={r['mention_id']:r for r in deferred}
    cm={r['mention_id']:r for r in cards}
    assert len(nm)==len(nodes)==4646 and len(relations)==2655 and len(rm)==1522
    assert set(nm)==set(oldmap)==set(cm)|set(dm) and not set(cm)&set(dm)
    assert set(rm)<=set(cm) and len(dm)==159
    partitions=collections.defaultdict(list)
    for mid in nm:
        key=rm[mid]['draft_concept_id'] if mid in rm else 'identity:'+mid
        partitions[key].append(mid)
    concepts=[]; assignments=[]; canonical={}; concept_by_id={}; role_mixed=[]
    for key,mids in sorted(partitions.items()):
        mids=sorted(mids); domains={nm[m]['domain'] for m in mids};assert len(domains)==1
        domain=next(iter(domains)); cid=identifier('draft:v2:'+domain,mids)
        label=rm[mids[0]]['judge_partition_definition'] if mids[0] in rm else nm[mids[0]]['raw_phrase']
        roles=sorted({cm[m]['role'] for m in mids if m in cm})
        deferred_here=any(m in dm for m in mids)
        if len(roles)>1:role_mixed.append(cid)
        row={'concept_id':cid,'domain':domain,'display_label':label,
             'display_label_source':'judge_partition_definition' if mids[0] in rm else 'raw_phrase',
             'member_count':len(mids),'source_mention_ids':js(mids),
             'raw_labels':js(sorted({nm[m]['raw_phrase'] for m in mids})),
             'paper_ids':js(sorted({nm[m]['paper_id'] for m in mids})),
             'source_roles':js(roles),'canonical_role':'','role_status':'deferred' if deferred_here else ('mixed_source_roles_astra_reviewed' if len(roles)>1 else 'source_role_preserved_not_newly_validated'),
             'judge_partition_id':key if mids[0] in rm else '',
             'normalization_basis':'explicit_judge_partition' if len(mids)>1 else ('reviewed_singleton' if mids[0] in rm else 'identity_only'),
             'concept_status':'draft_only','acceptance_status':'astra_reviewed' if mids[0] in rm else 'identity_only_unreviewed','required_human_review':False,'run_id':run_id}
        concepts.append(row);concept_by_id[cid]=row
        for mid in mids:
            canonical[mid]=cid
            assignments.append({'mention_id':mid,'domain':domain,'paper_id':nm[mid]['paper_id'],
                'initial_concept_id':oldmap[mid]['initial_concept_id'],'draft_concept_id':cid,
                'judge_partition_id':rm[mid]['draft_concept_id'] if mid in rm else '',
                'mapping_action':'project_to_shared_concept' if len(mids)>1 else 'retain_singleton',
                'decision_basis':row['normalization_basis'],'role_status':row['role_status'],
                'raw_label':nm[mid]['raw_phrase'],'claim_id':nm[mid]['claim_id'],
                'node_evidence_locator':'inputs/raw/node_evidence.csv::mention_id='+mid,
                'source_applied':False,'run_id':run_id})
    assert len(concept_by_id)==len(concepts)
    assignments.sort(key=lambda r:r['mention_id']);concepts.sort(key=lambda r:r['concept_id'])
    write('concepts_v2_draft.csv',concepts)
    write('normalization_assignments_v2_draft.csv',assignments)
    write('normalization_diff.csv',[dict(a,before_member_count=1,after_member_count=concept_by_id[a['draft_concept_id']]['member_count']) for a in assignments])
    write('rollback_assignments.csv',[dict(r,draft_concept_id=canonical[r['mention_id']],rollback_action='restore_exact_initial_assignment') for r in old])
    # Rich source evidence stays one row per original mention, including all original columns.
    write('node_evidence_projected.csv',[dict(r,draft_concept_id=canonical[r['mention_id']],role_deferred=r['mention_id'] in dm) for r in nodes])
    write('role_deferred_preserved.csv',[dict(r,draft_concept_id=canonical[r['mention_id']]) for r in deferred])

    projected=[]; flags=[]
    def flag(kind, ids, detail):
        ids=sorted(ids)
        flags.append({'flag_id':identifier('flag',[kind,ids]),'flag_type':kind,'relation_ids':js(ids),
                      'detail':detail,'resolution_status':'pending_context_review','automatic_action':'none'})
    exact=collections.defaultdict(list); endpoints=collections.defaultdict(list)
    for r in relations:
        s,o=r['subject_mention_id'],r['object_mention_id']
        assert s in nm and o in nm and nm[s]['domain']==nm[o]['domain']==r['domain']
        cs,co=canonical[s],canonical[o]
        deferred_edge=s in dm or o in dm; loop=cs==co; new_loop=loop and s!=o
        q=dict(r,draft_subject_concept_id=cs,draft_object_concept_id=co,
               original_self_loop=s==o,introduced_self_loop=new_loop,
               deferred_endpoint=deferred_edge,endpoint_changed=cs!=oldmap[s]['initial_concept_id'] or co!=oldmap[o]['initial_concept_id'],
               endpoint_semantically_consolidated=any(concept_by_id[x]['member_count']>1 for x in [cs,co]),
               projection_status='held_role_deferred' if deferred_edge else ('held_self_loop_review' if loop else 'draft_projection_only'),
               relation_evidence_locator='inputs/raw/relation_evidence.csv::relation_id='+r['relation_id'],
               scientific_relation_validated=False,run_id=run_id)
        projected.append(q)
        if loop:flag('introduced_self_loop' if new_loop else 'original_self_loop',[r['relation_id']],'保留原关系；核对等价分区与原始断言，不自动删除。')
        if deferred_edge:flag('deferred_role_endpoint',[r['relation_id']],'至少一端属于159个角色待核实节点，暂不进入可用关系投影。')
        key=(r['domain'],cs,co,r['raw_predicate'],r['assertion_type'],r['direction'],r['joint_factor_group'],r['condition_annotation_status'])
        exact[key].append(q);endpoints[(r['domain'],cs,co)].append(q)
    write('concept_relations_v2_draft.csv',projected)
    write('concept_relations_draft_eligible.csv',[r for r in projected if r['projection_status']=='draft_projection_only'])
    groups=[]
    for key,rr in sorted(exact.items()):
        if len(rr)>1:
            original_keys={(r['subject_mention_id'],r['object_mention_id'],r['raw_predicate'],r['assertion_type'],r['direction']) for r in rr}
            flag('projected_parallel_evidence',[r['relation_id'] for r in rr],f'{len(rr)}条证据投影为同一有向谓词/断言键；原始端点键{len(original_keys)}个。不同论文或条件不证明重复事实。')
        groups.append({'projection_group_id':identifier('relation_projection',key),'domain':key[0],
                       'subject_concept_id':key[1],'object_concept_id':key[2],'raw_predicate':key[3],
                       'assertion_type':key[4],'direction':key[5],'joint_factor_group':key[6],
                       'condition_annotation_status':key[7],'evidence_count':len(rr),
                       'relation_ids':js(sorted(r['relation_id'] for r in rr)),
                       'paper_ids':js(sorted({r['paper_id'] for r in rr})),
                       'aggregation_status':'navigation_only_no_evidence_deduplication'})
    write('relation_projection_groups.csv',groups)
    # Exact surface forms only. This is a triage detector, not relation ontology mapping.
    positive={'increases','enhances','improves','promotes','boosts','raises','strengthens','amplifies','enlarges'}
    negative={'decreases','reduces','suppresses','inhibits','lowers','weakens','limits','impairs'}
    for (domain,s,o),rr in sorted(endpoints.items()):
        predicates={r['raw_predicate'] for r in rr};ids=[r['relation_id'] for r in rr]
        if len(predicates)>1:
            flag('multiple_predicates_same_endpoints',ids,'同一概念端点有多个原谓词；只提示检查，不等同语义冲突。')
        pp=[r for r in rr if r['raw_predicate'] in positive and r['assertion_type']!='negated']
        nn=[r for r in rr if r['raw_predicate'] in negative and r['assertion_type']!='negated']
        if pp and nn:flag('opposing_surface_predicates',[r['relation_id'] for r in pp+nn],'精确谓词表命中增强/抑制方向；需核对材料、温度、机制和其他条件，不自动判矛盾。')
        for pred in predicates:
            same=[r for r in rr if r['raw_predicate']==pred]
            if any(r['assertion_type']=='negated' for r in same) and any(r['assertion_type']=='author_claim' for r in same):
                flag('assertion_polarity_candidate',[r['relation_id'] for r in same],'相同谓词出现negated与author_claim；保留语境再判。')
        reverse=endpoints.get((domain,o,s))
        if s<o and reverse:flag('reciprocal_direction_candidate',ids+[r['relation_id'] for r in reverse],'双向断言可能是反馈或不同过程，不能自动撤销任一方向。')
    write('relation_validation_flags.csv',flags,['flag_id','flag_type','relation_ids','detail','resolution_status','automatic_action'])
    save_json('relation_flag_rules.json',{'positive_exact_predicates':sorted(positive),'negative_exact_predicates':sorted(negative),
        'scope':'deterministic triage, not full semantic contradiction detection','predicates_normalized':False,
        'conditions_inferred':False,'parallel_evidence_deduplicated':False})
    mixed=[r for r in concepts if r['concept_id'] in role_mixed]
    write('concept_role_review.csv',mixed)

    # Reuse the fixed sample and its actual Astra dispositions; do not draw a new queue.
    worksheet=read(JUDGE/'group_acceptance.csv')
    assert len(worksheet)==50 and all(r['status']=='completed' for r in worksheet)
    write('astra_spotcheck_results.csv',worksheet)
    audit_nodes=[]
    for r in worksheet:
        i=int(r['group_index'])
        for mid in sorted(m for m in rm if int(rm[m]['group_index'])==i):
            audit_nodes.append(dict(nm[mid],audit_id=r['audit_id'],draft_concept_id=canonical[mid],
                draft_definition=concept_by_id[canonical[mid]]['display_label'],source_role=cm[mid]['role'],
                abstract_locator='inputs/raw/paper_coverage.csv::domain='+nm[mid]['domain']+';paper_id='+nm[mid]['paper_id']))
    write('astra_spotcheck_evidence.csv',audit_nodes)
    save_json('spotcheck_design.json',{'count':50,'members_reviewed':len(audit_nodes),
        'selection':'same frozen risk-directed sample as normalization_draft; not probability sampling',
        'acceptance_method':'astra_model_judge_replaces_human','astra_reviews_completed':50,
        'human_review_required':False,'independent_human_accuracy_measured':False,
        'replaces_frozen_200_relation_60_abstract_approximately_50_challenge_audit':False})

    for key,path in inputs.items():assert digest(path)==hashes[key],('source changed during build',key)
    summary={'run_id':run_id,'status':'draft_generated_not_applied','raw_nodes':len(nodes),'reviewed_nodes':len(rm),
        'draft_concepts':len(concepts),'node_count_reduction':len(nodes)-len(concepts),
        'identity_nodes_outside_equivalence_review':len(nodes)-len(rm),'deferred_role_nodes':len(dm),
        'raw_relations':len(relations),'projected_relations':len(projected),'projection_groups':len(groups),
        'relation_projection_status':dict(collections.Counter(r['projection_status'] for r in projected)),
        'flag_counts':dict(collections.Counter(r['flag_type'] for r in flags)),
        'mixed_role_concepts':len(mixed),'astra_spotcheck_groups':len(worksheet),
        'astra_spotchecks_completed':50,'human_review_required':False,'source_mutations':0,'formal_graph_built':False,
        'domain_counts':{domain:{'raw_nodes':sum(r['domain']==domain for r in nodes),'draft_concepts':sum(r['domain']==domain for r in concepts),'raw_relations':sum(r['domain']==domain for r in relations)} for domain in ['iTE','TG']}}
    save_json('summary.json',summary)
    save_json('input_manifest.json',{'run_id':run_id,'source_root':str(SOURCE),'inputs':[
        {'key':key,'source_path':str(path),'snapshot_path':'inputs/'+key,'sha256':hashes[key]} for key,path in inputs.items()],
        'source_hashes_unchanged':True,'script_sha256':digest(Path(__file__))})
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':build()
