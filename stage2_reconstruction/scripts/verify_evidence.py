#!/usr/bin/env python3
"""Read-only verification of reconstructed tables against the frozen TXT."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(base):
    manifest = json.loads((base/'delivery_manifest.json').read_text())
    for relative, metadata in manifest['outputs'].items():
        assert sha(base/relative) == metadata['sha256'], relative
    for item in manifest['source_files']:
        assert sha(base/item['snapshot_path']) == item['sha256'], item['snapshot_path']
    source = (base/'stage1_frozen'/'当前会话抽取结果.txt').read_text()
    paper_rows = read(base/'paper_coverage.csv')
    papers = {r['paper_id']:r for r in paper_rows}
    claims = {r['paper_id']:r for r in read(base/'claim_evidence.csv')}
    node_rows = read(base/'node_evidence.csv')
    nodes = {r['mention_id']:r for r in node_rows}
    edge_rows = read(base/'relation_evidence.csv')
    all_expected_nodes, all_expected_edges = [], []
    headers = list(re.finditer(r'^(iTE|TG) / (P\d+) / ([^\n]+)$', source, re.M))
    assert len(headers) == len(claims)
    for i,h in enumerate(headers):
        domain,pid,title = h.groups()
        body = source[h.end():headers[i+1].start() if i+1<len(headers) else len(source)]
        assert papers[pid]['domain'] == domain and papers[pid]['title'] == title
        node_section = body.split('节点：\n',1)[1].split('关系：\n',1)[0]
        edge_section = body.split('关系：\n',1)[1].split('限制／歧义：',1)[0]
        expected_nodes = [x for x in node_section.splitlines() if x.strip()]
        expected_edges = [x for x in edge_section.splitlines() if x.strip()]
        saved_nodes = [r for r in node_rows if r['paper_id']==pid]
        saved_edges = [r for r in edge_rows if r['paper_id']==pid]
        assert [f'{r["local_node_id"]} [{r["legacy_role"]}] {r["raw_phrase"]}' for r in saved_nodes] == expected_nodes, pid
        assert [f'{r["subject_mention_id"].split(":")[-1]} -> {r["object_mention_id"].split(":")[-1]}: {r["raw_predicate"]} [{r["assertion_type"]}]' for r in saved_edges] == expected_edges, pid
        for edge in saved_edges:
            for endpoint in ['subject_mention_id','object_mention_id']:
                assert nodes[edge[endpoint]]['paper_id']==pid
                assert nodes[edge[endpoint]]['domain']==domain
            assert edge['claim_id']==claims[pid]['claim_id']
        original_quote = body.split('原文证据：',1)[1].split('节点：',1)[0].strip()
        assert claims[pid]['quote']==original_quote
        if original_quote:
            c=claims[pid]
            assert papers[pid]['abstract'][int(c['quote_start_char']):int(c['quote_end_char'])]==original_quote
        limitation = body.split('限制／歧义：',1)[1].split('='*20,1)[0].strip()
        assert claims[pid]['limitations']==limitation
        all_expected_nodes.extend(expected_nodes)
        all_expected_edges.extend(expected_edges)
    assert len(node_rows)==len(all_expected_nodes)==len(nodes)
    assert len(edge_rows)==len(all_expected_edges)
    for node in node_rows:
        assert node['semantic_role']=='' and node['semantic_review_status']=='not_reviewed'
        spans=json.loads(node['phrase_span_candidates'])
        for start,end in spans:
            assert papers[node['paper_id']]['abstract'][start:end]==node['raw_phrase']
        if len(spans)!=1:
            assert node['phrase_start_char']==node['phrase_end_char']==''
    frozen_corpus = []
    for filename in ['ite_clean.csv','tg_clean.csv']:
        frozen_corpus.extend(read(base/'stage1_frozen'/'cleaned_ite_tg'/'data'/filename))
    assert len(paper_rows)==len(papers)==len(frozen_corpus)
    for original in frozen_corpus:
        p=papers[original['paper_id']]
        assert p['abstract']==original['摘要'] and p['doi']==original['DOI']
        if original['paper_id'] not in claims:
            assert p['coverage_status']=='missing_abstract' and not original['摘要'].strip()
    return dict(status='PASS', papers=len(papers), nodes=len(nodes), relations=len(edge_rows),
        verified='Output hashes, frozen inputs, every node/edge line, evidence, limitations, offsets and paper identity',
        semantic_review='not_performed',
        node_location_counts=dict(Counter(n['phrase_location_status'] for n in node_rows)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',nargs='?',type=Path,default=Path(__file__).resolve().parents[1]/'v1')
    print(json.dumps(verify(parser.parse_args().directory),ensure_ascii=False,indent=2))
