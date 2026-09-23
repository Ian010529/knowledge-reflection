from itertools import combinations
from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import StandardScaler


sys.path.insert(0, "/Users/ryan/Documents/Codex/2026-07-20/t-he/work")
import tg_adoption_prediction_demo as base


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
OUT = ROOT / "work" / "ite_self_iter"
OUT.mkdir(exist_ok=True)

ITE_SOURCES = ["iTE1", "iTE2"]
CANDIDATE_TYPES = {
    "solvation_entropy",
    "transport_mechanism",
    "phase_or_species_transition",
    "gel_microstructure",
    "electrode_interface",
    "material_system",
    "redox_chemistry",
}

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
        "axes.linewidth": 0.7,
        "legend.frameon": False,
    }
)


def concept_counts_ite(pc, cutoff):
    d = pc[(pc["year"] <= cutoff) & (pc["source"].isin(ITE_SOURCES))]
    counts = d.groupby("concept")["paper_id"].nunique().to_dict()
    typ = d.groupby("concept")["concept_type"].agg(lambda x: x.value_counts().idxmax()).to_dict()
    return counts, typ


def graph_ite_until(pc, cutoff):
    return base.graph_until(pc, cutoff, ITE_SOURCES)


def add_ite_pair_labels(pc, samples, horizon):
    start, end = horizon
    future = pc[(pc["source"].isin(ITE_SOURCES)) & (pc["year"].between(start, end))]
    labels = []
    examples = []
    for r in samples.itertuples():
        label = 0
        ex = ""
        for _, g in future.groupby("paper_id"):
            concepts = set(g["concept"])
            if r.concept_u in concepts and r.concept_v in concepts:
                label = 1
                ex = g["title"].iloc[0]
                break
        labels.append(label)
        examples.append(ex)
    out = samples.copy()
    out["future_edge_label"] = labels
    out["future_example_title"] = examples
    out["future_window"] = f"{start}-{end}"
    return out


def candidate_pairs_ite(pc, cutoff, max_pairs=20000):
    counts, typ = concept_counts_ite(pc, cutoff)
    concepts = [
        c
        for c, n in counts.items()
        if n >= 2
        and n <= 150
        and typ.get(c) in CANDIDATE_TYPES
        and c not in base.GENERIC
        and c not in base.BACKGROUND_ONLY_CONCEPTS
    ]
    concepts = sorted(concepts)
    if len(concepts) < 2:
        return pd.DataFrame()

    concept_to_idx, sim_matrix = base.build_embeddings(concepts)
    G_ite = graph_ite_until(pc, cutoff)
    G_all = base.graph_until(pc, cutoff)
    rows = []
    for u, v in combinations(concepts, 2):
        if G_ite.has_edge(u, v):
            continue
        sim = sim_matrix[concept_to_idx[u], concept_to_idx[v]]
        if sim > 0.90:
            continue
        try:
            dprev = nx.shortest_path_length(G_ite, u, v) if u in G_ite and v in G_ite else 99
        except nx.NetworkXNoPath:
            dprev = 99
        if dprev > 4 and sim < 0.06:
            continue
        feats = base.pair_features_from_graphs(
            pc,
            cutoff,
            u,
            v,
            typ,
            concept_to_idx,
            sim_matrix,
            G_all,
            G_ite,
            G_ite,
        )
        rows.append(
            {
                "cutoff_year": cutoff,
                "concept_u": u,
                "concept_v": v,
                "u_type": typ.get(u),
                "v_type": typ.get(v),
                "dprev_ite": min(dprev, 12),
                **feats,
            }
        )
    df = pd.DataFrame(rows)
    if len(df) > max_pairs:
        df["_score"] = (
            2.0 * df["common_neighbors"]
            + 6.0 * df["semantic_similarity"]
            - 0.12 * df["shortest_path"]
            + 0.04 * df["u_degree_ite"]
            + 0.04 * df["v_degree_ite"]
        )
        df = df.sort_values("_score", ascending=False).head(max_pairs).drop(columns="_score")
    return df


def graph_rank_score(df):
    rank = lambda s: s.fillna(0).rank(pct=True).to_numpy()
    return (
        1.0 * rank(df["preferential_attachment"])
        + 0.35 * rank(df["adamic_adar"])
        + 0.25 * rank(df["common_neighbors"])
        + 0.15 * rank(-df["shortest_path"])
        + 0.10 * rank(df["semantic_similarity"])
    )


def fit_predict(train, test):
    X_train = train[FEATURE_COLS].fillna(0).to_numpy()
    y_train = train["future_edge_label"].astype(int).to_numpy()
    X_test = test[FEATURE_COLS].fillna(0).to_numpy()
    y_test = test["future_edge_label"].astype(int).to_numpy()

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    lr = LogisticRegression(C=1.0, max_iter=3000, class_weight="balanced", random_state=11)
    lr.fit(X_train_s, y_train)
    lr_pred = lr.predict_proba(X_test_s)[:, 1]

    rf = RandomForestClassifier(
        n_estimators=600,
        min_samples_leaf=6,
        max_features=1.0,
        class_weight="balanced_subsample",
        random_state=11,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    rf_pred = rf.predict_proba(X_test)[:, 1]
    ml = 0.35 * lr_pred + 0.65 * rf_pred
    graph = graph_rank_score(test)
    hybrid = 0.35 * pd.Series(graph).rank(pct=True).to_numpy() + 0.65 * pd.Series(ml).rank(pct=True).to_numpy()

    scored = test.copy()
    scored["ml_score"] = ml
    scored["graph_score"] = graph
    scored["hybrid_score"] = hybrid

    metrics = {
        "n_train": len(train),
        "train_positive": int(y_train.sum()),
        "n_test": len(test),
        "test_positive": int(y_test.sum()),
    }
    for name, score in [("ml", ml), ("graph", graph), ("hybrid", hybrid)]:
        metrics[f"{name}_roc_auc"] = roc_auc_score(y_test, score)
        metrics[f"{name}_average_precision"] = average_precision_score(y_test, score)
        for k in [10, 25, 50, 100]:
            idx = np.argsort(score)[::-1][: min(k, len(score))]
            metrics[f"{name}_precision_at_{k}"] = float(y_test[idx].mean()) if len(idx) else np.nan
            metrics[f"{name}_hits_at_{k}"] = int(y_test[idx].sum()) if len(idx) else 0
    return scored.sort_values("hybrid_score", ascending=False), metrics


def plot_roc_pr(scored):
    y = scored["future_edge_label"].astype(int).to_numpy()
    models = [("ML", "ml_score", "#2b8cbe"), ("Graph", "graph_score", "#756bb1"), ("Hybrid", "hybrid_score", "#238b45")]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0), constrained_layout=True)
    for name, col, color in models:
        score = scored[col].to_numpy()
        fpr, tpr, _ = roc_curve(y, score)
        precision, recall, _ = precision_recall_curve(y, score)
        axes[0].plot(fpr, tpr, color=color, lw=1.4, label=f"{name} AUC={roc_auc_score(y, score):.3f}")
        axes[1].plot(recall, precision, color=color, lw=1.4, label=f"{name} AP={average_precision_score(y, score):.3f}")
    axes[0].plot([0, 1], [0, 1], color="#bdbdbd", lw=0.9, ls="--")
    axes[0].set_xlabel("False positive rate")
    axes[0].set_ylabel("True positive rate")
    axes[0].set_title("ROC curve", loc="left", fontsize=9)
    axes[0].legend(fontsize=6)
    axes[1].axhline(y.mean(), color="#bdbdbd", lw=0.9, ls="--", label=f"random={y.mean():.3f}")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_ylim(0, 1.02)
    axes[1].set_title("Precision-recall curve", loc="left", fontsize=9)
    axes[1].legend(fontsize=6)
    fig.suptitle("iTE -> iTE NMI-style future link prediction, cutoff 2022 -> 2023-2026", x=0.02, ha="left", fontsize=10)
    fig.savefig(OUT / "ite_self_nmi_style_roc_pr.png", dpi=600, bbox_inches="tight")
    fig.savefig(OUT / "ite_self_nmi_style_roc_pr.svg", bbox_inches="tight")
    fig.savefig(OUT / "ite_self_nmi_style_roc_pr.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_confusion(scored, k=25, score_col="hybrid_score"):
    y = scored["future_edge_label"].astype(int).to_numpy()
    score = scored[score_col].to_numpy()
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
    fig.colorbar(im, ax=ax, shrink=0.8, label="pairs")
    fig.savefig(OUT / f"ite_self_hybrid_confusion_top{k}.png", dpi=600, bbox_inches="tight")
    fig.savefig(OUT / f"ite_self_hybrid_confusion_top{k}.svg", bbox_inches="tight")
    fig.savefig(OUT / f"ite_self_hybrid_confusion_top{k}.pdf", bbox_inches="tight")
    plt.close(fig)


def main():
    _, pc_all = base.make_paper_concepts()
    pc = pc_all[pc_all["source"].isin(ITE_SOURCES)].copy()
    pc.to_csv(OUT / "ite_self_typed_concepts.csv", index=False)

    train_parts = []
    windows = []
    for cutoff in range(2014, 2022):
        horizon = (cutoff + 1, min(cutoff + 3, 2023))
        samples = candidate_pairs_ite(pc, cutoff)
        if samples.empty:
            continue
        labelled = add_ite_pair_labels(pc, samples, horizon)
        train_parts.append(labelled)
        windows.append(
            {
                "cutoff_year": cutoff,
                "future_window": f"{horizon[0]}-{horizon[1]}",
                "n_samples": len(labelled),
                "n_positive": int(labelled["future_edge_label"].sum()),
                "positive_rate": float(labelled["future_edge_label"].mean()),
            }
        )

    train = pd.concat(train_parts, ignore_index=True).drop_duplicates(["cutoff_year", "concept_u", "concept_v"])
    test = add_ite_pair_labels(pc, candidate_pairs_ite(pc, 2022), (2023, 2026))
    train.to_csv(OUT / "ite_self_train_samples.csv", index=False)
    test.to_csv(OUT / "ite_self_test_samples_2022_to_2026.csv", index=False)
    pd.DataFrame(windows).to_csv(OUT / "ite_self_window_summary.csv", index=False)

    if train["future_edge_label"].sum() < 2 or test["future_edge_label"].sum() < 1:
        raise RuntimeError("Not enough positives for iTE self-prediction.")

    scored, metrics = fit_predict(train, test)
    scored.to_csv(OUT / "ite_self_scored_candidates_2022_to_2026.csv", index=False)
    pd.DataFrame([metrics]).to_csv(OUT / "ite_self_backtest_metrics.csv", index=False)
    plot_roc_pr(scored)
    for k in [10, 25, 50, 100]:
        plot_confusion(scored, k=k)

    print("iTE concepts", pc["concept"].nunique(), "train", len(train), "test", len(test), "test positives", int(test["future_edge_label"].sum()))
    print(pd.DataFrame([metrics]).T.to_string(header=False))
    print("outputs", OUT)


if __name__ == "__main__":
    main()
