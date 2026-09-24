"""Count independent authored labels; never judge scientific meaning."""
import collections
import datetime
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
def read(name): return json.loads((D/name).read_text())
P={p['paper_id']:p for p in read('input_papers.json')}
C={(p['paper_id'],r['id']):r for p in read('initial.json') for r in p['records']}
G={(p['paper_id'],g['id']):g for p in read('reference.json') for g in p['claims']}
A=read('audit.json'); A=A['records'] if isinstance(A,dict) else A
B=read('coverage.json'); B=B['records'] if isinstance(B,dict) else B
assert len(A)==len(C) and {(r['paper_id'],r['id']) for r in A}==set(C)
assert len(B)==len(G) and {(r['paper_id'],r['id']) for r in B}==set(G)
assert all(r['verdict'] in {'supported','partial','unsupported','uncertain','out_of_scope'} for r in A)
assert all(r['coverage'] in {'complete','partial','missing'} and r['reference_status'] in {'valid','uncertain','out_of_scope'} for r in B)
for row in B:
    assert all((row['paper_id'],rid) in C for rid in row['candidate_ids'])
for name,sha in read('input_freeze.json').items():
    assert hashlib.sha256((D/name).read_bytes()).hexdigest()==sha,name
for name,sha in read('initial_freeze.json')['files'].items():
    assert hashlib.sha256((D/name).read_bytes()).hexdigest()==sha,name
for name,sha in read('reference.freeze.json')['files'].items():
    assert hashlib.sha256((D/name).read_bytes()).hexdigest()==sha,name
for p in read('reference.json'):
    for r in p['claims']:
        assert r['quote'] in P[p['paper_id']]['abstract'],(p['paper_id'],r['id'])

MAIN={'intrinsic_material_mechanism','thermodynamics','ion_mass_transport','electrode_interface_kinetics'}
def ratio(n,d): return dict(n=n,d=d,percent=round(100*n/d,2) if d else None)
result={}
for domain in ['iTE','TG']:
    rows=[r for r in A if P[r['paper_id']]['domain']==domain]
    cov=[r for r in B if P[r['paper_id']]['domain']==domain]
    main=[r for r in rows if C[r['paper_id'],r['id']]['scope'] in MAIN]
    fields=dict(papers=sum(p['domain']==domain for p in P.values()),
        precision=ratio(sum(r['verdict']=='supported' for r in rows),len(rows)),
        main_precision=ratio(sum(r['verdict']=='supported' for r in main),len(main)),
        verdicts=dict(collections.Counter(r['verdict'] for r in rows)),
        error_tags=dict(collections.Counter(t for r in rows for t in r['errors'])))
    for scope in ['all','main']:
        subset=[r for r in cov if scope=='all' or G[r['paper_id'],r['id']]['scope'] in MAIN]
        valid=[r for r in subset if r['reference_status']=='valid']
        fields[scope+'_reference_coverage_valid']=ratio(sum(r['coverage']=='complete' for r in valid),len(valid))
        fields[scope+'_reference_coverage_all_conservative']=ratio(sum(r['coverage']=='complete' and r['reference_status']=='valid' for r in subset),len(subset))
        fields[scope+'_reference_statuses']=dict(collections.Counter(r['reference_status'] for r in subset))
    result[domain]=fields
now=datetime.datetime.now(datetime.timezone.utc)
start=datetime.datetime.fromisoformat(read('selection.json')['started_at'])
meta=dict(completed_at=now.isoformat(),elapsed_seconds=round((now-start).total_seconds(),1),
    input_papers=len(P),reference_papers=len(read('reference.json')),candidate_records=len(C),reference_claims=len(G),
    input_abstract_characters=sum(len(p['abstract']) for p in P.values()),
    exact_token_usage=None,independent_agents=1,coverage_unit='compact_source_claims_not_atomic_graph_edges',
    limitations=['Small diagnostic sample; percentages are unweighted sample descriptions, not whole-corpus estimates.',
    'Coverage references only four preselected papers; not whole eight-paper or corpus recall.',
    'Same model in separate contexts; not an external gold standard.',
    'References group some outcomes; coverage is not atomic-edge recall and cannot be compared directly with earlier recall estimates.',
    'No repair after audit; this measures frozen first-pass extraction, not revised performance.'])
output=dict(meta=meta,domains=result)
with (D/'metrics.json').open('x') as f:json.dump(output,f,ensure_ascii=False,indent=2)
print(json.dumps(output,ensure_ascii=False))
