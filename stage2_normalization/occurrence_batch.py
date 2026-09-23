"""Continue the existing occurrence-pair queue with independent, bounded model calls.

Reuses the existing structured Codex runner; never resumes its conversation.
Only selection, evidence joining, validation and persistence are automated here.
"""
import argparse
import csv
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from full_review import run_batch as classifier

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNS = HERE / "occurrence_runs"
MODEL = "gpt-6-astra"
EFFORT = "high"
REVIEW_LEDGER = HERE / "takeover_review.json"


def read_json(path):
    return json.loads(path.read_text())


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_state():
    plan = read_json(HERE / "batch_plan.json")
    record = read_json(HERE / "model_decisions.json")
    for name, expected in plan["source_hashes"].items():
        assert digest(ROOT / name) == expected, f"Source changed: {name}"
    assert {p["comparison_id"] for p in plan["comparisons"]} == record["decisions"].keys()
    return plan, record


def select(plan, count):
    roles = {r["mention_id"]: r for r in read_csv("stage2_review/role_run_v2/role_model_proposals.csv")}
    pending = {r["mention_id"] for r in read_csv("stage2_review/role_run_v2/pending_review.csv")}
    members = {}
    for row in read_csv("stage2_review/v1/retrieval_unit_members.csv"):
        mid = row["mention_id"]
        if mid not in pending and roles[mid]["proposed_semantic_role"]:
            members.setdefault(row["retrieval_unit_id"], []).append(mid)
    sampled = {p["source_candidate_id"] for p in plan["comparisons"] if p.get("source_candidate_id")}
    seen = {tuple(sorted((p["left_mention_id"], p["right_mention_id"]))) for p in plan["comparisons"]}
    eligible = []
    for row in read_csv("stage2_review/v1/normalization_candidates.csv"):
        if row["candidate_id"] in sampled:
            continue
        left, right = members.get(row["left_unit_id"]), members.get(row["right_unit_id"])
        if not left or not right or tuple(sorted((left[0], right[0]))) in seen:
            continue
        eligible.append((float(row["char_ngram_cosine"]), row, left[0], right[0]))
    eligible.sort(key=lambda x: (-x[0], x[1]["candidate_id"]))
    first = max(int(p["comparison_id"][1:]) for p in plan["comparisons"]) + 1
    comparisons = []
    for index, (score, row, left, right) in enumerate(eligible[:count], first):
        bucket = ("lexical_cosine_ge_0.8" if score >= .8 else
                  "lexical_cosine_ge_0.7_lt_0.8" if score >= .7 else
                  "lexical_cosine_ge_0.6_lt_0.7" if score >= .6 else
                  "lexical_cosine_lt_0.6")
        comparisons.append(dict(comparison_id=f"N{index:04d}", domain=row["domain"],
                                left_mention_id=left, right_mention_id=right,
                                selection=bucket, source_candidate_id=row["candidate_id"]))
    candidates, evidence = build_packet(comparisons, roles)
    return comparisons, candidates, evidence, len(eligible)


def build_packet(comparisons, roles=None):
    if roles is None:
        roles = {r["mention_id"]: r for r in read_csv("stage2_review/role_run_v2/role_model_proposals.csv")}
    candidates = {p["comparison_id"]: dict(candidate_id=p["comparison_id"], domain=p["domain"],
                  left_mention_ids=[p["left_mention_id"]], right_mention_ids=[p["right_mention_id"]])
                  for p in comparisons}
    mids = {p[f"{side}_mention_id"] for p in comparisons for side in ("left", "right")}
    evidence = {mid: {k: roles[mid][k] for k in
                ("mention_id", "paper_id", "domain", "raw_phrase", "proposed_semantic_role", "quote")}
                for mid in sorted(mids)}
    return candidates, evidence


def conflicts(comparisons, decisions):
    parent = {}

    def find(mid):
        parent.setdefault(mid, mid)
        while parent[mid] != mid:
            parent[mid] = parent[parent[mid]]
            mid = parent[mid]
        return mid

    for p in comparisons:
        if decisions[p["comparison_id"]]["proposed_relation"] == "equivalent_to":
            parent[find(p["left_mention_id"])] = find(p["right_mention_id"])
    return [p["comparison_id"] for p in comparisons
            if decisions[p["comparison_id"]]["proposed_relation"] != "equivalent_to"
            and find(p["left_mention_id"]) == find(p["right_mention_id"])]


def usage(path):
    totals = {}
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event.get("type") == "turn.completed":
            for key, value in event.get("usage", {}).items():
                if isinstance(value, (int, float)):
                    totals[key] = totals.get(key, 0) + value
    return totals


def materialize():
    result = subprocess.run([sys.executable, str(HERE / "materialize.py")], cwd=ROOT,
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-3500:])
    return read_json(HERE / "validation_summary.json")


def run_one(batch_size, chunk_size, dry_run=False):
    if not dry_run:
        raise RuntimeError("旧逐对大模型执行流程已停用；保留历史结果及只读候选选择，改用 embedding 候选复核流程。")
    plan, record = load_state()
    assert not conflicts(plan["comparisons"], record["decisions"]), "Resolve existing conflicts first"
    ledger = read_json(REVIEW_LEDGER) if REVIEW_LEDGER.exists() else None
    review_ids = [cid for cid in ledger["pending_ids"] if cid not in ledger["completed"]] if ledger else []
    reviewing = bool(review_ids)
    if reviewing:
        by_id = {p["comparison_id"]: p for p in plan["comparisons"]}
        comparisons = [by_id[cid] for cid in review_ids[:batch_size]]
        candidates, evidence = build_packet(comparisons)
        remaining = len(review_ids)
    else:
        comparisons, candidates, evidence, remaining = select(plan, batch_size)
    if not comparisons:
        return {"status": "complete", "remaining_selectable_candidates": 0}
    ids = [p["comparison_id"] for p in comparisons]
    batch_id = (f"review_{ids[0]}_{ids[-1]}" if reviewing else
                f"{max(int(b['batch_id']) for b in plan['batches']) + 1:02d}")
    summary = dict(batch_id=batch_id, first=ids[0], last=ids[-1], count=len(ids),
                   model=MODEL, reasoning=EFFORT, mode="review" if reviewing else "new",
                   remaining_in_phase=remaining,
                   independent_calls=(len(ids) + chunk_size - 1) // chunk_size)
    if dry_run:
        sizes = []
        for start in range(0, len(ids), chunk_size):
            prompt, _, _ = classifier.build_input(ids[start:start + chunk_size], candidates, evidence)
            sizes.append(len(prompt))
        return dict(summary, status="dry_run", prompt_chars_per_call=sizes)
    baseline = {name: (HERE / name).read_bytes() for name in
                ("batch_plan.json", "model_decisions.json", "normalization_model_proposals.csv", "validation_summary.json")}
    if ledger is not None:
        baseline[REVIEW_LEDGER.name] = REVIEW_LEDGER.read_bytes()
    directory = RUNS / f"batch_{batch_id}_{ids[0]}_{ids[-1]}" / f"{MODEL}_{EFFORT}"
    directory.mkdir(parents=True, exist_ok=True)
    outputs, calls = [], []
    config = {"model": MODEL, "model_reasoning_effort": EFFORT,
              "respect_system_proxy": sys.platform == "darwin", "canonicalize_evidence_case": True,
              "bind_full_source_evidence": True}
    for index, start in enumerate(range(0, len(ids), chunk_size), 1):
        chunk_ids = ids[start:start + chunk_size]
        fingerprint, _ = classifier.input_fingerprint(chunk_ids, candidates, evidence, MODEL, EFFORT)
        chunk_dir = directory / f"chunk_{index:02d}_{fingerprint[:12]}"
        saved = chunk_dir / "validated.json"
        if saved.exists():
            response = read_json(saved)
            classifier.validate_cache(response, chunk_ids, candidates, evidence, MODEL, EFFORT)
        else:
            # Retain failed attempts without reusing their incomplete output.
            attempt = chunk_dir / f"attempt_{len(list(chunk_dir.glob('attempt_*'))) + 1:03d}"
            attempt.mkdir(parents=True)
            response = classifier.run_call(batch_id, chunk_ids, candidates, evidence, config, attempt, index)
            response["provenance"]["usage"] = usage(attempt / "events.jsonl")
            classifier.atomic_write_json(saved, response)
        outputs.extend(response["decisions"])
        calls.append(response["provenance"])
    classifier.validate({"decisions": outputs}, ids, candidates, evidence)
    proposed = {r["candidate_id"]: {"proposed_relation": r["proposed_relation"],
                "model_reason": r["model_reason"],
                "evidence_scope": "full_original_quotes_rechecked" if reviewing else "full_original_quotes_read"}
                for r in outputs}
    all_comparisons = plan["comparisons"] if reviewing else plan["comparisons"] + comparisons
    collision_ids = conflicts(all_comparisons, {**record["decisions"], **proposed})
    # Save complete evidence and output even when a semantic conflict prevents publication.
    classifier.atomic_write_json(directory / "batch.json", dict(summary, comparisons=comparisons,
        decisions=outputs, calls=calls, equivalence_conflict_ids=collision_ids))
    if collision_ids:
        return dict(summary, status="needs_semantic_review", conflict_ids=collision_ids,
                    artifact=str(directory / "batch.json"))
    for name, content in baseline.items():
        assert (HERE / name).read_bytes() == content, f"Concurrent edit: {name}; no batch published"
    if reviewing:
        for cid, current in proposed.items():
            previous = record["decisions"][cid]
            if previous != current:
                record.setdefault("revisions", []).append(dict(comparison_id=cid,
                    revision_batch=batch_id, previous=previous, current=current,
                    trigger="Parent-model full original-evidence rereview", model=MODEL, reasoning=EFFORT))
            ledger["completed"][cid] = dict(model=MODEL, reasoning=EFFORT,
                reviewed_at=datetime.now(timezone.utc).isoformat(),
                audit_path=str(directory.relative_to(ROOT)),
                reviewed_decision_sha256=hashlib.sha256(classifier.canonical_json(current).encode()).hexdigest())
    else:
        plan["comparisons"].extend(comparisons)
        plan["batches"].append(dict(batch_id=batch_id, comparison_first=ids[0], comparison_last=ids[-1],
            count=len(ids), selection="next unreviewed candidate representative occurrence pairs; no propagation",
            model=MODEL, reasoning=EFFORT, context_mode="independent_calls",
            completed_at=datetime.now(timezone.utc).isoformat(), audit_path=str(directory.relative_to(ROOT))))
    record["decisions"].update(proposed)
    try:
        classifier.atomic_write_json(HERE / "batch_plan.json", plan)
        classifier.atomic_write_json(HERE / "model_decisions.json", record)
        validated = materialize()
        if reviewing:
            classifier.atomic_write_json(REVIEW_LEDGER, ledger)
    except Exception:
        for name, content in baseline.items():
            (HERE / name).write_bytes(content)
        raise
    total_usage = {}
    for call in calls:
        for key, value in call.get("usage", {}).items():
            total_usage[key] = total_usage.get(key, 0) + value
    return dict(summary, status="validated", comparison_count=validated["comparison_count"],
                usage=total_usage, artifact=str(directory / "batch.json"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batches", type=int, default=1, help="0 continues until the queue is exhausted or blocked")
    parser.add_argument("--batch-size", type=int, default=36)
    parser.add_argument("--chunk-size", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--background", action="store_true", help="Start a detached runner and return its PID")
    args = parser.parse_args()
    if not args.dry_run:
        parser.error("旧逐对大模型执行流程已停用，不会启动模型或后台任务；--dry-run 仅查看历史队列。")
    assert args.batches >= 0 and 1 <= args.chunk_size <= 12 and 1 <= args.batch_size <= 40
    RUNS.mkdir(exist_ok=True)
    if args.background:
        assert not args.dry_run
        # Check the lock before launching; the child also acquires it before doing work.
        with (RUNS / "runner.lock").open("a") as check:
            fcntl.flock(check, fcntl.LOCK_EX | fcntl.LOCK_NB)
        command = [sys.executable, str(Path(__file__).resolve()), "--batches", str(args.batches),
                   "--batch-size", str(args.batch_size), "--chunk-size", str(args.chunk_size)]
        with (RUNS / "runner.log").open("a") as log:
            process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, start_new_session=True)
        print(json.dumps({"status": "launched", "pid": process.pid, "model": MODEL, "reasoning": EFFORT}))
        return 0
    with (RUNS / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        completed = 0
        while args.batches == 0 or completed < args.batches:
            if not args.dry_run:
                classifier.atomic_write_json(RUNS / "status.json", dict(status="running", pid=os.getpid(),
                    model=MODEL, reasoning=EFFORT, updated_at=datetime.now(timezone.utc).isoformat(),
                    last_validated_comparison_count=read_json(HERE / "validation_summary.json")["comparison_count"]))
            try:
                result = run_one(args.batch_size, args.chunk_size, args.dry_run)
            except Exception as error:
                result = dict(status="blocked", model=MODEL, reasoning=EFFORT,
                              error=f"{type(error).__name__}: {error}")
                classifier.atomic_write_json(RUNS / "status.json", result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
                return 1
            classifier.atomic_write_json(RUNS / "status.json", result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            if args.dry_run or result["status"] != "validated":
                return 2 if result["status"] == "needs_semantic_review" else 0
            completed += 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
