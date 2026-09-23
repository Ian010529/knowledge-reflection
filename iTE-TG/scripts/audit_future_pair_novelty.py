from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import pandas as pd


ROOT = Path("/Users/ryan/Documents/iTE&TG")
DATA = ROOT / "minimal_clean_concept_layer"
PRED = ROOT / "minimal_clean_predictions" / "future_unseen"


def normalized_terms(value: str) -> set[str]:
    value = str(value).strip()
    terms = {value}
    without_parentheses = re.sub(r"\s*\([^)]*\)", "", value).strip()
    if without_parentheses:
        terms.add(without_parentheses)
    return {
        term.casefold()
        for term in terms
        if 2 <= len(term) <= 70 and term.count(" ") <= 8
    }


def build_term_lookup(vocab: pd.DataFrame) -> dict[str, list[str]]:
    aliases = pd.read_csv(ROOT / "final_concept_layer" / "final_concept_alias_map.csv")
    merge = pd.read_csv(DATA / "prediction_family_merge_map.csv")
    remap = dict(zip(merge.source_concept_id, merge.target_concept_id))
    valid = set(vocab.concept_id)
    terms: dict[str, set[str]] = defaultdict(set)
    for row in vocab.itertuples(index=False):
        terms[row.concept_id].update(normalized_terms(row.canonical_concept))
    for row in aliases.itertuples(index=False):
        concept_id = remap.get(row.concept_id, row.concept_id)
        if concept_id in valid:
            terms[concept_id].update(normalized_terms(row.alias))

    manual = {
        "ionic thermodiffusion (Soret effect)": [
            "soret effect", "thermodiffusion", "ionic thermal diffusion"
        ],
        "poly(vinyl alcohol) (PVA)": ["polyvinyl alcohol", "pva"],
        "polyacrylamide (PAM)": ["polyacrylamide", "pam"],
        "gelatin-based polymer family": ["gelatin", "gelma"],
        "ethylene glycol": ["ethylene glycol"],
        "guanidinium chloride (GdmCl)": [
            "guanidinium chloride", "guanidine hydrochloride", "gdmcl", "guhcl"
        ],
        "carbon nanotube family": [
            "carbon nanotube", "cnt", "cnts", "swcnt", "mwcnt"
        ],
    }
    label_to_id = dict(zip(vocab.canonical_concept, vocab.concept_id))
    for label, values in manual.items():
        if label in label_to_id:
            terms[label_to_id[label]].update(value.casefold() for value in values)
    return {
        concept_id: sorted(values, key=len, reverse=True)
        for concept_id, values in terms.items()
    }


def term_present(text: str, term: str) -> bool:
    if len(term) <= 4 and term.isalnum():
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
    return term in text


def augmented_edges(
    papers: pd.DataFrame,
    mapping: pd.DataFrame,
    terms: dict[str, list[str]],
) -> tuple[set[tuple[str, str]], dict[tuple[str, str], str]]:
    mapped = mapping.groupby("paper_id").concept_id.agg(set).to_dict()
    edges: set[tuple[str, str]] = set()
    evidence: dict[tuple[str, str], str] = {}
    fields = ["title", "abstract", "material_raw", "mechanism_raw"]
    for paper in papers.itertuples(index=False):
        text = " ".join(str(getattr(paper, field, "")) for field in fields).casefold()
        found = set(mapped.get(paper.paper_id, set()))
        for concept_id, aliases in terms.items():
            if concept_id in found:
                continue
            if any(term_present(text, alias) for alias in aliases):
                found.add(concept_id)
        for pair in combinations(sorted(found), 2):
            edges.add(pair)
            evidence.setdefault(pair, paper.paper_id)
    return edges, evidence


def filter_predictions(
    filename: str,
    prefix: str,
    papers: pd.DataFrame,
    mapping: pd.DataFrame,
    terms: dict[str, list[str]],
) -> pd.DataFrame:
    predictions = pd.read_csv(PRED / filename)
    edges, evidence = augmented_edges(papers, mapping, terms)
    pairs = [
        tuple(sorted((row.concept_u_id, row.concept_v_id)))
        for row in predictions.itertuples(index=False)
    ]
    predictions["raw_corpus_pair_found"] = [pair in edges for pair in pairs]
    predictions["raw_corpus_evidence_paper_id"] = [
        evidence.get(pair, "") for pair in pairs
    ]
    audited = predictions[~predictions.raw_corpus_pair_found].copy()
    audited = audited.reset_index(drop=True)
    audited["novelty_audited_rank"] = range(1, len(audited) + 1)
    predictions.to_csv(PRED / f"{prefix}_novelty_audit_all.csv", index=False)
    audited.to_csv(PRED / f"{prefix}_novelty_audited_candidates.csv", index=False)
    audited.head(100).to_csv(PRED / f"{prefix}_novelty_audited_top100.csv", index=False)
    return audited


def main() -> None:
    vocab = pd.read_csv(DATA / "final_concept_vocabulary.csv")
    mapping = pd.read_csv(DATA / "final_paper_concept_map.csv")
    papers = pd.read_csv(DATA / "final_paper_index.csv").fillna("")
    terms = build_term_lookup(vocab)

    tg_ids = set(
        papers[papers.source_membership.str.contains("TG", na=False)].paper_id
    )
    tg_papers = papers[papers.paper_id.isin(tg_ids)]
    tg_mapping = mapping[mapping.paper_id.isin(tg_ids)]

    ite_audited = filter_predictions(
        "ite_to_tg_future_all_unseen_pairs.csv",
        "ite_to_tg",
        tg_papers,
        tg_mapping,
        terms,
    )
    tg_audited = filter_predictions(
        "tg_to_tg_future_all_unseen_pairs.csv",
        "tg_to_tg",
        tg_papers,
        tg_mapping,
        terms,
    )
    print(
        pd.DataFrame(
            [
                {"task": "iTE_to_TG", "audited_candidates": len(ite_audited)},
                {"task": "TG_to_TG", "audited_candidates": len(tg_audited)},
            ]
        ).to_string(index=False)
    )


if __name__ == "__main__":
    main()
