"""Join recorded model judgments to unchanged source evidence; no inference or merging."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read_csv(path):
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


plan = json.loads((HERE / "batch_plan.json").read_text())
decision_record = json.loads((HERE / "model_decisions.json").read_text())
decisions = decision_record["decisions"]
for name, expected in plan["source_hashes"].items():
    assert digest(ROOT / name) == expected, f"Source changed: {name}"
roles = {r["mention_id"]: r for r in read_csv("stage2_review/role_run_v2/role_model_proposals.csv")}
nodes = {r["mention_id"]: r for r in read_csv("stage2_reconstruction/v1/node_evidence.csv")}
pending = {r["mention_id"] for r in read_csv("stage2_review/role_run_v2/pending_review.csv")}
papers = {(r["domain"], r["paper_id"]): r for r in read_csv("stage2_reconstruction/v1/paper_coverage.csv")}
assert len(roles) == len(nodes) == 4646 and roles.keys() == nodes.keys()
assert len(pending) == plan["deferred_mentions"] and pending <= roles.keys()
for mid, r in roles.items():
    assert all(r[k] == nodes[mid][k] for k in ("domain", "paper_id", "raw_phrase", "quote")), mid
comparisons = plan["comparisons"]
assert len({p["comparison_id"] for p in comparisons}) == len(comparisons) == len(decisions)
assert {p["comparison_id"] for p in comparisons} == decisions.keys()
allowed = {"equivalent_to", "narrower_than", "broader_than", "related_to", "distinct_from", "uncertain"}
rows, seen_pairs, covered = [], set(), set()
for p in comparisons:
    cid = p["comparison_id"]
    judgment = decisions[cid]
    assert judgment["proposed_relation"] in allowed and judgment["model_reason"].strip(), cid
    mids = (p["left_mention_id"], p["right_mention_id"])
    assert mids[0] != mids[1] and not pending.intersection(mids), cid
    pair = tuple(sorted(mids))
    assert pair not in seen_pairs, cid
    seen_pairs.add(pair)
    covered.update(mids)
    row = dict(p)
    for side, mid in zip(("left", "right"), mids):
        source = roles[mid]
        assert source["domain"] == p["domain"], cid
        assert (source["domain"], source["paper_id"]) in papers, mid
        row.update({f"{side}_{k}": source[k] for k in ("paper_id", "raw_phrase", "proposed_semantic_role", "quote")})
    if judgment["proposed_relation"] == "equivalent_to":
        assert row["left_proposed_semantic_role"] == row["right_proposed_semantic_role"], cid
    row.update(judgment)
    row.update(annotation_status="model_proposed_pending_human", merge_applied="False",
               human_decision="", human_reason="")
    rows.append(row)

# A temporary connectivity check detects contradictory pair proposals; it never folds source IDs.
parent = {}


def find(mid):
    parent.setdefault(mid, mid)
    if parent[mid] != mid:
        parent[mid] = find(parent[mid])
    return parent[mid]


for r in rows:
    if r["proposed_relation"] == "equivalent_to":
        parent[find(r["left_mention_id"])] = find(r["right_mention_id"])
conflicts = [r["comparison_id"] for r in rows if r["proposed_relation"] != "equivalent_to"
            and find(r["left_mention_id"]) == find(r["right_mention_id"])]
assert not conflicts, conflicts
members = read_csv("stage2_review/v1/retrieval_unit_members.csv")
unit_of = {m["mention_id"]: m["retrieval_unit_id"] for m in members}
active_units = {unit_of[mid] for mid in roles.keys() - pending}
candidates = read_csv("stage2_review/v1/normalization_candidates.csv")
candidate_by_pair = {tuple(sorted((c["left_unit_id"], c["right_unit_id"]))): c["candidate_id"] for c in candidates}
active = {c["candidate_id"] for c in candidates if c["left_unit_id"] in active_units and c["right_unit_id"] in active_units}
sampled = set()
for r in rows:
    pair = tuple(sorted((unit_of[r["left_mention_id"]], unit_of[r["right_mention_id"]])))
    candidate_id = candidate_by_pair.get(pair)
    if r["source_candidate_id"]:
        assert candidate_id == r["source_candidate_id"]
    if candidate_id:
        sampled.add(candidate_id)
assert len(active) == plan["active_unit_candidates"] and sampled <= active
output = HERE / "normalization_model_proposals.csv"
if output.exists():
    with output.open(encoding="utf-8-sig", newline="") as stream:
        assert not any(r.get("human_decision") or r.get("human_reason") for r in csv.DictReader(stream)), "Human review present; preserve it as an independent acceptance record before regenerating."
with output.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
with output.open(encoding="utf-8-sig", newline="") as stream:
    assert list(csv.DictReader(stream)) == rows
summary = {
    "validation_passed": True, "comparison_count": len(rows),
    "by_relation": dict(Counter(r["proposed_relation"] for r in rows)),
    "by_domain": dict(Counter(r["domain"] for r in rows)),
    "by_selection": dict(Counter(r["selection"] for r in rows)),
    "by_evidence_scope": dict(Counter(r["evidence_scope"] for r in rows)),
    "by_batch": {batch["batch_id"]: dict(Counter(r["proposed_relation"] for r in rows
                 if batch["comparison_first"] <= r["comparison_id"] <= batch["comparison_last"]))
                 for batch in plan.get("batches", [])},
    "judgment_revision_count": len(decision_record.get("revisions", [])),
    "eligible_mentions": len(roles) - len(pending), "deferred_role_mentions": len(pending),
    "unique_mentions_in_reviewed_pairs": len(covered),
    "eligible_mentions_not_in_this_batch": len(roles.keys() - pending - covered),
    "original_unit_candidates": len(candidates), "active_unit_candidates": len(active),
    "unit_candidates_with_at_least_one_reviewed_occurrence_pair": len(sampled),
    "active_unit_candidates_without_reviewed_occurrence_pair": len(active - sampled),
    "deferred_unit_candidates": len(candidates) - len(active),
    "equivalence_conflict_ids": conflicts, "source_hashes_unchanged": plan["source_hashes"],
    "output_sha256": digest(output), "batch_plan_sha256": digest(HERE / "batch_plan.json"),
    "model_decisions_sha256": digest(HERE / "model_decisions.json"),
    "limitations": "Model proposals only. A reviewed occurrence pair does not resolve all members of its retrieval units. No human acceptance, node folding, or accuracy estimate.",
}
(HERE / "validation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "source_hashes_unchanged"}, ensure_ascii=False, indent=2))
