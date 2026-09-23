#!/usr/bin/env python3
"""Reconstruct the delivered core-claim TXT without adding or merging claims.

Uses only the delivered TXT and the two corrected corpora. No model calls.
Existing destinations are refused; each run is a separate snapshot.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TXT = Path('当前会话抽取结果.txt')
PLAN = Path('iTE_TG双知识图谱研究方案_v2.0_可执行版.docx')
CORPORA = {'iTE': Path('cleaned_ite_tg/data/ite_clean.csv'),
           'TG': Path('cleaned_ite_tg/data/tg_clean.csv')}
ROLES = {'material_strategy', 'interaction', 'mechanism',
         'physical_consequence', 'performance'}
ASSERTIONS = {'author_claim', 'association', 'hypothesis', 'negated'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_csv(path, rows):
    require(bool(rows), f'Empty table: {path.name}')
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def positions(text, phrase, offset=0):
    """All overlapping exact matches; zero-based Unicode character offsets."""
    result = []
    start = 0
    while phrase:
        start = text.find(phrase, start)
        if start < 0:
            break
        result.append([offset + start, offset + start + len(phrase)])
        start += 1
    return result


def parse(source, corpus):
    separators = list(re.finditer(r'^={20,}\s*\n', source, re.M))
    require(bool(separators), 'No record separators')
    preamble = source[:separators[0].start()]
    metadata = json.JSONDecoder().raw_decode(preamble[preamble.index('{'):])[0]
    blocks = []
    seen = set()
    for index, sep in enumerate(separators):
        end = separators[index + 1].start() if index + 1 < len(separators) else len(source)
        raw = source[sep.end():end].strip('\n')
        pattern = (r'(?P<domain>iTE|TG) / (?P<pid>P\d+) / (?P<title>[^\n]+)\n'
                   r'原文证据：\n(?P<quote>.*?)^节点：\n(?P<nodes>.*?)'
                   r'^关系：\n(?P<edges>.*?)^限制／歧义：(?P<limitations>.*)')
        m = re.fullmatch(pattern, raw, re.M | re.S)
        require(m is not None, f'Unparsed record {index + 1}')
        b = m.groupdict()
        pid = b['pid']
        require(pid not in seen, f'Duplicate paper {pid}')
        seen.add(pid)
        require(pid in corpus, f'Unknown paper {pid}')
        original = corpus[pid]
        require(b['domain'] == original['domain'], f'Domain mismatch {pid}')
        require(b['title'] == original['文章名'], f'Title mismatch {pid}')
        b['quote'] = b['quote'].strip()
        b['limitations'] = b['limitations'].strip()
        b['nodes_raw'], b['edges_raw'] = b['nodes'], b['edges']
        b['nodes'], b['edges'] = [], []
        local_ids = set()
        for line in b['nodes_raw'].splitlines():
            if not line.strip():
                continue
            node = re.fullmatch(r'(n\d+) \[([^\]]+)\] (.+)', line)
            require(node is not None, f'Unparsed node in {pid}: {line}')
            nid, role, label = node.groups()
            require(nid not in local_ids, f'Duplicate local ID in {pid}: {nid}')
            require(role in ROLES, f'Unknown legacy role: {role}')
            local_ids.add(nid)
            b['nodes'].append((nid, role, label))
        for line in b['edges_raw'].splitlines():
            if not line.strip():
                continue
            edge = re.fullmatch(r'(n\d+) -> (n\d+): (.+) \[([^\]]+)\]', line)
            require(edge is not None, f'Unparsed relation in {pid}: {line}')
            u, v, predicate, assertion = edge.groups()
            require(u in local_ids and v in local_ids, f'Dangling endpoint {pid}: {line}')
            require(assertion in ASSERTIONS, f'Unknown assertion: {assertion}')
            b['edges'].append((u, v, predicate, assertion))
        b['quote_spans'] = positions(original['摘要'], b['quote'])
        require(not b['quote'] or len(b['quote_spans']) == 1,
                f'Quote not uniquely locatable: {pid}')
        require(not b['nodes'] or b['quote'], f'Nodes with no evidence quote: {pid}')
        require(bool(original['摘要'].strip()) or not b['nodes'], f'Nodes with missing abstract: {pid}')
        b['record_index'] = index + 1
        b['txt_header_line'] = source.count('\n', 0, sep.end()) + 1
        b['raw_record_sha256'] = text_digest(raw)
        blocks.append(b)
    return metadata, blocks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'stage2_reconstruction'/'v1')
    args = parser.parse_args()
    out = args.output.resolve()
    require(not out.exists(), f'Destination exists; choose a new --output: {out}')
    corpus = {}
    for domain, path in CORPORA.items():
        for row_number, row in enumerate(read_csv(ROOT/path), 2):
            require(row['paper_id'] not in corpus, f'Duplicate corpus ID {row["paper_id"]}')
            corpus[row['paper_id']] = dict(row, domain=domain, corpus_path=str(path),
                                           corpus_csv_row=row_number)
    source = (ROOT/TXT).read_text(encoding='utf-8')
    metadata, blocks = parse(source, corpus)
    require(metadata['corpus_papers'] == len(corpus), 'Corpus count differs from TXT metadata')
    for domain, path in CORPORA.items():
        require(digest(ROOT/path) == metadata['inputs'][domain]['sha256'], f'Input hash mismatch: {domain}')
    by_paper = {b['pid']: b for b in blocks}
    require(all(not r['摘要'].strip() for p, r in corpus.items() if p not in by_paper),
            'A paper with an abstract is absent from TXT')
    run_id = 'txt_reconstruction_v1_' + digest(ROOT/TXT)[:12]
    papers, claims, nodes, relations, concepts, assignments = [], [], [], [], [], []
    for pid, c in sorted(corpus.items()):
        b = by_paper.get(pid)
        status = ('missing_abstract' if not c['摘要'].strip() else
                  'extracted_core_claim' if b['nodes'] else 'no_selected_core_claim')
        papers.append(dict(paper_id=pid, domain=c['domain'], title=c['文章名'],
            journal=c['期刊名'], doi=c['DOI'], year=c['年份'], source_membership=c['source_membership'],
            coverage_status=status, txt_record_present=bool(b),
            txt_header_line=b['txt_header_line'] if b else '',
            node_count=len(b['nodes']) if b else 0, relation_count=len(b['edges']) if b else 0,
            claim_id=f'{c["domain"]}:{pid}:claim_block' if b else '',
            abstract=c['摘要'], abstract_sha256=text_digest(c['摘要']),
            corpus_path=c['corpus_path'], corpus_csv_row=c['corpus_csv_row'],
            source_record_ids=c['source_record_ids'],
            limitation_note=b['limitations'] if b else 'Absent from TXT; restored from corpus registry only; no abstract or extraction added.',
            reconstruction_run_id=run_id))
    for b in blocks:
        prefix = f'{b["domain"]}:{b["pid"]}'
        claim_id = prefix + ':claim_block'
        qspan = b['quote_spans'][0] if b['quote_spans'] else ['', '']
        claims.append(dict(claim_id=claim_id, paper_id=b['pid'], domain=b['domain'],
            quote=b['quote'], quote_start_char=qspan[0], quote_end_char=qspan[1],
            quote_location_status='exact_unique' if b['quote'] else 'empty_in_export',
            evidence_scope='exported_paper_block_not_verified_atomic_claim',
            limitations=b['limitations'], txt_record_index=b['record_index'],
            txt_header_line=b['txt_header_line'], raw_record_sha256=b['raw_record_sha256'],
            semantic_review_status='not_reviewed', reconstruction_run_id=run_id))
        for nid, role, label in b['nodes']:
            mention_id = prefix + ':' + nid
            spans = positions(b['quote'], label, int(qspan[0]))
            unique = len(spans) == 1
            span_status = 'exact_unique_in_quote' if unique else 'multiple_exact_matches_in_quote' if spans else 'not_verbatim_in_quote'
            concept_id = prefix + ':initial_' + nid
            nodes.append(dict(mention_id=mention_id, paper_id=b['pid'], domain=b['domain'],
                local_node_id=nid, raw_phrase=label, legacy_role=role, semantic_role='',
                claim_id=claim_id, quote=b['quote'], phrase_location_status=span_status,
                phrase_start_char=spans[0][0] if unique else '',
                phrase_end_char=spans[0][1] if unique else '',
                phrase_span_candidates=json.dumps(spans),
                semantic_review_status='not_reviewed', reconstruction_run_id=run_id))
            concepts.append(dict(initial_concept_id=concept_id, domain=b['domain'],
                label=label, source_mention_id=mention_id, legacy_role=role, semantic_role='',
                normalization_status='unmerged_initialization', semantic_review_status='not_reviewed'))
            assignments.append(dict(mention_id=mention_id, initial_concept_id=concept_id,
                assignment_kind='identity_only_no_semantic_decision', decision_source='deterministic_reconstruction',
                reconstruction_run_id=run_id))
        for order, (u, v, predicate, assertion) in enumerate(b['edges'], 1):
            relations.append(dict(relation_id=f'{prefix}:r{order:03d}', paper_id=b['pid'],
                domain=b['domain'], subject_mention_id=prefix+':'+u, object_mention_id=prefix+':'+v,
                raw_predicate=predicate, assertion_type=assertion,
                direction='subject_to_object_as_exported', claim_id=claim_id,
                quote=b['quote'], limitations=b['limitations'],
                joint_factor_group='', condition_annotation_status='not_reconstructed',
                semantic_review_status='not_reviewed', graph_status='machine_candidate_only',
                reconstruction_run_id=run_id))
    require(len(nodes) == metadata['node_count'], 'Node total differs from TXT metadata')
    require(len(relations) == metadata['edge_count'], 'Relation total differs from TXT metadata')
    tables = {'paper_coverage.csv': papers, 'claim_evidence.csv': claims,
              'node_evidence.csv': nodes, 'relation_evidence.csv': relations,
              'initial_concepts.csv': concepts, 'initial_normalization_assignments.csv': assignments}
    out.mkdir(parents=True)
    frozen = out/'stage1_frozen'
    frozen.mkdir()
    source_manifest = []
    for relative in [TXT, *CORPORA.values(), PLAN]:
        dest = frozen/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, dest)
        require(digest(dest) == digest(ROOT/relative), f'Snapshot hash mismatch: {relative}')
        dest.chmod(0o444)
        source_manifest.append(dict(project_path=str(relative), snapshot_path=str(dest.relative_to(out)),
                                    sha256=digest(dest), bytes=dest.stat().st_size))
    write_json(frozen/'source_metadata.json', metadata)
    for name, rows in tables.items():
        write_csv(out/name, rows)
    # Round-trip through the saved CSVs, then verify foreign keys and offsets.
    saved = {name: read_csv(out/name) for name in tables}
    checks = {}
    checks['all_tables_roundtrip_without_cell_changes'] = all(
        actual == [{k: str(v) for k, v in row.items()} for row in tables[name]]
        for name, actual in saved.items())
    checks['all_corpus_papers_retained'] = {r['paper_id'] for r in saved['paper_coverage.csv']} == set(corpus)
    node_ids = {r['mention_id'] for r in saved['node_evidence.csv']}
    claim_ids = {r['claim_id'] for r in saved['claim_evidence.csv']}
    checks['unique_node_ids'] = len(node_ids) == len(nodes)
    checks['unique_relation_ids'] = len({r['relation_id'] for r in relations}) == len(relations)
    checks['all_relation_endpoints_exist'] = all(
        r['subject_mention_id'] in node_ids and r['object_mention_id'] in node_ids for r in relations)
    checks['all_evidence_foreign_keys_exist'] = all(r['claim_id'] in claim_ids for r in nodes+relations)
    checks['all_nonempty_quotes_roundtrip_to_abstract'] = all(
        not r['quote'] or corpus[r['paper_id']]['摘要'][int(r['quote_start_char']):int(r['quote_end_char'])] == r['quote']
        for r in saved['claim_evidence.csv'])
    checks['all_reported_node_offsets_exact'] = all(
        not r['phrase_start_char'] or corpus[r['paper_id']]['摘要'][int(r['phrase_start_char']):int(r['phrase_end_char'])] == r['raw_phrase']
        for r in saved['node_evidence.csv'])
    checks['initial_concept_mapping_is_one_to_one'] = (
        len({r['initial_concept_id'] for r in assignments}) == len(nodes)
        and {r['mention_id'] for r in assignments} == node_ids)
    checks['no_model_or_human_review_claimed'] = all(r['semantic_review_status']=='not_reviewed' for r in nodes+relations)
    checks['original_input_hashes_unchanged'] = all(digest(ROOT/x['project_path'])==x['sha256'] for x in source_manifest)
    require(all(checks.values()), f'Validation failed: {checks}')
    summary = dict(reconstruction_run_id=run_id, status='PASS_STRUCTURAL_ONLY',
        table_counts={k:len(v) for k,v in tables.items()},
        coverage_by_domain={d:dict(Counter(r['coverage_status'] for r in papers if r['domain']==d)) for d in CORPORA},
        node_counts_by_domain=dict(Counter(r['domain'] for r in nodes)),
        relation_counts_by_domain=dict(Counter(r['domain'] for r in relations)),
        quote_location_counts=dict(Counter(r['quote_location_status'] for r in claims)),
        node_phrase_location_counts=dict(Counter(r['phrase_location_status'] for r in nodes)),
        legacy_role_counts=dict(Counter(r['legacy_role'] for r in nodes)),
        assertion_type_counts=dict(Counter(r['assertion_type'] for r in relations)),
        restored_registry_only_papers=[r['paper_id'] for r in papers if not r['txt_record_present']],
        checks=checks,
        limitations=['No extraction completeness or semantic accuracy audit performed.',
            'IDs are newly assigned reconstruction IDs, not recovered IDs from missing exports.',
            'Initial concepts are one per mention; no semantic normalization or merging performed.',
            'Quote offsets reference original CSV abstract text, zero-based Unicode indices, end exclusive.',
            'Node labels absent verbatim from quotes are retained; this flag is not a semantic error judgment.',
            'Conditions, joint factor groups, sentence IDs, original model identity and original run logs cannot be recovered from this TXT alone.'])
    write_json(out/'validation_report.json', summary)
    report = f'''# Stage 2 结构化证据重建报告

本次完成确认版研究方案 Stage 2 的 Step 0：冻结现有文件，并将 TXT 中已有内容转成结构化证据表。未重新抽取摘要，未调用模型，未合并概念，未进行科学语义审核。

## 已完成

- 论文登记：{len(papers):,} 篇，iTE 1,644 篇、TG 333 篇。
- TXT 记录：{len(claims):,} 条，覆盖全部 1,971 篇有摘要论文及 1 篇缺摘要 TG 论文。
- 原始节点：{len(nodes):,} 个；原始关系：{len(relations):,} 条，全部保留。
- 其余 5 篇缺摘要 iTE 论文从语料登记表补回，仅恢复登记，不添加抽取。
- 1,937 段非空引用全部精确且唯一定位，35 条记录原本没有引用。
- 结构校验全部通过，原始文件哈希未改变。

## 文件使用顺序

1. paper_coverage.csv：论文身份、全文摘要字段、覆盖状态和逐篇限制。
2. claim_evidence.csv：每篇导出块的证据引用及字符位置；一个块不等于一个经验证的原子科学主张。
3. node_evidence.csv 与 relation_evidence.csv：节点、关系及证据外键，所有原标签与断言类型保留。
4. initial_concepts.csv 与 initial_normalization_assignments.csv：一节点一概念的未合并起点。
5. validation_report.json 与 delivery_manifest.json：结构校验及文件哈希。

## 必须保留的解释

1,858 篇记录有节点；113 篇未选出核心陈述；6 篇缺摘要。未选出陈述不表示全文没有机制，也不能直接记为抽取错误。论文来源域不等于机制分类。

节点名称可能是概括性短语，未必逐字出现在引用中。精确位置状态为 {json.dumps(summary['node_phrase_location_counts'], ensure_ascii=False)}。仅唯一逐字匹配时填写单一位置，多处匹配保留所有候选；其余留空。任何定位状态都不能替代语义审计。

所有节点的 semantic_role 留空，semantic_review_status 为 not_reviewed。新生成的 {len(concepts):,} 个 initial concept 是逐节点占位概念，不是最终独立机制数；不能与旧方案中尚未交付的 4,333 个规范概念等同。343 项旧合并决定没有从 TXT 中恢复，也没有推测补造。

## 下一步

在本目录的冻结证据基础上另建角色标注和归一化审核表；先制定并试用角色 v2，按计划抽样审计关系和核心陈述覆盖，再生成同域归一化候选。只有确认同义的决定才可在新版本中合并。现阶段不据此生成正式中心性、社区或跨域排名结论。
'''
    (out/'README.md').write_text(report, encoding='utf-8')
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(), reconstruction_run_id=run_id,
        schema_version='reconstructed_core_claim_v1', source_files=source_manifest,
        script=dict(path=str(Path(__file__).relative_to(ROOT)), sha256=digest(Path(__file__))),
        sources_not_used=['historical concept/graph/prediction directories', 'source material/mechanism annotation columns'],
        outputs={str(p.relative_to(out)):dict(sha256=digest(p),bytes=p.stat().st_size)
                 for p in sorted(out.glob('*')) if p.is_file()})
    write_json(out/'delivery_manifest.json', manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
