from collections import defaultdict
from itertools import combinations
from pathlib import Path
import math
import re
import sys

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler


sys.path.insert(0, "/Users/ryan/Documents/Codex/2026-07-20/t-he/work")
import tg_adoption_prediction_demo as curated


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
DATA_DIR = Path("/Users/ryan/Documents/Codex/2026-07-15/r/work")
OUT = ROOT / "work" / "ite_experiment_suite"
OUT.mkdir(exist_ok=True)

ITE_SOURCES = ["iTE1", "iTE2"]

FEATURE_COLS = [
    "u_degree_all",
    "v_degree_all",
    "u_degree_tg",
    "v_degree_tg",
    "u_degree_ite",
    "v_degree_ite",
    "common_neighbors",
    "adamic_adar",
    "preferential_attachment",
    "shortest_path",
    "semantic_similarity",
    "cross_type",
    "ite_lead_years_for_u",
    "u_seen_in_ite",
    "u_seen_in_tg",
    "v_seen_in_tg",
]

STOP = {
    "the", "and", "for", "with", "from", "into", "onto", "this", "that", "these", "those", "their",
    "using", "based", "enabled", "effect", "effects", "study", "studies", "performance", "high",
    "low", "grade", "heat", "thermal", "thermoelectric", "ionic", "thermocell", "device", "devices",
    "energy", "harvesting", "power", "generation", "materials", "material", "properties", "property",
}

DOMAIN_WORDS = re.compile(
    r"redox|ion|ionic|cation|anion|solvation|hydration|entropy|soret|thermodiffusion|"
    r"diffusion|migration|transport|hydrogel|ionogel|eutogel|eutectic|polymer|"
    r"cellulose|mxene|pedot|pva|pam|gelatin|gelma|electrode|interface|charge-transfer|"
    r"crystallization|phase|water|moisture|humidity|nanochannel|channel|complexation|"
    r"coordination|anti-freez|antifreez|organohydrogel|chaotropic|photothermal|"
    r"refrigeration|thermal charging|liquid|solvent|membrane|selective|conductivity"
)


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"[^a-z0-9+\-/():., ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,.;:")


def read_ite_papers():
    frames = [
        curated.read_source(DATA_DIR / "iTE1_first1000_material_mechanism.csv", "iTE1"),
        curated.read_source(DATA_DIR / "iTE2_first711_material_mechanism.csv", "iTE2"),
    ]
    papers = pd.concat(frames, ignore_index=True)
    return papers[papers["year"].between(1990, 2026)].copy()


def normalize_phrase(phrase):
    phrase = clean_text(phrase)
    phrase = re.sub(r"^(a|an|the|novel|high-performance|high performance|efficient|enhanced)\s+", "", phrase)
    phrase = re.sub(r"\b(low-grade heat|energy harvesting|thermoelectric performance|power density)\b", " ", phrase)
    phrase = re.sub(r"\s+", " ", phrase).strip(" ,.;:-")
    words = phrase.split()
    while words and words[0] in STOP:
        words = words[1:]
    while words and words[-1] in STOP:
        words = words[:-1]
    return " ".join(words)


def phrase_type(phrase):
    if phrase in curated.MANUAL_CONCEPTS:
        return curated.MANUAL_CONCEPTS[phrase][0]
    return curated.concept_type(phrase)


def extract_open_phrases_from_row(row):
    text_fields = [
        clean_text(row.material),
        clean_text(row.mechanism),
        clean_text(row.title),
    ]
    full = ". ".join(text_fields)
    out = set()

    # Keep the curated concepts as the interpretable backbone.
    for c, _typ in curated.extract_phrases(row).items():
        out.add(c)

    clauses = re.split(r";|\.|,| while | whereas | through | via | by | due to | enabled by | using | with | and ", full)
    for clause in clauses:
        clause = normalize_phrase(clause)
        if not clause or not DOMAIN_WORDS.search(clause):
            continue
        words = clause.split()
        if 2 <= len(words) <= 8 and 10 <= len(clause) <= 88:
            out.add(clause)
        # Also keep compact n-grams around domain terms.
        if 4 <= len(words) <= 18:
            for n in [2, 3, 4, 5]:
                for i in range(0, len(words) - n + 1):
                    gram = normalize_phrase(" ".join(words[i : i + n]))
                    if 10 <= len(gram) <= 70 and DOMAIN_WORDS.search(gram):
                        out.add(gram)

    return {p for p in out if p not in curated.GENERIC and len(p.split()) >= 2}


def make_open_concepts(papers, min_freq=2, max_freq=120, max_concepts=500):
    rows = []
    for row in papers.itertuples():
        for concept in extract_open_phrases_from_row(row):
            rows.append(
                {
                    "paper_id": row.paper_id,
                    "source": row.source,
                    "year": row.year,
                    "title": row.title,
                    "doi": row.doi,
                    "concept": concept,
                    "concept_type": phrase_type(concept),
                }
            )
    pc = pd.DataFrame(rows).drop_duplicates(["paper_id", "concept"])
    counts = pc.groupby("concept")["paper_id"].nunique()
    keep = counts[(counts >= min_freq) & (counts <= max_freq)].index
    pc = pc[pc["concept"].isin(keep)].copy()

    # Prefer concepts with repeated use, domain specificity and moderate length.
    counts = pc.groupby("concept")["paper_id"].nunique()
    score = {}
    for concept, n in counts.items():
        specificity = sum(1 for w in concept.split() if w not in STOP)
        score[concept] = math.log1p(n) * (1 + min(specificity, 6) / 6)
    selected = [c for c, _ in sorted(score.items(), key=lambda kv: kv[1], reverse=True)[:max_concepts]]
    return pc[pc["concept"].isin(selected)].copy()


def make_curated_ite_concepts():
    _, pc = curated.make_paper_concepts()
    return pc[pc["source"].isin(ITE_SOURCES)].copy()


def graph_until(pc, cutoff):
    return curated.graph_until(pc, cutoff, ITE_SOURCES)


def concept_counts(pc, cutoff, min_count):
    d = pc[(pc["year"] <= cutoff) & (pc["source"].isin(ITE_SOURCES))]
    counts = d.groupby("concept")["paper_id"].nunique().to_dict()
    typ = d.groupby("concept")["concept_type"].agg(lambda x: x.value_counts().idxmax()).to_dict()
    concepts = [
        c
        for c, n in counts.items()
        if n >= min_count
        and n <= 150
        and c not in curated.GENERIC
        and c not in curated.BACKGROUND_ONLY_CONCEPTS
    ]
    return sorted(concepts), counts, typ


def edge_lookup(pc, start, end):
    d = pc[(pc["source"].isin(ITE_SOURCES)) & (pc["year"].between(start, end))]
    edges = {}
    for _, g in d.groupby("paper_id"):
        concepts = sorted(g["concept"].unique())
        title = g["title"].iloc[0]
        for u, v in combinations(concepts, 2):
            edges.setdefault((u, v), title)
    return edges


def pair_features(pc, cutoff, concepts, typ, G_ite, sims, idx, u, v):
    G_all = G_ite

    def deg(c):
        return G_ite.degree(c) if c in G_ite else 0

    common = len(list(nx.common_neighbors(G_ite, u, v))) if u in G_ite and v in G_ite else 0
    try:
        dist = nx.shortest_path_length(G_ite, u, v) if u in G_ite and v in G_ite else 99
    except nx.NetworkXNoPath:
        dist = 99
    try:
        aa = next(nx.adamic_adar_index(G_ite, [(u, v)]))[2] if u in G_ite and v in G_ite else 0
    except ZeroDivisionError:
        aa = 0
    sim = sims[idx[u], idx[v]]
    return {
        "u_degree_all": deg(u),
        "v_degree_all": deg(v),
        "u_degree_tg": 0,
        "v_degree_tg": 0,
        "u_degree_ite": deg(u),
        "v_degree_ite": deg(v),
        "common_neighbors": common,
        "adamic_adar": aa,
        "preferential_attachment": deg(u) * deg(v),
        "shortest_path": min(dist, 12),
        "semantic_similarity": sim,
        "cross_type": int(typ.get(u) != typ.get(v)),
        "ite_lead_years_for_u": 0,
        "u_seen_in_ite": int(deg(u) > 0),
        "u_seen_in_tg": 0,
        "v_seen_in_tg": 0,
        "dprev": min(dist, 12),
    }


def candidate_pairs(pc, cutoff, policy, min_count, max_pairs=25000):
    concepts, counts, typ = concept_counts(pc, cutoff, min_count)
    if len(concepts) < 2:
        return pd.DataFrame()
    idx, sims = curated.build_embeddings(concepts)
    G = graph_until(pc, cutoff)
    rows = []
    for u, v in combinations(concepts, 2):
        if G.has_edge(u, v):
            continue
        feats = pair_features(pc, cutoff, concepts, typ, G, sims, idx, u, v)
        sim = feats["semantic_similarity"]
        dprev = feats["dprev"]
        if policy == "frontier":
            if dprev > 4 and sim < 0.06:
                continue
        elif policy == "dprev23":
            if dprev not in {2, 3}:
                continue
        elif policy == "broad":
            if dprev > 8 and sim < 0.03:
                continue
        else:
            raise ValueError(policy)
        rows.append(
            {
                "cutoff_year": cutoff,
                "concept_u": u,
                "concept_v": v,
                "u_type": typ.get(u),
                "v_type": typ.get(v),
                **feats,
            }
        )
    df = pd.DataFrame(rows)
    if len(df) > max_pairs:
        df["_frontier_score"] = (
            2.0 * df["common_neighbors"]
            + 1.4 * df["adamic_adar"].rank(pct=True)
            + 8.0 * df["semantic_similarity"]
            - 0.25 * df["shortest_path"]
            + 0.02 * df["preferential_attachment"].rank(pct=True)
        )
        df = df.sort_values("_frontier_score", ascending=False).head(max_pairs).drop(columns="_frontier_score")
    return df


def label_samples(pc, samples, horizon):
    start, end = horizon
    future_edges = edge_lookup(pc, start, end)
    past_edges = edge_lookup(pc, 1900, start - 1)
    labels, titles = [], []
    for r in samples.itertuples():
        key = tuple(sorted([r.concept_u, r.concept_v]))
        if key in past_edges:
            y, title = 0, ""
        elif key in future_edges:
            y, title = 1, future_edges[key]
        else:
            y, title = 0, ""
        labels.append(y)
        titles.append(title)
    out = samples.copy()
    out["future_edge_label"] = labels
    out["future_example_title"] = titles
    out["future_window"] = f"{start}-{end}"
    return out


def graph_rank_score(df):
    rank = lambda s: s.fillna(0).rank(pct=True).to_numpy()
    return (
        1.0 * rank(df["preferential_attachment"])
        + 0.35 * rank(df["adamic_adar"])
        + 0.25 * rank(df["common_neighbors"])
        + 0.15 * rank(-df["shortest_path"])
        + 0.10 * rank(df["semantic_similarity"])
    )


def fit_score(train, test):
    X_train = train[FEATURE_COLS].fillna(0).to_numpy()
    y_train = train["future_edge_label"].astype(int).to_numpy()
    X_test = test[FEATURE_COLS].fillna(0).to_numpy()
    y_test = test["future_edge_label"].astype(int).to_numpy()

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    lr = LogisticRegression(C=1.0, class_weight="balanced", max_iter=3000, random_state=19)
    lr.fit(X_train_s, y_train)
    lr_pred = lr.predict_proba(X_test_s)[:, 1]

    rf = RandomForestClassifier(
        n_estimators=250,
        min_samples_leaf=6,
        max_features=1.0,
        class_weight="balanced_subsample",
        random_state=19,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    rf_pred = rf.predict_proba(X_test)[:, 1]
    ml = 0.35 * lr_pred + 0.65 * rf_pred
    graph = graph_rank_score(test)
    hybrid = 0.35 * pd.Series(graph).rank(pct=True).to_numpy() + 0.65 * pd.Series(ml).rank(pct=True).to_numpy()

    scores = {"ml": ml, "graph": graph, "hybrid": hybrid}
    rows = []
    for name, score in scores.items():
        row = {
            "model": name,
            "roc_auc": roc_auc_score(y_test, score) if len(set(y_test)) > 1 else np.nan,
            "average_precision": average_precision_score(y_test, score) if len(set(y_test)) > 1 else np.nan,
        }
        for k in [10, 25, 50, 100]:
            idx = np.argsort(score)[::-1][: min(k, len(score))]
            row[f"precision_at_{k}"] = float(y_test[idx].mean()) if len(idx) else np.nan
            row[f"hits_at_{k}"] = int(y_test[idx].sum()) if len(idx) else 0
        rows.append(row)
    scored = test.copy()
    for name, score in scores.items():
        scored[f"{name}_score"] = score
    return pd.DataFrame(rows), scored


def run_one(name, pc, policy, min_count):
    train_parts = []
    win_rows = []
    for cutoff in range(2014, 2022):
        horizon = (cutoff + 1, min(cutoff + 3, 2023))
        cand = candidate_pairs(pc, cutoff, policy, min_count)
        if cand.empty:
            continue
        labelled = label_samples(pc, cand, horizon)
        train_parts.append(labelled)
        win_rows.append(
            {
                "cutoff_year": cutoff,
                "n_samples": len(labelled),
                "n_positive": int(labelled["future_edge_label"].sum()),
                "positive_rate": float(labelled["future_edge_label"].mean()) if len(labelled) else 0,
            }
        )
    if not train_parts:
        return None, None, None
    train = pd.concat(train_parts, ignore_index=True).drop_duplicates(["cutoff_year", "concept_u", "concept_v"])
    test = label_samples(pc, candidate_pairs(pc, 2022, policy, min_count), (2023, 2026))
    if train["future_edge_label"].sum() < 2 or test["future_edge_label"].sum() < 2:
        return None, train, test
    metrics, scored = fit_score(train, test)
    for col, val in [
        ("experiment", name),
        ("policy", policy),
        ("min_count", min_count),
        ("n_concepts", pc["concept"].nunique()),
        ("n_train", len(train)),
        ("train_positive", int(train["future_edge_label"].sum())),
        ("n_test", len(test)),
        ("test_positive", int(test["future_edge_label"].sum())),
        ("test_positive_rate", float(test["future_edge_label"].mean())),
    ]:
        metrics[col] = val
    scored.to_csv(OUT / f"{name}_{policy}_min{min_count}_scored.csv", index=False)
    pd.DataFrame(win_rows).to_csv(OUT / f"{name}_{policy}_min{min_count}_windows.csv", index=False)

    # dprev stratification for the hybrid score.
    strat = []
    for bucket, sub in scored.groupby("dprev"):
        if len(sub) < 5 or sub["future_edge_label"].nunique() < 2:
            continue
        y = sub["future_edge_label"].astype(int).to_numpy()
        s = sub["hybrid_score"].to_numpy()
        row = {
            "experiment": name,
            "policy": policy,
            "min_count": min_count,
            "dprev": bucket,
            "n": len(sub),
            "positive": int(y.sum()),
            "positive_rate": float(y.mean()),
            "hybrid_auc": roc_auc_score(y, s),
            "hybrid_ap": average_precision_score(y, s),
        }
        for k in [10, 25, 50]:
            idx = np.argsort(s)[::-1][: min(k, len(s))]
            row[f"hybrid_p_at_{k}"] = float(y[idx].mean())
            row[f"hybrid_hits_at_{k}"] = int(y[idx].sum())
        strat.append(row)
    pd.DataFrame(strat).to_csv(OUT / f"{name}_{policy}_min{min_count}_dprev_strat.csv", index=False)
    return metrics, train, test


def main():
    papers = read_ite_papers()
    curated_pc = make_curated_ite_concepts()
    open300_pc = make_open_concepts(papers, min_freq=2, max_freq=120, max_concepts=300)
    open600_pc = make_open_concepts(papers, min_freq=2, max_freq=120, max_concepts=600)
    curated_pc.to_csv(OUT / "concepts_curated.csv", index=False)
    open300_pc.to_csv(OUT / "concepts_open300.csv", index=False)
    open600_pc.to_csv(OUT / "concepts_open600.csv", index=False)

    configs = [
        ("curated", curated_pc, "frontier", 2),
        ("curated", curated_pc, "dprev23", 2),
        ("curated", curated_pc, "broad", 2),
        ("open300", open300_pc, "frontier", 2),
        ("open300", open300_pc, "dprev23", 2),
        ("open300", open300_pc, "broad", 2),
        # open600 is written to disk for later inspection, but full multi-window
        # modelling is too slow and noisy for this first comparison.
    ]

    all_metrics = []
    for name, pc, policy, min_count in configs:
        print("RUN", name, policy, min_count, "concepts", pc["concept"].nunique())
        metrics, _train, _test = run_one(name, pc, policy, min_count)
        if metrics is not None:
            all_metrics.append(metrics)
    if all_metrics:
        summary = pd.concat(all_metrics, ignore_index=True)
        cols = [
            "experiment", "policy", "min_count", "model", "n_concepts", "n_train", "train_positive",
            "n_test", "test_positive", "test_positive_rate", "roc_auc", "average_precision",
            "precision_at_10", "hits_at_10", "precision_at_25", "hits_at_25",
            "precision_at_50", "hits_at_50", "precision_at_100", "hits_at_100",
        ]
        summary = summary[cols].sort_values(["precision_at_25", "average_precision", "roc_auc"], ascending=False)
        summary.to_csv(OUT / "ite_experiment_summary.csv", index=False)
        print(summary.to_string(index=False))
        strat_files = list(OUT.glob("*_dprev_strat.csv"))
        if strat_files:
            pd.concat([pd.read_csv(p) for p in strat_files if p.stat().st_size > 1], ignore_index=True).to_csv(
                OUT / "ite_experiment_dprev_summary.csv", index=False
            )
    print("outputs", OUT)


if __name__ == "__main__":
    main()
