from itertools import combinations
from pathlib import Path
import sys

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_curve, roc_auc_score, roc_curve
from sklearn.preprocessing import StandardScaler
import matplotlib as mpl
import matplotlib.pyplot as plt


sys.path.insert(0, "/Users/ryan/Documents/Codex/2026-07-20/t-he/work")
import tg_adoption_prediction_demo as base


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
IN = ROOT / "work" / "open_concepts_iter" / "open_nmi_paper_concepts_1500.csv"
OUT = ROOT / "work" / "ite_self_nmi_clean_iter"
OUT.mkdir(exist_ok=True)

ITE_SOURCES = {"iTE1", "iTE2"}
FEATURE_COLS = base.FEATURE_COLS

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
    }
)


def load_pc():
    pc = pd.read_csv(IN)
    pc = pc[pc["source"].isin(ITE_SOURCES)].copy()
    pc = pc[pc["year"].between(1990, 2026)].copy()
    pc["graph_role"] = pc["graph_role"].fillna("background")
    return pc


def graph_until(pc, cutoff):
    return base.graph_until(pc, cutoff, list(ITE_SOURCES))


def concept_meta(pc, cutoff, min_count=2, max_count=150):
    d = pc[(pc["year"] <= cutoff) & (pc["source"].isin(ITE_SOURCES))]
    counts = d.groupby("concept")["paper_id"].nunique().to_dict()
    typ = d.groupby("concept")["concept_type"].agg(lambda x: x.value_counts().idxmax()).to_dict()
    role = d.groupby("concept")["graph_role"].agg(lambda x: x.value_counts().idxmax()).to_dict()
    candidates = sorted(
        c
        for c, n in counts.items()
        if min_count <= n <= max_count and role.get(c) == "recommendation_candidate"
    )
    return candidates, counts, typ


def edge_lookup(pc, start, end):
    d = pc[(pc["source"].isin(ITE_SOURCES)) & (pc["year"].between(start, end))]
    edges = {}
    for _, g in d.groupby("paper_id"):
        concepts = sorted(g["concept"].unique())
        title = g["title"].iloc[0]
        for u, v in combinations(concepts, 2):
            edges.setdefault((u, v), title)
    return edges


def graph_score(df):
    rank = lambda s: s.fillna(0).rank(pct=True).to_numpy()
    return (
        1.0 * rank(df["preferential_attachment"])
        + 0.35 * rank(df["adamic_adar"])
        + 0.25 * rank(df["common_neighbors"])
        + 0.15 * rank(-df["shortest_path"])
        + 0.10 * rank(df["semantic_similarity"])
    )


def pair_features(pc, cutoff, candidates, typ, G, idx, sims, u, v):
    def deg(c):
        return G.degree(c) if c in G else 0

    common = len(list(nx.common_neighbors(G, u, v))) if u in G and v in G else 0
    try:
        dist = nx.shortest_path_length(G, u, v) if u in G and v in G else 99
    except nx.NetworkXNoPath:
        dist = 99
    try:
        aa = next(nx.adamic_adar_index(G, [(u, v)]))[2] if u in G and v in G else 0
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


def candidate_pairs(pc, cutoff, policy="dprev23", min_count=2, max_pairs=30000):
    candidates, _counts, typ = concept_meta(pc, cutoff, min_count=min_count)
    if len(candidates) < 2:
        return pd.DataFrame()
    idx, sims = base.build_embeddings(candidates)
    G = graph_until(pc, cutoff)
    rows = []
    for u, v in combinations(candidates, 2):
        if G.has_edge(u, v):
            continue
        feats = pair_features(pc, cutoff, candidates, typ, G, idx, sims, u, v)
        sim = feats["semantic_similarity"]
        dprev = feats["dprev"]
        if policy == "dprev23" and dprev not in {2, 3}:
            continue
        if policy == "frontier" and dprev > 4 and sim < 0.06:
            continue
        if policy == "broad" and dprev > 8 and sim < 0.03:
            continue
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
        df["_rank_score"] = (
            2.0 * df["common_neighbors"]
            + 1.4 * df["adamic_adar"].rank(pct=True)
            + 8.0 * df["semantic_similarity"]
            - 0.25 * df["shortest_path"]
            + 0.02 * df["preferential_attachment"].rank(pct=True)
        )
        df = df.sort_values("_rank_score", ascending=False).head(max_pairs).drop(columns="_rank_score")
    return df


def label_samples(pc, samples, horizon):
    start, end = horizon
    future_edges = edge_lookup(pc, start, end)
    labels, titles = [], []
    for r in samples.itertuples():
        key = tuple(sorted([r.concept_u, r.concept_v]))
        title = future_edges.get(key, "")
        labels.append(int(bool(title)))
        titles.append(title)
    out = samples.copy()
    out["future_edge_label"] = labels
    out["future_example_title"] = titles
    out["future_window"] = f"{start}-{end}"
    return out


def fit_score(train, test):
    X_train = train[FEATURE_COLS].fillna(0).to_numpy()
    y_train = train["future_edge_label"].astype(int).to_numpy()
    X_test = test[FEATURE_COLS].fillna(0).to_numpy()
    y_test = test["future_edge_label"].astype(int).to_numpy()

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    lr = LogisticRegression(C=1.0, class_weight="balanced", max_iter=3000, random_state=23)
    lr.fit(X_train_s, y_train)
    lr_pred = lr.predict_proba(X_test_s)[:, 1]

    rf = RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=8,
        max_features=1.0,
        class_weight="balanced_subsample",
        random_state=23,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    rf_pred = rf.predict_proba(X_test)[:, 1]

    ml = 0.35 * lr_pred + 0.65 * rf_pred
    graph = graph_score(test)
    hybrid = 0.35 * pd.Series(graph).rank(pct=True).to_numpy() + 0.65 * pd.Series(ml).rank(pct=True).to_numpy()

    scored = test.copy()
    scored["ml_score"] = ml
    scored["graph_score"] = graph
    scored["hybrid_score"] = hybrid

    rows = []
    for name, score in [("ml", ml), ("graph", graph), ("hybrid", hybrid)]:
        row = {
            "model": name,
            "roc_auc": roc_auc_score(y_test, score),
            "average_precision": average_precision_score(y_test, score),
        }
        for k in [10, 25, 50, 100]:
            idx = np.argsort(score)[::-1][: min(k, len(score))]
            row[f"precision_at_{k}"] = float(y_test[idx].mean()) if len(idx) else np.nan
            row[f"hits_at_{k}"] = int(y_test[idx].sum()) if len(idx) else 0
        rows.append(row)
    return scored.sort_values("hybrid_score", ascending=False), pd.DataFrame(rows)


def plot_roc_pr(scored, policy):
    y = scored["future_edge_label"].astype(int).to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), constrained_layout=True)
    for name, col, color in [("ML", "ml_score", "#2b8cbe"), ("Graph", "graph_score", "#756bb1"), ("Hybrid", "hybrid_score", "#238b45")]:
        score = scored[col].to_numpy()
        fpr, tpr, _ = roc_curve(y, score)
        precision, recall, _ = precision_recall_curve(y, score)
        axes[0].plot(fpr, tpr, color=color, lw=1.3, label=f"{name} AUC={roc_auc_score(y, score):.3f}")
        axes[1].plot(recall, precision, color=color, lw=1.3, label=f"{name} AP={average_precision_score(y, score):.3f}")
    axes[0].plot([0, 1], [0, 1], color="#bdbdbd", lw=0.9, ls="--")
    axes[0].set_xlabel("False positive rate")
    axes[0].set_ylabel("True positive rate")
    axes[0].legend(fontsize=6)
    axes[0].set_title("ROC", loc="left", fontsize=9)
    axes[1].axhline(y.mean(), color="#bdbdbd", lw=0.9, ls="--", label=f"random={y.mean():.3f}")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_ylim(0, 1.02)
    axes[1].legend(fontsize=6)
    axes[1].set_title("Precision-recall", loc="left", fontsize=9)
    fig.suptitle(f"iTE -> iTE with NMI-clean concepts ({policy}), cutoff 2022 -> 2023-2026", x=0.02, ha="left", fontsize=10)
    for ext in ["png", "svg", "pdf"]:
        fig.savefig(OUT / f"ite_self_nmi_clean_{policy}_roc_pr.{ext}", dpi=600 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def plot_confusion(scored, policy, k=25):
    y = scored["future_edge_label"].astype(int).to_numpy()
    score = scored["hybrid_score"].to_numpy()
    pred = np.zeros(len(y), dtype=int)
    pred[np.argsort(score)[::-1][: min(k, len(y))]] = 1
    cm = confusion_matrix(y, pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(2.8, 2.5), constrained_layout=True)
    im = ax.imshow(cm, cmap=mpl.colormaps["Blues"])
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["Pred 0", "Pred 1"])
    ax.set_yticklabels(["True 0", "True 1"])
    vmax = cm.max()
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=10, color="white" if cm[i, j] > vmax * 0.55 else "#1b1b1b")
    tn, fp, fn, tp = cm.ravel()
    ax.set_xlabel(f"P={tp / max(1, tp + fp):.2f}, R={tp / max(1, tp + fn):.2f}")
    ax.set_title(f"Hybrid top-{k}", fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.8)
    for ext in ["png", "svg", "pdf"]:
        fig.savefig(OUT / f"ite_self_nmi_clean_{policy}_confusion_top{k}.{ext}", dpi=600 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def run_policy(pc, policy):
    train_parts = []
    windows = []
    for cutoff in range(2014, 2022):
        horizon = (cutoff + 1, min(cutoff + 3, 2023))
        cand = candidate_pairs(pc, cutoff, policy=policy)
        if cand.empty:
            continue
        labelled = label_samples(pc, cand, horizon)
        train_parts.append(labelled)
        windows.append(
            {
                "policy": policy,
                "cutoff_year": cutoff,
                "n_samples": len(labelled),
                "n_positive": int(labelled["future_edge_label"].sum()),
                "positive_rate": float(labelled["future_edge_label"].mean()) if len(labelled) else 0,
            }
        )
    train = pd.concat(train_parts, ignore_index=True).drop_duplicates(["cutoff_year", "concept_u", "concept_v"])
    test = label_samples(pc, candidate_pairs(pc, 2022, policy=policy), (2023, 2026))
    scored, metrics = fit_score(train, test)
    for col, val in [
        ("policy", policy),
        ("n_concepts_all_ite", pc["concept"].nunique()),
        ("n_candidate_concepts_ite", pc.loc[pc["graph_role"] == "recommendation_candidate", "concept"].nunique()),
        ("n_train", len(train)),
        ("train_positive", int(train["future_edge_label"].sum())),
        ("n_test", len(test)),
        ("test_positive", int(test["future_edge_label"].sum())),
        ("test_positive_rate", float(test["future_edge_label"].mean())),
    ]:
        metrics[col] = val
    scored.to_csv(OUT / f"ite_self_nmi_clean_{policy}_scored.csv", index=False)
    train.to_csv(OUT / f"ite_self_nmi_clean_{policy}_train.csv", index=False)
    pd.DataFrame(windows).to_csv(OUT / f"ite_self_nmi_clean_{policy}_windows.csv", index=False)
    plot_roc_pr(scored, policy)
    for k in [10, 25, 50, 100]:
        plot_confusion(scored, policy, k=k)
    return metrics


def main():
    pc = load_pc()
    pc.to_csv(OUT / "ite_self_nmi_clean_paper_concepts.csv", index=False)
    all_metrics = []
    for policy in ["dprev23", "frontier", "broad"]:
        print("RUN", policy)
        metrics = run_policy(pc, policy)
        all_metrics.append(metrics)
    summary = pd.concat(all_metrics, ignore_index=True)
    cols = [
        "policy", "model", "n_concepts_all_ite", "n_candidate_concepts_ite", "n_train", "train_positive",
        "n_test", "test_positive", "test_positive_rate", "roc_auc", "average_precision",
        "precision_at_10", "hits_at_10", "precision_at_25", "hits_at_25",
        "precision_at_50", "hits_at_50", "precision_at_100", "hits_at_100",
    ]
    summary = summary[cols].sort_values(["precision_at_25", "average_precision", "roc_auc"], ascending=False)
    summary.to_csv(OUT / "ite_self_nmi_clean_summary.csv", index=False)
    print(summary.to_string(index=False))
    print("outputs", OUT)


if __name__ == "__main__":
    main()
