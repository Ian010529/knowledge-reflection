"""Check asymmetric dedup, complete TG retention, and source-cell preservation."""
from pathlib import Path
import csv
import hashlib
import json
import re
import unicodedata

ROOT = Path(__file__).resolve().parent


def read(name):
    with (ROOT / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def norm(value, field):
    if field == 'DOI':
        return re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', value.strip().casefold()).strip(' .;,')
    return ''.join(c for c in unicodedata.normalize('NFKC', value).casefold() if c.isalnum())


def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    require(manifest['version'] == 'asymmetric_dedup_v2', 'Wrong cleaning policy')
    for name, expected in manifest['output_sha256'].items():
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, f'Output modified: {name}')
    if (ROOT.parent / 'source_tables').exists():
        for name, expected in manifest['input_sha256'].items():
            p = ROOT.parent / name
            require(p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == expected,
                    f'Upstream input changed: {name}')
    ite, tg = read('data/ite_clean.csv'), read('data/tg_clean.csv')
    records = read('audit/all_original_records.csv')
    original = {r['source_record_id']: r for r in records}
    require(len(original) == len(records), 'Repeated source-record IDs')
    ip, tp = {p['paper_id'] for p in ite}, {p['paper_id'] for p in tg}
    raw_i = {r['paper_id'] for r in records if r['source_family'] == 'iTE'}
    raw_t = {r['paper_id'] for r in records if r['source_family'] == 'TG'}
    require(tp == raw_t, 'TG papers lost or added')
    require(ip == raw_i - raw_t, 'iTE removal exceeds cross-source duplicates')
    require(not ip & tp, 'Shared paper remains in iTE')
    require(ip | tp == raw_i | raw_t, 'A unique paper was discarded')
    require(len(ip) == len(ite) and len(tp) == len(tg), 'Duplicate output paper IDs')
    for field in ['DOI', '文章名']:
        a = [norm(p[field], field) for p in ite if norm(p[field], field)]
        b = [norm(p[field], field) for p in tg if norm(p[field], field)]
        require(not set(a) & set(b), f'Cross-corpus duplicate {field}')
        require(len(a) == len(set(a)) and len(b) == len(set(b)), f'Within-corpus duplicate {field}')
    for family, rows in [('iTE', ite), ('TG', tg)]:
        require(len(rows) == manifest['counts'][family], 'Count mismatch')
        for p in rows:
            r = original[p['representative_record_id']]
            require(r['source_family'] == family, 'Representative from wrong source')
            for c in ['文章名', '期刊名', 'DOI', '年份', '摘要', '材料', '机制']:
                require(p[c] == r[c], f'Original cell modified: {p["paper_id"]}/{c}')
    removed = read('audit/removed_from_ite_kept_in_tg.csv')
    require({r['paper_id'] for r in removed} == raw_i & raw_t, 'Removal audit incorrect')
    require(all(r['source_family'] == 'iTE' for r in removed), 'Wrong removal side')
    print(json.dumps({'status': 'PASS', 'iTE': len(ite), 'TG': len(tg),
                      'removed_from_TG': 0, 'unique_papers_lost': 0,
                      'all_original_cells_preserved': True, 'cross_corpus_overlap': 0}))


if __name__ == '__main__':
    main()
