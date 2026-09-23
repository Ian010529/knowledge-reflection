"""BM25 label retrieval + cached focused-context vectors, isolated RRF trial."""
import csv
import hashlib
import json
import math
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE / 'semantic_candidates_v2'
PRIOR = HERE / 'embedding_input_trial'
OUT = HERE / 'keyword_semantic_trial'
K1, B, TOP, RRF_K = 1.2, .75, 10, 60


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def readcsv(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def writecsv(name, rows):
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def tokenize(text):
    # Keep one-character tokens (n/p), negation and Unicode letters; no stemming.
    return re.findall(r'[^\W_]+', text.casefold())


def main():
    start = time.perf_counter()
    OUT.mkdir(exist_ok=True)
    files = [p for d in [BASE, PRIOR] for p in d.iterdir() if p.is_file()]
    files += [HERE / 'model_decisions.json', HERE / 'normalization_model_proposals.csv']
    hashes = {str(p.relative_to(HERE)): sha(p) for p in files}
    nodes = readcsv(BASE / 'embedding_inputs.csv')
    mids = [r['mention_id'] for r in nodes]
    assert len(mids) == 4487 and mids == sorted(mids)
    index = {m: i for i, m in enumerate(mids)}
    meta = json.loads((PRIOR / 'summary.json').read_text())
    fp = meta['metrics']['focused_clause']['input_fingerprint']
    with np.load(PRIOR / ('vectors_focused_clause_' + fp[:20] + '.npz')) as z:
        assert z['mention_ids'].tolist() == mids
        vec = z['vectors']
    samples = json.loads((PRIOR / 'sample.json').read_text())
    judgments = json.loads((PRIOR / 'review_notes.json').read_text())['judgments']
    query_ids = {index[s[side + '_mention_id']] for s in samples for side in ['left', 'right']}
    names = ['bm25_label', 'focused_vector', 'bm25_plus_vector_rrf']
    neighbors = {name: np.full((len(nodes), TOP), -1, dtype=np.int32) for name in names}
    top_scores = {name: np.full((len(nodes), TOP), np.nan) for name in names}
    max_check_diff, checked_queries = 0., 0
    tokens = [Counter(tokenize(n['label'])) for n in nodes]
    assert all(tokens)
    for domain in ['TG', 'iTE']:
        indices = [i for i, n in enumerate(nodes) if n['domain'] == domain]
        local_tokens = [tokens[i] for i in indices]
        lengths = np.array([sum(t.values()) for t in local_tokens], dtype=float)
        avgdl = float(np.mean(lengths))
        postings = defaultdict(list)
        for j, counts in enumerate(local_tokens):
            for t, tf in counts.items():
                postings[t].append((j, tf))
        lookup = {}
        for t, post in postings.items():
            ids = np.array([j for j, _ in post])
            tf = np.array([f for _, f in post], dtype=float)
            idf = math.log1p((len(indices) - len(post) + .5) / (len(post) + .5))
            lookup[t] = (ids, idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * lengths[ids] / avgdl)))
        matrix = vec[indices]
        for chunk in range(0, len(indices), 128):
            sims = np.clip(matrix[chunk:chunk + 128] @ matrix.T, -1., 1.)
            for offset, dense in enumerate(sims):
                q = chunk + offset
                src = indices[q]
                lexical = np.zeros(len(indices))
                for t in sorted(local_tokens[q]):
                    ids, contribution = lookup[t]
                    lexical[ids] += contribution
                if src in query_ids:
                    # Independently compute scalar BM25 over every same-domain document.
                    reference = []
                    for counts in local_tokens:
                        dl = sum(counts.values())
                        value = 0.
                        for t in sorted(local_tokens[q]):
                            tf = counts.get(t, 0)
                            df = len(postings[t])
                            if tf:
                                value += math.log(1 + (len(indices) - df + .5) / (df + .5)) * tf * (K1 + 1) / (tf + K1 * (1 - B + B * dl / avgdl))
                        reference.append(value)
                    diff = float(np.max(np.abs(lexical - reference)))
                    max_check_diff = max(max_check_diff, diff)
                    assert diff < 1e-10
                    checked_queries += 1
                lexical[q], dense[q] = -np.inf, -np.inf
                lorder = [j for j in np.argsort(-lexical, kind='stable') if lexical[j] > 0][:TOP]
                dorder = np.argsort(-dense, kind='stable')[:TOP].tolist()
                fusion = defaultdict(float)
                for order in [lorder, dorder]:
                    for rank, j in enumerate(order, 1):
                        fusion[j] += 1 / (RRF_K + rank)
                forder = sorted(fusion, key=lambda j: (-fusion[j], mids[indices[j]]))[:TOP]
                for name, order, values in [('bm25_label', lorder, lexical), ('focused_vector', dorder, dense),
                                            ('bm25_plus_vector_rrf', forder, fusion)]:
                    neighbors[name][src, :len(order)] = [indices[j] for j in order]
                    top_scores[name][src, :len(order)] = [values[j] for j in order]
        print('Completed ' + domain, flush=True)
    # Frozen vector branch must reproduce the previous trial's sample rankings.
    for r in readcsv(PRIOR / 'sample_top10.csv'):
        if r['variant'] == 'focused_clause':
            assert neighbors['focused_vector'][index[r['source']], int(r['rank']) - 1] == index[r['target']]
    for name, arr in neighbors.items():
        for i, row in enumerate(arr):
            ids = [j for j in row if j >= 0]
            assert len(ids) == len(set(ids)) and i not in ids
            assert all(nodes[j]['domain'] == nodes[i]['domain'] for j in ids)
            if name != 'bm25_label':
                assert len(ids) == 10
    history = [r for r in readcsv(BASE / 'candidates.csv') if r['historical_comparison_id']]
    sets = {name: [set(row[row >= 0]) for row in arr] for name, arr in neighbors.items()}

    def hit(pair, name):
        a, b = index[pair['left_mention_id']], index[pair['right_mention_id']]
        return b in sets[name][a] or a in sets[name][b]

    pair_rows, metrics, sample_neighbors = [], {}, []
    for name, arr in neighbors.items():
        for s in samples:
            a, b = index[s['left_mention_id']], index[s['right_mention_id']]
            left = np.flatnonzero(arr[a] == b)
            right = np.flatnonzero(arr[b] == a)
            pair_rows.append(dict(method=name, comparison_id=s['historical_comparison_id'], domain=s['domain'],
                selection=s['selection'], review=judgments[s['historical_comparison_id']][0],
                left_label=s['left_label'], right_label=s['right_label'], found=hit(s, name),
                left_to_right_top10_rank=int(left[0] + 1) if len(left) else '',
                right_to_left_top10_rank=int(right[0] + 1) if len(right) else ''))
        equiv = [r for r in history if r['historical_relation_aligned'] == 'equivalent_to']
        metrics[name] = dict(sample={label: {'total': len(sub := [r for r in pair_rows if r['method'] == name and
            r['selection'] == 'stratified' and r['review'] == label]), 'found': sum(r['found'] for r in sub)}
            for label in ['equivalent', 'non_equivalent', 'uncertain']},
            challenge_found=[r['found'] for r in pair_rows if r['method'] == name and r['selection'] == 'known_challenge'],
            historical_equivalent_found=sum(hit(r, name) for r in equiv), historical_equivalent_total=len(equiv),
            unordered_candidate_pairs=len({tuple(sorted((i, int(j)))) for i, row in enumerate(arr) for j in row if j >= 0}),
            queries_with_fewer_than_10=int(np.sum(np.sum(arr >= 0, axis=1) < 10)))
        for src in sorted(query_ids):
            for rank, dst in enumerate(arr[src], 1):
                if dst >= 0:
                    sample_neighbors.append(dict(method=name, source=mids[src], source_label=nodes[src]['label'],
                        target=mids[dst], target_label=nodes[dst]['label'], rank=rank,
                        score=float(top_scores[name][src, rank - 1])))
    writecsv('pair_results.csv', pair_rows)
    writecsv('sample_top10.csv', sample_neighbors)
    writecsv('historical_coverage.csv', [dict(comparison_id=r['historical_comparison_id'],
        historical_relation=r['historical_relation_aligned'], **{name: hit(r, name) for name in names}) for r in history])
    np.savez_compressed(OUT / 'all_top10.npz', mention_ids=np.array(mids), **neighbors)
    assert all(sha(HERE / n) == h for n, h in hashes.items())
    summary = dict(corpus_size=len(nodes), bm25=dict(k1=K1, b=B, field='node label', query='unique label tokens',
        tokenizer='Unicode alphanumeric regex [^\\W_]+, casefold; punctuation split; retain stopwords, n/p and negation; no stemming, synonym expansion or chemical formula parser',
        idf='log(1 + (N - df + 0.5)/(df + 0.5))', domain_local_statistics=True,
        zero_score_documents_excluded=True, note='Python BM25 method trial, not an Elasticsearch deployment or exact analyzer/norm emulation'),
        fusion=dict(method='equal-weight RRF', rank_constant=RRF_K, channel_window=TOP, final_top_k=TOP,
                    ties='ascending mention ID'), vector_input_fingerprint=fp, model=meta['model'], revision=meta['revision'],
        metrics=metrics, elapsed_seconds=time.perf_counter() - start, new_embedding_calls=0, new_llm_calls=0,
        source_hashes=hashes, source_files_unchanged=True, sample_is_human_gold=False, sample_is_independent_test=False,
        validation=dict(bm25_queries_independently_scored=checked_queries, max_abs_score_error=max_check_diff,
                        vector_sample_rankings_match_prior=True, no_cross_domain_or_self_or_duplicate_neighbors=True),
        script_sha256=sha(Path(__file__)))
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k in ['metrics', 'elapsed_seconds', 'validation']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
