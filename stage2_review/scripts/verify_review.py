#!/usr/bin/env python3
"""Read-only checks of review provenance, IDs, sampling and label separation."""
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'v1'
SOURCE = BASE.parent / 'stage2_reconstruction' / 'v1'

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def unique(rows, field):
    result = {r[field]: r for r in rows}
    assert len(result) == len(rows), field
    return result

prep = json.loads((OUT / 'preparation_manifest.json').read_text())
for name, digest in prep['source_files'].items():
    assert sha(SOURCE / name) == digest, name
for name, digest in prep['outputs'].items():
    assert sha(OUT / name) == digest, name
assert sha(BASE / 'scripts/prepare_review.py') == prep['script_sha256']
manifest = BASE / 'delivery_manifest.json'
if manifest.exists():
    for name, digest in json.loads(manifest.read_text())['files'].items():
        assert sha(BASE / name) == digest, name

papers = unique(read(SOURCE / 'paper_coverage.csv'), 'paper_id')
nodes = unique(read(SOURCE / 'node_evidence.csv'), 'mention_id')
relations = unique(read(SOURCE / 'relation_evidence.csv'), 'relation_id')
design = json.loads((OUT / 'sampling_and_candidate_design.json').read_text())
dev = set(design['role_development_papers'])
assert len(dev) == 40
assert Counter(papers[p]['domain'] for p in dev) == {'iTE': 20, 'TG': 20}
roles = unique(read(OUT / 'role_model_proposals_pilot.csv'), 'mention_id')
reviews = unique(read(OUT / 'relation_model_review_pilot.csv'), 'relation_id')
assert set(roles) == {k for k, n in nodes.items() if n['paper_id'] in dev}
assert set(reviews) == {k for k, r in relations.items() if r['paper_id'] in dev}
for mid, r in roles.items():
    n = nodes[mid]
    for field in ('paper_id', 'domain', 'raw_phrase', 'quote', 'claim_id', 'legacy_role'):
        assert r[field] == n[field], (mid, field)
for rid, r in reviews.items():
    source = relations[rid]
    assert r['subject'] == nodes[source['subject_mention_id']]['raw_phrase']
    assert r['object'] == nodes[source['object_mention_id']]['raw_phrase']
    assert r['predicate'] == source['raw_predicate']
    assert r['quote'] == source['quote']
    assert r['assertion_type'] == source['assertion_type']

audit = read(OUT / 'relation_audit_sample.csv')
gold = read(OUT / 'abstract_gold_annotation_blank.csv')
unique(audit, 'relation_id'); unique(gold, 'paper_id')
assert Counter(r['domain'] for r in audit) == {'iTE': 100, 'TG': 100}
assert Counter(r['domain'] for r in gold) == {'iTE': 30, 'TG': 30}
assert not dev & {r['paper_id'] for r in audit + gold}
for r in audit:
    source = relations[r['relation_id']]
    assert r['quote'] == source['quote'] and r['paper_id'] == source['paper_id']
    assert r['full_abstract'] == papers[r['paper_id']]['abstract']
for r in gold:
    assert r['abstract'] == papers[r['paper_id']]['abstract']
for domain in ('iTE', 'TG'):
    for suffix, sample in (('relations', [r for r in audit if r['domain'] == domain]),
                           ('abstracts', design[domain + '_abstract_sample_weights'])):
        spec = design[domain + '_' + suffix]
        strata = {r['stratum']: r for r in spec['strata']}
        counts = Counter(r['stratum'] for r in sample)
        assert sum(s['population_count'] for s in strata.values()) == spec['population']
        assert sum(counts.values()) == spec['sample']
        for s, n in counts.items():
            assert n == strata[s]['sample_count']
        for r in sample:
            s = strata[r['stratum']]
            assert int(r['stratum_population']) == s['population_count']
            assert math.isclose(float(r['inclusion_probability']), s['sample_count'] / s['population_count'])
            assert math.isclose(float(r['inverse_probability_weight']), s['population_count'] / s['sample_count'])
    assert {r['paper_id'] for r in design[domain + '_abstract_sample_weights']} == {
        r['paper_id'] for r in gold if r['domain'] == domain}

units = unique(read(OUT / 'retrieval_units.csv'), 'retrieval_unit_id')
members = unique(read(OUT / 'retrieval_unit_members.csv'), 'mention_id')
assert set(members) == set(nodes)
for mid, m in members.items():
    assert units[m['retrieval_unit_id']]['label'] == nodes[mid]['raw_phrase']
    assert units[m['retrieval_unit_id']]['domain'] == nodes[mid]['domain'] == m['domain']
pairs = unique(read(OUT / 'normalization_candidates.csv'), 'candidate_id')
pair_keys = set()
for r in pairs.values():
    a, b = r['left_unit_id'], r['right_unit_id']
    assert a < b and (a, b) not in pair_keys
    pair_keys.add((a, b))
    assert units[a]['domain'] == units[b]['domain'] == r['domain']
    assert r['left_label'] == units[a]['label'] and r['right_label'] == units[b]['label']
    assert r['decision_status'] == 'unreviewed_candidate' and not r['concept_relation']
    assert 0 <= float(r['char_ngram_cosine']) <= 1
    assert 0 <= float(r['structural_jaccard']) <= 1
normalization = read(OUT / 'normalization_model_review_pilot.csv')
unique(normalization, 'proposal_id')
for r in normalization:
    a, b = nodes[r['left_mention_id']], nodes[r['right_mention_id']]
    assert a['domain'] == b['domain'] == r['domain']
    for side, n in (('left', a), ('right', b)):
        assert r[side + '_quote'] == n['quote']
        assert r[side + '_full_abstract'] == papers[n['paper_id']]['abstract']
    assert r['merge_applied'] == 'False'
    assert r['proposed_relation'] in {'equivalent_to', 'narrower_than', 'broader_than', 'related_to', 'distinct_from', 'uncertain'}
for r in list(roles.values()) + list(reviews.values()) + normalization:
    assert r['proposal_status'] == 'model_proposed_pending_human'
for path in OUT.glob('*.csv'):
    for r in read(path):
        assert all(not value for key, value in r.items() if key.startswith('human_'))
print(json.dumps(dict(status='PASS', source_hashes_unchanged=True,
    role_proposals=len(roles), relation_reviews=len(reviews), normalization_proposals=len(normalization),
    relation_audit_sample=len(audit), abstract_audit_sample=len(gold),
    candidate_pairs=len(pairs), human_labels=0, concepts_merged=0,
    validation_scope='Provenance, content joins, IDs, sample separation, weights and model/human label separation; not scientific correctness.'), ensure_ascii=False, indent=2))
