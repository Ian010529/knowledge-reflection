from itertools import combinations
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import gaussian_kde
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
import umap


ROOT = Path("/Users/ryan/Documents/Codex/2026-07-20/t-he")
IN = ROOT / "work" / "open_concepts_iter" / "open_nmi_paper_concepts_1500.csv"
OUT = ROOT / "work" / "tg_concept_density_map"
OUT.mkdir(exist_ok=True)

ITE_SOURCES = {"TG"}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
    }
)


def build_graph_stats(pc):
    degree = {c: 0 for c in pc["concept"].unique()}
    weighted_degree = {c: 0 for c in pc["concept"].unique()}
    edges = {}
    for _, g in pc.groupby("paper_id"):
        concepts = sorted(g["concept"].unique())
        for u, v in combinations(concepts, 2):
            key = (u, v)
            edges[key] = edges.get(key, 0) + 1
    neighbor_sets = {c: set() for c in degree}
    for (u, v), w in edges.items():
        neighbor_sets[u].add(v)
        neighbor_sets[v].add(u)
        weighted_degree[u] += w
        weighted_degree[v] += w
    for c, ns in neighbor_sets.items():
        degree[c] = len(ns)
    return degree, weighted_degree


def concept_embeddings(concepts):
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
        lowercase=True,
    )
    X_char = vectorizer.fit_transform(concepts)
    word_vectorizer = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 3),
        min_df=1,
        lowercase=True,
    )
    X_word = word_vectorizer.fit_transform(concepts)
    X = np.hstack([X_char.toarray(), X_word.toarray()])
    n_components = min(120, X.shape[0] - 1, X.shape[1] - 1)
    X_red = TruncatedSVD(n_components=n_components, random_state=9).fit_transform(X)
    X_red = normalize(X_red)
    reducer = umap.UMAP(
        n_neighbors=18,
        min_dist=0.12,
        metric="cosine",
        random_state=9,
    )
    return reducer.fit_transform(X_red)


LABEL_TYPES = {
    "transport_mechanism",
    "solvation_entropy",
    "redox_chemistry",
    "gel_microstructure",
    "electrode_interface",
    "phase_or_species_transition",
    "material_system",
}

GENERIC_LABEL_RE = (
    r"thermogalvanic cells?|thermogalvanic effect|temperature difference|"
    r"temperature gradients?|seebeck coefficients?|power density|thermal conductivity|"
    r"ionic conductivity|electrical conductivity|high thermopower|power generation|"
    r"energy conversion|heat-to-electricity conversion|thermoelectric conversion|"
    r"temperature range|temperature coefficient|thermogalvanic power"
)

MECHANISM_MATERIAL_RE = (
    r"redox|ferri|ferro|solvation|entropy|soret|thermodiffusion|diffusion|"
    r"migration|transport|hydrogel|electrolyte|ionic liquid|bacterial cellulose|"
    r"phase transition|crystallization|charge transfer|kinetics|electrode|"
    r"concentration gradient|water molecules|ion "
)


def label_priority(row):
    if row.concept_type not in LABEL_TYPES:
        return -1
    concept = row.concept
    if pd.Series([concept]).str.contains(GENERIC_LABEL_RE, case=False, regex=True).iloc[0]:
        return -1
    score = row.degree + 0.25 * row.weighted_degree + 1.2 * row.doc_freq
    if row.concept_type in {"transport_mechanism", "solvation_entropy", "redox_chemistry", "gel_microstructure", "electrode_interface"}:
        score += 80
    elif row.concept_type == "phase_or_species_transition":
        score += 55
    elif row.concept_type == "material_system":
        score += 20
    if pd.Series([concept]).str.contains(MECHANISM_MATERIAL_RE, case=False, regex=True).iloc[0]:
        score += 45
    return score


def pick_tile_labels(df, tile_size=1.55, max_labels=30):
    d = df.copy()
    xmin, ymin = d["x"].min(), d["y"].min()
    d["tile_x"] = np.floor((d["x"] - xmin) / tile_size).astype(int)
    d["tile_y"] = np.floor((d["y"] - ymin) / tile_size).astype(int)
    d["label_priority"] = d.apply(label_priority, axis=1)
    d = d[d["label_priority"] > 0].copy()
    picked = (
        d.sort_values(["label_priority", "degree", "weighted_degree", "doc_freq"], ascending=False)
        .groupby(["tile_x", "tile_y"], as_index=False)
        .head(1)
        .sort_values(["label_priority", "degree", "weighted_degree"], ascending=False)
        .head(max_labels)
        .copy()
    )
    return picked


def draw_map(df, labels):
    x = df["x"].to_numpy()
    y = df["y"].to_numpy()
    pad_x = (x.max() - x.min()) * 0.14
    pad_y = (y.max() - y.min()) * 0.09
    xlim = (x.min() - pad_x, x.max() + pad_x)
    ylim = (y.min() - pad_y, y.max() + pad_y)

    xx, yy = np.mgrid[xlim[0] : xlim[1] : 260j, ylim[0] : ylim[1] : 260j]
    kde = gaussian_kde(np.vstack([x, y]), bw_method=0.18)
    zz = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)

    cmap = LinearSegmentedColormap.from_list(
        "nmi_density",
        ["#3b0f70", "#2f6f9f", "#28a878", "#a6d96a", "#fde725"],
    )

    fig, ax = plt.subplots(figsize=(7.0, 6.0), constrained_layout=True)
    density = ax.contourf(xx, yy, zz, levels=80, cmap=cmap, alpha=0.88)
    ax.scatter(x, y, s=8, c="#352060", alpha=0.35, lw=0, rasterized=True, label="All concepts")
    ax.scatter(
        labels["x"],
        labels["y"],
        s=18,
        c="#e60012",
        edgecolor="white",
        linewidth=0.25,
        zorder=5,
        label="Material/mechanism hub in tile",
    )

    for i, row in enumerate(labels.itertuples()):
        dx = 0.08 if i % 3 != 0 else -0.08
        dy = 0.08 if i % 2 == 0 else -0.08
        ha = "left" if dx > 0 else "right"
        ax.text(
            row.x + dx,
            row.y + dy,
            row.concept,
            fontsize=5.8,
            ha=ha,
            va="center",
            color="#202020",
            bbox=dict(boxstyle="square,pad=0.13", facecolor="white", edgecolor="none", alpha=0.64),
            zorder=6,
        )

    ax.set_xlabel("UMAP component 1")
    ax.set_ylabel("UMAP component 2")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_title("Map of thermogalvanic material and mechanism concepts", loc="left", fontsize=9.5, pad=7)

    cbar = fig.colorbar(density, ax=ax, shrink=0.86, pad=0.02)
    cbar.set_label("Kernel density estimate", rotation=270, labelpad=12)
    leg = ax.legend(
        loc="lower right",
        fontsize=6.5,
        markerscale=1.2,
        handletextpad=0.6,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        framealpha=0.62,
    )
    for text in leg.get_texts():
        text.set_color("#3d4864")
    return fig


def main():
    pc = pd.read_csv(IN)
    pc = pc[pc["source"].isin(ITE_SOURCES)].copy()
    counts = pc.groupby("concept")["paper_id"].nunique()
    keep = counts[counts >= 3].index
    pc = pc[pc["concept"].isin(keep)].copy()

    degree, weighted_degree = build_graph_stats(pc)
    meta = (
        pc.groupby("concept", as_index=False)
        .agg(
            doc_freq=("paper_id", "nunique"),
            first_year=("year", "min"),
            last_year=("year", "max"),
            concept_type=("concept_type", lambda x: x.value_counts().idxmax()),
            graph_role=("graph_role", lambda x: x.value_counts().idxmax()),
        )
        .sort_values("doc_freq", ascending=False)
    )
    concepts = meta["concept"].tolist()
    coords = concept_embeddings(concepts)
    meta["x"] = coords[:, 0]
    meta["y"] = coords[:, 1]
    meta["degree"] = meta["concept"].map(degree).fillna(0).astype(int)
    meta["weighted_degree"] = meta["concept"].map(weighted_degree).fillna(0).astype(int)
    labels = pick_tile_labels(meta, tile_size=1.55, max_labels=30)

    meta.to_csv(OUT / "tg_nmi_concept_map_source.csv", index=False)
    labels.to_csv(OUT / "tg_nmi_concept_map_tile_labels.csv", index=False)

    fig = draw_map(meta, labels)
    stem = OUT / "tg_nmi_concept_density_map"
    fig.savefig(stem.with_suffix(".png"), dpi=700, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=700, bbox_inches="tight")
    plt.close(fig)

    print("concepts", len(meta))
    print("papers", pc["paper_id"].nunique())
    print("labels", len(labels))
    print("outputs", OUT)


if __name__ == "__main__":
    main()
