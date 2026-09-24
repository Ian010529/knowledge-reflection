"""Materialize targeted model decisions without mutating frozen extraction files.

No inference calls. --draft prepares blinded postcheck inputs; --final consumes
independent judgments; --self-test exercises in-memory synthetic records only.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import sys

D = Path(__file__).resolve().parent
F = D.parent / 'full_extraction_v1'
sys.path.insert(0, str(D.parent))
from modality_guard import guard

CONTENT = ('relation_id', 'subject', 'subject_role', 'predicate', 'object',
           'object_role', 'quote', 'context_quotes', 'assertion', 'modality',
           'modality_evidence', 'conditions', 'joint_factors', 'scope', 'claim_scope')
BODY_KEYS = {'subject', 'subject_role', 'predicate', 'object', 'object_role',
             'e', 'assertion', 'modality', 'me', 'conditions', 'joint_factors',
             'scope', 'claim_scope'}
VERDICTS = {'supported', 'partial', 'unsupported', 'out_of_scope', 'uncertain'}
PENDING = 'model_reviewed_pending_independent_check'


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_many(directory, objects):
    """Preflight every output before exclusive creation; identical bytes reusable."""
    encoded = {directory / name: json.dumps(value, ensure_ascii=False, indent=2) + '\n'
               for name, value in objects.items()}
    for path, text in encoded.items():
        require(not path.exists() or path.read_text() == text,
                f'Refusing to overwrite different output: {path}')
    directory.mkdir(parents=True, exist_ok=True)
    for path, text in encoded.items():
        if not path.exists():
            with path.open('x') as handle:
                handle.write(text)


def node_index(paper):
    index = collections.defaultdict(set)
    for r in paper['records']:
        for side in ('subject', 'object'):
            index[(r[side], r[side + '_role'])].add(r[side + '_id'])
    return index


def expand(body, src, rid, short_id, index, before=None):
    require(set(body) == BODY_KEYS, f'Invalid BODY fields: {rid}')
    segments = {s['id']: s for s in src['segments']}
    require(body['e'] and all(type(k) is int and k in segments
                            for k in body['e'] + body['me']), f'Invalid evidence IDs: {rid}')
    require(all(isinstance(body[k], str) and body[k].strip()
                for k in ('subject', 'predicate', 'object')), f'Empty relation: {rid}')
    evidence = [segments[k] for k in dict.fromkeys(body['e'])]
    methods = [segments[k] for k in dict.fromkeys(body['me'])]
    for s in evidence + methods:
        require(src['abstract'][s['start']:s['end']] == s['text'], 'Source segment offset mismatch')
    record = {k: copy.deepcopy(v) for k, v in body.items() if k not in ('e', 'me')}
    record.update(id=short_id, relation_id=rid, quote=evidence[0]['text'],
                  context_quotes=[s['text'] for s in evidence[1:]],
                  modality_evidence=[s['text'] for s in methods],
                  evidence_spans=[dict(start=s['start'], end=s['end']) for s in evidence],
                  modality_spans=[dict(start=s['start'], end=s['end']) for s in methods],
                  status='accepted', note='Targeted audit revision; independent check pending.')
    for side in ('subject', 'object'):
        key = (record[side], record[side + '_role'])
        if before and key == (before[side], before[side + '_role']):
            node_id = before[side + '_id']
        elif len(index.get(key, ())) == 1:
            node_id = next(iter(index[key]))
        else:
            node_id = f"{src['paper_id']}:audit_v1_{short_id}_{side}"
        record[side + '_id'] = node_id
        index[key].add(node_id)
    checked, alerts = guard([src], [dict(paper_id=src['paper_id'], records=[record])])
    record = checked[0]['records'][0]
    if not record['modality_evidence']:
        record['modality_spans'] = []
    return record, alerts


def omission_links(body, src, hints):
    """Structural authorization only; semantic correspondence needs model review."""
    require(hints, f"No omission hints permit additions for {src['paper_id']}")
    selected = [s['text'] for s in src['segments'] if s['id'] in body['e']]
    links = []
    for hint in hints:
        ref = hint['reference']
        quotes = [ref.get('quote', '')] + ref.get('context_quotes', [])
        if any(q and (q in s or s in q) for q in quotes for s in selected):
            links.append(ref['relation_id'])
    return links


def build_draft(baseline, sources, jobs, scope_ids, expected_uncertain=660):
    """jobs: [{id, provenance, input:[paper packets], response:{papers:[...]}}]."""
    result = copy.deepcopy(baseline)
    papers = {p['paper_id']: p for p in result}
    originals = {r['relation_id']: (p['paper_id'], r) for p in baseline for r in p['records']}
    require(len(originals) == sum(len(p['records']) for p in baseline), 'Duplicate baseline relation ID')
    uncertain = {rid for rid, (_, r) in originals.items() if r['status'] == 'uncertain'}
    require(len(uncertain) == expected_uncertain and uncertain <= set(scope_ids), 'Original uncertain coverage mismatch')
    require(len(scope_ids) == len(set(scope_ids)) and set(scope_ids) <= set(originals), 'Invalid repair scope')
    seen, seen_papers, logs, rejected, checks, alerts = set(), set(), [], [], {}, []
    for paper in result:
        for r in paper['records']:
            r['review_status'] = 'not_targeted_by_full_audit_v1'
            r['decision_source'] = {'run': 'full_extraction_v1', 'action': 'unchanged'}
    for job in jobs:
        packets = {p['paper_id']: p for p in job['input']}
        outputs = job['response']['papers']
        require(len(packets) == len(job['input']), 'Duplicate job paper')
        require(len(outputs) == len(packets) and {p['paper_id'] for p in outputs} == set(packets), 'Repair job paper mismatch')
        for output in outputs:
            pid = output['paper_id']
            require(pid not in seen_papers, f'Duplicate repair paper: {pid}')
            seen_papers.add(pid)
            packet, paper, src = packets[pid], papers[pid], sources[pid]
            index = node_index(paper)
            current = {r['relation_id']: r for r in paper['records']}
            got = [d['relation_id'] for d in output['decisions']]
            require(len(got) == len(set(got)) and set(got) == set(packet['target_ids']), 'Target decision mismatch')
            for decision in output['decisions']:
                rid, action = decision['relation_id'], decision['action']
                require(rid not in seen and rid in originals and originals[rid][0] == pid, 'Duplicate/foreign decision')
                seen.add(rid)
                before = copy.deepcopy(originals[rid][1])
                require(action in {'keep', 'replace', 'reject', 'uncertain'}, 'Unknown repair action')
                require((action == 'replace') == (decision['record'] is not None), 'Invalid replacement BODY presence')
                provenance = dict(job['provenance'], job_id=job['id'], action=action)
                after, local_alerts = copy.deepcopy(before), []
                if action == 'replace':
                    after, local_alerts = expand(decision['record'], src, rid, before['id'], index, before)
                if action in {'keep', 'replace'}:
                    after['status'] = 'accepted'
                    after['review_status'] = PENDING if action == 'replace' or before['status'] == 'uncertain' else 'model_reviewed_kept_not_independently_rechecked'
                elif action == 'uncertain':
                    after['status'] = 'uncertain'
                    after['review_status'] = 'model_reviewed_uncertain'
                after['decision_source'] = provenance
                after['review_reason'] = decision['reason']
                alerts.extend(local_alerts)
                if action == 'reject':
                    rejected.append(dict(paper_id=pid, relation_id=rid, original=before,
                                         decision_source=provenance, reason=decision['reason'],
                                         review_status='proposed_rejection_pending_independent_check'))
                    current.pop(rid)
                    after = None
                else:
                    current[rid] = after
                if action in {'replace', 'reject'} or action == 'keep' and before['status'] == 'uncertain':
                    checks[rid] = dict(paper_id=pid, record=before if action == 'reject' else copy.deepcopy(after))
                logs.append(dict(paper_id=pid, relation_id=rid, action=action, before=before,
                                 after=copy.deepcopy(after), reason=decision['reason'],
                                 decision_source=provenance, modality_guard_alerts=local_alerts))
            for number, body in enumerate(output['additions'], 1):
                short_id = f'a{number:03}'
                rid = f'{pid}:audit_v1_{short_id}'
                require(rid not in originals and rid not in current, 'New relation ID collision')
                hint_ids = omission_links(body, src, packet['omission_hints'])
                after, local_alerts = expand(body, src, rid, short_id, index)
                provenance = dict(job['provenance'], job_id=job['id'], action='add', omission_reference_ids=hint_ids,
                                  omission_link_status='quote_overlap_candidate_links' if hint_ids else 'hint_association_pending_review')
                after.update(review_status=PENDING, decision_source=provenance)
                current[rid] = after
                checks[rid] = dict(paper_id=pid, record=copy.deepcopy(after))
                logs.append(dict(paper_id=pid, relation_id=rid, action='add', before=None,
                                 after=copy.deepcopy(after), reason='Targeted omission hint addition; see source model response.',
                                 decision_source=provenance, modality_guard_alerts=local_alerts))
                alerts.extend(local_alerts)
            paper['records'] = list(current.values())
            paper['review_status'] = 'targeted_revision_only_not_whole_paper_acceptance'
    require(seen == set(scope_ids), 'Global decisions differ from repair_scope.target_ids')
    bypaper = collections.defaultdict(list)
    for rid, item in sorted(checks.items()):
        bypaper[item['paper_id']].append({k: copy.deepcopy(item['record'][k]) for k in CONTENT})
    items = [dict(paper_id=pid, title=sources[pid]['title'],
                  segments=[dict(id=s['id'], text=s['text']) for s in sources[pid]['segments']],
                  targets=targets) for pid, targets in sorted(bypaper.items())]
    return dict(revised_all=result, change_log=logs, rejected=rejected,
                postcheck_items=items, modality_guard_alerts=alerts)


def finalize(draft, judgments):
    result = copy.deepcopy(draft['revised_all'])
    papers = {p['paper_id']: p for p in result}
    records = {r['relation_id']: r for p in result for r in p['records']}
    expected = {r['relation_id'] for p in draft['postcheck_items'] for r in p['targets']}
    require(set(judgments) == expected, 'Postcheck judgments must cover exact target set')
    rejected, logs = [], copy.deepcopy(draft['change_log'])
    rejected_map = {r['relation_id']: r for r in draft['rejected']}
    for change in logs:
        rid = change['relation_id']
        if rid not in judgments:
            continue
        judge = copy.deepcopy(judgments[rid])
        require(judge['verdict'] in VERDICTS, 'Invalid postcheck verdict')
        change['independent_postcheck'] = judge
        if change['action'] == 'reject' and judge['verdict'] in {'unsupported', 'out_of_scope'}:
            row = copy.deepcopy(rejected_map[rid])
            row.update(review_status='independently_confirmed_rejection', independent_postcheck=judge)
            rejected.append(row)
            change['final_disposition'] = 'excluded_after_independent_check'
            continue
        if change['action'] == 'reject':
            record = copy.deepcopy(change['before'])
            record.update(status='uncertain', review_status='rejection_disputed_restored_uncertain',
                          decision_source=change['decision_source'])
            papers[change['paper_id']]['records'].append(record)
            change['final_disposition'] = 'restored_uncertain'
        else:
            record = records[rid]
            record['status'] = 'accepted' if judge['verdict'] == 'supported' else 'uncertain'
            record['review_status'] = 'reviewed_supported' if judge['verdict'] == 'supported' else 'independent_check_disputed_uncertain'
            change['final_disposition'] = record['review_status']
        record['independent_postcheck'] = judge
        change['after'] = copy.deepcopy(record)
    return result, rejected, logs


def finalize_single_pass(draft):
    """User-authorized one-review-pass delivery; no second model judgment."""
    result = copy.deepcopy(draft['revised_all'])
    records = {r['relation_id']: r for p in result for r in p['records']}
    logs = copy.deepcopy(draft['change_log'])
    rejected = copy.deepcopy(draft['rejected'])
    for change in logs:
        rid, action = change['relation_id'], change['action']
        if action == 'reject':
            change['final_disposition'] = 'excluded_by_single_model_review'
            continue
        record = records[rid]
        if action == 'keep':
            record.update(status='accepted', review_status='model_reviewed_supported_single_pass')
        elif action in {'replace', 'add'}:
            record.update(status='accepted', review_status='model_repaired_not_independently_rechecked')
            record['note'] = 'Targeted single-pass audit revision; no second independent semantic check performed.'
        else:
            record.update(status='uncertain', review_status='model_reviewed_uncertain')
        change['after'] = copy.deepcopy(record)
        change['final_disposition'] = record['review_status']
    for row in rejected:
        row['review_status'] = 'rejected_by_single_model_review_not_independently_rechecked'
    return result, rejected, logs


def resolve_joint_factor_ids(final, baseline, raw_nodes, logs):
    """Expand only unchanged original joint-factor tokens using local raw IDs."""
    original = {r['relation_id']: r for p in baseline for r in p['records']}
    changes = {entry['relation_id']: entry for entry in logs}
    resolutions = []
    for paper in final:
        pid = paper['paper_id']
        nodes = raw_nodes.get(pid, {})
        for record in paper['records']:
            rid = record['relation_id']
            before = original.get(rid)
            if before is None or record['joint_factors'] != before['joint_factors']:
                continue
            values = copy.deepcopy(record['joint_factors'])
            mapped = [{'raw_id': token, 'label': nodes[token]}
                      for token in values if token in nodes and nodes[token] != token]
            if not mapped:
                continue
            record['joint_factor_raw_values'] = values
            record['joint_factor_local_resolution'] = mapped
            record['joint_factors'] = [nodes.get(token, token) for token in values]
            row = dict(paper_id=pid, relation_id=rid, before=values,
                       after=copy.deepcopy(record['joint_factors']),
                       local_resolution=mapped,
                       reason='Mechanical expansion of exact original model-local node IDs; no new semantic judgment.')
            resolutions.append(row)
            if rid in changes:
                changes[rid]['after'] = copy.deepcopy(record)
                changes[rid]['joint_factor_technical_resolution'] = row
    return resolutions


def load_raw_nodes():
    nodes = {}
    for batch in read(F / 'manifest.json')['batches']:
        directory = F / 'batches' / batch['id']
        attempt = read(directory / 'SUCCESS.json')['attempt']
        response = directory / f'attempt_{attempt:02}' / 'response.json'
        for paper in read(response)['papers']:
            pid = paper['paper_id']
            require(pid not in nodes, 'Duplicate raw paper while resolving joint factors')
            local = {n['id']: n['label'] for n in paper['nodes']}
            require(len(local) == len(paper['nodes']), 'Duplicate raw node ID')
            nodes[pid] = local
    return nodes


def load_inputs():
    baseline_path = F / 'extraction_all.json'
    frozen = read(D / 'freeze.json')
    require(sha(baseline_path) == frozen['baseline_sha256'], 'Frozen baseline changed')
    sources, input_hashes = {}, {}
    manifest = read(F / 'manifest.json')
    for batch in manifest['batches']:
        path = F / 'inputs' / (batch['id'] + '.json')
        require(sha(path) == batch['sha256'], 'Frozen source input changed')
        input_hashes[str(path)] = sha(path)
        for paper in read(path):
            require(paper['paper_id'] not in sources, 'Duplicate source paper')
            sources[paper['paper_id']] = paper
    jobs = []
    for job in read(D / 'repair_jobs.json'):
        path = D / 'jobs' / 'repair' / (job['id'] + '.json')
        response = D / 'runs' / job['id'] / 'response.json'
        success = read(response.parent / 'SUCCESS.json')
        require(sha(path) == job['input_sha256'] == success['input_sha256'], 'Repair input hash mismatch')
        require(sha(response) == success['response_sha256'], 'Repair response hash mismatch')
        jobs.append(dict(id=job['id'], input=read(path), response=read(response),
                         provenance=dict(response_path=str(response.relative_to(D)), response_sha256=sha(response),
                                         input_sha256=sha(path), model=success.get('model'))))
    baseline = read(baseline_path)
    draft = build_draft(baseline, sources, jobs, read(D / 'repair_scope.json')['target_ids'])
    require(sha(baseline_path) == frozen['baseline_sha256'], 'Baseline changed while materializing')
    require(all(sha(p) == h for p, h in input_hashes.items()), 'Source changed while materializing')
    return draft


def load_judgments(draft):
    jobs = read(D / 'postcheck_jobs.json')
    judgments = {}
    expected_content = {r['relation_id']: r for p in draft['postcheck_items'] for r in p['targets']}
    expected_papers = {p['paper_id']: p for p in draft['postcheck_items']}
    for job in jobs:
        path = D / 'jobs' / 'postcheck' / (job['id'] + '.json')
        response = D / 'runs' / job['id'] / 'response.json'
        success = read(response.parent / 'SUCCESS.json')
        require(sha(path) == job['input_sha256'] == success['input_sha256'], 'Postcheck input hash mismatch')
        require(sha(response) == success['response_sha256'], 'Postcheck response hash mismatch')
        packets = read(path)
        for packet in packets:
            expected = expected_papers[packet['paper_id']]
            require(packet['title'] == expected['title'] and packet['segments'] == expected['segments'], 'Postcheck source content mismatch')
            require(set(packet) == {'paper_id', 'title', 'segments', 'targets'}, 'Unblinded postcheck packet fields')
            require({r['relation_id'] for r in packet['targets']} <= {r['relation_id'] for r in expected['targets']}, 'Postcheck target assigned to wrong paper')
        targets = [r for p in packets for r in p['targets']]
        require(all(expected_content.get(r['relation_id']) == r for r in targets), 'Postcheck candidate content mismatch')
        rows = read(response)['judgments']
        require(len(rows) == len(targets) and {r['relation_id'] for r in rows} == {r['relation_id'] for r in targets}, 'Postcheck batch coverage mismatch')
        for row in rows:
            rid = row['relation_id']
            require(rid not in judgments, 'Duplicate postcheck judgment')
            judgments[rid] = dict(row, source=dict(job_id=job['id'], response_sha256=sha(response),
                                                  response_path=str(response.relative_to(D))))
    return judgments


def self_test():
    src = dict(paper_id='PTEST', title='Synthetic', abstract='A. B.',
               segments=[dict(id=0, start=0, end=3, text='A. '), dict(id=1, start=3, end=5, text='B.')])
    body = dict(subject='A', subject_role='material_entity', predicate='relates', object='B',
                object_role='quantity', e=[0, 1], assertion='author_claim', modality='experimental',
                me=[1], conditions='', joint_factors=[], scope='thermodynamics', claim_scope='own_work')
    original, _ = expand(body, src, 'PTEST:r001', 'r001', collections.defaultdict(set))
    original.update(status='uncertain', subject_id='PTEST:n1', object_id='PTEST:n2')
    base = [dict(paper_id='PTEST', domain='iTE', records=[original])]
    old = copy.deepcopy(base)
    packet = dict(paper_id='PTEST', target_ids=['PTEST:r001'], omission_hints=[dict(reference=original)])
    response = dict(papers=[dict(paper_id='PTEST', decisions=[dict(relation_id='PTEST:r001', action='reject', record=None, reason='test')], additions=[body])])
    draft = build_draft(base, {'PTEST':src}, [dict(id='test', provenance={}, input=[packet], response=response)], ['PTEST:r001'], expected_uncertain=1)
    new = draft['revised_all'][0]['records'][0]
    assert new['id'] == 'a001' and new['relation_id'] == 'PTEST:audit_v1_a001'
    assert new['subject_id'] == 'PTEST:n1' and new['object_id'] == 'PTEST:n2'
    assert new['quote'] == 'A. ' and new['context_quotes'] == ['B.']
    assert new['evidence_spans'] == [dict(start=0,end=3),dict(start=3,end=5)]
    assert new['modality_evidence'] == ['B.'] and base == old
    assert all(not ({'status','review_status','decision_source','note'} & set(t)) for p in draft['postcheck_items'] for t in p['targets'])
    js = {rid:dict(relation_id=rid, verdict='partial', reason='test', issues=[]) for rid in ['PTEST:r001','PTEST:audit_v1_a001']}
    final, rejected, _ = finalize(draft, js)
    assert not rejected and len(final[0]['records']) == 2
    assert all(r['status'] == 'uncertain' for r in final[0]['records'])
    js['PTEST:r001']['verdict'] = 'unsupported'
    js['PTEST:audit_v1_a001']['verdict'] = 'supported'
    final, rejected, _ = finalize(draft, js)
    assert len(rejected) == 1 and final[0]['records'][0]['review_status'] == 'reviewed_supported'
    assert base == old
    require(omission_links(dict(body, e=[1]), src, [dict(reference=dict(original, quote='A. ', context_quotes=[]))]) == [], 'Non-overlap must remain reviewable')
    try:
        build_draft(base, {'PTEST':src}, [], [], expected_uncertain=1)
    except ValueError:
        pass
    else:
        raise AssertionError('Missing original uncertain target was not rejected')
    changed = dict(body, subject='C')
    replaced, _ = expand(changed, src, 'PTEST:r001', 'r001', node_index(base[0]), original)
    assert replaced['object_id'] == 'PTEST:n2' and replaced['subject_id'] == 'PTEST:audit_v1_r001_subject'
    single, single_rejected, single_logs = finalize_single_pass(draft)
    assert len(single_rejected) == 1 and len(single[0]['records']) == 1
    assert single[0]['records'][0]['review_status'] == 'model_repaired_not_independently_rechecked'
    assert single_rejected[0]['original'] == original and base == old
    keep_draft = copy.deepcopy(draft)
    keep_record = copy.deepcopy(original)
    keep_draft['revised_all'][0]['records'].append(keep_record)
    keep_draft['rejected'] = []
    keep_draft['change_log'][0].update(action='keep', after=keep_record)
    kept, _, _ = finalize_single_pass(keep_draft)
    kept_original = next(r for r in kept[0]['records'] if r['relation_id'] == 'PTEST:r001')
    assert kept_original['status'] == 'accepted' and kept_original['review_status'] == 'model_reviewed_supported_single_pass'
    factor_base = copy.deepcopy(base)
    factor_base[0]['records'][0]['joint_factors'] = ['dt', 'unknown', 'dt-more']
    factor_final = copy.deepcopy(factor_base)
    factor_final[0]['records'][0]['review_status'] = 'not_targeted_by_full_audit_v1'
    resolution = resolve_joint_factor_ids(factor_final, factor_base, {'PTEST': {'dt': 'Temperature gradient'}, 'POTHER': {'unknown': 'Wrong paper'}}, [])
    resolved = factor_final[0]['records'][0]
    assert len(resolution) == 1 and resolved['joint_factors'] == ['Temperature gradient', 'unknown', 'dt-more']
    assert resolved['joint_factor_raw_values'] == ['dt', 'unknown', 'dt-more']
    assert resolved['review_status'] == 'not_targeted_by_full_audit_v1'
    assert factor_base[0]['records'][0]['joint_factors'] == ['dt', 'unknown', 'dt-more']
    changed_factors = copy.deepcopy(factor_base)
    changed_factors[0]['records'][0]['joint_factors'] = ['model revised dt']
    assert not resolve_joint_factor_ids(changed_factors, factor_base, {'PTEST': {'dt': 'Temperature gradient'}}, [])
    print('PASS: exact local joint-factor expansion, source/status preservation, single-pass keep/reject/add, new IDs, local node reuse, exact quote expansion, immutable source, blinded targets, rejection restoration, strict support gate')


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--draft', action='store_true')
    group.add_argument('--final', action='store_true')
    group.add_argument('--single-pass-final', action='store_true')
    group.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    draft = load_inputs()
    if args.draft:
        write_many(D / 'draft', {name+'.json':value for name,value in draft.items()})
        print(json.dumps(dict(postcheck_targets=sum(len(p['targets']) for p in draft['postcheck_items']), changes=len(draft['change_log']))))
        return
    if args.single_pass_final:
        write_many(D / 'draft', {name+'.json':value for name,value in draft.items()})
        judgments = {}
        final, rejected, logs = finalize_single_pass(draft)
    else:
        for name, value in draft.items():
            require(read(D / 'draft' / (name+'.json')) == value, 'Draft changed since independent postcheck')
        judgments = load_judgments(draft)
        final, rejected, logs = finalize(draft, judgments)
    factor_resolutions = []
    if args.single_pass_final:
        factor_resolutions = resolve_joint_factor_ids(final, read(F/'extraction_all.json'), load_raw_nodes(), logs)
    summary = dict(joint_factor_resolution_records=len(factor_resolutions),
                   joint_factor_resolution_papers=len({r['paper_id'] for r in factor_resolutions}),
                   single_review_pass=args.single_pass_final,
                   independent_postcheck_performed=not args.single_pass_final,
                   baseline_sha256=sha(F/'extraction_all.json'), papers=len(final),
                   relations=sum(len(p['records']) for p in final), rejected=len(rejected),
                   actions=dict(collections.Counter(x['action'] for x in logs)),
                   postcheck_verdicts=dict(collections.Counter(j['verdict'] for j in judgments.values())),
                   status_counts=dict(collections.Counter(r['status'] for p in final for r in p['records'])),
                   review_status_counts=dict(collections.Counter(r['review_status'] for p in final for r in p['records'])),
                   scope_note=('Single targeted Astra review pass, independent of original extraction. Repairs/additions have no second independent semantic check; not whole-corpus semantic acceptance or a new population quality estimate.' if args.single_pass_final else 'Targeted revision verification only; not a new independent whole-corpus acceptance sample or population quality estimate.'))
    files = dict(revised_all=final, rejected=rejected, change_log=logs, summary=summary)
    if args.single_pass_final:
        files['joint_factor_resolution'] = factor_resolutions
    for domain in ('iTE','TG'):
        files['revised_'+domain] = [p for p in final if p['domain'] == domain]
    write_many(D/'final', {name+'.json':value for name,value in files.items()})
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
