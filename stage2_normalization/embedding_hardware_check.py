"""Bounded 100-text hardware benchmark; writes no normalization decisions."""
import json
import resource
import subprocess
import time
from pathlib import Path

START = time.perf_counter()
print("Loading embedding libraries", flush=True)
import numpy as np
import torch
from huggingface_hub import HfApi
from sentence_transformers import SentenceTransformer
import occurrence_batch as queue

OUT = Path(__file__).resolve().parent / "embedding_baseline"
MODEL = "nomic-ai/nomic-embed-text-v1.5"


def memory():
    return {"process_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**2,
            "swap": subprocess.check_output(["sysctl", "vm.swapusage"], text=True).strip(),
            "pressure": subprocess.check_output(["memory_pressure", "-Q"], text=True).strip(),
            "mps_driver_mib": torch.mps.driver_allocated_memory() / 1024**2 if DEVICE == "mps" else None}


OUT.mkdir(exist_ok=True)
torch.set_num_threads(2)
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
if DEVICE == "mps":
    # Bound this process's MPS allocator on the 8-GB host.
    torch.mps.set_per_process_memory_fraction(0.35)
plan, record = queue.load_state()
protected = {name: queue.digest(queue.HERE / name) for name in
             ("batch_plan.json", "model_decisions.json", "normalization_model_proposals.csv")}
remaining, _, _, remaining_count = queue.select(plan, 100000)
pairs = plan["comparisons"] + remaining
roles = {r["mention_id"]: r for r in queue.read_csv("stage2_review/role_run_v2/role_model_proposals.csv")}
mids = sorted({p[side + "_mention_id"] for p in pairs for side in ("left", "right")})
texts = {mid: "clustering: " + roles[mid]["raw_phrase"] + ". Context: " +
         " ".join(roles[mid]["quote"].split()[:80]) for mid in mids}
# Cover the full input-length range, including the longest text, deterministically.
ordered = sorted(mids, key=lambda mid: (len(texts[mid]), mid))
selected = [ordered[i] for i in np.linspace(0, len(ordered) - 1, 100, dtype=int)]
sample = [texts[mid] for mid in selected]
report = {"status": "loading", "model": MODEL, "device": DEVICE,
          "torch_threads": 2, "mps_memory_fraction": 0.35 if DEVICE == "mps" else None,
          "sample_count": len(sample), "queue_unique_mentions": len(mids),
          "queue_pair_count": len(pairs), "sample_method": "100 character-length quantiles including longest text",
          "sample_mention_ids": selected, "before": memory(), "runs": []}
path = OUT / "hardware_check.json"


def save():
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


save()
try:
    print(f"Loading {MODEL} on {DEVICE}; test restricted to 100 texts", flush=True)
    revision = HfApi().model_info(MODEL).sha
    report["revision"] = revision
    loading_start = time.perf_counter()
    model = SentenceTransformer(MODEL, revision=revision, device=DEVICE, trust_remote_code=False)
    model.max_seq_length = 512
    report["model_load_seconds"] = time.perf_counter() - loading_start
    lengths = [len(model.tokenizer.encode(text, add_special_tokens=True)) for text in sample]
    report["sample_token_lengths"] = {"min": min(lengths), "mean": float(np.mean(lengths)),
                                      "max": max(lengths), "over_512": sum(n > 512 for n in lengths)}
    print("Model loaded; warming up with one text", flush=True)
    model.encode(sample[:1], batch_size=1, normalize_embeddings=True, show_progress_bar=False)
    if DEVICE == "mps":
        torch.mps.synchronize()
    reference = None
    for batch_size in (1, 4):
        print(f"Benchmark batch_size={batch_size}", flush=True)
        started = time.perf_counter()
        vectors = model.encode(sample, batch_size=batch_size, normalize_embeddings=True,
                               convert_to_numpy=True, show_progress_bar=False)
        if DEVICE == "mps":
            torch.mps.synchronize()
        elapsed = time.perf_counter() - started
        assert vectors.shape == (100, 768) and np.isfinite(vectors).all()
        assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4)
        run = {"batch_size": batch_size, "seconds": elapsed,
               "texts_per_second": 100 / elapsed,
               "projected_queue_encoding_minutes": elapsed / 100 * len(mids) / 60,
               "memory": memory()}
        if reference is not None:
            run["minimum_cosine_vs_batch_1"] = float(np.sum(reference * vectors, axis=1).min())
            assert run["minimum_cosine_vs_batch_1"] > .999
        reference = vectors
        report["runs"].append(run)
        save()
        print(json.dumps(run), flush=True)
    np.savez_compressed(OUT / "hardware_check_vectors.npz", mention_ids=np.array(selected), vectors=reference)
    report["status"] = "passed"
except Exception as error:
    report["status"] = "failed"
    report["error"] = f"{type(error).__name__}: {error}"
    raise
finally:
    report["total_seconds_including_import_and_download"] = time.perf_counter() - START
    report["after"] = memory()
    report["decision_files_unchanged"] = all(queue.digest(queue.HERE / n) == h for n, h in protected.items())
    save()
