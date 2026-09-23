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

from plot_tg_material_mechanism_embedding_density import CANONICAL_PATTERNS, OUT, DATA

MATERIAL_TAGS = {
    "hydrogel thermocell platform",
    "porous/redox electrode interface",
    "ferri/ferrocyanide redox couple",
    "Fe2+/Fe3+ redox hydrogel",
    "PVA hydrogel electrolyte",
    "gelatin/GelMA hydrogel",
    "iodide/triiodide redox couple",
    "thermogalvanic electrolyte",
    "ionic liquid electrolyte",
    "deep eutectic/eutogel electrolyte",
    "MXene/carbon photothermal scaffold",
    "PEDOT:PSS redox/electrode system",
    "cellulose hydrogel scaffold",
}

MECHANISM_TAGS = {
    "thermodiffusion/Soret transport",
    "ion transport/diffusion/migration",
    "redox entropy engineering",
    "selective solvation entropy",
    "redox concentration gradient",
    "salting-out/crystallization transition",
    "chaotropic polymer-water regulation",
    "host-guest/crown-ether complexation",
    "photothermal/radiative thermal management",
    "self-powered sensing/wearable interface",
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
    return re.sub(r"\s+", " ", text).strip(" ;,.")


def tags_for(text):
    low = clean_text(text).lower()
    return [label for label, pat in CANONICAL_PATTERNS if re.search(pat, low)]


def make_entries():
    df = pd.read_csv(DATA)
    rows = []
    tag_rows = []
    for i, row in df.iterrows():
        paper_id = f"TG_{i:04d}"
        for role, col in [("material", "材料"), ("mechanism", "机制")]:
            text = clean_text(row[col])
            if not text:
                continue
            entry_id = f"{paper_id}_{role}"
            rows.append(
                {
                    "entry_id": entry_id,
                    "paper_id": paper_id,
                    "year": int(row["年份"]),
                    "title": row["文章名"],
                    "doi": row["DOI"],
                    "role": role,
                    "text": text,
                }
            )
            for tag in tags_for(text):
                tag_rows.append(
                    {
                        "entry_id": entry_id,
                        "paper_id": paper_id,
                        "year": int(row["年份"]),
                        "role": role,
                        "tag": tag,
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(tag_rows)


def embed_texts(texts):
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=5000)
    word = TfidfVectorizer(analyzer="word", ngram_range=(1, 3), min_df=1, max_features=5000)
    X = np.hstack([char.fit_transform(texts).toarray(), word.fit_transform(texts).toarray()])
    n_components = min(120, X.shape[0] - 2, X.shape[1] - 1)
    X = TruncatedSVD(n_components=n_components, random_state=21).fit_transform(X)
    X = normalize(X)
    return umap.UMAP(n_neighbors=20, min_dist=0.08, metric="cosine", random_state=21).fit_transform(X)


def make_label_table(entries, tag_rows, min_papers=3):
    tagged = tag_rows.merge(entries[["entry_id", "x", "y"]], on="entry_id", how="left")
    labels = (
        tagged.groupby("tag", as_index=False)
        .agg(
            doc_freq=("paper_id", "nunique"),
            first_year=("year", "min"),
            last_year=("year", "max"),
            x=("x", "mean"),
            y=("y", "mean"),
            roles=("role", lambda x: "/".join(sorted(set(x)))),
        )
    )
    labels = labels[labels["doc_freq"] >= min_papers].copy()
    labels["recentness"] = (labels["last_year"] >= 2024).astype(int) * 3
    labels["label_score"] = labels["doc_freq"] * 2 + (labels["last_year"] - labels["first_year"] + 1) + labels["recentness"]
    return labels.sort_values(["label_score", "doc_freq"], ascending=False).head(16)


def make_role_label_table(entries, tag_rows, role, min_papers=2, max_labels=12):
    role_tags = tag_rows[tag_rows["role"] == role].merge(entries[["entry_id", "x", "y"]], on="entry_id", how="left")
    labels = (
        role_tags.groupby("tag", as_index=False)
        .agg(
            doc_freq=("paper_id", "nunique"),
            first_year=("year", "min"),
            last_year=("year", "max"),
            x=("x", "mean"),
            y=("y", "mean"),
        )
    )
    labels = labels[labels["doc_freq"] >= min_papers].copy()
    allowed = MATERIAL_TAGS if role == "material" else MECHANISM_TAGS
    labels = labels[labels["tag"].isin(allowed)].copy()
    labels["label_score"] = labels["doc_freq"] * 2 + (labels["last_year"] - labels["first_year"] + 1)
    return labels.sort_values(["label_score", "doc_freq"], ascending=False).head(max_labels)


def draw(entries, labels):
    x = entries["x"].to_numpy()
    y = entries["y"].to_numpy()
    pad_x = (x.max() - x.min()) * 0.16
    pad_y = (y.max() - y.min()) * 0.14
    xlim = (x.min() - pad_x, x.max() + pad_x)
    ylim = (y.min() - pad_y, y.max() + pad_y)
    xx, yy = np.mgrid[xlim[0] : xlim[1] : 280j, ylim[0] : ylim[1] : 280j]
    kde = gaussian_kde(np.vstack([x, y]), bw_method=0.20)
    zz = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
    cmap = LinearSegmentedColormap.from_list("nmi_density", ["#3b0f70", "#2f6f9f", "#28a878", "#a6d96a", "#fde725"])

    fig, ax = plt.subplots(figsize=(7.2, 6.0), constrained_layout=True)
    density = ax.contourf(xx, yy, zz, levels=80, cmap=cmap, alpha=0.88)
    for role, color in [("material", "#223b73"), ("mechanism", "#2f6448")]:
        sub = entries[entries["role"] == role]
        ax.scatter(sub["x"], sub["y"], s=9, c=color, alpha=0.35, lw=0, rasterized=True, label=role.capitalize())
    ax.scatter(labels["x"], labels["y"], s=22, c="#e60012", edgecolor="white", linewidth=0.25, zorder=5, label="Most recurrent theme")
    for i, row in enumerate(labels.itertuples()):
        dx = 0.08 if i % 3 != 0 else -0.08
        dy = 0.08 if i % 2 == 0 else -0.08
        ax.text(
            row.x + dx,
            row.y + dy,
            row.tag,
            fontsize=5.8,
            ha="left" if dx > 0 else "right",
            va="center",
            color="#202020",
            bbox=dict(boxstyle="square,pad=0.13", facecolor="white", edgecolor="none", alpha=0.68),
            zorder=6,
        )
    ax.set_xlabel("UMAP component 1")
    ax.set_ylabel("UMAP component 2")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_title("TG raw material/mechanism embedding density", loc="left", fontsize=9.5, pad=7)
    cbar = fig.colorbar(density, ax=ax, shrink=0.86, pad=0.02)
    cbar.set_label("Kernel density estimate", rotation=270, labelpad=12)
    leg = ax.legend(loc="upper right", fontsize=6.5, frameon=True, facecolor="white", edgecolor="none", framealpha=0.68)
    for text in leg.get_texts():
        text.set_color("#3d4864")
    return fig


def density_panel(ax, sub, labels, title, point_color, label_color):
    x = sub["x"].to_numpy()
    y = sub["y"].to_numpy()
    all_x = entries_global["x"].to_numpy()
    all_y = entries_global["y"].to_numpy()
    pad_x = (all_x.max() - all_x.min()) * 0.12
    pad_y = (all_y.max() - all_y.min()) * 0.14
    xlim = (all_x.min() - pad_x, all_x.max() + pad_x)
    ylim = (all_y.min() - pad_y, all_y.max() + pad_y)
    xx, yy = np.mgrid[xlim[0] : xlim[1] : 220j, ylim[0] : ylim[1] : 220j]
    kde = gaussian_kde(np.vstack([x, y]), bw_method=0.22)
    zz = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
    zz = np.ma.masked_less(zz, zz.max() * 0.055)
    cmap = LinearSegmentedColormap.from_list(
        f"{title}_density",
        ["#ffffff", "#dbeafe", "#8ecae6", "#52b788", "#f6d365"],
    )
    density = ax.contourf(xx, yy, zz, levels=42, cmap=cmap, alpha=0.92)
    ax.scatter(sub["x"], sub["y"], s=4.2, c=point_color, alpha=0.30, lw=0, rasterized=True)
    ax.scatter(labels["x"], labels["y"], s=20, c=label_color, edgecolor="white", linewidth=0.25, zorder=5)
    offsets = [(-0.95, 0.34), (0.18, 0.28), (-0.55, -0.22), (0.34, -0.30), (-0.22, -0.52), (0.46, 0.10)]
    for i, row in enumerate(labels.itertuples()):
        dx, dy = offsets[i % len(offsets)]
        ax.annotate(
            row.tag,
            xy=(row.x, row.y),
            xytext=(row.x + dx, row.y + dy),
            fontsize=5.6,
            ha="left" if dx > 0 else "right",
            va="center",
            color="#202020",
            bbox=dict(boxstyle="square,pad=0.12", facecolor="white", edgecolor="none", alpha=0.76),
            arrowprops=dict(arrowstyle="-", color="#7b8794", lw=0.35, shrinkA=1.5, shrinkB=1.5),
            zorder=6,
        )
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_title(title, loc="left", fontsize=8.5, pad=5)
    ax.set_xlabel("UMAP component 1")
    ax.set_ylabel("UMAP component 2")
    ax.set_facecolor("white")
    return density


def draw_split(entries, material_labels, mechanism_labels):
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.65), constrained_layout=True, sharex=True, sharey=True)
    density_panel(
        axes[0],
        entries[entries["role"] == "material"],
        material_labels,
        "TG material landscape",
        "#31527f",
        "#d7191c",
    )
    density = density_panel(
        axes[1],
        entries[entries["role"] == "mechanism"],
        mechanism_labels,
        "TG mechanism landscape",
        "#2d6a4f",
        "#d7191c",
    )
    cbar = fig.colorbar(density, ax=axes, shrink=0.82, pad=0.015)
    cbar.set_label("Kernel density estimate", rotation=270, labelpad=12)
    return fig


def main():
    global entries_global
    entries, tag_rows = make_entries()
    coords = embed_texts(entries["text"].tolist())
    entries["x"] = coords[:, 0]
    entries["y"] = coords[:, 1]
    entries_global = entries
    labels = make_label_table(entries, tag_rows, min_papers=3)
    material_labels = make_role_label_table(entries, tag_rows, "material", min_papers=2, max_labels=5)
    mechanism_labels = make_role_label_table(entries, tag_rows, "mechanism", min_papers=2, max_labels=6)
    entries.to_csv(OUT / "tg_full_material_mechanism_entries_embedding_source.csv", index=False)
    tag_rows.to_csv(OUT / "tg_full_material_mechanism_entry_tags.csv", index=False)
    labels.to_csv(OUT / "tg_full_material_mechanism_embedding_labels.csv", index=False)
    material_labels.to_csv(OUT / "tg_material_embedding_labels.csv", index=False)
    mechanism_labels.to_csv(OUT / "tg_mechanism_embedding_labels.csv", index=False)
    fig = draw(entries, labels)
    stem = OUT / "tg_full_material_mechanism_embedding_density_map"
    fig.savefig(stem.with_suffix(".png"), dpi=700, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=700, bbox_inches="tight")
    plt.close(fig)
    split_fig = draw_split(entries, material_labels, mechanism_labels)
    split_stem = OUT / "tg_material_vs_mechanism_embedding_density_map"
    split_fig.savefig(split_stem.with_suffix(".png"), dpi=700, bbox_inches="tight")
    split_fig.savefig(split_stem.with_suffix(".svg"), bbox_inches="tight")
    split_fig.savefig(split_stem.with_suffix(".pdf"), bbox_inches="tight")
    split_fig.savefig(split_stem.with_suffix(".tiff"), dpi=700, bbox_inches="tight")
    plt.close(split_fig)
    print("entries", len(entries))
    print("papers", entries["paper_id"].nunique())
    print("labels", len(labels))
    print("outputs", OUT)


if __name__ == "__main__":
    main()
