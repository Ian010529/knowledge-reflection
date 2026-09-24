"""Project authored judgments, preserving raw evidence; never infer semantic acceptance."""
from work import *
from roles import ROLES
from reference_roles import roles as refroles
import re
FINAL=OUT/'final';FINAL.mkdir(exist_ok=True)
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def js(x):return json.dumps(x,ensure_ascii=False,sort_keys=True)
def hid(prefix,x):return prefix+hashlib.sha256(js(x).encode()).hexdigest()[:20]
def write(name,rows,fields=None):
 with (FINAL/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows({k:(js(v) if isinstance(v,(list,dict)) else v) for k,v in r.items()} for r in rows)
def save(name,x):(FINAL/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
# Guard the immutable evidence/reference against accidental changes.
for x in json.loads((OUT/'input_manifest.json').read_text()):
 assert hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'],x['path']
 assert hashlib.sha256((OUT/x['snapshot']).read_bytes()).hexdigest()==x['sha256']
freeze=json.loads((OUT/'abstract_reference_freeze.json').read_text());assert hashlib.sha256((OUT/'abstract_reference.jsonl').read_bytes()).hexdigest()==freeze['sha256']
refs=jl(OUT/'abstract_reference.jsonl');recall=jl(OUT/'abstract_recall_judgments.jsonl');audits=jl(OUT/'relation_audit_judgments.jsonl');rolejudges=jl(OUT/'role_judgments.jsonl');follow=jl(OUT/'equivalence_followup.jsonl')
assert (len(refs),len(recall),len(audits),len(rolejudges),len(follow))==(60,143,200,159,489)
old=read(OUT/'inputs/normalization_assignments_v2_draft.csv');oldcons=read(BASE/'normalization_draft_v2/concepts_v2_draft.csv');oldc={r['concept_id']:r for r in oldcons}
# Start only from explicitly reviewed partitions. Only the additional authored accept merges.
parent={r['draft_concept_id']:r['draft_concept_id'] for r in old};oldmap={r['mention_id']:r['draft_concept_id'] for r in old}
def root(a):
 while parent[a]!=a:a=parent[a]
 return a
def union(a,b):
 a,b=root(a),root(b)
 if a!=b:parent[max(a,b)]=min(a,b)
for r in follow:
 if r['decision']=='accept':union(oldmap[r['left_mention_id']],oldmap[r['right_mention_id']])
parts=collections.defaultdict(list)
for mid,c in oldmap.items():parts[root(c)].append(mid)
cards=jl(BASE/'normalization_draft_v2/inputs/roles/evidence_cards.jsonl');rolemap={r['mention_id']:r['role'] for r in cards};rolemap.update({r['mention_id']:r['accepted_role'] for r in rolejudges});assert set(rolemap)==set(nm)
labels={};concepts=[];mapping={};assignments=[];node_rows=[]
for part,mids in sorted(parts.items()):
 mids=sorted(mids);domain=nm[mids[0]]['domain'];assert {nm[m]['domain'] for m in mids}=={domain}
 cid=hid('concept:v2:'+domain+':',mids);olds=sorted({oldmap[m] for m in mids});label=oldc[olds[0]]['display_label'] if len(olds)==1 else '电子与空穴双极输运贡献'
 roles=sorted({rolemap[m] for m in mids});pids=sorted({nm[m]['paper_id'] for m in mids})
 c={'concept_id':cid,'domain':domain,'display_label':label,'semantic_role':roles[0] if len(roles)==1 else 'context_dependent','source_roles':roles,'member_count':len(mids),'paper_count':len(pids),'source_mention_ids':mids,'paper_ids':pids,'normalization_status':'astra_equivalence_accepted' if len(mids)>1 else 'retained_identity','human_review_required':False,'concept_type':'evidence_concept'}
 concepts.append(c);labels[cid]=label
 for mid in mids:
  mapping[mid]=cid;n=nm[mid]
  assignments.append({'mention_id':mid,'domain':domain,'paper_id':n['paper_id'],'concept_id':cid,'previous_concept_id':oldmap[mid],'mapping_action':'merged_explicitly_reviewed' if len(mids)>1 else 'retained_singleton','semantic_role':rolemap[mid],'role_source':'astra_completion' if any(x['mention_id']==mid for x in rolejudges) else 'preserved_source_model_role','raw_label':n['raw_phrase']})
  node_rows.append(dict(n,concept_id=cid,accepted_semantic_role=rolemap[mid],role_provenance=assignments[-1]['role_source']))
# Preserve all pair outcomes (including uncertainty), never silently transitively merge them.
pairs=[];fm={r['pair_id']:r for r in follow}
for source,rr in [('equivalent_proposals',read(OUT/'inputs/pair_judgments.csv')),('original_uncertain',read(OUT/'inputs/original_uncertain_disposition.csv'))]:
 for r in rr:
  f=fm.get(r['pair_id']);dec=f['decision'] if f else r['judge_decision'];rel=f['semantic_relation'] if f else r.get('judge_relation',{'accept':'equivalent_to','reject':'distinct_from','uncertain':'uncertain'}[dec])
  row={'pair_id':r['pair_id'],'domain':nm[r['left_mention_id']]['domain'],'left_mention_id':r['left_mention_id'],'right_mention_id':r['right_mention_id'],'left_concept_id':mapping[r['left_mention_id']],'right_concept_id':mapping[r['right_mention_id']],'decision':dec,'semantic_relation':rel,'reason':f['reason'] if f else r['judge_reason'],'review_source':source,'review_status':'astra_adjudicated','merge_applied':dec=='accept'}
  assert row['domain']==nm[row['right_mention_id']]['domain']
  if dec!='accept':assert row['left_concept_id']!=row['right_concept_id'],('negative constraint violation',row)
  if dec=='accept':assert row['left_concept_id']==row['right_concept_id'],row
  pairs.append(row)
# Supplement concepts have authored identities scoped to one paper, not global lexical merges.
suppnodes={}
def supplement(d,p,label,role,kind='reference_concept'):
 key=(d,p,label,role);cid=hid('concept:v2:'+d+':supp:',key)
 if cid not in suppnodes:
  mid=hid(d+':'+p+':astra_node:',key)
  suppnodes[cid]={'mention_id':mid,'concept_id':cid,'domain':d,'paper_id':p,'raw_label':label,'semantic_role':role,'source':'astra_authored_local_repair','concept_type':kind}
  concepts.append({'concept_id':cid,'domain':d,'display_label':label,'semantic_role':role,'source_roles':[role],'member_count':1,'paper_count':1,'source_mention_ids':[mid],'paper_ids':[p],'normalization_status':'astra_authored_paper_scoped_identity','human_review_required':False,'concept_type':kind});labels[cid]=label
 return cid
scopealiases={'device_engineering':'device_thermal_management','thermal_management':'device_thermal_management','corrosion_electrodeposition':'other_adjacent_domain','synthesis_processing':'other_adjacent_domain','review_overview':'other_adjacent_domain','reported_performance_context':'other_adjacent_domain','retracted_excluded':'other_adjacent_domain'}
def scope(s):return scopealiases.get(s,s)
main_scopes={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics'}
# Explicit scope refinements authored after semantic review; mechanical/environmental edges remain peripheral.
stability={31,101,125,140,149,150,163,164,177,190}
iontransport={18,19,21,27,28,40,47,52,55,57,59,63,66,71,83,105,106,107,109,111,115,117,123,128,131,132,138,141,145,153,155,160,162,165,178,180,181,194}
electrode={4,110,126,129,143,171,186,193}
for a in audits:
 a['final_analysis_scope']='mechanical_environmental_stability' if a['sample_index'] in stability else ('ion_mass_transport' if a['sample_index'] in iontransport else ('electrode_interface_kinetics' if a['sample_index'] in electrode else scope(a['analysis_scope'])))
# Exact reference matches independently add semantic acceptance; partial matches are superseded by explicit repaired claims.
refmap={c['reference_id']:(r,c) for r in refs for c in r['reference_claims']};rmatches=collections.defaultdict(list);superseded=collections.defaultdict(list)
for x in recall:
 for rid in x['matched_relation_ids']:
  (rmatches if x['baseline_coverage']=='exact' else superseded)[rid].append(x['reference_id'])
am={a['relation_id']:a for a in audits}
# Exact replacements are authored here, not parsed or inferred from the Chinese instructions.
overrides={26:{'subject':'interactions between mixed octahedral-tetrahedral [TS4]Cu6 complexes','subject_role':'interaction'},29:{'object':'electrochemical Seebeck coefficient alpha','object_role':'performance_function'},46:{'subject':'effective control of free-ion movement by zwitterionic side-chain moiety positions','subject_role':'design_strategy'},94:{'predicate':'used with aim of enhancing','modality':'design_purpose'},95:{'object':'pressure-temperature-humidity readout with minimal crosstalk','object_role':'performance_function'},118:{'predicate':'interpreted as predominant deposition contribution at lower laser power','modality':'author_interpretation'},135:{'predicate':'interpreted competing dissolution contribution reducing net deposition at high laser power','modality':'author_interpretation'},147:{'object':'thermogalvanic temperature coefficient alpha of Fe3+/Fe2+','object_role':'performance_function'},148:{'subject':'high Seebeck coefficient','subject_role':'performance_function'},166:{'predicate':'combined design is reported with high tensile strength','modality':'combined_design_report'},170:{'predicate':'intentionally used to modulate','modality':'design_purpose'}}
claimrows=[];revisions=[];factorrows=[]
previous_annotations={r['relation_id']:r for r in read(BASE/'normalization_draft_v2/relation_model_annotations.csv')}
for raw in relations:
 d,p=raw['domain'],raw['paper_id'];rid=raw['relation_id'];a=am.get(rid);sc='scope_unreviewed';status='source_extraction_not_individually_accepted';mod=previous_annotations.get(rid,{}).get('judge_evidence_modality','not_reclassified')
 pred=raw['raw_predicate'];sub=mapping[raw['subject_mention_id']];obj=mapping[raw['object_mention_id']];group='';factors='';revision='';qual=''
 if rid in rmatches:
  r,c=refmap[rmatches[rid][0]];status='astra_reference_match_accepted';sc=scope(r['analysis_scope']);mod=c['assertion_qualifier']
 if a:
  sc=a['final_analysis_scope'];mod=a['evidence_modality'];status='astra_supported_as_reported';qual=a['reason'];i=a['sample_index']
  if a['baseline_status']=='qualify':
   status='astra_repaired';revision=a['repair_instruction'];ov=overrides.get(i,{})
   pred=ov.get('predicate',pred);mod=ov.get('modality',mod)
   if 'subject' in ov:sub=supplement(d,p,ov['subject'],ov['subject_role'],'relation_repair_concept')
   if 'object' in ov:obj=supplement(d,p,ov['object'],ov['object_role'],'relation_repair_concept')
   if a['joint_factor_requirement']:
    factors=a['joint_factor_requirement'];group=hid('joint:'+d+':'+p+':',factors)
    sub=supplement(d,p,factors,'compound_joint_factors','logical_conjunction')
    factorrows.append({'joint_factor_group':group,'domain':d,'paper_id':p,'joint_concept_id':sub,'members_text':factors,'origin_relation_id':rid,'interpretation':'joint assertion only; no independently established individual effects'})
   revisions.append({'relation_id':rid,'revision_kind':'qualification_or_representation','before_subject':nm[raw['subject_mention_id']]['raw_phrase'],'before_predicate':raw['raw_predicate'],'before_object':nm[raw['object_mention_id']]['raw_phrase'],'after_subject':labels[sub],'after_predicate':pred,'after_object':labels[obj],'modality':mod,'joint_factor_group':group,'instruction':revision,'status':'applied'})
 active=status!='source_extraction_not_individually_accepted'
 if rid in superseded:active=False;status+=';superseded_by_reference_repair'
 if (d,p)==('iTE','P1842'):active=False;status='quarantined_retracted_source'
 claimrows.append({'claim_record_id':rid,'origin_relation_id':rid,'domain':d,'paper_id':p,'subject_concept_id':sub,'predicate':pred,'object_concept_id':obj,'assertion_type':raw['assertion_type'],'evidence_modality':mod,'quote':raw['quote'],'analysis_scope':sc,'review_status':status,'active_reviewed_claim':active,'main_analysis_eligible':active and sc in main_scopes,'joint_factor_group':group,'joint_factors_text':factors,'conditions_evidence':raw['quote'],'condition_encoding':'source_quote_preserved_not_fully_structured','reference_links':rmatches.get(rid,[])+superseded.get(rid,[]),'limitation_note':qual,'source_abstract_sha256':pm[d,p]['abstract_sha256']})
for x in recall:
 if x['baseline_coverage']=='exact':continue
 r,c=refmap[x['reference_id']];i=r['sample_index'];ci=r['reference_claims'].index(c);assert len(refroles[i])==len(r['reference_claims'])
 sr,orr=refroles[i][ci];d,p=r['domain'],r['paper_id'];sub=supplement(d,p,c['subject'],ROLES[sr]);obj=supplement(d,p,c['object'],ROLES[orr]);mod=c['assertion_qualifier'];quarantine=(d,p)==('iTE','P1842')
 sc=scope(r['analysis_scope']);cid=c['reference_id'];assert c['quote'] in pm[d,p]['abstract']
 claimrows.append({'claim_record_id':cid,'origin_relation_id':'','domain':d,'paper_id':p,'subject_concept_id':sub,'predicate':c['predicate'],'object_concept_id':obj,'assertion_type':'negated' if 'negation' in mod else ('hypothesis' if any(t in mod for t in ['suggest','possible','proposal','interpretation']) else 'author_claim'),'evidence_modality':mod,'quote':c['quote'],'analysis_scope':sc,'review_status':'quarantined_retracted_source' if quarantine else 'astra_authored_reference_repair','active_reviewed_claim':not quarantine,'main_analysis_eligible':not quarantine and sc in main_scopes,'joint_factor_group':hid('joint:'+d+':'+p+':',c['subject']) if 'joint' in mod else '', 'joint_factors_text':c['subject'] if 'joint' in mod else '', 'conditions_evidence':c['quote'],'condition_encoding':'authored_qualifier_plus_exact_quote','reference_links':[cid],'limitation_note':r['scope_note'],'source_abstract_sha256':pm[d,p]['abstract_sha256']})
 revisions.append({'relation_id':cid,'revision_kind':'missing_or_partial_reference_supplement','before_subject':'','before_predicate':'','before_object':'','after_subject':c['subject'],'after_predicate':c['predicate'],'after_object':c['object'],'modality':mod,'joint_factor_group':claimrows[-1]['joint_factor_group'],'instruction':x['reason'],'status':'applied_quarantined' if quarantine else 'applied'})
# Model evidence and human columns never conflated.
auditrows=[]
for a in audits:
 r=sample[a['sample_index']];final=next(c for c in claimrows if c['claim_record_id']==a['relation_id'])
 auditrows.append(dict(a,post_repair_status='resolved_by_reference_repair' if a['relation_id'] in superseded else ('applied_and_rechecked' if a['baseline_status']=='qualify' else 'unchanged_supported'),inclusion_probability=r['inclusion_probability'],inverse_probability_weight=r['inverse_probability_weight'],stratum=r['stratum'],judge_evidence_valid=True,judge_direction_valid=True,judge_assertion_valid_before=a['strict_correct'],judge_conditions_and_representation_valid_before=a['strict_correct'],human_label='',human_review_required=False,final_subject=labels[final['subject_concept_id']],final_predicate=final['predicate'],final_object=labels[final['object_concept_id']]))
write('concepts_v2.csv',concepts);write('normalization_assignments_v2.csv',assignments);write('concept_relations_v2.csv',pairs);write('normalization_audit_v2.csv',pairs);write('extraction_audit_v2.csv',auditrows);write('node_evidence_v2.csv',node_rows);write('supplemental_nodes_v2.csv',list(suppnodes.values()));write('scientific_claims_v2.csv',claimrows);write('relation_revisions.csv',revisions);write('joint_factor_groups.csv',factorrows);write('role_acceptance_v2.csv',rolejudges)
# Diagnostics and weighted ratios.
design=json.loads((OUT/'inputs/sampling_and_candidate_design.json').read_text());metrics={}
for d in ['iTE','TG']:
 aa=[a for a in auditrows if a['domain']==d];den=sum(float(a['inverse_probability_weight']) for a in aa);num=sum(float(a['inverse_probability_weight']) for a in aa if a['strict_correct'])
 w={a['paper_id']:a['inverse_probability_weight'] for a in design[d+'_abstract_sample_weights']};xs=[x for x in recall if x['domain']==d];rd=sum(w[x['paper_id']] for x in xs);rn=sum(w[x['paper_id']] for x in xs if x['baseline_coverage']=='exact')
 metrics[d]={'audit_n':len(aa),'strict_supported':sum(a['strict_correct'] for a in aa),'qualifications':sum(not a['strict_correct'] for a in aa),'weighted_baseline_strict_precision':num/den,'reference_claims':len(xs),'exact_reference_matches':sum(x['baseline_coverage']=='exact' for x in xs),'weighted_baseline_core_recall':rn/rd,'precision_target':0.90,'recall_target':0.70,'baseline_gate_pass':num/den>=.9 and rn/rd>=.7,'post_repair_sample_coverage':1.0,'post_repair_sample_not_independent':True}
summary={'completion_scope':'specified audits, pending-role and equivalence disposition, local repair, normalization projection and domain graph construction','input_raw_nodes':len(nodes),'input_raw_relations':len(relations),'original_node_concepts':len(parts),'all_concepts_including_supplements':len(concepts),'supplemental_nodes':len(suppnodes),'new_reference_claims':sum(not c['origin_relation_id'] for c in claimrows),'all_claim_records':len(claimrows),'active_reviewed_claims':sum(c['active_reviewed_claim'] for c in claimrows),'main_eligible_claims':sum(c['main_analysis_eligible'] for c in claimrows),'role_deferred_reviewed':len(rolejudges),'equivalence_followup_counts':dict(collections.Counter(x['decision'] for x in follow)),'final_pair_decisions':dict(collections.Counter(x['decision'] for x in pairs)),'human_review_required':False,'metrics':metrics,'release_status':'evidence_complete_quality_limited_model_reviewed_release','scope_warning':'Unreviewed claims remain in complete evidence/projection graphs and are excluded from accepted main analysis. Post-repair sample coverage is not held-out corpus accuracy. Stage4 quality gate remains closed.'}
save('quality_report_v2.json',summary)
save('scope_policy.json',{'allowed_plan_scopes':sorted(main_scopes|{'device_thermal_management','mechanical_environmental_stability','application_sensing','measurement_method_model','other_adjacent_domain'}),'extension':'scope_unreviewed is an explicit conservative quarantine, never a guessed scientific scope','aliases_from_authored_reviews':scopealiases,'edge_scope_overrides':{'mechanical_environmental_stability':sorted(stability),'ion_mass_transport':sorted(iontransport),'electrode_interface_kinetics':sorted(electrode)},'retracted_papers':['iTE:P1842'],'cross_domain_merges':False})
print(js(summary))
