"""Local embeddings and same-domain Top-10 candidates; never calls a generative LLM.

Initial concepts remain one-to-one with mentions. Retrieval groups organize
review only; a concrete-pair judgment is never propagated to other members.
"""
import csv
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "semantic_candidates_v2"
MODEL = "nomic-ai/nomic-embed-text-v1.5"
REVISION = "e9b6763023c676ca8431644204f50c2b100d9aab"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(name, rows, fields=None):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def key(a, b):
    return tuple(sorted((a, b)))


def pair_id(prefix, pair):
    return prefix + hashlib.sha256("|".join(pair).encode()).hexdigest()[:20]


def short_context(label, quote):
    words = list(re.finditer(r"\S+", quote))
    assert words
    match = re.search(re.escape(label), quote, re.IGNORECASE)
    start = 0
    if match:
        first = next(i for i, word in enumerate(words) if word.end() > match.start())
        last = max(i for i, word in enumerate(words) if word.start() < match.end())
        start = max(0, min(first - 20, len(words) - 80))
        if last >= start + 80:
            start = max(0, last - 79)
    end = min(len(words), start + 80)
    a, b = words[start].start(), words[end - 1].end()
    return quote[a:b], a, b, "phrase_anchored" if match else "first_80_words_phrase_not_found"


def main():
    started = time.perf_counter()
    OUT.mkdir(exist_ok=True)
    sources = ["stage2_reconstruction/v1/initial_concepts.csv",
               "stage2_reconstruction/v1/initial_normalization_assignments.csv",
               "stage2_reconstruction/v1/node_evidence.csv",
               "stage2_reconstruction/v1/relation_evidence.csv",
               "stage2_review/role_run_v2/role_model_proposals.csv",
               "stage2_review/role_run_v2/pending_review.csv",
               "stage2_review/v1/retrieval_unit_members.csv",
               "stage2_review/v1/normalization_candidates.csv",
               "stage2_normalization/batch_plan.json", "stage2_normalization/model_decisions.json",
               "stage2_normalization/normalization_model_proposals.csv",
               "stage2_normalization/occurrence_runs/status.json"]
    hashes = {name: digest(ROOT / name) for name in sources}
    plan = json.loads((HERE / "batch_plan.json").read_text())
    for name, expected in plan["source_hashes"].items():
        assert digest(ROOT / name) == expected, f"Changed source: {name}"
    decisions = json.loads((HERE / "model_decisions.json").read_text())["decisions"]
    roles = {r["mention_id"]: r for r in read_csv(sources[4])}
    pending_rows = read_csv(sources[5])
    pending = {r["mention_id"] for r in pending_rows}
    concepts = {r["source_mention_id"]: r for r in read_csv(sources[0])}
    assignments = {r["mention_id"]: r["initial_concept_id"] for r in read_csv(sources[1])}
    nodes = {r["mention_id"]: r for r in read_csv(sources[2])}
    assert len(concepts) == len(assignments) == len(nodes) == len(roles) == 4646
    mids = sorted(mid for mid, r in roles.items() if mid not in pending and r["proposed_semantic_role"])
    assert len(mids) + len(pending) == len(roles)
    eligible = set(mids)
    members = defaultdict(list)
    unit = {}
    for row in read_csv(sources[6]):
        mid = row["mention_id"]
        unit[mid] = row["retrieval_unit_id"]
        if mid in eligible:
            members[unit[mid]].append(mid)
    inputs = []
    for mid in mids:
        r, c = roles[mid], concepts[mid]
        assert c["initial_concept_id"] == assignments[mid]
        assert c["label"] == r["raw_phrase"] == nodes[mid]["raw_phrase"]
        assert r["domain"] == c["domain"] == nodes[mid]["domain"]
        context, start, end, method = short_context(c["label"], r["quote"])
        inputs.append(dict(mention_id=mid, initial_concept_id=c["initial_concept_id"],
            domain=r["domain"], paper_id=r["paper_id"], label=c["label"],
            current_role=r["proposed_semantic_role"], retrieval_unit_id=unit[mid],
            concept_status="unmerged_initialization", quote=r["quote"],
            context=context, context_start=start, context_end=end, context_method=method,
            embedding_text="clustering: " + c["label"] + ". Context: " + " ".join(context.split())))
    write_csv("embedding_inputs.csv", inputs)
    write_csv("role_deferred.csv", pending_rows)
    spec = dict(model=MODEL, revision=REVISION, max_seq_length=512,
                normalize_embeddings=True, inputs=[(r["mention_id"], r["embedding_text"]) for r in inputs])
    fingerprint = hashlib.sha256(json.dumps(spec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    cache = OUT / ("vectors_" + fingerprint[:20] + ".npz")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    torch.set_num_threads(2)
    if device == "mps":
        torch.mps.set_per_process_memory_fraction(.35)
    encode_started = time.perf_counter()
    cache_reused = cache.exists()
    if cache_reused:
        with np.load(cache, allow_pickle=False) as saved:
            assert saved["mention_ids"].tolist() == mids
            vectors = saved["vectors"]
        print(f"Reused {len(mids)} cached vectors", flush=True)
    else:
        print(f"Encoding {len(mids)} initial concepts locally on {device}, batch_size=4", flush=True)
        model = SentenceTransformer(MODEL, revision=REVISION, device=device,
                                    trust_remote_code=False, local_files_only=True)
        model.max_seq_length = 512
        texts = [r["embedding_text"] for r in inputs]
        lengths = [len(model.tokenizer.encode(text)) for text in texts]
        assert max(lengths) <= 512, "Inspect overlong inputs instead of silently truncating evidence"
        vectors = model.encode(texts, batch_size=4, normalize_embeddings=True,
                               convert_to_numpy=True, show_progress_bar=True)
        np.savez_compressed(cache, mention_ids=np.array(mids), vectors=vectors)
    encoding_seconds = time.perf_counter() - encode_started
    assert vectors.shape == (len(mids), 768) and np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4)
    index = {mid: i for i, mid in enumerate(mids)}
    history = {key(p["left_mention_id"], p["right_mention_id"]): p for p in plan["comparisons"]}
    assert len(history) == len(decisions) == len(plan["comparisons"])
    candidate_pairs = {}
    groups = {}

    def group(g):
        return groups.setdefault(g, {"channels": set(), "legacy_ids": set(), "pairs": set()})

    def add(a, b, channels, legacy_id=""):
        assert a != b and a in eligible and b in eligible and roles[a]["domain"] == roles[b]["domain"]
        p = key(a, b)
        entry = candidate_pairs.setdefault(p, {"channels": set(), "legacy_ids": set(), "ranks": {}})
        entry["channels"].update(channels)
        g = group(key(unit[a], unit[b]))
        g["channels"].update(channels)
        g["pairs"].add(p)
        if legacy_id:
            entry["legacy_ids"].add(legacy_id)
            g["legacy_ids"].add(legacy_id)
        return entry

    neighbors, historical_ranks = [], {}
    history_targets = defaultdict(set)
    for a, b in history:
        history_targets[a].add(b)
        history_targets[b].add(a)
    for domain in sorted({roles[mid]["domain"] for mid in mids}):
        ids = [mid for mid in mids if roles[mid]["domain"] == domain]
        matrix = vectors[[index[mid] for mid in ids]]
        local = {mid: i for i, mid in enumerate(ids)}
        for start in range(0, len(ids), 128):
            scores = np.clip(matrix[start:start + 128] @ matrix.T, -1.0, 1.0)
            for offset, row in enumerate(scores):
                a = ids[start + offset]
                row[start + offset] = -np.inf
                order = np.argsort(-row, kind="stable")
                ranks = np.empty(len(ids), dtype=int)
                ranks[order] = np.arange(1, len(ids) + 1)
                for b in history_targets[a]:
                    historical_ranks[(a, b)] = int(ranks[local[b]])
                for rank, j in enumerate(order[:10], 1):
                    b = ids[j]
                    neighbors.append(dict(domain=domain, source_concept_id=assignments[a],
                        target_concept_id=assignments[b], source_mention_id=a, target_mention_id=b,
                        rank=rank, cosine_similarity=float(row[j])))
                    add(a, b, {"semantic_top10"})["ranks"][a] = rank
    write_csv("semantic_neighbors.csv", neighbors)
    deferred_groups = []
    legacy_rows = read_csv(sources[7])
    for row in legacy_rows:
        left, right = members[row["left_unit_id"]], members[row["right_unit_id"]]
        if not left or not right:
            deferred_groups.append({**row, "defer_reason": "no_role_eligible_member_on_at_least_one_side"})
            continue
        # Preserve existing representative-pair policy, not a Cartesian expansion.
        add(left[0], right[0], set(row["candidate_channels"].split(";")), row["candidate_id"])
    write_csv("legacy_candidates_deferred.csv", deferred_groups, list(legacy_rows[0]) + ["defer_reason"])
    for uid, same_label in list(members.items()):
        for mid in same_label[1:]:
            add(same_label[0], mid, {"exact_label_context_review"})
    for (a, b), p in history.items():
        add(a, b, {"historical_comparison"}, p.get("source_candidate_id", ""))
    flagged = set()
    old_status = json.loads((HERE / "occurrence_runs/status.json").read_text())
    if old_status.get("status") == "needs_semantic_review":
        audit_path = Path(old_status["artifact"])
        hashes[str(audit_path.relative_to(ROOT))] = digest(audit_path)
        old_audit = json.loads(audit_path.read_text())
        flagged.update(old_status["conflict_ids"])
        flagged.update(p["comparison_id"] for p in old_audit["comparisons"])
    rows = []
    reverse = {"broader_than": "narrower_than", "narrower_than": "broader_than"}
    for (a, b), info in sorted(candidate_pairs.items()):
        p = history.get((a, b))
        cid = p["comparison_id"] if p else ""
        prior = decisions.get(cid, {})
        relation = prior.get("proposed_relation", "")
        reversed_history = bool(p and p["left_mention_id"] != a)
        aligned_relation = reverse.get(relation, relation) if reversed_history else relation
        status = ("needs_review_flagged_history" if cid in flagged else
                  "needs_review_existing_uncertain" if relation == "uncertain" else
                  "reuse_model_proposal_pending_human" if p else "needs_review_new_candidate")
        rows.append(dict(candidate_id=pair_id("candidate:", (a, b)), domain=roles[a]["domain"],
            left_concept_id=assignments[a], right_concept_id=assignments[b],
            left_mention_id=a, right_mention_id=b, left_label=roles[a]["raw_phrase"], right_label=roles[b]["raw_phrase"],
            left_role=roles[a]["proposed_semantic_role"], right_role=roles[b]["proposed_semantic_role"],
            group_id=pair_id("group:", key(unit[a], unit[b])),
            candidate_channels=";".join(sorted(info["channels"])),
            cosine_similarity=float(np.clip(vectors[index[a]] @ vectors[index[b]], -1.0, 1.0)),
            left_to_right_rank=info["ranks"].get(a, ""), right_to_left_rank=info["ranks"].get(b, ""),
            legacy_candidate_ids=";".join(sorted(info["legacy_ids"])), historical_comparison_id=cid,
            historical_original_left=p["left_mention_id"] if p else "",
            historical_original_right=p["right_mention_id"] if p else "",
            historical_original_relation=relation, historical_relation_aligned=aligned_relation,
            historical_original_reason=prior.get("model_reason", ""),
            historical_evidence_scope=prior.get("evidence_scope", ""), review_status=status,
            human_decision="", human_reason="", merge_applied=False))
    write_csv("candidates.csv", rows)
    review_rows = [r for r in rows if r["review_status"].startswith("needs_review")]
    write_csv("review_queue.csv", review_rows, list(rows[0]))
    group_rows = []
    for (left, right), info in sorted(groups.items()):
        ln, rn = len(members[left]), len(members[right])
        possible = ln * rn if left != right else ln * (ln - 1) // 2
        group_rows.append(dict(group_id=pair_id("group:", (left, right)),
            left_unit_id=left, right_unit_id=right, left_eligible_members=ln, right_eligible_members=rn,
            candidate_channels=";".join(sorted(info["channels"])),
            legacy_candidate_ids=";".join(sorted(info["legacy_ids"])),
            explicit_candidate_pairs=len(info["pairs"]), possible_member_pairs=possible,
            all_member_pairs_listed=len(info["pairs"]) == possible,
            group_status="retrieval_group_only_no_judgment_propagation"))
    write_csv("candidate_groups.csv", group_rows)
    assert len(neighbors) == len(mids) * 10
    assert len({r["candidate_id"] for r in rows}) == len(rows)
    assert sum(bool(r["historical_comparison_id"]) for r in rows) == len(history)
    assert all(r["human_decision"] == r["human_reason"] == "" and not r["merge_applied"] for r in rows)
    assert all(digest(ROOT / name) == expected for name, expected in hashes.items())
    equivalent_pairs = [pair for pair, p in history.items() if decisions[p["comparison_id"]]["proposed_relation"] == "equivalent_to"]
    coverage = {str(k): sum(min(historical_ranks[(a, b)], historical_ranks[(b, a)]) <= k
                            for a, b in equivalent_pairs) for k in (10, 20, 50)}
    high_scores = [r for r in rows if r["cosine_similarity"] > .95]
    summary = dict(status="validated_candidate_generation_only", generated_at=datetime.now(timezone.utc).isoformat(),
        model=MODEL, revision=REVISION, input_fingerprint=fingerprint, vector_cache=cache.name,
        script_sha256=digest(Path(__file__)), source_hashes=hashes,
        versions={p: version(p) for p in ("torch", "transformers", "sentence-transformers", "numpy")},
        device=device, batch_size=4, threads=2, max_seq_length=512, mps_memory_fraction=.35,
        input_concept_status="one_mention_one_unmerged_initial_concept_no_final_canonical_merges",
        context_policy="80 contiguous source words anchored near first phrase match; leading words only if phrase absent",
        context_methods=dict(Counter(r["context_method"] for r in inputs)),
        eligible_mentions=len(mids), role_deferred=len(pending), by_domain=dict(Counter(roles[mid]["domain"] for mid in mids)),
        embedding_stage_seconds=encoding_seconds, cache_reused=cache_reused, total_seconds=time.perf_counter() - started,
        directed_top10_neighbors=len(neighbors), semantic_unordered_pairs=sum("semantic_top10" in r["candidate_channels"].split(";") for r in rows),
        legacy_unit_candidates=len(legacy_rows), legacy_unit_candidates_deferred=len(deferred_groups),
        merged_candidate_pairs=len(rows), candidate_groups=len(group_rows),
        candidate_pairs_by_domain=dict(Counter(r["domain"] for r in rows)),
        review_status_counts=dict(Counter(r["review_status"] for r in rows)),
        historical_pairs_retained=len(history), current_unpublished_reassessment_ids=sorted(flagged),
        historical_equivalent_pair_count=len(equivalent_pairs), historical_equivalent_retrieval_coverage=coverage,
        above_095_count=len(high_scores),
        above_095_same_paper_count=sum(roles[r["left_mention_id"]]["paper_id"] == roles[r["right_mention_id"]]["paper_id"] for r in high_scores),
        above_095_historical_relations=dict(Counter(r["historical_original_relation"] for r in high_scores if r["historical_original_relation"])),
        coverage_note="Diagnostic against historical model proposals, not human-gold recall or normalization accuracy.",
        limitations=["Top-10 is the planned starting point, not validated as sufficient coverage.",
            "No similarity threshold assigns a relation or triggers merging.",
            "Shared paper context can yield high similarity for different or opposite concepts; 0.95 is not validated for automatic equivalence.",
            "Legacy structural candidates use legacy-role signatures, not refreshed semantic-role signatures.",
            "Legacy group representatives do not cover every member combination; group coverage is explicit.",
            "Historical judgments remain model proposals, with original orientation and reasons retained.",
            "No new model review, human acceptance, graph construction, or actual merge has been performed."],
        validation=dict(source_files_unchanged=True, normalized_finite_vectors=True, no_cross_domain_pairs=True,
            no_self_pairs=True, unique_pairs=True, exactly_ten_neighbors_per_eligible_concept=True,
            all_historical_pairs_preserved=True, human_fields_blank=True, merges_applied=0))
    write_json("summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("source_hashes", "current_unpublished_reassessment_ids")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
