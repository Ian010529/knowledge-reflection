#!/usr/bin/env python3
"""Join recorded model role decisions to evidence. Does not infer any labels."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE.parent / 'stage2_reconstruction/v1'
PILOT = BASE / 'v1'
BATCH = BASE / 'batch02_v1'
ROLE_CODES = dict(M='material_entity', D='design_strategy', C='condition', I='interaction',
                  P='mechanism_process', S='state_structure', Q='quantity', X='descriptor',
                  F='performance_function', A='application', U='')
# Select existing uncertainty notes for review; this does not infer or change roles.
REVIEW_MARKERS = ('ambigu', 'unresolved', 'underspecified', 'ontology_gap',
                  'review', 'alternative', 'compound_mixed_roles', 'mixture',
                  'incomplete', 'encoding_artifact')

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write(path, rows, fields=None):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--review-decisions', type=Path,
                    help='Explicitly recorded second-pass decisions for the pending items')
    ap.add_argument('--followup-decisions', type=Path,
                    help='Recorded follow-up on the remaining pending mentions; requires --review-decisions')
    args = ap.parse_args()
    assert not args.output.exists(), 'Refuse to overwrite existing delivery'
    nodes = read(SOURCE / 'node_evidence.csv')
    decisions = {}
    overrides = json.loads((BATCH / 'pilot_calibration_overrides.json').read_text())['overrides']
    for r in read(PILOT / 'role_model_proposals_pilot.csv'):
        extra = overrides.get(r['mention_id'], {})
        flags = ';'.join(filter(None, (r['role_flags'], extra.get('add_flags', ''))))
        decisions[r['mention_id']] = dict(role=r['proposed_semantic_role'], detail=r['role_detail'],
            flags=flags, reason=r['model_reason'], calibration_reason=extra.get('calibration_reason', ''),
            decision_source='pilot_recalibration', evidence_scope='original_quote_rechecked')
    manual = json.loads((BATCH / 'model_role_decisions.json').read_text())
    for pid, values in manual['papers'].items():
        paper_nodes = [n for n in nodes if n['paper_id'] == pid]
        assert len(values) == len(paper_nodes), pid
        for n, (role, detail, flags, reason) in zip(paper_nodes, values):
            assert n['mention_id'] not in decisions
            decisions[n['mention_id']] = dict(role=role, detail=detail, flags=flags, reason=reason,
                calibration_reason='', decision_source='batch02_v1', evidence_scope='full_abstract_and_quote')
    # Each compact code is explicitly assigned by the model after reading the evidence.
    # The mapping expands recorded decisions; it is not a keyword classification algorithm.
    bulk_dir = BASE / 'bulk_roles_v2'
    if bulk_dir.exists():
        for path in sorted(bulk_dir.glob('decisions_*.json')):
            data = json.loads(path.read_text())
            for pid, values in data['papers'].items():
                paper_nodes = [n for n in nodes if n['paper_id'] == pid]
                codes = values['roles'].split()
                assert len(codes) == len(paper_nodes), (pid, len(codes), len(paper_nodes))
                for n, code in zip(paper_nodes, codes):
                    assert n['mention_id'] not in decisions, n['mention_id']
                    extra = values.get('details', {}).get(n['local_node_id'], {})
                    decisions[n['mention_id']] = dict(role=ROLE_CODES[code], detail=extra.get('detail', ''),
                        flags=extra.get('flags', 'ontology_gap' if code == 'U' else ''),
                        reason=extra.get('reason', ''), calibration_reason='',
                        decision_source=path.name, evidence_scope=values.get('evidence_scope', data.get('evidence_scope', 'original_quote')))
    review_summary = None
    if args.review_decisions:
        review = json.loads(args.review_decisions.read_text())
        expected = {mid for mid, d in decisions.items() if not d['role'] or
                    any(marker in d['flags'] for marker in REVIEW_MARKERS)}
        lookup = {(n['paper_id'], n['local_node_id']): n['mention_id'] for n in nodes}
        reviewed = set()
        changed = newly_assigned = newly_unresolved = still_pending = 0
        for pid, values in review['papers'].items():
            for nid, value in values.items():
                if nid == 'scope':
                    continue
                mid = lookup[(pid, nid)]
                assert mid in expected and mid not in reviewed, mid
                code, flags, reason = value
                assert code in ROLE_CODES and reason and (code != 'U' or flags), mid
                old_role = decisions[mid]['role']
                role = ROLE_CODES[code]
                changed += role != old_role
                newly_assigned += bool(role) and not old_role
                newly_unresolved += bool(old_role) and not role
                still_pending += not role or any(m in flags for m in REVIEW_MARKERS)
                decisions[mid].update(role=role, flags=flags, reason=reason, calibration_reason='',
                    decision_source=args.review_decisions.name,
                    evidence_scope=values.get('scope', 'original_quote_rechecked'))
                reviewed.add(mid)
        assert reviewed == expected, ('Review coverage mismatch', expected - reviewed)
        review_summary = dict(reviewed_nodes=len(reviewed), roles_changed=changed,
            previously_unresolved_now_assigned=newly_assigned,
            previously_assigned_now_unresolved=newly_unresolved,
            cleared_pending_flags=len(reviewed)-still_pending, still_pending=still_pending,
            independent_human_review=False)
    followup_summary = None
    if args.followup_decisions:
        assert args.review_decisions, 'Follow-up requires the preceding review'
        followup = json.loads(args.followup_decisions.read_text())
        for name, expected_hash in followup['input_hashes'].items():
            assert sha(BASE.parent / name) == expected_hash, f'Follow-up input changed: {name}'
        expected = {mid for mid, d in decisions.items() if not d['role'] or
                    any(marker in d['flags'] for marker in REVIEW_MARKERS)}
        assert set(followup['decisions']) == expected, 'Follow-up coverage mismatch'
        changed = cleared = newly_assigned = newly_unresolved = 0
        for mid, value in followup['decisions'].items():
            old = decisions[mid]
            assert value['previous_role'] == old['role'], mid
            code, flags, reason = value['role_code'], value['flags'], value['reason']
            assert code in ROLE_CODES and reason and (code != 'U' or flags), mid
            role = ROLE_CODES[code]
            changed += role != old['role']
            newly_assigned += bool(role) and not old['role']
            newly_unresolved += bool(old['role']) and not role
            cleared += bool(role) and not any(m in flags for m in REVIEW_MARKERS)
            old.update(role=role, flags=flags, reason=reason, calibration_reason='',
                       decision_source=args.followup_decisions.name,
                       evidence_scope=value['evidence_scope'])
        followup_summary = dict(reviewed_nodes=len(expected), roles_changed=changed,
            previously_unresolved_now_assigned=newly_assigned,
            previously_assigned_now_unresolved=newly_unresolved,
            cleared_pending_flags=cleared, still_pending=len(expected)-cleared,
            independent_human_review=False)
    out = args.output.resolve(); out.mkdir(parents=True)
    rows = []
    pending = []
    for n in nodes:
        if n['mention_id'] not in decisions:
            continue
        d = decisions[n['mention_id']]
        assert d['role'] in ROLE_CODES.values(), n['mention_id']
        rows.append(dict(mention_id=n['mention_id'], paper_id=n['paper_id'], domain=n['domain'],
            raw_phrase=n['raw_phrase'], proposed_semantic_role=d['role'], quote=n['quote'],
            evidence_scope=d['evidence_scope'], decision_source=d['decision_source'],
            annotation_status='model_proposed_pending_human' if d['role'] else 'unresolved_role_pending_review',
            human_decision='', human_role='', human_reason=''))
        review_flags = [f for f in d['flags'].split(';') if any(m in f for m in REVIEW_MARKERS)]
        if not d['role'] or review_flags:
            pending.append(dict(rows[-1], review_flags=';'.join(review_flags),
                review_note=' '.join(dict.fromkeys(filter(None, (d['reason'], d['calibration_reason']))))))
    write(out / 'role_model_proposals.csv', rows)
    write(out / 'pending_review.csv', pending, list(rows[0]) + ['review_flags', 'review_note'])
    summary = dict(status='MODEL_ANNOTATION_NOT_HUMAN_ACCEPTED', source_nodes=len(nodes),
        processed_nodes=len(rows), assigned_proposed_roles=sum(bool(r['proposed_semantic_role']) for r in rows),
        unresolved_roles=sum(not r['proposed_semantic_role'] for r in rows), remaining_nodes=len(nodes)-len(rows),
        by_domain=dict(Counter(r['domain'] for r in rows)),
        role_distribution=dict(Counter(r['proposed_semantic_role'] or 'unresolved' for r in rows)),
        pending_review_nodes=len(pending), human_reviewed=0, concepts_merged=0, source_relations_modified=0)
    if review_summary:
        summary['second_pass_review'] = review_summary
    if followup_summary:
        summary['third_pass_review'] = followup_summary
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    source_hashes = {n: sha(SOURCE / n) for n in ('node_evidence.csv','relation_evidence.csv','paper_coverage.csv')}
    input_paths = [BATCH / n for n in ('ROLE_RULES_v2.md','model_role_decisions.json',
        'pilot_calibration_overrides.json','selection.json')]
    input_paths += [PILOT / 'role_model_proposals_pilot.csv']
    input_paths += sorted(bulk_dir.glob('decisions_*.json')) if bulk_dir.exists() else []
    if args.review_decisions:
        input_paths.append(args.review_decisions.resolve())
    if args.followup_decisions:
        input_paths.append(args.followup_decisions.resolve())
    (out / 'provenance.json').write_text(json.dumps(dict(source_files=source_hashes,
        decision_files={str(p.relative_to(BASE)):sha(p) for p in input_paths},
        rule_sha256=sha(BATCH / 'ROLE_RULES_v2.md'), materializer_sha256=sha(Path(__file__))),indent=2)+'\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
