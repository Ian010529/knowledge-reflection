"""Freeze complete candidate coverage and evidence packets, without assigning new labels."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def save(name, data):
    (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


previous_plan = json.loads((HERE.parent / "batch_plan.json").read_text())
source_hashes = dict(previous_plan["source_hashes"])
for name in ["stage2_normalization/batch_plan.json", "stage2_normalization/model_decisions.json"]:
    source_hashes[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
for name, expected in source_hashes.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
roles = {r["mention_id"]: r for r in read("stage2_review/role_run_v2/role_model_proposals.csv")}
pending = {r["mention_id"] for r in read("stage2_review/role_run_v2/pending_review.csv")}
members, unit_of = defaultdict(list), {}
for row in read("stage2_review/v1/retrieval_unit_members.csv"):
    members[row["retrieval_unit_id"]].append(row["mention_id"])
    unit_of[row["mention_id"]] = row["retrieval_unit_id"]
previous = {}
decisions = json.loads((HERE.parent / "model_decisions.json").read_text())["decisions"]
for pair in previous_plan["comparisons"]:
    mids = pair["left_mention_id"], pair["right_mention_id"]
    previous[mids] = dict(decisions[pair["comparison_id"]], previous_comparison_id=pair["comparison_id"])
candidates, reused, deferred = {}, {}, {}
inverse = {"broader_than": "narrower_than", "narrower_than": "broader_than"}
for candidate in read("stage2_review/v1/normalization_candidates.csv"):
    cid = candidate["candidate_id"]
    item = {k: candidate[k] for k in ["candidate_id", "domain", "left_unit_id", "right_unit_id", "left_label", "right_label"]}
    for side in ("left", "right"):
        mids = sorted(members[item[f"{side}_unit_id"]])
        item[f"{side}_mention_ids"] = [mid for mid in mids if mid not in pending]
        item[f"{side}_deferred_mention_ids"] = [mid for mid in mids if mid in pending]
    candidates[cid] = item
    left, right = item["left_mention_ids"], item["right_mention_ids"]
    if not left or not right:
        deferred[cid] = {"status": "deferred_role_review", "reason": "至少一侧没有角色已明确的节点；未作语义判断。"}
    elif len(left) == len(right) == 1:
        direct = (left[0], right[0])
        reverse = (right[0], left[0])
        if direct in previous or reverse in previous:
            result = dict(previous[direct if direct in previous else reverse])
            if direct not in previous:
                result["proposed_relation"] = inverse.get(result["proposed_relation"], result["proposed_relation"])
                result["model_reason"] = "左右顺序相对既有记录反转；以下为原记录理由：" + result["model_reason"]
            reused[cid] = result

todo = [cid for cid in candidates if cid not in reused and cid not in deferred]
# Packing is administrative: no similarity score or keyword determines a semantic judgment.
batches, current, pooled = [], [], set()
for cid in todo:
    item = candidates[cid]
    mids = set(item["left_mention_ids"] + item["right_mention_ids"])
    next_pool = pooled | mids
    size = sum(len(roles[mid]["quote"]) + 250 for mid in next_pool)
    if current and (len(current) >= 80 or size > 120000):
        batches.append(current)
        current, pooled = [], set()
    current.append(cid)
    pooled.update(mids)
if current:
    batches.append(current)
assert len(candidates) == 18884 and len(todo) + len(reused) + len(deferred) == len(candidates)
manifest = {
    "scope": "Complete retrieval-candidate disposition. Review every eligible occurrence supplied on each side; heterogeneous senses must remain uncertain. No node folding or human acceptance.",
    "source_hashes": source_hashes,
    "candidate_count": len(candidates), "eligible_candidates": len(candidates) - len(deferred),
    "previous_singleton_results_reused": len(reused), "needs_model_review": len(todo),
    "deferred_role_candidates": len(deferred),
    "batches": [{"batch_id": f"B{i:04d}", "candidate_ids": ids} for i, ids in enumerate(batches, 1)],
}
save("manifest.json", manifest)
save("candidates.json", candidates)
save("evidence.json", {mid: {k: row[k] for k in ["mention_id", "domain", "paper_id", "raw_phrase", "proposed_semantic_role", "quote"]}
                       for mid, row in roles.items() if mid not in pending})
save("reused.json", reused)
save("deferred.json", deferred)
print(json.dumps({k: v for k, v in manifest.items() if k not in ("source_hashes", "batches")}, ensure_ascii=False))
print("Evidence batches prepared:", len(batches))
