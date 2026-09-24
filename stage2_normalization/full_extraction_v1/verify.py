"""Read-only delivery checks; does not judge semantic accuracy or call a model."""
import collections
import csv
import datetime
import hashlib
import json
from pathlib import Path
import run

D = Path(__file__).resolve().parent
m = run.read(D / 'manifest.json')
assert run.sha(D / 'PROMPT.md') == m['prompt_sha256']
assert run.sha(D / 'schema.json') == m['schema_sha256']
sources = {}
for relative, digest in m['sources'].items():
    path = run.ROOT / relative
    assert run.sha(path) == digest, relative
    domain = 'iTE' if path.name == 'ite_clean.csv' else 'TG'
    for row in csv.DictReader(path.open(encoding='utf-8-sig')):
        assert row['paper_id'] not in sources
        sources[row['paper_id']] = dict(domain=domain, abstract=row['摘要'], title=row['文章名'])

allrows, stats, covered, relation_ids = [], [], set(), set()
quote_spans = 0
for b in m['batches']:
    path = D / 'inputs' / (b['id'] + '.json')
    assert run.sha(path) == b['sha256']
    papers = run.read(path)
    assert [p['paper_id'] for p in papers] == b['ids']
    for p in papers:
        pid = p['paper_id']
        assert pid not in covered
        covered.add(pid)
        assert all(p[k] == sources[pid][k] for k in ('domain', 'abstract', 'title'))
        assert p['input_hash'] == hashlib.sha256(p['abstract'].encode()).hexdigest()
        assert p['segments'] == run.segment(p['abstract'])
    base = D / 'batches' / b['id']
    success = run.read(base / 'SUCCESS.json')
    assert success['input_sha256'] == b['sha256']
    assert success['output_sha256'] == run.sha(base / 'extraction.json')
    attempt = base / f"attempt_{success['attempt']:02}"
    call = run.read(attempt / 'call.json')
    assert (call['model'], call['reasoning'], call['returncode']) == (m['model'], m['reasoning'], 0)
    regenerated, alerts = run.validate_expand(papers, run.read(attempt / 'response.json'))
    output = run.read(base / 'extraction.json')
    assert regenerated == output
    assert alerts == run.read(base / 'modality_audit.json')
    assert success['papers'] == len(output)
    assert success['relations'] == sum(len(p['records']) for p in output)
    for p in output:
        for r in p['records']:
            assert r['relation_id'] not in relation_ids
            relation_ids.add(r['relation_id'])
            for quotes, spans in (([r['quote']] + r['context_quotes'], r['evidence_spans']),
                                  (r['modality_evidence'], r['modality_spans'])):
                assert len(quotes) == len(spans)
                for q, s in zip(quotes, spans):
                    assert sources[p['paper_id']]['abstract'][s['start']:s['end']] == q
                    quote_spans += 1
    allrows.extend(output)
    stats.append(dict(batch=b['id'], **success))

missing = run.read(D / 'missing_abstracts.json')
assert len(missing) == 6 and len({p['paper_id'] for p in missing}) == 6
assert {p['paper_id'] for p in missing} == {pid for pid, p in sources.items() if not p['abstract'].strip()}
assert covered == {pid for pid, p in sources.items() if p['abstract'].strip()}
assert len(allrows) == len(covered) == 1971 and len(sources) == 1977
assert run.read(D / 'extraction_all.json') == allrows
assert run.read(D / 'batch_statistics.json') == stats
domains = {}
for domain in ('iTE', 'TG'):
    rows = [p for p in allrows if p['domain'] == domain]
    assert run.read(D / f'extraction_{domain}.json') == rows
    records = [r for p in rows for r in p['records']]
    domains[domain] = dict(papers=len(rows), relations=len(records),
                          no_relations=sum(not p['records'] for p in rows),
                          status=dict(collections.Counter(r['status'] for r in records)),
                          modality=dict(collections.Counter(r['modality'] for r in records)),
                          scope=dict(collections.Counter(r['scope'] for r in records)))
usage = collections.Counter()
for b in stats:
    for u in b['usage']:
        usage.update(u)
result = dict(verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              check='PASS', semantic_accuracy='not_evaluated_by_this_program',
              batches=len(stats), papers=len(allrows), missing_abstracts=len(missing),
              relations=len(relation_ids), exact_quote_spans=quote_spans,
              domains=domains, successful_call_usage=dict(usage),
              artifact_sha256={name: run.sha(D / name) for name in
                               ('extraction_all.json', 'extraction_iTE.json', 'extraction_TG.json',
                                'missing_abstracts.json', 'batch_statistics.json', 'manifest.json',
                                'PROMPT.md', 'schema.json', 'run.py', 'verify.py')})
print(json.dumps(result, ensure_ascii=False, indent=2))
