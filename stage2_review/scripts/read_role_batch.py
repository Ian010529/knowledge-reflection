#!/usr/bin/env python3
"""Print source passages for the current model to read; no role inference."""
import argparse
import csv
import json
import re
from pathlib import Path

base = Path(__file__).resolve().parents[1]
source = base.parent / 'stage2_reconstruction/v1'
ap = argparse.ArgumentParser()
ap.add_argument('batch', type=int)
ap.add_argument('--start', type=int, default=0)
ap.add_argument('--count', type=int, default=40)
args = ap.parse_args()
plan = json.loads((base / 'bulk_roles_v2/batch_plan.json').read_text())
selected = plan['batches'][args.batch - 1]['papers'][args.start:args.start + args.count]
with (source / 'node_evidence.csv').open(encoding='utf-8-sig') as f:
    nodes = list(csv.DictReader(f))
for pid in selected:
    ns = [n for n in nodes if n['paper_id'] == pid]
    quote = ns[0]['quote']
    # Select complete node-containing sentences, not a generated summary.
    # Dotted chemical names/abbreviations can split unusually; expand 100 chars
    # around the phrase if any phrase crosses the split.
    bounds = [0] + [m.end() for m in re.finditer(r'(?<=[.!?])\s+(?=[A-Z])', quote)] + [len(quote)]
    spans = set()
    for n in ns:
        phrase = n['raw_phrase']
        starts = [m.start() for m in re.finditer(re.escape(phrase), quote)]
        assert starts, n['mention_id']
        for start in starts:
            end = start + len(phrase)
            left = max(b for b in bounds if b <= start)
            right = min(b for b in bounds if b >= end)
            spans.add((left, right))
    merged = []
    for lo, hi in sorted(spans):
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(hi, merged[-1][1])
        else:
            merged.append([lo, hi])
    passages = ' […] '.join(quote[lo:hi].strip() for lo, hi in merged)
    print(f'\n{pid} ({ns[0]["domain"]})')
    print(' | '.join(n['local_node_id'] + '=' + n['raw_phrase'] for n in ns))
    print(passages)
