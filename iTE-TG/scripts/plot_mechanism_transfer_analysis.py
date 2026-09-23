from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path("/Users/ryan/Documents/iTE&TG")
FLOW = ROOT / "mechanism_transfer_workflow"
FIG = FLOW / "figures"
FIG.mkdir(exist_ok=True)

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
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)

COLORS = {
    "signal": "#197278",
    "accent": "#D95D39",
    "neutral": "#A7B0B5",
    "light": "#DCE3E6",
    "dark": "#27343A",
}


def save(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")


def main() -> None:
    events = pd.read_csv(FLOW / "mechanism_pair_transfer_events.csv")
    transfers = events[events.transfer_status.eq("iTE_then_TG")].copy()
    status_order = ["iTE_only", "iTE_then_TG", "same_year", "TG_then_iTE", "TG_only"]
    status_labels = [
        "iTE only",
        "iTE → TG",
        "Same year",
        "TG → iTE",
        "TG only",
    ]
    status = (
        events.transfer_status.value_counts().reindex(status_order).fillna(0)
    )

    lags = transfers.transfer_lag_years.dropna().astype(int)
    lag_counts = lags.value_counts().sort_index()
    cumulative = np.array([(lags <= year).mean() for year in range(1, 11)])
    annual = (
        transfers.groupby("tg_first_year").size().rename("count").reset_index()
    )
    annual = annual[annual.tg_first_year >= 2015]

    events["type_pair"] = events.apply(
        lambda row: " + ".join(sorted([row.u_type, row.v_type])), axis=1
    )
    type_stats = (
        events[events.transfer_status.isin(["iTE_only", "iTE_then_TG"])]
        .groupby("type_pair")
        .transfer_status.value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )
    for column in ["iTE_only", "iTE_then_TG"]:
        if column not in type_stats:
            type_stats[column] = 0
    type_stats["eligible"] = type_stats.iTE_only + type_stats.iTE_then_TG
    type_stats["transfer_rate"] = (
        type_stats.iTE_then_TG / type_stats.eligible
    )
    type_stats = type_stats[type_stats.eligible >= 8].nlargest(
        9, "eligible"
    ).sort_values("transfer_rate")
    short_type = {
        "transport_mechanism": "transport",
        "solvation_entropy": "solvation/entropy",
        "gel_microstructure": "gel structure",
        "phase_or_species_transition": "phase/species",
        "electrode_interface": "electrode interface",
        "device_mechanism": "device",
    }
    type_labels = [
        " + ".join(short_type.get(part, part) for part in value.split(" + "))
        for value in type_stats.type_pair
    ]

    fig = plt.figure(figsize=(7.2, 5.8), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1.05, 1])
    axes = [
        fig.add_subplot(grid[0, 0]),
        fig.add_subplot(grid[0, 1]),
        fig.add_subplot(grid[1, 0]),
        fig.add_subplot(grid[1, 1]),
    ]

    ax = axes[0]
    bars = ax.barh(
        range(len(status)),
        status.values,
        color=[
            COLORS["neutral"],
            COLORS["signal"],
            COLORS["light"],
            COLORS["accent"],
            COLORS["light"],
        ],
        height=0.62,
    )
    ax.set_yticks(range(len(status)), status_labels)
    ax.invert_yaxis()
    ax.set_xlabel("Unique pure-mechanism pairs")
    ax.set_title("a  Most relations remain domain-specific", loc="left", fontsize=8)
    for bar, value in zip(bars, status.values):
        ax.text(value + 4, bar.get_y() + bar.get_height() / 2, str(int(value)), va="center")
    ax.set_xlim(0, max(status.values) * 1.18)

    ax = axes[1]
    bins = np.arange(0.5, min(10.5, lags.max() + 1.5), 1)
    ax.hist(lags.clip(upper=10), bins=bins, color=COLORS["signal"], alpha=0.85)
    ax.set_xlabel("Transfer lag (years; ≥10 pooled)")
    ax.set_ylabel("Transferred pairs")
    ax.set_title("b  Transfer typically occurs within five years", loc="left", fontsize=8)
    twin = ax.twinx()
    twin.plot(range(1, 11), cumulative * 100, color=COLORS["accent"], marker="o", ms=2.8)
    twin.axhline(80, color=COLORS["neutral"], lw=0.8, ls="--")
    twin.set_ylabel("Cumulative transferred (%)")
    twin.set_ylim(0, 105)
    ax.text(0.03, 0.93, "median = 3 y", transform=ax.transAxes, va="top", color=COLORS["dark"])

    ax = axes[2]
    ax.bar(
        annual.tg_first_year.astype(int),
        annual["count"],
        color=COLORS["signal"],
        width=0.72,
    )
    ax.set_xlabel("First appearance in TG")
    ax.set_ylabel("New iTE → TG pairs")
    ax.set_title("c  Observed transfer is concentrated in recent TG growth", loc="left", fontsize=8)
    ax.set_xticks(annual.tg_first_year.astype(int)[::2])

    ax = axes[3]
    ax.barh(
        range(len(type_stats)),
        type_stats.transfer_rate * 100,
        color=COLORS["accent"],
        height=0.58,
    )
    ax.set_yticks(range(len(type_stats)), type_labels)
    ax.set_xlabel("Observed transfer rate (%)")
    ax.set_title("d  Transfer differs across mechanism families", loc="left", fontsize=8)
    for index, row in enumerate(type_stats.itertuples(index=False)):
        ax.text(
            row.transfer_rate * 100 + 1,
            index,
            f"{int(row.iTE_then_TG)}/{int(row.eligible)}",
            va="center",
            fontsize=6,
        )
    ax.set_xlim(0, max(type_stats.transfer_rate * 100) * 1.28)

    fig.suptitle(
        "Mechanism-pair knowledge flow from ionic thermoelectrics to thermogalvanics",
        x=0.01,
        ha="left",
        fontsize=10,
        fontweight="bold",
    )
    save(fig, FIG / "mechanism_transfer_analysis")
    plt.close(fig)
    type_stats.assign(display_label=type_labels).to_csv(
        FLOW / "mechanism_type_transfer_rates.csv", index=False
    )


if __name__ == "__main__":
    main()
