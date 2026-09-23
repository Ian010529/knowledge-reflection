from pathlib import Path
import re

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
DATA_DIR = Path("/Users/ryan/Documents/Codex/2026-07-15/r/work")

DATASETS = {
    "tg": [
        (DATA_DIR / "TG_first333_material_mechanism.csv", "TG"),
    ],
    "ite": [
        (DATA_DIR / "iTE1_first1000_material_mechanism.csv", "iTE1"),
        (DATA_DIR / "iTE2_first711_material_mechanism.csv", "iTE2"),
    ],
}

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


def clean_text(text):
    text = str(text).strip()
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ;,.")


def short_label(text, max_words=5, max_chars=44):
    text = clean_text(text)
    words = text.split()
    label = " ".join(words[:max_words])
    if len(words) > max_words:
        label += "..."
    if len(label) > max_chars:
        label = label[: max_chars - 3].rstrip(" ,;:-") + "..."
    return label


def read_entries(kind):
    rows = []
    for path, source in DATASETS[kind]:
        df = pd.read_csv(path)
        for i, row in df.iterrows():
            paper_id = f"{source}_{i:04d}"
            for role, col in [("material", "材料"), ("mechanism", "机制")]:
                text = clean_text(row[col])
                if not text:
                    continue
                rows.append(
                    {
                        "entry_id": f"{paper_id}_{role}",
                        "paper_id": paper_id,
                        "source": source,
                        "year": int(row["年份"]),
                        "title": row["文章名"],
                        "doi": row["DOI"],
                        "role": role,
                        "text": text,
                        "label": short_label(text),
                    }
                )
    return pd.DataFrame(rows)


def embed_entries(texts, seed):
    max_features = 5000 if len(texts) < 1000 else 3500
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=max_features)
    word = TfidfVectorizer(analyzer="word", ngram_range=(1, 3), min_df=1, max_features=max_features)
    X = np.hstack([char.fit_transform(texts).toarray(), word.fit_transform(texts).toarray()])
    n_components = min(120, X.shape[0] - 2, X.shape[1] - 1)
    X = TruncatedSVD(n_components=n_components, random_state=seed).fit_transform(X)
    X = normalize(X)
    return umap.UMAP(
        n_neighbors=18 if len(texts) < 1000 else 28,
        min_dist=0.08,
        metric="cosine",
        random_state=seed,
    ).fit_transform(X)


def point_density(sub):
    x = sub["x"].to_numpy()
    y = sub["y"].to_numpy()
    if len(sub) < 4:
        return np.ones(len(sub))
    kde = gaussian_kde(np.vstack([x, y]), bw_method=0.23)
    return kde(np.vstack([x, y]))


def select_labels(sub, n_labels, tile_size):
    d = sub.copy()
    d["density_at_point"] = point_density(d)
    d["tile_x"] = np.floor((d["x"] - d["x"].min()) / tile_size).astype(int)
    d["tile_y"] = np.floor((d["y"] - d["y"].min()) / tile_size).astype(int)
    picked = (
        d.sort_values(["density_at_point", "year"], ascending=False)
        .groupby(["tile_x", "tile_y"], as_index=False)
        .head(1)
        .sort_values("density_at_point", ascending=False)
        .head(n_labels)
        .copy()
    )
    return picked.sort_values("y", ascending=False).reset_index(drop=True)


def adjusted_label_positions(labels, xlim, ylim):
    if labels.empty:
        return labels
    out = labels.copy()
    width = xlim[1] - xlim[0]
    height = ylim[1] - ylim[0]
    mid = (xlim[0] + xlim[1]) / 2
    left_x = xlim[0] + width * 0.035
    right_x = xlim[1] - width * 0.035
    min_gap = height * 0.075
    for side, side_mask in [("left", out["x"] < mid), ("right", out["x"] >= mid)]:
        idx = out[side_mask].sort_values("y", ascending=False).index.tolist()
        last_y = None
        for j in idx:
            y = float(out.loc[j, "y"])
            if last_y is not None and y > last_y - min_gap:
                y = last_y - min_gap
            y = min(max(y, ylim[0] + height * 0.05), ylim[1] - height * 0.05)
            out.loc[j, "label_x"] = left_x if side == "left" else right_x
            out.loc[j, "label_y"] = y
            out.loc[j, "ha"] = "left" if side == "left" else "right"
            last_y = y
    return out


def density_panel(ax, all_entries, role, label_count, point_color, label_color, title):
    sub = all_entries[all_entries["role"] == role].copy()
    all_x = all_entries["x"].to_numpy()
    all_y = all_entries["y"].to_numpy()
    pad_x = (all_x.max() - all_x.min()) * 0.24
    pad_y = (all_y.max() - all_y.min()) * 0.16
    xlim = (all_x.min() - pad_x, all_x.max() + pad_x)
    ylim = (all_y.min() - pad_y, all_y.max() + pad_y)

    x = sub["x"].to_numpy()
    y = sub["y"].to_numpy()
    xx, yy = np.mgrid[xlim[0] : xlim[1] : 260j, ylim[0] : ylim[1] : 230j]
    kde = gaussian_kde(np.vstack([x, y]), bw_method=0.23)
    zz = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
    zz = np.ma.masked_less(zz, zz.max() * 0.055)
    cmap = LinearSegmentedColormap.from_list(
        f"{role}_white_density",
        ["#ffffff", "#e9f3fb", "#b9dff1", "#76c7a2", "#f3d46b"],
    )
    density = ax.contourf(xx, yy, zz, levels=46, cmap=cmap, alpha=0.94)
    ax.scatter(sub["x"], sub["y"], s=2.2, c=point_color, alpha=0.24, lw=0, rasterized=True)

    tile = max((xlim[1] - xlim[0]), (ylim[1] - ylim[0])) / 5.3
    labels = select_labels(sub, label_count, tile)
    labels = adjusted_label_positions(labels, xlim, ylim)
    ax.scatter(labels["x"], labels["y"], s=16, c=label_color, edgecolor="white", linewidth=0.25, zorder=5)
    for row in labels.itertuples():
        ax.annotate(
            row.label,
            xy=(row.x, row.y),
            xytext=(row.label_x, row.label_y),
            fontsize=5.5,
            ha=row.ha,
            va="center",
            color="#202020",
            bbox=dict(boxstyle="square,pad=0.12", facecolor="white", edgecolor="none", alpha=0.82),
            arrowprops=dict(arrowstyle="-", color="#8b95a1", lw=0.34, shrinkA=1.5, shrinkB=1.4),
            zorder=6,
        )
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_title(title, loc="left", fontsize=8.6, pad=5)
    ax.set_xlabel("UMAP component 1")
    ax.set_ylabel("UMAP component 2")
    ax.set_facecolor("white")
    return density, labels


def plot_kind(kind):
    out = ROOT / "work" / f"{kind}_raw_material_mechanism_density_map"
    out.mkdir(exist_ok=True)
    entries = read_entries(kind)
    coords = embed_entries(entries["text"].tolist(), seed=31 if kind == "tg" else 37)
    entries["x"] = coords[:, 0]
    entries["y"] = coords[:, 1]

    n_labels = 6 if kind == "tg" else 7
    fig, axes = plt.subplots(1, 2, figsize=(7.7, 3.65), constrained_layout=True, sharex=True, sharey=True)
    density, material_labels = density_panel(
        axes[0],
        entries,
        "material",
        n_labels,
        "#31527f",
        "#d7191c",
        f"{kind.upper()} material landscape",
    )
    density, mechanism_labels = density_panel(
        axes[1],
        entries,
        "mechanism",
        n_labels,
        "#2d6a4f",
        "#d7191c",
        f"{kind.upper()} mechanism landscape",
    )
    cbar = fig.colorbar(density, ax=axes, shrink=0.82, pad=0.015)
    cbar.set_label("Kernel density estimate", rotation=270, labelpad=12)

    entries.to_csv(out / f"{kind}_raw_material_mechanism_embedding_source.csv", index=False)
    material_labels.to_csv(out / f"{kind}_material_raw_labels.csv", index=False)
    mechanism_labels.to_csv(out / f"{kind}_mechanism_raw_labels.csv", index=False)
    stem = out / f"{kind}_raw_material_vs_mechanism_density_map"
    fig.savefig(stem.with_suffix(".png"), dpi=700, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=700, bbox_inches="tight")
    plt.close(fig)
    print(kind, "entries", len(entries), "papers", entries["paper_id"].nunique(), "out", out)


def main():
    for kind in ["tg", "ite"]:
        plot_kind(kind)


if __name__ == "__main__":
    main()
