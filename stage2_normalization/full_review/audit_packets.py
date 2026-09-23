"""Offline, lossless prompt-size experiment; never changes the active runner/plan.

Run with Python 3. Sizes are characters, not billed tokens. The encoder is an
experimental input format and must pass a model pilot before production use.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCE_INSTRUCTION = (
    "\n输入中 evidence 的 quote_ref 指向同一输入 quotes 字典中的完整原文；"
    "按引用读取全文。保留每个 mention_id 自己的论文、短语、角色和语境，"
    "共用原文不代表节点同义。quote 字段仍为直接原文。\n"
)


def encode(packet):
    """Factor only exactly repeated strings; retain all per-mention metadata."""
    counts = Counter(row["quote"] for row in packet["evidence"].values())
    refs = {quote: f"q{i}" for i, quote in enumerate(sorted(
        quote for quote, count in counts.items() if count > 1
    ))}
    evidence = {}
    for mid, original in packet["evidence"].items():
        row = dict(original)
        if row["quote"] in refs:
            row["quote_ref"] = refs[row.pop("quote")]
        evidence[mid] = row
    return {"candidates": packet["candidates"], "evidence": evidence,
            "quotes": {ref: quote for quote, ref in refs.items()}}


def decode(packet):
    evidence = {}
    for mid, original in packet["evidence"].items():
        row = dict(original)
        if "quote_ref" in row:
            row["quote"] = packet["quotes"][row.pop("quote_ref")]
        evidence[mid] = row
    return {"candidates": packet["candidates"], "evidence": evidence}


def group_shared_evidence(ids, candidates, evidence, instructions, max_chars, max_candidates):
    """Dry-run ordering only: neighboring pairs share complete mention records.

    Size/ID ordering is administrative and assigns no semantic relation.
    Uses the existing production packet schema, without quote references.
    """
    dumps = lambda obj: json.dumps(obj, ensure_ascii=False)
    mids = {cid: set(candidates[cid]["left_mention_ids"] + candidates[cid]["right_mention_ids"])
            for cid in ids}
    weights = {mid: len(dumps(mid)) + len(dumps(row)) + 4 for mid, row in evidence.items()}
    row_weights = {cid: len(dumps(candidates[cid])) + 2 for cid in ids}
    adjacent = {}
    for cid in ids:
        for mid in mids[cid]:
            adjacent.setdefault(mid, set()).add(cid)
    rank = {cid: i for i, cid in enumerate(ids)}
    remaining = set(ids)
    batches = []
    while remaining:
        chosen, pooled, nearby = [], set(), set()
        budget = len(instructions + "\n\n" + dumps({"candidates": [], "evidence": {}}))
        while remaining and len(chosen) < max_candidates:
            options = (nearby & remaining) or {min(remaining, key=rank.get)}
            def cost(cid):
                return row_weights[cid] + sum(weights[mid] for mid in mids[cid] - pooled)
            fitting = [cid for cid in options if budget + cost(cid) <= max_chars]
            if not fitting:
                break
            cid = min(fitting, key=lambda cid: (cost(cid), rank[cid]))
            budget += cost(cid)
            chosen.append(cid)
            remaining.remove(cid)
            for mid in mids[cid] - pooled:
                nearby.update(adjacent[mid])
            pooled.update(mids[cid])
        assert chosen, "A single candidate exceeds the unchanged prompt-size ceiling"
        packet = {"candidates": [candidates[cid] for cid in chosen],
                  "evidence": {mid: evidence[mid] for mid in sorted(pooled)}}
        actual_chars = len(instructions + "\n\n" + dumps(packet))
        assert actual_chars <= max_chars
        assert set(packet["evidence"]) == set().union(*(mids[cid] for cid in chosen))
        batches.append({"candidate_ids": chosen, "prompt_chars": actual_chars})
    flattened = [cid for batch in batches for cid in batch["candidate_ids"]]
    assert len(flattened) == len(set(flattened)) == len(ids) and set(flattened) == set(ids)
    return batches


def main():
    read = lambda name: json.loads((HERE / name).read_text())
    manifest, candidates, evidence = (read(name + ".json") for name in (
        "manifest", "candidates", "evidence"))
    for name, expected in manifest["source_hashes"].items():
        assert hashlib.sha256((HERE.parents[1] / name).read_bytes()).hexdigest() == expected, name
    instructions = (HERE / "INSTRUCTIONS.md").read_text()
    sizes = []
    seen = []
    for batch in manifest["batches"]:
        ids = batch["candidate_ids"]
        seen.extend(ids)
        mids = sorted({mid for cid in ids for side in ("left", "right")
                       for mid in candidates[cid][f"{side}_mention_ids"]})
        packet = {"candidates": [candidates[cid] for cid in ids],
                  "evidence": {mid: evidence[mid] for mid in mids}}
        factored = encode(packet)
        assert decode(factored) == packet, batch["batch_id"]
        original_size = len(instructions + "\n\n" + json.dumps(packet, ensure_ascii=False))
        new_size = len(instructions + REFERENCE_INSTRUCTION + "\n\n" + json.dumps(factored, ensure_ascii=False))
        sizes.append({"batch_id": batch["batch_id"], "candidate_count": len(ids),
                      "original_prompt_chars": original_size,
                      "factored_prompt_chars": new_size})
    assert len(seen) == len(set(seen)) == manifest["needs_model_review"]
    assert set(seen) == set(candidates) - set(read("reused.json")) - set(read("deferred.json"))
    old = sum(row["original_prompt_chars"] for row in sizes)
    new = sum(row["factored_prompt_chars"] for row in sizes)
    grouped = group_shared_evidence(seen, candidates, evidence, instructions,
                                    max(row["original_prompt_chars"] for row in sizes),
                                    max(row["candidate_count"] for row in sizes))
    grouped_chars = sum(batch["prompt_chars"] for batch in grouped)
    report = {
        "scope": "offline round-trip and prompt-character audit only; no model calls",
        "production_rollout": False,
        "source_hashes_verified": True,
        "catalog_hashes": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                           for name in ("manifest.json", "candidates.json", "evidence.json", "INSTRUCTIONS.md")},
        "candidate_count": len(seen), "batch_count": len(sizes),
        "candidate_coverage_exact_once": True, "all_batches_exact_round_trip": True,
        "original_prompt_chars": old, "factored_prompt_chars": new,
        "character_reduction_percent": round(100 * (1 - new / old), 2),
        "batches_that_grow": sum(row["factored_prompt_chars"] > row["original_prompt_chars"] for row in sizes),
        "first_batch": sizes[0],
        "shared_mention_grouping": {
            "production_rollout": False,
            "same_input_schema_and_full_quotes": True,
            "candidate_coverage_exact_once": True,
            "batch_count": len(grouped), "prompt_chars": grouped_chars,
            "character_reduction_percent": round(100 * (1 - grouped_chars / old), 2),
            "max_prompt_chars": max(batch["prompt_chars"] for batch in grouped),
            "baseline_max_prompt_chars": max(row["original_prompt_chars"] for row in sizes),
            "max_candidates_per_batch": max(len(batch["candidate_ids"]) for batch in grouped)
        },
        "limitations": [
            "Character reduction is not token, billing or elapsed-time reduction.",
            "Round-trip equality proves data preservation, not model comprehension or semantic correctness.",
            "A representative paired model pilot is required before changing production input format.",
            "Semantic summaries are excluded; each supplied occurrence retains its full source quotation.",
            "Experimental grouping changes order only in a dry run; it does not modify the active manifest or results.",
            "Batch order can affect model judgments despite identical evidence; pilot verification still applies."
        ]
    }
    (HERE / "optimization_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
