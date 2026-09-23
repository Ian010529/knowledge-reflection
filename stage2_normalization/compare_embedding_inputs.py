"""Isolated input ablation: frozen Nomic/Top-10, full eligible retrieval corpus.

No API calls, model judgment propagation, source rewrites, or node merges.
"""
import csv
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

HERE = Path(__file__).resolve().parent
BASE = HERE / 'semantic_candidates_v2'
OUT = HERE / 'embedding_input_trial'
MODEL = 'nomic-ai/nomic-embed-text-v1.5'
REVISION = 'e9b6763023c676ca8431644204f50c2b100d9aab'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def csvout(name, rows):
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def focused_context(row):
    """Literal source sentence/semicolon clause containing first label occurrence.

    No semantic rewriting or comma/conjunction splitting. Abbreviations such as
    e.g. are protected; decimals are not split. Long spans retain the existing
    <=80-word source window, with the fallback recorded.
    """
    quote = row['quote']
    match = re.search(re.escape(row['label']), quote, re.I)
    assert match
    bounds = [0]
    for delim in re.finditer(r';\s+|[.!?]\s+(?=[A-Z])|\n+', quote):
        prefix = quote[max(0, delim.start() - 8):delim.start() + 1].lower()
        if re.search(r'(?:e\.g\.|i\.e\.|et al\.|fig\.|dr\.)$', prefix):
            continue
        if match.start() < delim.end() and delim.start() < match.end():
            continue
        bounds.append(delim.end())
    bounds.append(len(quote))
    start = max(b for b in bounds if b <= match.start())
    end = min(b for b in bounds if b >= match.end())
    while start < end and quote[start].isspace():
        start += 1
    while end > start and quote[end - 1].isspace():
        end -= 1
    context = quote[start:end]
    method = 'source_sentence_or_semicolon_clause'
    if len(context.split()) > 80:
        context, start, end = row['context'], int(row['context_start']), int(row['context_end'])
        method = 'long_clause_existing_80_word_window'
    assert context == quote[start:end]
    assert re.search(re.escape(row['label']), context, re.I)
    return context, start, end, method


def main():
    started = time.perf_counter()
    protected = list(BASE.iterdir()) + [HERE / 'model_decisions.json', HERE / 'normalization_model_proposals.csv']
    hashes = {str(p.relative_to(HERE)): sha(p) for p in protected if p.is_file()}
    nodes = list(csv.DictReader((BASE / 'embedding_inputs.csv').open(encoding='utf-8-sig')))
    sample = json.loads((OUT / 'sample.json').read_text())
    review = json.loads((OUT / 'review_notes.json').read_text())
    assert set(review['judgments']) == {s['historical_comparison_id'] for s in sample}
    mids = [n['mention_id'] for n in nodes]
    assert mids == sorted(mids) and len(mids) == 4487
    index = {mid: i for i, mid in enumerate(mids)}
    focused = []
    for n in nodes:
        context, a, b, method = focused_context(n)
        focused.append(dict(mention_id=n['mention_id'], label=n['label'], context=context,
                            context_start=a, context_end=b, method=method,
                            embedding_text='clustering: ' + n['label'] + '. Context: ' + ' '.join(context.split())))
    csvout('focused_inputs.csv', focused)
    texts = {
        'baseline_80': [n['embedding_text'] for n in nodes],
        'focused_clause': [n['embedding_text'] for n in focused],
        'label_only': ['clustering: ' + n['label'] for n in nodes],
    }
    baseline_spec = dict(model=MODEL, revision=REVISION, max_seq_length=512,
                         normalize_embeddings=True, inputs=list(zip(mids, texts['baseline_80'])))
    fp = hashlib.sha256(json.dumps(baseline_spec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    with np.load(BASE / ('vectors_' + fp[:20] + '.npz'), allow_pickle=False) as z:
        assert z['mention_ids'].tolist() == mids
        baseline_vectors = z['vectors']
    torch.set_num_threads(2)
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    if device == 'mps':
        torch.mps.set_per_process_memory_fraction(.35)
    model = None
    results, near_rows, metrics = [], [], {}
    history = [r for r in csv.DictReader((BASE / 'candidates.csv').open(encoding='utf-8-sig'))
               if r['historical_comparison_id']]
    queries = {s[side + '_mention_id'] for s in sample for side in ['left', 'right']}
    targets = {}
    for pair in history + sample:
        a, b = pair['left_mention_id'], pair['right_mention_id']
        targets.setdefault(a, set()).add(b)
        targets.setdefault(b, set()).add(a)
    for variant, inputs in texts.items():
        tick = time.perf_counter()
        spec = dict(model=MODEL, revision=REVISION, max_seq_length=512,
                    normalize_embeddings=True, inputs=list(zip(mids, inputs)))
        fingerprint = hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        cache = OUT / ('vectors_' + variant + '_' + fingerprint[:20] + '.npz')
        reused = variant == 'baseline_80' or cache.exists()
        if variant == 'baseline_80':
            vectors = baseline_vectors
        elif cache.exists():
            with np.load(cache, allow_pickle=False) as z:
                assert z['mention_ids'].tolist() == mids
                vectors = z['vectors']
        else:
            if model is None:
                model = SentenceTransformer(MODEL, revision=REVISION, device=device,
                                            trust_remote_code=False, local_files_only=True)
                model.max_seq_length = 512
            assert max(len(model.tokenizer.encode(t)) for t in inputs) <= 512
            print('Encoding ' + variant + ': ' + str(len(inputs)), flush=True)
            vectors = model.encode(inputs, batch_size=4, normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=False)
            np.savez_compressed(cache, vectors=vectors, mention_ids=np.array(mids))
        assert vectors.shape == (4487, 768) and np.isfinite(vectors).all()
        assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4)
        encoding_seconds = time.perf_counter() - tick
        ranks = {}
        for domain in ['TG', 'iTE']:
            indices = [i for i, n in enumerate(nodes) if n['domain'] == domain]
            local_index = {mids[i]: j for j, i in enumerate(indices)}
            matrix = vectors[indices]
            for start in range(0, len(indices), 128):
                similarities = np.clip(matrix[start:start + 128] @ matrix.T, -1, 1)
                for offset, scores in enumerate(similarities):
                    src = indices[start + offset]
                    scores[start + offset] = -np.inf
                    order = np.argsort(-scores, kind='stable')
                    rr = np.empty(len(indices), dtype=np.int32)
                    rr[order] = np.arange(1, len(indices) + 1)
                    ranks[mids[src]] = {mid: int(rr[local_index[mid]]) for mid in targets.get(mids[src], ())}
                    if mids[src] in queries:
                        for rank, j in enumerate(order[:10], 1):
                            target = nodes[indices[j]]
                            near_rows.append(dict(variant=variant, source=mids[src], source_label=nodes[src]['label'],
                                target=target['mention_id'], target_label=target['label'], rank=rank,
                                cosine=float(scores[j]), same_paper=nodes[src]['paper_id'] == target['paper_id']))
        for s in sample:
            a, b = s['left_mention_id'], s['right_mention_id']
            cid = s['historical_comparison_id']
            results.append(dict(comparison_id=cid, selection=s['selection'], domain=s['domain'], variant=variant,
                left_label=s['left_label'], right_label=s['right_label'],
                source_review=review['judgments'][cid][0], historical_relation=s['historical_relation_aligned'],
                left_to_right_rank=ranks[a][b], right_to_left_rank=ranks[b][a],
                either_direction_top10=min(ranks[a][b], ranks[b][a]) <= 10,
                cosine=float(np.clip(vectors[index[a]] @ vectors[index[b]], -1, 1))))
        equiv = [r for r in history if r['historical_relation_aligned'] == 'equivalent_to']
        metrics[variant] = dict(encoding_seconds=encoding_seconds, cache_reused=reused, input_fingerprint=fingerprint,
            historical_equivalent_exact_pair_top10=sum(min(ranks[r['left_mention_id']][r['right_mention_id']],
                ranks[r['right_mention_id']][r['left_mention_id']]) <= 10 for r in equiv),
            historical_equivalent_total=len(equiv),
            sample_counts={label: {'total': len(sub := [r for r in results if r['variant'] == variant and
                r['selection'] == 'stratified' and r['source_review'] == label]),
                'top10': sum(r['either_direction_top10'] for r in sub)}
                for label in ['equivalent', 'non_equivalent', 'uncertain']})
        print(variant + ': ' + json.dumps(metrics[variant], ensure_ascii=False), flush=True)
        del ranks
    csvout('pair_results.csv', results)
    csvout('sample_top10.csv', near_rows)
    assert all(sha(HERE / name) == value for name, value in hashes.items())
    dump('summary.json', dict(model=MODEL, revision=REVISION, device=device, top_k=10, corpus_size=len(nodes),
        sample_size=len(sample), reviewer_type=review['reviewer_type'],
        sample_design='seed context-trial-v1: SHA256-sorted within domain x historical relation; 6 distinct, 6 related, 3 same-label equivalent, 3 different-label equivalent per domain; plus N0838 known challenge',
        focused_methods=dict(Counter(r['method'] for r in focused)),
        baseline_mean_context_words=float(np.mean([len(n['context'].split()) for n in nodes])),
        focused_mean_context_words=float(np.mean([len(n['context'].split()) for n in focused])),
        metrics=metrics, total_seconds=time.perf_counter() - started,
        protected_source_hashes=hashes, sources_unchanged=True,
        sample_sha256=sha(OUT / 'sample.json'), review_sha256=sha(OUT / 'review_notes.json'),
        script_sha256=sha(Path(__file__)), merge_applied=False, human_gold=False))


if __name__ == '__main__':
    main()
