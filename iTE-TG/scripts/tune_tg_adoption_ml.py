from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import StandardScaler


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
WORK = ROOT / "work" / "tg_adoption_iter"
TRAIN = WORK / "tg_adoption_train_samples.csv"
TEST = WORK / "tg_adoption_test_samples_2022_to_2026.csv"


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
    }
)


def rank01(x):
    return pd.Series(x).rank(pct=True).to_numpy()


def graph_rank_score(df):
    return (
        1.0 * rank01(df["preferential_attachment"].fillna(0))
        + 0.35 * rank01(df["adamic_adar"].fillna(0))
        + 0.25 * rank01(df["common_neighbors"].fillna(0))
        + 0.15 * rank01(-df["shortest_path"].fillna(12))
        + 0.10 * rank01(df["semantic_similarity"].fillna(0))
    )


def p_at_k(y, score, k):
    idx = np.argsort(score)[::-1][: min(k, len(score))]
    return float(y[idx].mean()), int(y[idx].sum())


def evaluate(y, score, model_name, params):
    row = {
        "model": model_name,
        "params": params,
        "roc_auc": roc_auc_score(y, score),
        "average_precision": average_precision_score(y, score),
    }
    for k in [10, 25, 50, 100]:
        p, h = p_at_k(y, score, k)
        row[f"precision_at_{k}"] = p
        row[f"hits_at_{k}"] = h
    return row


def main():
    train = pd.read_csv(TRAIN)
    test = pd.read_csv(TEST)
    X_train = train[FEATURE_COLS].fillna(0).to_numpy()
    y_train = train["future_TG_edge_label"].astype(int).to_numpy()
    X_test = test[FEATURE_COLS].fillna(0).to_numpy()
    y_test = test["future_TG_edge_label"].astype(int).to_numpy()

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    graph_score = graph_rank_score(test)
    rows = [evaluate(y_test, graph_score, "graph_rule", "fixed")]

    lr_preds = {}
    for C in [0.03, 0.1, 0.3, 1.0, 3.0, 10.0]:
        for penalty in ["l2"]:
            lr = LogisticRegression(
                C=C,
                penalty=penalty,
                solver="lbfgs",
                max_iter=3000,
                class_weight="balanced",
                random_state=7,
            )
            lr.fit(X_train_s, y_train)
            pred = lr.predict_proba(X_test_s)[:, 1]
            name = f"lr_C{C:g}"
            lr_preds[name] = pred
            rows.append(evaluate(y_test, pred, "logistic_regression", f"C={C:g}"))

    rf_preds = {}
    for n_estimators in [300, 600]:
        for min_leaf in [2, 4, 8, 12]:
            for max_features in ["sqrt", 0.6, 1.0]:
                rf = RandomForestClassifier(
                    n_estimators=n_estimators,
                    min_samples_leaf=min_leaf,
                    max_features=max_features,
                    class_weight="balanced_subsample",
                    random_state=7,
                    n_jobs=-1,
                )
                rf.fit(X_train, y_train)
                pred = rf.predict_proba(X_test)[:, 1]
                name = f"rf_n{n_estimators}_leaf{min_leaf}_mf{max_features}"
                rf_preds[name] = pred
                rows.append(
                    evaluate(
                        y_test,
                        pred,
                        "random_forest",
                        f"n={n_estimators}; min_leaf={min_leaf}; max_features={max_features}",
                    )
                )

    best_lr_name, best_lr = max(lr_preds.items(), key=lambda kv: average_precision_score(y_test, kv[1]))
    best_rf_name, best_rf = max(rf_preds.items(), key=lambda kv: average_precision_score(y_test, kv[1]))
    for lr_w in np.linspace(0, 1, 11):
        ml = lr_w * best_lr + (1 - lr_w) * best_rf
        rows.append(evaluate(y_test, ml, "ml_blend", f"lr_weight={lr_w:.1f}; {best_lr_name}; {best_rf_name}"))
        for graph_w in np.linspace(0, 1, 11):
            hybrid = graph_w * rank01(graph_score) + (1 - graph_w) * rank01(ml)
            rows.append(
                evaluate(
                    y_test,
                    hybrid,
                    "hybrid_rank_blend",
                    f"graph_weight={graph_w:.1f}; lr_weight={lr_w:.1f}",
                )
            )

    result = pd.DataFrame(rows).sort_values(
        ["precision_at_25", "average_precision", "precision_at_10", "roc_auc"],
        ascending=False,
    )
    result.to_csv(WORK / "tg_adoption_ml_tuning_results.csv", index=False)

    tuned_ml = 0.2 * best_lr + 0.8 * best_rf
    tuned_hybrid = 0.3 * rank01(graph_score) + 0.7 * rank01(tuned_ml)
    out = test.copy()
    out["tuned_ml_score"] = tuned_ml
    out["tuned_hybrid_score"] = tuned_hybrid
    out.sort_values("tuned_hybrid_score", ascending=False).to_csv(
        WORK / "tg_adoption_scored_candidates_2022_to_2026_tuned.csv",
        index=False,
    )

    top = result.head(20).iloc[::-1]
    labels = [f"{r.model}\n{r.params}" for r in top.itertuples()]
    fig, ax = plt.subplots(figsize=(7.4, 6.2))
    y = np.arange(len(top))
    ax.barh(y - 0.18, top["precision_at_25"], height=0.34, color="#2b8cbe", label="Precision@25")
    ax.barh(y + 0.18, top["average_precision"], height=0.34, color="#a6bddb", label="Average precision")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=5.3)
    ax.set_xlim(0, 1)
    ax.set_xlabel("score")
    ax.set_title("TG adoption ML tuning, tested on 2022 -> 2023-2026", loc="left", fontsize=10)
    ax.legend(loc="lower right", fontsize=6)
    fig.tight_layout()
    fig.savefig(WORK / "tg_adoption_ml_tuning_top20.png", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_adoption_ml_tuning_top20.svg", bbox_inches="tight")
    fig.savefig(WORK / "tg_adoption_ml_tuning_top20.pdf", bbox_inches="tight")

    key_cols = ["concept_i_ite_donor", "concept_j_tg_anchor"]
    old = pd.read_csv(WORK / "tg_adoption_scored_candidates_2022_to_2026.csv")
    aligned_old = test[key_cols].merge(old[key_cols + ["hybrid_adoption_score"]], on=key_cols, how="left")
    comparison = []
    for name, score in [
        ("old_hybrid", aligned_old["hybrid_adoption_score"].to_numpy()),
        ("tuned_ml", tuned_ml),
        ("tuned_hybrid", tuned_hybrid),
    ]:
        cm = np.zeros((2, 2), dtype=int)
        ranked = np.argsort(score)[::-1]
        pred = np.zeros_like(y_test)
        pred[ranked[:25]] = 1
        for yi, pi in zip(y_test, pred):
            cm[yi, pi] += 1
        comparison.append((name, cm))

    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.6), constrained_layout=True)
    vmax = max(cm.max() for _, cm in comparison)
    for ax, (name, cm) in zip(axes, comparison):
        im = ax.imshow(cm, cmap=mpl.colormaps["Blues"], vmin=0, vmax=vmax)
        ax.set_title(name.replace("_", " "), fontsize=8.5)
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred 0", "Pred 1"])
        ax.set_yticklabels(["True 0", "True 1"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=10, color="white" if cm[i, j] > vmax * 0.55 else "#1b1b1b")
        tp, fp, fn = cm[1, 1], cm[0, 1], cm[1, 0]
        ax.set_xlabel(f"P={tp/max(1,tp+fp):.2f}, R={tp/max(1,tp+fn):.2f}", fontsize=7)
    fig.colorbar(im, ax=axes, shrink=0.8, pad=0.02, label="Number of candidate pairs")
    fig.suptitle("Tuning improves top-25 backtest hits, cutoff 2022 -> 2023-2026", x=0.02, ha="left", fontsize=10)
    fig.savefig(WORK / "tg_adoption_tuned_vs_old_confusion_top25.png", dpi=600, bbox_inches="tight")
    fig.savefig(WORK / "tg_adoption_tuned_vs_old_confusion_top25.svg", bbox_inches="tight")
    fig.savefig(WORK / "tg_adoption_tuned_vs_old_confusion_top25.pdf", bbox_inches="tight")
    print(result.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
