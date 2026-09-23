"""One bounded Codex classification call; preserves raw output and validates evidence."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RELATIONS = ["equivalent_to", "broader_than", "narrower_than", "related_to", "distinct_from", "uncertain"]
REQUIRED_MODEL = "gpt-5.6-sol"
REQUIRED_REASONING = "medium"


def load(name):
    return json.loads((HERE / name).read_text())


def schema():
    evidence = {"type": "object", "additionalProperties": False,
                "properties": {"mention_id": {"type": "string"}, "quote_span": {"type": "string"}},
                "required": ["mention_id", "quote_span"]}
    item = {"type": "object", "additionalProperties": False,
            "properties": {"candidate_id": {"type": "string"},
                           "proposed_relation": {"type": "string", "enum": RELATIONS},
                           "model_reason": {"type": "string"},
                           "left_evidence": evidence, "right_evidence": evidence},
            "required": ["candidate_id", "proposed_relation", "model_reason", "left_evidence", "right_evidence"]}
    return {"type": "object", "additionalProperties": False,
            "properties": {"decisions": {"type": "array", "items": item}}, "required": ["decisions"]}


def canonical_json(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_input(ids, candidates, evidence):
    packet_candidates = [candidates[cid] for cid in ids]
    mids = sorted({mid for c in packet_candidates for side in ("left", "right") for mid in c[f"{side}_mention_ids"]})
    packet = {"candidates": packet_candidates, "evidence": {mid: evidence[mid] for mid in mids}}
    prompt = (HERE / "INSTRUCTIONS.md").read_text() + "\n\n" + json.dumps(packet, ensure_ascii=False)
    schema_text = json.dumps(schema())
    return prompt, schema_text, mids


def input_fingerprint(ids, candidates, evidence, model, reasoning):
    prompt, schema_text, _ = build_input(ids, candidates, evidence)
    parts = {"candidate_ids": ids, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
             "schema_sha256": hashlib.sha256(schema_text.encode()).hexdigest(),
             "model": model, "reasoning_effort": reasoning}
    return hashlib.sha256(canonical_json(parts).encode()).hexdigest(), parts


def validate(data, ids, candidates, evidence):
    rows = data["decisions"]
    assert len(rows) == len(ids) and {r["candidate_id"] for r in rows} == set(ids), "Missing/duplicate candidate IDs"
    for row in rows:
        cid = row["candidate_id"]
        assert row["proposed_relation"] in RELATIONS and len(row["model_reason"].strip()) >= 12, cid
        item = candidates[cid]
        for side in ("left", "right"):
            support = row[f"{side}_evidence"]
            assert support["mention_id"] in item[f"{side}_mention_ids"], cid
            assert len(support["quote_span"]) >= 8 and support["quote_span"] in evidence[support["mention_id"]]["quote"], cid
        if row["proposed_relation"] == "equivalent_to":
            roles = {evidence[mid]["proposed_semantic_role"] for mid in item["left_mention_ids"] + item["right_mention_ids"]}
            assert len(roles) == 1, f"Equivalent across roles: {cid}"


def bind_full_source_evidence(response, candidates, evidence):
    """Use the already supplied full source when the model paraphrases an excerpt.

    This is evidence attachment, not a semantic repair or a model-selected quote.
    The unmodified response remains in response.json.
    """
    bindings = []
    for row in response["decisions"]:
        candidate = candidates[row["candidate_id"]]
        for side in ("left", "right"):
            support = row[f"{side}_evidence"]
            mid = support["mention_id"]
            assert mid in candidate[f"{side}_mention_ids"], row["candidate_id"]
            quote = evidence[mid]["quote"]
            if len(support["quote_span"]) < 8 or support["quote_span"] not in quote:
                bindings.append({"candidate_id": row["candidate_id"], "side": side,
                    "model_excerpt": support["quote_span"],
                    "binding": "program_attached_full_original_quote; not a model-selected verbatim excerpt"})
                support["quote_span"] = quote
    return bindings


def validate_cache(data, ids, candidates, evidence, model, reasoning, allow_legacy=False):
    """Validate semantic output and bind it to every byte of input plus model settings."""
    validate(data, ids, candidates, evidence)
    expected, parts = input_fingerprint(ids, candidates, evidence, model, reasoning)
    provenance = data.get("provenance", {})
    actual = provenance.get("input_fingerprint_sha256")
    if actual == expected:
        return expected
    if allow_legacy:
        calls = provenance.get("calls", [])
        if len(calls) == 1:
            call = calls[0]
            schema_paths = [Path(call["command"][i + 1]) for i, value in enumerate(call.get("command", [])[:-1])
                            if value == "--output-schema"]
            archived_schema_ok = len(schema_paths) == 1 and schema_paths[0].is_file() and hashlib.sha256(
                schema_paths[0].read_text().encode()).hexdigest() == parts["schema_sha256"]
            if (call.get("candidate_ids") == ids and call.get("prompt_sha256") == parts["prompt_sha256"]
                    and call.get("model") == model and call.get("reasoning_effort") == reasoning
                    and archived_schema_ok):
                return expected
    raise AssertionError(f"cache fingerprint mismatch: expected {expected}, got {actual or 'missing'}")


def atomic_write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def next_attempt_dir(batch_id):
    """Create a new attempt directory without overwriting earlier raw logs."""
    parent = HERE / "raw" / batch_id
    parent.mkdir(parents=True, exist_ok=True)
    numbers = []
    for path in parent.glob("attempt_*"):
        try:
            numbers.append(int(path.name.split("_")[-1]))
        except ValueError:
            pass
    path = parent / f"attempt_{max(numbers, default=1) + 1:03d}"
    path.mkdir()
    return path


def run_call(batch_id, ids, candidates, evidence, config, run_dir, chunk_index):
    """Run and validate one checkpointable subset of a manifest batch."""
    prompt, schema_text, mids = build_input(ids, candidates, evidence)
    (run_dir / "input.txt").write_text(prompt)
    schema_path = run_dir / "schema.json"
    schema_path.write_text(schema_text)
    binary = shutil.which("codex")
    assert binary, "Codex CLI unavailable"
    command = [binary, "exec", "--ignore-user-config", "--skip-git-repo-check", "--ephemeral", "--sandbox", "read-only",
               "--output-schema", str(schema_path), "--output-last-message", str(run_dir / "response.json"), "--json"]
    for key in ("model", "model_reasoning_effort"):
        if config.get(key):
            command.extend(["-c", f"{key}={json.dumps(config[key])}"])
    for feature in ("shell_tool", "unified_exec", "apps", "plugins", "multi_agent", "browser_use", "computer_use", "image_generation", "hooks"):
        command.extend(["--disable", feature])
    command.extend(["--enable", "skip_host_skill_discovery"])
    if config.get("respect_system_proxy"):
        command.extend(["--enable", "respect_system_proxy"])
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="normalization-input-") as cwd:
        command.extend(["--cd", cwd, "-"])
        with (run_dir / "events.jsonl").open("w") as stdout, (run_dir / "stderr.txt").open("w") as stderr:
            completed = subprocess.run(command, input=prompt, text=True, stdout=stdout, stderr=stderr, timeout=1800)
    fingerprint, fingerprint_parts = input_fingerprint(ids, candidates, evidence, config["model"], config["model_reasoning_effort"])
    meta = {"batch_id": batch_id, "chunk_index": chunk_index, "candidate_count": len(ids),
            "candidate_ids": ids, "input_mention_count": len(mids),
            "model": config.get("model", "CLI default"), "reasoning_effort": config.get("model_reasoning_effort", "CLI default"),
            "command": command, "returncode": completed.returncode, "elapsed_seconds": round(time.time() - started, 2),
            "prompt_chars": len(prompt), **fingerprint_parts, "input_fingerprint_sha256": fingerprint}
    atomic_write_json(run_dir / "run.json", meta)
    assert completed.returncode == 0, f"{batch_id} chunk {chunk_index}: CLI failure; inspect {run_dir}"
    response = json.loads((run_dir / "response.json").read_text())
    if config.get("canonicalize_evidence_case"):
        corrections = []
        for row in response["decisions"]:
            for side in ("left", "right"):
                support = row[f"{side}_evidence"]
                span = support["quote_span"]
                quote = evidence[support["mention_id"]]["quote"]
                if span and span not in quote:
                    matches = list(re.finditer(re.escape(span), quote, re.IGNORECASE))
                    if len(matches) == 1:
                        exact = matches[0].group()
                        support["quote_span"] = exact
                        corrections.append({"candidate_id": row["candidate_id"], "side": side,
                                            "previous": span, "current": exact,
                                            "reason": "Unique case-insensitive literal match; restore source casing only"})
        if corrections:
            meta["literal_evidence_corrections"] = corrections
            atomic_write_json(run_dir / "run.json", meta)
    if config.get("bind_full_source_evidence"):
        bindings = bind_full_source_evidence(response, candidates, evidence)
        if bindings:
            meta["source_evidence_bindings"] = bindings
            atomic_write_json(run_dir / "run.json", meta)
    validate(response, ids, candidates, evidence)
    response["provenance"] = meta
    return response


def run(batch_id, model=None, reasoning=None, chunk_size=10):
    manifest, candidates, evidence = load("manifest.json"), load("candidates.json"), load("evidence.json")
    for name, expected in manifest["source_hashes"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    batch = next(x for x in manifest["batches"] if x["batch_id"] == batch_id)
    ids = batch["candidate_ids"]
    config_path = Path.home() / ".codex/config.toml"
    config = tomllib.loads(config_path.read_text()) if config_path.exists() else {}
    config["model"] = model or REQUIRED_MODEL
    config["model_reasoning_effort"] = reasoning or REQUIRED_REASONING
    assert config["model"] == REQUIRED_MODEL and config["model_reasoning_effort"] == REQUIRED_REASONING, "Full review requires gpt-5.6-sol medium"
    out = HERE / "results" / f"{batch_id}.json"
    if out.exists():
        result = json.loads(out.read_text())
        try:
            fingerprint = validate_cache(result, ids, candidates, evidence, config["model"], config["model_reasoning_effort"], allow_legacy=True)
        except AssertionError as error:
            atomic_write_json(HERE / "results" / "stale" / f"{batch_id}.json",
                              {"batch_id": batch_id, "status": "stale_needs_rerun", "reason": str(error), "preserved_result": str(out)})
            return {"batch_id": batch_id, "status": "stale_needs_rerun", "count": 0}
        return {"batch_id": batch_id, "status": "cached", "count": len(ids), "input_fingerprint_sha256": fingerprint}
    assert chunk_size > 0
    partial_dir = HERE / "results" / ".partials" / batch_id
    partial_dir.mkdir(parents=True, exist_ok=True)
    decisions, calls = [], []
    for chunk_index, start in enumerate(range(0, len(ids), chunk_size), 1):
        chunk_ids = ids[start:start + chunk_size]
        chunk_fingerprint, _ = input_fingerprint(chunk_ids, candidates, evidence, config["model"], config["model_reasoning_effort"])
        partial = partial_dir / f"chunk_{chunk_index:03d}_{chunk_fingerprint[:16]}.json"
        if partial.exists():
            response = json.loads(partial.read_text())
            validate_cache(response, chunk_ids, candidates, evidence, config["model"], config["model_reasoning_effort"])
        else:
            attempt = next_attempt_dir(batch_id)
            run_dir = attempt / f"chunk_{chunk_index:03d}"
            run_dir.mkdir()
            response = run_call(batch_id, chunk_ids, candidates, evidence, config, run_dir, chunk_index)
            atomic_write_json(partial, response)
        decisions.extend(response["decisions"])
        calls.append(response.get("provenance", {}))
    full_fingerprint, full_parts = input_fingerprint(ids, candidates, evidence, config["model"], config["model_reasoning_effort"])
    response = {"decisions": decisions, "provenance": {"batch_id": batch_id, "chunk_size": chunk_size,
                "model": config.get("model", "CLI default"), "reasoning_effort": config.get("model_reasoning_effort", "CLI default"),
                **full_parts, "input_fingerprint_sha256": full_fingerprint, "calls": calls}}
    validate_cache(response, ids, candidates, evidence, config["model"], config["model_reasoning_effort"])
    atomic_write_json(out, response)
    return {"batch_id": batch_id, "status": "validated_model_output", "count": len(ids)}


if __name__ == "__main__":
    raise SystemExit("旧全量候选大模型执行入口已停用；历史输出与证据校验函数保留。")
