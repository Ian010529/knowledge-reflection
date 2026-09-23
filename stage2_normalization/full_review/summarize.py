"""Report actual completion; unprocessed candidates remain explicitly unreviewed."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from run_batch import REQUIRED_MODEL, REQUIRED_REASONING, validate_cache

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
load = lambda name: json.loads((HERE / name).read_text())
manifest, candidates, evidence = load("manifest.json"), load("candidates.json"), load("evidence.json")
reused, deferred = load("reused.json"), load("deferred.json")
for name, expected in manifest["source_hashes"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
decisions, result_sources, finished, stale = dict(reused), {cid: "reused.json" for cid in reused}, [], []
for batch in manifest["batches"]:
    revised = HERE / "results" / "revised" / f"{batch['batch_id']}.json"
    path = revised if revised.exists() else HERE / "results" / f"{batch['batch_id']}.json"
    if not path.exists():
        continue
    result = json.loads(path.read_text())
    try:
        validate_cache(result, batch["candidate_ids"], candidates, evidence,
                       REQUIRED_MODEL, REQUIRED_REASONING, allow_legacy=True)
    except AssertionError as error:
        stale.append({"batch_id": batch["batch_id"], "status": "stale_needs_rerun",
                      "reason": str(error), "preserved_result": str(path.relative_to(HERE))})
        continue
    for row in result["decisions"]:
        cid = row["candidate_id"]
        assert cid not in decisions, cid
        decisions[cid] = row
        result_sources[cid] = str(path.relative_to(HERE))
    finished.append(batch["batch_id"])
rows = []
for cid, item in candidates.items():
    result = decisions.get(cid, {})
    status = "model_proposed_pending_human" if result else deferred.get(cid, {}).get("status", "unreviewed")
    row = {k: item[k] for k in ["candidate_id", "domain", "left_unit_id", "right_unit_id", "left_label", "right_label"]}
    row.update({k: ";".join(item[k]) for k in ["left_mention_ids", "right_mention_ids", "left_deferred_mention_ids", "right_deferred_mention_ids"]})
    row.update(status=status, proposed_relation=result.get("proposed_relation", ""),
               model_reason=result.get("model_reason", deferred.get(cid, {}).get("reason", "")),
               decision_source=result_sources.get(cid, ""), merge_applied="False", human_decision="", human_reason="")
    rows.append(row)
output = HERE / "candidate_review.csv"
if output.exists():
    with output.open(encoding="utf-8-sig", newline="") as stream:
        assert not any(r["human_decision"] or r["human_reason"] for r in csv.DictReader(stream)), "Human review present; refusing overwrite"
temporary = output.with_suffix(".csv.tmp")
with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
temporary.replace(output)
counts = Counter(r["status"] for r in rows)
summary = {"candidate_count": len(rows), "by_status": dict(counts),
           "by_relation": dict(Counter(r["proposed_relation"] for r in rows if r["proposed_relation"])),
           "validated_batches": len(finished), "stale_batches": len(stale), "total_batches": len(manifest["batches"]),
           "eligible_review_complete": counts["unreviewed"] == 0,
           "all_candidates_semantically_reviewed": counts["unreviewed"] == 0 and not deferred,
           "source_hashes_unchanged": True, "node_merges_applied": 0,
           "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
(HERE / "progress.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
(HERE / "stale_results.json").write_text(json.dumps(stale, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(summary, ensure_ascii=False, indent=2))
