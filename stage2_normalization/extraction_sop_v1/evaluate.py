"""Validate and calculate explicitly authored labels. No semantic scoring in code."""
import json,csv,copy,hashlib,collections
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
def load(name):return json.loads((D/name).read_text())
def dump(name,x):(D/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
P={p['paper_id']:p for p in load('input_papers.json')}
I=load('extraction_initial.json');R=load('extraction_reviewed.json');F=load('model_reference.json')
J={j['relation_id']:j for j in load('review_judgments.json')};B=load('baseline_records.json');BJ=load('baseline_judgments.json')
freezes={}
for path in sorted(D.glob('*_freeze.json')):
    for name,expected in json.loads(path.read_text()).items():
        assert sha(D/name)==expected,(path,name)
        freezes[name]=expected
for path,expected in load('selection.json')['source_hashes'].items():assert sha(ROOT/path)==expected,path
assert not(set(P)&set(load('selection.json')['excluded']))
assert len({p['doi'].strip().lower() for p in P.values()})==len(P)
assert len({r['relation_id'] for r in I})==len(I)
assert len({r['relation_id'] for r in R})==len(R)
assert len({f['reference_id'] for f in F})==len(F)
assert {r['relation_id'] for r in B}=={j['relation_id'] for j in BJ}
span_count=0
for r in I+R:
    assert r['input_hash']==P[r['paper_id']]['input_hash']
    for e in r['evidence']+r.get('context_evidence',[]):
        assert P[r['paper_id']]['abstract'][e['char_start']:e['char_end']]==e['quote']
        span_count+=1
for f in F:
    e=f['evidence'];assert P[f['paper_id']]['abstract'][e['char_start']:e['char_end']]==e['quote']
    for version,records in [('initial',I),('reviewed',R)]:
        assert set(f[version]['relation_ids'])<={r['relation_id'] for r in records if r['paper_id']==f['paper_id']}
confirmed={f['reference_id'] for f in F if f['status']=='confirmed'}
for j in BJ:assert set(j['reference_ids'])<={f['reference_id'] for f in F}

# Repair raw authoring ID allocation collisions only. No merging by synonyms or physics.
export=copy.deepcopy(R);registry={};id_log=[];seen_raw={};collisions=[]
for r in export:
    pid=r['paper_id']
    for side in ['subject','object']:
        n=r[side];key=(pid,n['label'],n['semantic_role']);old_id=n['local_id']
        if old_id in seen_raw and seen_raw[old_id]!=key:collisions.append(dict(relation_id=r['relation_id'],side=side,raw_id=old_id,labels=[seen_raw[old_id][1],key[1]]))
        seen_raw[old_id]=key
        if key not in registry:registry[key]=f'{pid}:entity:{1+sum(k[0]==pid for k in registry):03}'
        n['authoring_local_id']=old_id;n['local_id']=registry[key]
        id_log.append(dict(relation_id=r['relation_id'],side=side,old_id=old_id,new_id=n['local_id'],label=n['label'],role=n['semantic_role']))
all_ids={}
for r in export:
    for side in ['subject','object']:
        n=r[side];v=(r['paper_id'],n['label'],n['semantic_role'])
        assert n['local_id'] not in all_ids or all_ids[n['local_id']]==v
        all_ids[n['local_id']]=v
dump('extraction_reviewed_validated.json',export)
dump('id_materialization_log.json',dict(policy='Exact (paper_id,label,role) identity only; no semantic normalization; frozen author records retained.',collisions=collisions,mappings=id_log))

MAIN={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics'}
metrics=[]
for scope in ['all','main']:
 for group in ['all','iTE','TG','TG_only','shared']:
    pids={pid for pid,p in P.items() if group=='all' or p['domain']==group or (group=='TG_only' and p['source_membership']=='TG') or (group=='shared' and p['source_membership']=='iTE|TG')}
    refs=[f for f in F if f['paper_id'] in pids and f['status']=='confirmed' and (scope=='all' or f['scope']=='main')]
    for ver,records in [('initial',I),('reviewed',R)]:
        subset=[r for r in records if r['paper_id'] in pids and (scope=='all' or r['analysis_scope'] in MAIN)]
        correct=sum(J[r['relation_id']]['initial_label']=='supported' for r in subset) if ver=='initial' else sum(r['review_status']=='accepted' for r in subset)
        covered=sum(f[ver]['label']=='full' for f in refs)
        metrics.append(dict(scope=scope,group=group,version=ver,papers=len(pids),strict_supported=correct,predictions=len(subset),model_strict_acceptance=correct/len(subset) if subset else None,covered_reference=covered,confirmed_reference=len(refs),model_reference_coverage=covered/len(refs) if refs else None))
old_full={rid for j in BJ if j['semantic_label']=='full' for rid in j['reference_ids']}
new_full={f['reference_id'] for f in F if f['reviewed']['label']=='full'}
residual=[dict(reference_id=f['reference_id'],paper_id=f['paper_id'],statement=f['statement'],status=f['status'],reviewed=f['reviewed']) for f in F if f['reviewed']['label']!='full']
dump('metrics.json',dict(evaluation_kind='same-conversation Astra exploratory; not independent validation',metrics=metrics,baseline=dict(records=len(B),confirmed_references_fully_covered=len(old_full&confirmed),confirmed_reference_denominator=len(confirmed),full_old_reference_not_preserved=sorted(old_full-new_full),comparison_limit='Old focal-claim extraction has a different coverage objective. Coverage includes original quote/context and is not old-system production precision.'),residual=residual))
with (D/'metrics.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
dump('validation.json',dict(status='PASS',source_and_freeze_hashes_verified=len(freezes)+len(load('selection.json')['source_hashes']),sample_count=len(P),prior_registered_audit_overlap=0,duplicate_doi=0,initial_records=len(I),reviewed_records=len(R),reference_claims=len(F),confirmed_reference_claims=len(confirmed),exact_evidence_spans_checked=span_count+len(F),validated_entity_ids=len(all_ids),raw_id_collision_observations=len(collisions),note='Quote location and ID consistency do not establish semantic correctness. Corrected export only renumbers entity IDs.'))
print(json.dumps([m for m in metrics if m['scope']=='all' and m['group'] in ['all','iTE','TG']],ensure_ascii=False,indent=2))
print('remaining',residual,'ID collisions',len(collisions))
