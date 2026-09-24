"""Read-only consistency checks; no model calls or scientific-quality claims."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import materialize as m

D, F = m.D, m.F
read, sha = m.read, m.sha
base = read(F/'extraction_all.json')
final = read(D/'final/revised_all.json')
freeze = read(D/'freeze.json')
assert sha(F/'extraction_all.json') == freeze['baseline_sha256']
for name, digest in freeze['files'].items():
    assert sha(D/name) == digest, name
reference_freeze = read(D/'reference_freeze.json')
assert sha(D/'reference.json') == reference_freeze['sha256']
for job_id, digest in reference_freeze['files'].items():
    assert sha(D/'runs'/job_id/'response.json') == digest
sources = {}
for batch in read(F/'manifest.json')['batches']:
    path = F/'inputs'/(batch['id']+'.json')
    assert sha(path) == batch['sha256']
    for p in read(path):
        assert p['paper_id'] not in sources
        sources[p['paper_id']] = p
assert [p['paper_id'] for p in base] == [p['paper_id'] for p in final]
orig = {r['relation_id']:r for p in base for r in p['records']}
rows = {r['relation_id']:r for p in final for r in p['records']}
assert len(rows) == sum(len(p['records']) for p in final)
logs = read(D/'final/change_log.json')
changes = {c['relation_id']:c for c in logs}
assert len(changes) == len(logs)
rejects = read(D/'final/rejected.json')
reject_ids = {r['relation_id'] for r in rejects}
assert set(orig)-set(rows) == reject_ids
assert not reject_ids & set(rows)
assert set(rows)-set(orig) == {c['relation_id'] for c in logs if c['action']=='add'}
assert {c['relation_id'] for c in logs if c['action']!='add'} == set(read(D/'repair_scope.json')['target_ids'])
for c in logs:
    if c['before'] is not None:
        assert c['before'] == orig[c['relation_id']]
    assert c['after'] == rows.get(c['relation_id'])
for r in rejects:
    assert r['original'] == orig[r['relation_id']]
mechanical = {c['relation_id']:c for c in read(D/'final/joint_factor_resolution.json')}
raw = m.load_raw_nodes()
span_count = 0
remaining_local_tokens = []
for p in final:
    pid = p['paper_id']
    for r in p['records']:
        rid = r['relation_id']
        assert rid.startswith(pid+':')
        assert all(r[s+'_id'].startswith(pid+':') for s in ('subject','object'))
        for quotes, spans in [([r['quote']]+r['context_quotes'],r['evidence_spans']), (r['modality_evidence'],r['modality_spans'])]:
            assert len(quotes) == len(spans)
            for q,s in zip(quotes,spans):
                assert sources[pid]['abstract'][s['start']:s['end']] == q
                span_count += 1
        assert r['modality']=='unspecified' or r['modality_evidence']
        if rid not in changes:
            assert r['review_status']=='not_targeted_by_full_audit_v1'
            for k,v in orig[rid].items():
                if k!='joint_factors':
                    assert r[k]==v, (rid,k)
            assert r['joint_factors']==(mechanical[rid]['after'] if rid in mechanical else orig[rid]['joint_factors'])
        if rid in mechanical:
            assert r['joint_factor_raw_values']==orig[rid]['joint_factors']
            assert r['joint_factors']==[raw[pid].get(t,t) for t in orig[rid]['joint_factors']]
        tokens=[t for t in r['joint_factors'] if t in raw[pid] and raw[pid][t]!=t]
        if tokens:
            remaining_local_tokens.append(dict(relation_id=rid,tokens=tokens))
uncertain_ids={rid for rid,r in orig.items() if r['status']=='uncertain'}
assert len(uncertain_ids)==660 and uncertain_ids<=set(changes)
for domain in ('iTE','TG'):
    assert read(D/f'final/revised_{domain}.json')==[p for p in final if p['domain']==domain]
usage=collections.Counter(); phases=collections.Counter(); starts=[]; ends=[]
for phase in ('reference','precision','coverage','repair'):
    for job in read(D/f'{phase}_jobs.json'):
        success=read(D/'runs'/job['id']/'SUCCESS.json')
        assert sha(D/'runs'/job['id']/'response.json')==success['response_sha256']
        assert sha(D/'jobs'/phase/(job['id']+'.json'))==success['input_sha256']==job['input_sha256']
        assert success['attempt']==1
        for u in success['usage']:
            usage.update(u)
        end=datetime.datetime.fromisoformat(success['finished_at']); ends.append(end)
        starts.append(end-datetime.timedelta(seconds=success['elapsed_seconds']))
        phases[phase]+=1
report=dict(validation='PASS',semantic_quality_not_verified=True,baseline_sha256=sha(F/'extraction_all.json'),
            papers=len(final),relations=len(rows),checked_quote_and_method_spans=span_count,
            original_uncertain_actions=dict(collections.Counter(changes[rid]['action'] for rid in uncertain_ids)),
            per_domain={d:dict(papers=sum(p['domain']==d for p in final),relations=sum(len(p['records']) for p in final if p['domain']==d),
                status=dict(collections.Counter(r['status'] for p in final if p['domain']==d for r in p['records']))) for d in ('iTE','TG')},
            remaining_exact_local_joint_tokens=remaining_local_tokens,
            modality_guard_alerts=read(D/'draft/modality_guard_alerts.json'),
            successful_calls=dict(phases),usage=dict(usage),model_call_wall_minutes=(max(ends)-min(starts)).total_seconds()/60,
            outputs_sha256={p.name:sha(p) for p in sorted((D/'final').glob('*.json'))})
m.write_many(D,{'verification.json':report})
print(json.dumps(report,ensure_ascii=False,indent=2))
