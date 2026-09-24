import json,csv,collections,hashlib,copy,datetime
from pathlib import Path
D=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
labels=read(D/'match_labels.json'); byid={x['pair_id']:x for x in labels}; extra=read(D/'initial_extra_packet.json')
extra_judgments={
'PAIR-b6079fd74196':(1,'uncertain','右侧把低热导率纳入 power factor 联合归因，证据归因待定；不能按共享两项因素判完整对应。'),
'PAIR-e42b47f245fa':(0,'supported_as_qualified','扩散限制与固液相变、迁移差与功率均不同。'),
'PAIR-deaf44b583e8':(0,'supported_as_qualified','热泳差/Seebeck 与界面电荷转移阻力/短路电流不同。'),
'PAIR-29c37d29990c':(1,'uncertain','右侧额外纳入低热导率对 power factor 的归因，不能删去该歧义后视为完整等价。')}
for p in extra:
 level,source,why=extra_judgments[p['pair_id']]
 byid[p['pair_id']]=dict(pair_id=p['pair_id'],review_id='initial-extra-'+p['review_id'],relation_match=level,left_source='supported_as_qualified',right_source=source,strict_positive=False,condition_compatibility='insufficient',rationale=why,judge='Astra')
(D/'initial_extra_labels.json').write_text(json.dumps([byid[p['pair_id']] for p in extra],ensure_ascii=False,indent=2)+'\n')
metrics=[]
for version,path in [('initial',D/'initial_run'),('reviewed',D)]:
 rankings=read(path/'rankings.json');scores={r['pair_id']:r for r in csv.DictReader(open(path/'candidate_scores.csv'))}
 for method,ids in rankings.items():
  for k in (20,50):
   top=ids[:k];js=[byid[i] for i in top];pos=sum(j['strict_positive'] for j in js)
   metrics.append(dict(version=version,method=method,k=k,returned=len(top),strict_positives=pos,precision_at_k=pos/k if len(top)==k else None,precision_among_returned=pos/len(top) if top else None,positive_yield_per_k=pos/k,partial=sum(j['relation_match']==1 for j in js),nonmatch=sum(j['relation_match']==0 for j in js),paper_pairs=len({(scores[i]['iTE_paper'],scores[i]['TG_paper']) for i in top}),positive_paper_pairs=len({(scores[i]['iTE_paper'],scores[i]['TG_paper']) for i in top if byid[i]['strict_positive']})))
(D/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')
with open(D/'metrics.csv','w') as f:
 w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
# Technical validation and graph provenance statistics, not semantic accuracy.
papers=read(D/'input_papers.json');ps={p['paper_id']:p for p in papers};rs=read(D/'extraction_reviewed.json');initial=read(D/'extraction_initial.json');changes=read(D/'review_changes.json')
for manifest in ['extraction_freeze.json','matching_freeze.json']:
 for f,h in read(D/manifest).items():assert hashlib.sha256((D/f).read_bytes()).hexdigest()==h,(manifest,f)
assert len({r['relation_id'] for r in rs})==len(rs)
for r in rs:
 p=ps[r['paper_id']];assert p['abstract'][r['char_start']:r['char_end']]==r['quote'];assert hashlib.sha256(p['abstract'].encode()).hexdigest()==r['input_hash']
 assert r['subject']['concept_id'].startswith(r['domain']+'-') and r['object']['concept_id'].startswith(r['domain']+'-')
 assert bool(r['joint_factors'])==bool(r['joint_factor_group'])
scopes={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics'}
main=[r for r in rs if r['review_status']=='accepted' and r['analysis_scope'] in scopes];motifs=[]
for a in main:
 for b in main:
  if a['relation_id']!=b['relation_id'] and a['paper_id']==b['paper_id'] and a['object']['concept_id']==b['subject']['concept_id']:
   motifs.append(dict(paper_id=a['paper_id'],domain=a['domain'],first=a['relation_id'],second=b['relation_id'],shared=a['object']['canonical_label'],provenance='same_paper_explicit_two_edge_path; not proof of transitive causation'))
(D/'same_paper_two_edge_paths.json').write_text(json.dumps(motifs,ensure_ascii=False,indent=2)+'\n')
comparison=read(D/'old_to_new_comparison.json');old=read(D/'old_relation_evidence.json');mr=read(D/'run_metadata.json')
# Largest repeated source pair and the effect of review on each method's top list.
scores={r['pair_id']:r for r in csv.DictReader(open(D/'candidate_scores.csv'))};ranks=read(D/'rankings.json');iranks=read(D/'initial_run/rankings.json')
top_changes={m:{str(k):len(set(ranks[m][:k])-set(iranks[m][:k])) for k in [20,50]} for m in ranks}
concentration={m:collections.Counter((scores[p]['iTE_paper'],scores[p]['TG_paper']) for p in ids[:20]).most_common(3) for m,ids in ranks.items()}
q=dict(status='development_pilot_complete_not_release',technical_checks_pass=True,quote_spans_verified=len(rs),input_paper_count=len(papers),source_membership={dom:dict(collections.Counter(p['source_membership'] for p in papers if p['domain']==dom)) for dom in ['iTE','TG']},initial_relations=len(initial),reviewed_relations=len(rs),main_relation_records=len(main),review_change_counts=dict(collections.Counter(c['action'] for c in changes)),same_paper_two_edge_paths=len(motifs),path_counts_by_domain=dict(collections.Counter(x['domain'] for x in motifs)),old_comparison_statuses=dict(collections.Counter(x['status'] for x in comparison)),match_labels=len(labels),match_levels=dict(collections.Counter(x['relation_match'] for x in labels)),strict_positive_relations=sum(x['strict_positive'] for x in labels),strict_positive_paper_pairs=2,all_conditions_insufficient=True,top_k_new_pairs_after_review=top_changes,top20_paper_pair_concentration=concentration,independent_precision_recall_available=False,formal_quality_gate_passed=False,paid_api_calls=0)
(D/'quality_summary.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(q,ensure_ascii=False));print(json.dumps(metrics,ensure_ascii=False))
