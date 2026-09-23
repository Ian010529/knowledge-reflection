"""Apply an explicitly reviewed revision file without altering the preserved original result."""
import json
from pathlib import Path

from run_batch import (REQUIRED_MODEL, REQUIRED_REASONING, atomic_write_json,
                       input_fingerprint, load, validate_cache)

HERE = Path(__file__).resolve().parent


def apply(batch_id):
    manifest, candidates, evidence = load("manifest.json"), load("candidates.json"), load("evidence.json")
    batch = next(item for item in manifest["batches"] if item["batch_id"] == batch_id)
    ids = batch["candidate_ids"]
    original_path = HERE / "results" / f"{batch_id}.json"
    original = json.loads(original_path.read_text())
    revision_path = HERE / "revisions" / f"{batch_id}.json"
    revision = json.loads(revision_path.read_text())
    assert revision["review_model"] == REQUIRED_MODEL and revision["reasoning_effort"] == REQUIRED_REASONING
    changes = {row["candidate_id"]: row for row in revision["revisions"]}
    assert set(changes) <= set(ids)
    decisions = []
    for row in original["decisions"]:
        row = dict(row)
        change = changes.get(row["candidate_id"])
        if change:
            assert row["proposed_relation"] == change["old_relation"]
            row["proposed_relation"] = change["new_relation"]
            row["model_reason"] = change["reason"]
        decisions.append(row)
    fingerprint, parts = input_fingerprint(ids, candidates, evidence, REQUIRED_MODEL, REQUIRED_REASONING)
    result = {"decisions": decisions, "provenance": {
        "batch_id": batch_id, "model": REQUIRED_MODEL, "reasoning_effort": REQUIRED_REASONING,
        "review_mode": "direct_full_batch_semantic_recheck", "reviewed_candidate_ids": ids,
        "preserved_original": str(original_path.relative_to(HERE)),
        "revision_source": str(revision_path.relative_to(HERE)),
        **parts, "input_fingerprint_sha256": fingerprint}}
    validate_cache(result, ids, candidates, evidence, REQUIRED_MODEL, REQUIRED_REASONING)
    output = HERE / "results" / "revised" / f"{batch_id}.json"
    atomic_write_json(output, result)
    return output, len(changes)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_id")
    args = parser.parse_args()
    output, count = apply(args.batch_id)
    print(json.dumps({"batch_id": args.batch_id, "revisions": count, "output": str(output)}, ensure_ascii=False))
