from __future__ import annotations

import hashlib
import json
import re
from itertools import combinations
from pathlib import Path

import pandas as pd


ROOT = Path("/Users/ryan/Documents/iTE&TG")
SOURCE = ROOT / "final_concept_layer"
OUT = ROOT / "minimal_clean_concept_layer"
OUT.mkdir(exist_ok=True)


def concept_id(label: str) -> str:
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:10].upper()
    return f"C{digest}"


FAMILY_RULES = [
    {
        "canonical": "ferri/ferrocyanide family",
        "type": "material_entity",
        "subtype": "redox couple family",
        "pattern": r"ferri.?ferrocyanide|ferricyanide|ferrocyanide|\[?fe\s*\(\s*cn\s*\)\s*6\]?|k3fe\s*\(\s*cn\s*\)\s*6|k4fe\s*\(\s*cn\s*\)\s*6",
        "collapse": r"ferri/ferrocyanide$|\[Fe\(CN\)6\]|K3Fe\(CN\)6|K4Fe\(CN\)6",
    },
    {
        "canonical": "PEDOT family",
        "type": "material_entity",
        "subtype": "conducting polymer family",
        "pattern": r"\bPEDOT(?::PSS|-PSS|-Tos)?\b|poly\s*\(\s*3,?4-ethylenedioxythiophene\s*\)",
        "collapse": r"^PEDOT$|^PEDOT:PSS$",
    },
    {
        "canonical": "gelatin-based polymer family",
        "type": "material_entity",
        "subtype": "biopolymer family",
        "pattern": r"\bgelatin\b|\bGelMA\b|gelatin methacryloyl|gelatin methacrylate",
        "collapse": r"^gelatin$",
    },
    {
        "canonical": "carbon nanotube family",
        "type": "material_entity",
        "subtype": "carbon material family",
        "pattern": r"carbon nanotube|\bCNTs?\b|\bSWCNTs?\b|\bMWCNTs?\b",
        "collapse": r"^carbon nanotube$",
    },
    {
        "canonical": "dynamic crosslinked gel network",
        "type": "gel_microstructure",
        "subtype": "network structure",
        "pattern": r"dynamic[- ]crosslink|dynamic covalent|reversible crosslink|self[- ]heal(?:ing)? network",
        "collapse": r"^dynamic crosslinked gel network$|^dynamic crosslinking$",
    },
]

SUPPLEMENT_RULES = [
    {
        "canonical": "guanidinium chloride (GdmCl)",
        "pattern": r"guanidinium chloride|guanidine hydrochloride|\bGdmCl\b|\bGuHCl\b",
    },
    {
        "canonical": "Hofmeister/chaotropic effect",
        "pattern": r"Hofmeister|chaotrop|kosmotrop|specific[- ]ion effect",
    },
    {
        "canonical": "ionic thermodiffusion (Soret effect)",
        "pattern": r"\bSoret\b|thermodiffusion|thermal diffusion of ions?|ionic thermal diffusion",
    },
    {
        "canonical": "iodide/triiodide",
        "pattern": r"iodide.?triiodide|triiodide.?iodide|\bI\s*[-−]\s*/\s*I3\s*[-−]|\bI3\s*[-−]",
    },
    {
        "canonical": "ferri/ferrocyanide redox chemistry",
        "pattern": r"ferri.?ferrocyanide|ferricyanide.?ferrocyanide|Fe\s*\(\s*CN\s*\)\s*6.*redox",
    },
]

# Manual adjudication of matches found only in the abstract. Only ``core`` rows
# become positive concept links; the other roles remain in the audit table.
ABSTRACT_REVIEW = {
    # Ferri/ferrocyanide is the studied redox chemistry.
    **{
        (paper_id, "ferri/ferrocyanide redox chemistry"): (
            "core",
            "Fe(CN)6 redox chemistry is part of the studied thermogalvanic system.",
        )
        for paper_id in [
            "P0016", "P0023", "P0031", "P0043", "P0048", "P0056", "P0061",
            "P0083", "P0084", "P0133", "P0191", "P0219", "P0231", "P0278",
            "P0332", "P1614",
        ]
    },
    # Ferri/ferrocyanide is only a canonical comparator for another chemistry.
    ("P0020", "ferri/ferrocyanide family"): (
        "background_comparison",
        "The studied couple is Ni(bpy)3; Fe(CN)6 is only the canonical benchmark.",
    ),
    ("P0020", "ferri/ferrocyanide redox chemistry"): (
        "background_comparison",
        "The studied couple is Ni(bpy)3; Fe(CN)6 is only the canonical benchmark.",
    ),
    ("P0160", "ferri/ferrocyanide family"): (
        "background_comparison",
        "Ferrocyanide is cited as a state-of-the-art comparator, not the cell chemistry.",
    ),
    ("P0195", "ferri/ferrocyanide family"): (
        "background_comparison",
        "Ferricyanide is a performance reference for the host-guest redox system.",
    ),
    # Soret/thermodiffusion is an investigated or operative mechanism.
    **{
        (paper_id, "ionic thermodiffusion (Soret effect)"): (
            "core",
            "Ion thermodiffusion is an operative or directly investigated mechanism.",
        )
        for paper_id in [
            "P0212", "P0245", "P0310", "P0347", "P0353", "P0367", "P0379",
            "P0401", "P0463", "P0497", "P0530", "P0578", "P0589", "P0681",
            "P0684", "P0713", "P0821", "P0878", "P0972", "P1316", "P1404",
            "P1542", "P1700",
        ]
    },
    ("P0220", "ionic thermodiffusion (Soret effect)"): (
        "background_comparison",
        "The proposed homogeneous-temperature mechanism is contrasted with Soret operation.",
    ),
    ("P0524", "ionic thermodiffusion (Soret effect)"): (
        "background_comparison",
        "Soret conversion is introductory context for a gradient-independent mechanism.",
    ),
    ("P0645", "ionic thermodiffusion (Soret effect)"): (
        "mechanism_rejected",
        "Operando measurements conclude that Zn migration is electrochemical, not thermodiffusive.",
    ),
    # Carbon nanotubes are physically used or tested in the reported system.
    **{
        (paper_id, "carbon nanotube family"): (
            "core",
            "Carbon nanotubes are an experimentally used electrode/material component.",
        )
        for paper_id in ["P0320", "P0398", "P1553"]
    },
    ("P1938", "carbon nanotube family"): (
        "excluded_out_of_scope",
        "MWCNT is one tested modifier in a non-iTE analytical sensor paper.",
    ),
    ("P0423", "Hofmeister/chaotropic effect"): (
        "core",
        "Specific-ion salting-in/salting-out behavior is part of the studied mechanism.",
    ),
}


def evidence_match(
    paper: pd.Series,
    pattern: str,
    fields: tuple[str, ...] = ("title", "material_raw", "mechanism_raw"),
) -> tuple[str, str] | None:
    compiled = re.compile(pattern, re.I)
    for field in fields:
        text = "" if pd.isna(paper[field]) else str(paper[field])
        match = compiled.search(text)
        if match:
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 140)
            return field, text[start:end]
    return None


def main() -> None:
    vocab = pd.read_csv(SOURCE / "final_concept_vocabulary.csv")
    mapping = pd.read_csv(SOURCE / "final_paper_concept_map.csv")
    papers = pd.read_csv(SOURCE / "final_paper_index.csv")
    aliases = pd.read_csv(SOURCE / "final_concept_alias_map.csv")

    core = vocab[vocab["graph_role"] == "prediction_core"].copy()
    id_to_family: dict[str, dict] = {}
    family_rows = []
    merge_rows = []
    for rule in FAMILY_RULES:
        family_id = concept_id(rule["canonical"])
        matched = core[
            core["canonical_concept"].str.contains(
                rule["collapse"], case=False, regex=True, na=False
            )
        ]
        for row in matched.itertuples(index=False):
            id_to_family[row.concept_id] = {
                "concept_id": family_id,
                "canonical_concept": rule["canonical"],
                "concept_type": rule["type"],
                "concept_subtype": rule["subtype"],
            }
            merge_rows.append(
                {
                    "source_concept_id": row.concept_id,
                    "source_concept": row.canonical_concept,
                    "target_concept_id": family_id,
                    "target_concept": rule["canonical"],
                    "relationship": "prediction_family_collapse",
                }
            )
        family_rows.append(
            {
                "concept_id": family_id,
                "canonical_concept": rule["canonical"],
                "concept_type": rule["type"],
                "concept_subtype": rule["subtype"],
                "parent_domain": "materials and chemical species"
                if rule["type"] == "material_entity"
                else "soft-material structure",
                "graph_role": "prediction_core",
                "prediction_eligible": True,
                "evidence_only": False,
            }
        )

    clean = mapping.copy()
    for source_id, target in id_to_family.items():
        mask = clean["concept_id"] == source_id
        for column, value in target.items():
            clean.loc[mask, column] = value
        clean.loc[mask, "extraction_method"] = (
            clean.loc[mask, "extraction_method"].astype(str)
            + "+prediction_family_collapse"
        )

    supplemental_lookup = {
        row.canonical_concept: row
        for row in core.itertuples(index=False)
    }
    added_rows = []
    audit_rows = []
    abstract_review_rows = []
    all_rules = [
        {
            "canonical": rule["canonical"],
            "pattern": rule["pattern"],
            "target": {
                "concept_id": concept_id(rule["canonical"]),
                "canonical_concept": rule["canonical"],
                "concept_type": rule["type"],
                "concept_subtype": rule["subtype"],
            },
            "rule_kind": "family_recall",
        }
        for rule in FAMILY_RULES
    ]
    for rule in SUPPLEMENT_RULES:
        existing = supplemental_lookup.get(rule["canonical"])
        if existing is None:
            continue
        all_rules.append(
            {
                "canonical": rule["canonical"],
                "pattern": rule["pattern"],
                "target": {
                    "concept_id": existing.concept_id,
                    "canonical_concept": existing.canonical_concept,
                    "concept_type": existing.concept_type,
                    "concept_subtype": existing.concept_subtype,
                },
                "rule_kind": "synonym_recall",
            }
        )

    existing_pairs = set(zip(clean["paper_id"], clean["concept_id"]))
    for paper in papers.itertuples(index=False):
        paper_series = pd.Series(paper._asdict())
        for rule in all_rules:
            evidence = evidence_match(paper_series, rule["pattern"])
            if evidence is None:
                abstract_evidence = evidence_match(
                    paper_series, rule["pattern"], fields=("abstract",)
                )
                if abstract_evidence is not None:
                    field, snippet = abstract_evidence
                    target = rule["target"]
                    key = (paper.paper_id, target["concept_id"])
                    was_existing = key in existing_pairs
                    decision, rationale = ABSTRACT_REVIEW.get(
                        (paper.paper_id, rule["canonical"]),
                        ("unresolved", "No manual decision recorded."),
                    )
                    abstract_review_rows.append(
                        {
                            "paper_id": paper.paper_id,
                            "year": paper.year,
                            "source_membership": paper.source_membership,
                            "canonical_concept": rule["canonical"],
                            "evidence_field": field,
                            "evidence_text": snippet,
                            "decision": decision,
                            "rationale": rationale,
                            "mapping_status": (
                                "already_mapped_core"
                                if decision == "core" and was_existing
                                else "added_core"
                                if decision == "core"
                                else "not_added"
                            ),
                        }
                    )
                    if decision == "core":
                        if key not in existing_pairs:
                            added_rows.append(
                                {
                                    "paper_id": paper.paper_id,
                                    "concept_id": target["concept_id"],
                                    "canonical_concept": target["canonical_concept"],
                                    "concept_type": target["concept_type"],
                                    "concept_subtype": target["concept_subtype"],
                                    "evidence_field": field,
                                    "evidence_text": snippet,
                                    "extraction_method": "manual_abstract_adjudication",
                                    "confidence": 0.92,
                                }
                            )
                            existing_pairs.add(key)
                continue
            field, snippet = evidence
            target = rule["target"]
            key = (paper.paper_id, target["concept_id"])
            was_existing = key in existing_pairs
            audit_rows.append(
                {
                    "paper_id": paper.paper_id,
                    "year": paper.year,
                    "source_membership": paper.source_membership,
                    "concept_id": target["concept_id"],
                    "canonical_concept": target["canonical_concept"],
                    "evidence_field": field,
                    "evidence_text": snippet,
                    "rule_kind": rule["rule_kind"],
                    "mapping_status": "already_mapped" if was_existing else "added",
                }
            )
            if was_existing:
                continue
            added_rows.append(
                {
                    "paper_id": paper.paper_id,
                    "concept_id": target["concept_id"],
                    "canonical_concept": target["canonical_concept"],
                    "concept_type": target["concept_type"],
                    "concept_subtype": target["concept_subtype"],
                    "evidence_field": field,
                    "evidence_text": snippet,
                    "extraction_method": f"minimal_clean_{rule['rule_kind']}",
                    "confidence": 0.96 if field != "abstract" else 0.90,
                }
            )
            existing_pairs.add(key)

    if added_rows:
        clean = pd.concat([clean, pd.DataFrame(added_rows)], ignore_index=True)
    clean = clean.sort_values(
        ["paper_id", "concept_id", "confidence"], ascending=[True, True, False]
    ).drop_duplicates(["paper_id", "concept_id"], keep="first")

    clean_vocab = core[~core["concept_id"].isin(id_to_family)].copy()
    family_frame = pd.DataFrame(family_rows)
    for column in clean_vocab.columns:
        if column not in family_frame:
            family_frame[column] = pd.NA
    clean_vocab = pd.concat(
        [clean_vocab, family_frame[clean_vocab.columns]], ignore_index=True
    )
    stats = (
        clean.groupby("concept_id")
        .agg(
            document_frequency=("paper_id", "nunique"),
            max_confidence=("confidence", "max"),
        )
        .reset_index()
    )
    source_lookup = papers.set_index("paper_id")["source_membership"].to_dict()
    clean["_source"] = clean["paper_id"].map(source_lookup)
    domain_stats = []
    for cid, group in clean.groupby("concept_id"):
        domain_stats.append(
            {
                "concept_id": cid,
                "iTE_document_frequency": group[
                    group["_source"].str.contains("iTE", na=False)
                ]["paper_id"].nunique(),
                "TG_document_frequency": group[
                    group["_source"].str.contains("TG", na=False)
                ]["paper_id"].nunique(),
            }
        )
    clean = clean.drop(columns="_source")
    clean_vocab = clean_vocab.drop(
        columns=[
            "document_frequency",
            "iTE_document_frequency",
            "TG_document_frequency",
            "max_confidence",
        ],
        errors="ignore",
    ).merge(stats, on="concept_id", how="left").merge(
        pd.DataFrame(domain_stats), on="concept_id", how="left"
    )

    pair_rows = []
    mapped_with_year = clean.merge(
        papers[["paper_id", "year", "source_membership", "title"]],
        on="paper_id",
        how="left",
    )
    for paper_id, group in mapped_with_year.groupby("paper_id"):
        concepts = sorted(group["concept_id"].unique())
        if len(concepts) < 2:
            continue
        meta = group.iloc[0]
        label_lookup = group.drop_duplicates("concept_id").set_index(
            "concept_id"
        )["canonical_concept"].to_dict()
        for left, right in combinations(concepts, 2):
            pair_rows.append(
                {
                    "paper_id": paper_id,
                    "year": meta["year"],
                    "source_membership": meta["source_membership"],
                    "concept_u_id": left,
                    "concept_v_id": right,
                    "concept_u": label_lookup[left],
                    "concept_v": label_lookup[right],
                    "title": meta["title"],
                }
            )
    pair_evidence = pd.DataFrame(pair_rows)

    clean.to_csv(OUT / "clean_paper_concept_map.csv", index=False)
    clean_vocab.to_csv(OUT / "clean_prediction_vocabulary.csv", index=False)
    clean.to_csv(OUT / "final_paper_concept_map.csv", index=False)
    clean_vocab.to_csv(OUT / "final_concept_vocabulary.csv", index=False)
    pd.DataFrame(merge_rows).to_csv(OUT / "prediction_family_merge_map.csv", index=False)
    pd.DataFrame(audit_rows).to_csv(OUT / "supplemental_mapping_audit.csv", index=False)
    pd.DataFrame(abstract_review_rows).to_csv(
        OUT / "abstract_only_mapping_review.csv", index=False
    )
    pair_evidence.to_csv(OUT / "clean_pair_evidence.csv", index=False)
    papers.to_csv(OUT / "clean_paper_index.csv", index=False)
    papers.to_csv(OUT / "final_paper_index.csv", index=False)

    summary = {
        "original_core_concepts": int(len(core)),
        "clean_core_concepts": int(len(clean_vocab)),
        "original_paper_concept_links": int(len(mapping)),
        "clean_paper_concept_links": int(len(clean)),
        "family_collapsed_concepts": int(len(id_to_family)),
        "supplemental_links_added": int(
            (pd.DataFrame(audit_rows)["mapping_status"] == "added").sum()
        ),
        "abstract_only_rows_reviewed": int(len(abstract_review_rows)),
        "abstract_core_links_eligible": int(
            sum(row["decision"] == "core" for row in abstract_review_rows)
        ),
        "abstract_unresolved_rows": int(
            sum(row["decision"] == "unresolved" for row in abstract_review_rows)
        ),
        "pair_evidence_rows": int(len(pair_evidence)),
    }
    (OUT / "minimal_clean_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
