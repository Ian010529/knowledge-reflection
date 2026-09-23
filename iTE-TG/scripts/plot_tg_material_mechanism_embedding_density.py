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
DATA = Path("/Users/ryan/Documents/Codex/2026-07-15/r/work/TG_first333_material_mechanism.csv")
OUT = ROOT / "work" / "tg_material_mechanism_density_map"
OUT.mkdir(exist_ok=True)

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


CANONICAL_PATTERNS = [
    ("Fe2+/Fe3+ redox hydrogel", r"fe2\+|fe3\+|ferric|ferrous|iron-based"),
    ("ferri/ferrocyanide redox couple", r"ferri|ferrocyanide|fe\(cn\)|\[fe\(cn\)6\]"),
    ("iodide/triiodide redox couple", r"iodide|triiodide|i-/i3|polyiodide"),
    ("organic redox couple", r"tempo|viologen|quinone|pyrazine|organic redox|hydroquinone|benzoquinone"),
    ("PVA hydrogel electrolyte", r"\bpva\b|poly\(vinyl alcohol\)|polyvinyl alcohol"),
    ("alginate hydrogel", r"alginate"),
    ("gelatin/GelMA hydrogel", r"gelatin|gelma"),
    ("cellulose hydrogel scaffold", r"cellulose|nanocellulose|bacterial cellulose"),
    ("ionogel electrolyte", r"ionogel"),
    ("deep eutectic/eutogel electrolyte", r"deep eutectic|\bdes\b|eutogel|eutectogel"),
    ("ionic liquid electrolyte", r"ionic liquid|imidazolium|emim|bmim"),
    ("PEDOT:PSS redox/electrode system", r"pedot|pss"),
    ("MXene/carbon photothermal scaffold", r"mxene|ti3c2|carbon|cnt|graphene"),
    ("porous/redox electrode interface", r"electrode|carbon cloth|porous|aerogel|charge transfer|redox kinetics"),
    ("hydrogel thermocell platform", r"hydrogel|thermocell"),
    ("thermogalvanic electrolyte", r"thermogalvanic electrolyte|redox electrolyte|liquid electrolyte"),
    ("selective solvation entropy", r"selective .*solvation|solvation entropy|solvation shell|hydration shell|nitrile|clo4|water structure"),
    ("redox entropy engineering", r"redox entropy|reaction entropy|entropy change|entropy difference"),
    ("thermodiffusion/Soret transport", r"thermodiffusion|soret|thermal diffusion|thermophoretic"),
    ("ion transport/diffusion/migration", r"ion transport|ionic transport|ion diffusion|ion migration|mass transport|mobility"),
    ("redox concentration gradient", r"concentration gradient|redox gradient|species redistribution"),
    ("salting-out/crystallization transition", r"salting-out|crystallization|phase transition|phase change|micellization"),
    ("chaotropic polymer-water regulation", r"chaotropic|polymer-water|hydrogen bonding|water retention|antifreezing|anti-freezing"),
    ("host-guest/crown-ether complexation", r"host-guest|cyclodextrin|crown ether|complexation|coordination"),
    ("photothermal/radiative thermal management", r"photothermal|radiative cooling|solar|evaporation"),
    ("self-powered sensing/wearable interface", r"sensing|sensor|wearable|e-skin|skin|wound|biometric|fingertip|strain|pressure"),
]

BAD_LABEL_RE = re.compile(
    r"seebeck|power density|thermal conductivity|temperature difference|temperature gradient|"
    r"efficiency|performance|voltage output|thermopower$",
    re.I,
)


def clean_text(text):
    text = str(text).strip()
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ;,.")


def canonical_tags(text, role):
    low = clean_text(text).lower()
    tags = []
    for label, pat in CANONICAL_PATTERNS:
        if re.search(pat, low):
            tags.append(label)
    # Keep a few compact source phrases when they are already readable.
    chunks = re.split(r";|,| while | whereas | through | via | by | enabled by | with ", clean_text(text))
    for chunk in chunks:
        chunk = clean_text(chunk)
        if 18 <= len(chunk) <= 74 and re.search(r"hydrogel|redox|solvation|thermodiffusion|soret|ion |electrode|eutectic|polymer|cellulose|crystallization|chaotropic", chunk, re.I):
            if not BAD_LABEL_RE.search(chunk):
                tags.append(chunk)
    out = []
    seen = set()
    for tag in tags:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            out.append(tag)
    return out


def make_nodes():
    df = pd.read_csv(DATA)
    rows = []
    for i, row in df.iterrows():
        paper_id = f"TG_{i:04d}"
        for role, col in [("material", "材料"), ("mechanism", "机制")]:
            for tag in canonical_tags(row[col], role):
                rows.append(
                    {
                        "paper_id": paper_id,
                        "year": int(row["年份"]),
                        "title": row["文章名"],
                        "doi": row["DOI"],
                        "role": role,
                        "phrase": tag,
                    }
                )
    nodes = pd.DataFrame(rows).drop_duplicates(["paper_id", "role", "phrase"])
    counts = nodes.groupby("phrase")["paper_id"].nunique()
    keep = counts[counts >= 2].index
    nodes = nodes[nodes["phrase"].isin(keep)].copy()
    return nodes


def embed_phrases(phrases):
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    word = TfidfVectorizer(analyzer="word", ngram_range=(1, 3), min_df=1)
    X = np.hstack([char.fit_transform(phrases).toarray(), word.fit_transform(phrases).toarray()])
    n_components = min(80, X.shape[0] - 1, X.shape[1] - 1)
    X = TruncatedSVD(n_components=n_components, random_state=17).fit_transform(X)
    X = normalize(X)
    return umap.UMAP(n_neighbors=12, min_dist=0.10, metric="cosine", random_state=17).fit_transform(X)


def pick_labels(meta, tile_size=1.2, max_labels=34):
    d = meta.copy()
    d["tile_x"] = np.floor((d["x"] - d["x"].min()) / tile_size).astype(int)
    d["tile_y"] = np.floor((d["y"] - d["y"].min()) / tile_size).astype(int)
    d["label_score"] = d["doc_freq"] * 2 + d["paper_span"] + d["recentness"]
    role_bonus = d["role"].map({"mechanism": 8, "material": 5}).fillna(0)
    d["label_score"] += role_bonus
    picked = (
        d.sort_values(["label_score", "doc_freq"], ascending=False)
        .groupby(["tile_x", "tile_y"], as_index=False)
        .head(1)
        .sort_values(["label_score", "doc_freq"], ascending=False)
    )
    picked = picked.drop_duplicates("phrase", keep="first").head(max_labels)
    return picked


def draw(meta, labels):
    x = meta["x"].to_numpy()
    y = meta["y"].to_numpy()
    pad_x = (x.max() - x.min()) * 0.24
    pad_y = (y.max() - y.min()) * 0.18
    xlim = (x.min() - pad_x, x.max() + pad_x)
    ylim = (y.min() - pad_y, y.max() + pad_y)
    xx, yy = np.mgrid[xlim[0] : xlim[1] : 260j, ylim[0] : ylim[1] : 260j]
    kde = gaussian_kde(np.vstack([x, y]), bw_method=0.22)
    zz = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
    cmap = LinearSegmentedColormap.from_list("nmi_density", ["#3b0f70", "#2f6f9f", "#28a878", "#a6d96a", "#fde725"])

    fig, ax = plt.subplots(figsize=(7.2, 6.0), constrained_layout=True)
    density = ax.contourf(xx, yy, zz, levels=80, cmap=cmap, alpha=0.88)
    colors = {"material": "#243b73", "mechanism": "#315f4a", "both": "#5c4a7d"}
    for role, sub in meta.groupby("role"):
        ax.scatter(sub["x"], sub["y"], s=10, c=colors.get(role, "#352060"), alpha=0.42, lw=0, rasterized=True, label=role.capitalize())
    ax.scatter(labels["x"], labels["y"], s=20, c="#e60012", edgecolor="white", linewidth=0.25, zorder=5, label="Most recurrent material/mechanism")

    for i, row in enumerate(labels.itertuples()):
        dx = 0.08 if i % 3 != 0 else -0.08
        dy = 0.08 if i % 2 == 0 else -0.08
        ax.text(
            row.x + dx,
            row.y + dy,
            row.phrase,
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
    ax.set_title("TG materials and mechanisms in embedding space", loc="left", fontsize=9.5, pad=7)
    cbar = fig.colorbar(density, ax=ax, shrink=0.86, pad=0.02)
    cbar.set_label("Kernel density estimate", rotation=270, labelpad=12)
    leg = ax.legend(loc="upper right", fontsize=6.5, frameon=True, facecolor="white", edgecolor="none", framealpha=0.68)
    for text in leg.get_texts():
        text.set_color("#3d4864")
    return fig


def main():
    nodes = make_nodes()
    meta = (
        nodes.groupby("phrase", as_index=False)
        .agg(
            doc_freq=("paper_id", "nunique"),
            first_year=("year", "min"),
            last_year=("year", "max"),
            role=("role", lambda x: "both" if x.nunique() > 1 else x.iloc[0]),
        )
    )
    meta["paper_span"] = meta["last_year"] - meta["first_year"] + 1
    meta["recentness"] = (meta["last_year"] >= 2024).astype(int) * 3
    coords = embed_phrases(meta["phrase"].tolist())
    meta["x"] = coords[:, 0]
    meta["y"] = coords[:, 1]
    labels = pick_labels(meta)
    nodes.to_csv(OUT / "tg_material_mechanism_nodes_by_paper.csv", index=False)
    meta.to_csv(OUT / "tg_material_mechanism_embedding_source.csv", index=False)
    labels.to_csv(OUT / "tg_material_mechanism_embedding_labels.csv", index=False)

    fig = draw(meta, labels)
    stem = OUT / "tg_material_mechanism_embedding_density_map"
    fig.savefig(stem.with_suffix(".png"), dpi=700, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=700, bbox_inches="tight")
    plt.close(fig)
    print("nodes", len(meta))
    print("paper-node rows", len(nodes))
    print("papers", nodes["paper_id"].nunique())
    print("labels", len(labels))
    print("outputs", OUT)


if __name__ == "__main__":
    main()
