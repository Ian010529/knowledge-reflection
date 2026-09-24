"""Validate evidence location, not scientific meaning, for NEW extraction only.

Usage: python3 modality_guard.py input_papers.json raw_records.json output.json
Inputs are paper arrays with paper_id and abstract / records respectively.
Writes a new record array and output.json.audit.json; refuses overwrites.
Supplements rather than replaces the general extraction validator.
"""
import copy
import json
import sys
from pathlib import Path

MODALITIES = {"experimental", "computational", "theoretical", "mixed", "unspecified"}


def guard(papers, raw):
    sources = {p["paper_id"]: p["abstract"] for p in papers}
    if len(sources) != len(papers):
        raise ValueError("Duplicate source paper_id")
    result, audit, seen = copy.deepcopy(raw), [], set()
    for paper in result:
        pid = paper["paper_id"]
        if pid not in sources or pid in seen:
            raise ValueError(f"Unknown or duplicate paper_id: {pid}")
        seen.add(pid)
        for record in paper["records"]:
            proposed = record.get("modality")
            modality = "unspecified" if proposed in (None, "") else proposed
            if modality not in MODALITIES:
                raise ValueError(f"{pid}:{record['id']}: invalid modality")
            evidence = record.get("modality_evidence", [])
            if not isinstance(evidence, list) or any(
                not isinstance(q, str) or not q.strip() for q in evidence
            ):
                raise ValueError(f"{pid}:{record['id']}: evidence must be nonempty quote strings")
            reason = None
            if any(q not in sources[pid] for q in evidence):
                reason = "evidence_not_in_this_abstract"
            elif modality != "unspecified" and not evidence:
                reason = "missing_modality_evidence"
            elif proposed in (None, ""):
                reason = "default_unspecified"
            if reason:
                audit.append({"paper_id": pid, "record_id": record["id"],
                              "proposed_modality": proposed,
                              "proposed_modality_evidence": evidence,
                              "reason": reason, "final_modality": "unspecified"})
                modality, evidence = "unspecified", []
            record["modality"] = modality
            record["modality_evidence"] = evidence
    return result, audit


def main(source_path, raw_path, output_path):
    output = Path(output_path)
    audit_path = Path(str(output) + ".audit.json")
    if output.exists() or audit_path.exists():
        raise FileExistsError("Refusing to overwrite output or audit")
    papers = json.loads(Path(source_path).read_text(encoding="utf-8"))
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    result, audit = guard(papers, raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    for path, value in ((output, result), (audit_path, audit)):
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"papers": len(result), "modality_adjustments": len(audit)}))


if __name__ == "__main__":
    main(*sys.argv[1:])
