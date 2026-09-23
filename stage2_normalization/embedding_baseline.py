"""Score the existing occurrence-pair queue with cached local embeddings.

This creates a separate similarity baseline, not six-class decisions or merges.
Run: .venv-embedding/bin/python stage2_normalization/embedding_baseline.py
"""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import HfApi
from sentence_transformers import SentenceTransformer

import occurrence_batch as queue

OUT = Path(__file__).resolve().parent / "embedding_baseline"
MODEL = "nomic-ai/nomic-embed-text-v1.5"


def save_json(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    OUT.mkdir(exist_ok=True)
    plan, record = queue.load_state()
    remaining, _, _, remaining_count = queue.select(plan, 100000)
    assert len(remaining) == remaining_count
    comparisons = plan["comparisons"] + remaining
    roles = {r["mention_id"]: r for r in queue.read_csv("stage2_review/role_run_v2/role_model_proposals.csv")}
    mids = sorted({p[s + "_mention_id"] for p in comparisons for s in ("left", "right")})
    # Fixed extractive context: no LLM summary or rewriting of source evidence.
    texts = ["clustering: " + roles[mid]["raw_phrase"] + ". Context: " +
             " ".join(roles[mid]["quote"].split()[:80]) for mid in mids]
    revision = HfApi().model_info(MODEL).sha
    spec = {"model": MODEL, "revision": revision, "prefix": "clustering: ",
            "context": "first 80 whitespace-delimited words of original quote",
            "max_sequence_length": 512, "normalize_embeddings": True,
            "mentions": [{"mention_id": mid, "text": text} for mid, text in zip(mids, texts)]}
    fingerprint = hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    cache = OUT / (fingerprint + ".npz")
    if cache.exists():
        with np.load(cache, allow_pickle=False) as saved:
            assert saved["mention_ids"].tolist() == mids
            vectors = saved["vectors"]
        print(f"Reused {len(mids)} cached vectors", flush=True)
    else:
        torch.set_num_threads(2)
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        if device == "mps":
            torch.mps.set_per_process_memory_fraction(0.35)
        print(f"Encoding {len(mids)} mentions with {MODEL}@{revision} on {device}", flush=True)
        model = SentenceTransformer(MODEL, revision=revision, device=device, trust_remote_code=False)
        model.max_seq_length = 512
        vectors = model.encode(texts, batch_size=4, normalize_embeddings=True,
                               convert_to_numpy=True, show_progress_bar=True)
        np.savez_compressed(cache, mention_ids=np.array(mids), vectors=vectors)
    assert vectors.shape[0] == len(mids) and np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4)
    save_json("embedding_inputs.json", {"fingerprint": fingerprint, **spec})
    index = {mid: i for i, mid in enumerate(mids)}
    results = []
    for p in comparisons:
        left, right = p["left_mention_id"], p["right_mention_id"]
        assert roles[left]["domain"] == roles[right]["domain"] == p["domain"]
        score = float(np.dot(vectors[index[left]], vectors[index[right]]))
        results.append({"comparison_id": p["comparison_id"], "domain": p["domain"],
            "source_candidate_id": p.get("source_candidate_id", ""),
            "left_mention_id": left, "right_mention_id": right,
            "left_phrase": roles[left]["raw_phrase"], "right_phrase": roles[right]["raw_phrase"],
            "cosine_similarity": score, "above_0_95": score > .95,
            "same_current_role": roles[left]["proposed_semantic_role"] == roles[right]["proposed_semantic_role"],
            "existing_model_relation": record["decisions"].get(p["comparison_id"], {}).get("proposed_relation", ""),
            "scope": "previously_judged" if p["comparison_id"] in record["decisions"] else "remaining_candidate"})
    with (OUT / "similarity_scores.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    high = [r for r in results if r["above_0_95"]]
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL, "model_revision": revision, "input_fingerprint": fingerprint,
        "script_sha256": queue.digest(Path(__file__)),
        "source_hashes": plan["source_hashes"],
        "decision_table_sha256": queue.digest(queue.HERE / "model_decisions.json"),
        "versions": {p: version(p) for p in ("torch", "transformers", "sentence-transformers", "numpy")},
        "mention_count": len(mids), "pair_count": len(results),
        "batch_size": 4, "torch_threads": 2,
        "remaining_candidate_count": remaining_count,
        "above_0_95_count": len(high),
        "above_0_95_by_scope": dict(Counter(r["scope"] for r in high)),
        "above_0_95_prior_model_relations": dict(Counter(r["existing_model_relation"] for r in high if r["existing_model_relation"])),
        "above_0_95_role_mismatches": sum(not r["same_current_role"] for r in high),
        "limitations": ["Existing model judgments are not human gold labels; disagreement is not an accuracy estimate.",
            "0.95 is an imported trial threshold, not calibrated on this corpus.",
            "Label plus extractive context follows the local plan; this is not an exact reproduction of GraphAgents node inputs.",
            "Only existing eligible occurrence pairs are scored; no new Top-10 candidates or Cartesian expansion.",
            "Scores do not assign six-class relations, publish decisions, or merge any nodes."]}
    save_json("summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
