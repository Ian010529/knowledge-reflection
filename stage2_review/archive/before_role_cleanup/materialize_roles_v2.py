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
ROLE_REASONS = {
    'M': '按原句中的实体对象判定；不把材料名称本身当作操作或机制。',
    'D': '原短语指对体系进行的设计、制备或运行操作。',
    'C': '原句中作为工况、给定水平或外部施加/改变的运行条件。',
    'I': '原短语指对象之间的相互作用；具体物种限定保留在原文。',
    'P': '原短语指发生的动态物理/化学过程；不等同于该过程的速率或其他量。',
    'S': '原短语描述空间组织、结构或状态；没有将其直接视为实施操作。',
    'Q': '原短语指物理量或量的变化；不等同于材料实体或微观过程。',
    'X': '在所引上下文中作为模型的预测/解释特征；不升级为因果机制。',
    'F': '在所引上下文中作为目标响应、输出性能或实现的功能。',
    'A': '原短语指应用场景或用途，而非微观过程。',
    'U': '现有十类无法可靠覆盖该短语，保留节点并留空主角色待审。',
}

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write(path, rows):
    assert rows
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    assert not args.output.exists(), 'Refuse to overwrite existing delivery'
    nodes = read(SOURCE / 'node_evidence.csv')
    by_id = {n['mention_id']: n for n in nodes}
    papers = {p['paper_id']: p for p in read(SOURCE / 'paper_coverage.csv')}
    relations = {r['relation_id']: r for r in read(SOURCE / 'relation_evidence.csv')}
    decisions = {}
    overrides = json.loads((BATCH / 'pilot_calibration_overrides.json').read_text())['overrides']
    for r in read(PILOT / 'role_model_proposals_pilot.csv'):
        extra = overrides.get(r['mention_id'], {})
        flags = ';'.join(filter(None, (r['role_flags'], extra.get('add_flags', ''))))
        decisions[r['mention_id']] = dict(role=r['proposed_semantic_role'], detail=r['role_detail'],
            flags=flags, reason=r['model_reason'], calibration_reason=extra.get('calibration_reason',
            '按规则 v2 重读原证据句后保留原模型建议，未升级成人工标签。'),
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
                        reason=extra.get('reason', ROLE_REASONS[code]), calibration_reason='',
                        decision_source=path.name, evidence_scope=values.get('evidence_scope', data.get('evidence_scope', 'original_quote')))
    out = args.output.resolve(); out.mkdir(parents=True)
    rows = []
    for n in nodes:
        if n['mention_id'] not in decisions:
            continue
        d = decisions[n['mention_id']]
        assert d['role'] in ROLE_CODES.values(), n['mention_id']
        rows.append(dict(mention_id=n['mention_id'], paper_id=n['paper_id'], domain=n['domain'],
            raw_phrase=n['raw_phrase'], legacy_role=n['legacy_role'], proposed_semantic_role=d['role'],
            role_detail=d['detail'], role_flags=d['flags'], model_reason=d['reason'],
            calibration_reason=d['calibration_reason'], quote=n['quote'], claim_id=n['claim_id'],
            full_abstract=papers[n['paper_id']]['abstract'], evidence_scope=d['evidence_scope'],
            rule_version='ROLE_RULES_v2', decision_source=d['decision_source'],
            annotation_status='model_proposed_pending_human' if d['role'] else 'ontology_gap_pending_review',
            annotation_author='Codex current session', human_decision='', human_role='', human_reason=''))
    write(out / 'role_model_proposals.csv', rows)
    write(out / 'batch02_role_proposals.csv', [r for r in rows if r['decision_source'] == 'batch02_v1'])
    write(out / 'pilot_recalibrated.csv', [r for r in rows if r['decision_source'] == 'pilot_recalibration'])
    unresolved = [r for r in rows if r['role_flags'] or not r['proposed_semantic_role']]
    write(out / 'flagged_nodes.csv', unresolved)
    queue = [dict(mention_id=n['mention_id'], domain=n['domain'], paper_id=n['paper_id'],
                  raw_phrase=n['raw_phrase'], status='not_yet_annotated') for n in nodes if n['mention_id'] not in decisions]
    if queue:
        write(out / 'remaining_nodes.csv', queue)
    issue_data = json.loads((BATCH / 'relation_issue_decisions.json').read_text())
    issues = []
    for i, issue in enumerate(issue_data['issues'], 1):
        for rid in issue['relation_ids']:
            r = relations[rid]
            issues.append(dict(issue_id=f'issue_v2_{i:03d}', relation_id=rid, paper_id=r['paper_id'],
                issue_type=issue['issue_type'], reason=issue['reason'], proposed_action=issue['proposed_action'],
                subject=by_id[r['subject_mention_id']]['raw_phrase'], predicate=r['raw_predicate'],
                object=by_id[r['object_mention_id']]['raw_phrase'], quote=r['quote'],
                status='model_issue_pending_review', source_edit_applied=False))
    write(out / 'relation_issue_register.csv', issues)
    qualifiers = []
    for i, q in enumerate(issue_data['qualifiers'], 1):
        pid = q['paper_id']; domain = papers[pid]['domain']
        for local in q['relation_local_ids']:
            r = relations[f'{domain}:{pid}:{local}']
            assert q['evidence'] in r['quote'], q
            qualifiers.append(dict(qualifier_id=f'qualifier_v2_{i:03d}', relation_id=r['relation_id'],
                paper_id=pid, kind=q['kind'], mention_ids=';'.join(f'{domain}:{pid}:{n}' for n in q['mention_local_ids']),
                exact_evidence=q['evidence'], evidence_start_in_quote=r['quote'].index(q['evidence']),
                interpretation=q['interpretation'], status='model_proposed_pending_human'))
    write(out / 'relation_qualifiers.csv', qualifiers)
    summary = dict(status='MODEL_ANNOTATION_NOT_HUMAN_ACCEPTED', source_nodes=len(nodes),
        processed_nodes=len(rows), assigned_proposed_roles=sum(bool(r['proposed_semantic_role']) for r in rows),
        ontology_gaps=sum(not r['proposed_semantic_role'] for r in rows), remaining_nodes=len(queue),
        by_domain=dict(Counter(r['domain'] for r in rows)),
        role_distribution=dict(Counter(r['proposed_semantic_role'] or 'unresolved' for r in rows)),
        flagged_nodes=len(unresolved), issue_groups=len(issue_data['issues']),
        issue_relation_rows=len(issues), qualifier_groups=len(issue_data['qualifiers']),
        qualifier_relation_rows=len(qualifiers), human_reviewed=0, concepts_merged=0, source_relations_modified=0)
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    source_hashes = {n: sha(SOURCE / n) for n in ('node_evidence.csv','relation_evidence.csv','paper_coverage.csv')}
    input_paths = [BATCH / n for n in ('ROLE_RULES_v2.md','model_role_decisions.json',
        'pilot_calibration_overrides.json','relation_issue_decisions.json','selection.json')]
    input_paths += sorted(bulk_dir.glob('decisions_*.json')) if bulk_dir.exists() else []
    (out / 'provenance.json').write_text(json.dumps(dict(source_files=source_hashes,
        decision_files={str(p.relative_to(BASE)):sha(p) for p in input_paths},
        rule_sha256=sha(BATCH / 'ROLE_RULES_v2.md'), materializer_sha256=sha(Path(__file__))),indent=2)+'\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
