"""Portfolio-ready charts generated from the Python model outputs."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .engine import LBOResult


NAVY = "#17365D"
BLUE = "#4472C4"
LIGHT_BLUE = "#9DC3E6"
GREEN = "#70AD47"
RED = "#C00000"
GOLD = "#BF9000"
GREY = "#7F8C8D"


def _apply_style(ax: plt.Axes, title: str, ylabel: str = "") -> None:
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=NAVY)
    ax.set_ylabel(ylabel, color="#404040")
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#BFBFBF")
    ax.grid(axis="y", color="#E7E6E6", linewidth=0.7)
    ax.tick_params(colors="#595959")


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generate_charts(
    base_result: LBOResult,
    sensitivities: dict[str, pd.DataFrame],
    assets_dir: str | Path,
) -> list[Path]:
    """Generate all README and presentation charts from model data."""

    output_dir = Path(assets_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    operating = base_result.operating_model
    debt = base_result.debt_schedule
    years = operating.index.to_numpy()
    paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    ax.plot(years, operating["Revenue"] / 1e6, marker="o", color=BLUE, label="Revenue")
    ax.plot(years, operating["EBITDA"] / 1e6, marker="o", color=GREEN, label="EBITDA")
    _apply_style(ax, "Revenue and EBITDA evolution", "€ millions")
    ax.set_xticks(years, [f"Year {year}" for year in years])
    ax.legend(frameon=False, ncol=2, loc="upper left")
    path = output_dir / "revenue_ebitda.png"
    _save(fig, path)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(8.8, 4.2))
    ax.plot(
        years,
        operating["EBITDA Margin"] * 100,
        marker="o",
        linewidth=2.5,
        color=GOLD,
    )
    _apply_style(ax, "EBITDA margin evolution", "EBITDA margin (%)")
    ax.set_xticks(years, [f"Year {year}" for year in years])
    path = output_dir / "ebitda_margin.png"
    _save(fig, path)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    bottom = np.zeros(len(debt))
    colors = [BLUE, LIGHT_BLUE, GREY]
    for tranche, color in zip(base_result.debt_assumptions.tranches, colors):
        values = debt[f"{tranche.name} Closing"].to_numpy() / 1e6
        ax.bar(debt.index, values, bottom=bottom, label=tranche.name, color=color)
        bottom += values
    _apply_style(ax, "Debt paydown and deleveraging", "Closing debt (€ millions)")
    ax.set_xticks(debt.index, [f"Year {year}" for year in debt.index])
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    path = output_dir / "debt_paydown.png"
    _save(fig, path)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(8.8, 4.2))
    ax.plot(
        debt.index,
        debt["Net Debt / EBITDA"],
        marker="o",
        linewidth=2.5,
        color=NAVY,
    )
    _apply_style(ax, "Net leverage profile", "Net Debt / EBITDA (x)")
    ax.set_xticks(debt.index, [f"Year {year}" for year in debt.index])
    ax.axhline(3.0, color="#BFBFBF", linewidth=1, linestyle="--")
    path = output_dir / "net_leverage.png"
    _save(fig, path)
    paths.append(path)

    bridge = base_result.value_creation
    start_value = float(bridge.iloc[0]["Amount"]) / 1e6
    changes = bridge.iloc[1:-1].copy()
    change_values = changes["Amount"].to_numpy(dtype=float) / 1e6
    end_value = float(bridge.iloc[-1]["Amount"]) / 1e6
    labels = ["Entry equity"] + changes["Component"].tolist() + ["Exit equity"]
    signed_values = [start_value] + change_values.tolist() + [end_value]
    heights = [start_value]
    bottoms = [0.0]
    running = start_value
    for change in change_values:
        bottoms.append(min(running, running + change))
        heights.append(abs(change))
        running += change
    bottoms.append(0.0)
    heights.append(end_value)
    colors = [NAVY] + [GREEN if value >= 0 else RED for value in change_values] + [GOLD]
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    ax.bar(range(len(heights)), heights, bottom=bottoms, color=colors, width=0.7)
    for index, (value, height, bottom) in enumerate(zip(signed_values, heights, bottoms)):
        y_position = bottom + height if value >= 0 else bottom
        ax.text(
            index,
            y_position + (8 if value >= 0 else -8),
            f"€{value:,.0f}M",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=8,
            color="#404040",
        )
    _apply_style(ax, "Sponsor equity value creation", "€ millions")
    ax.set_xticks(range(len(labels)), labels, rotation=25, ha="right")
    path = output_dir / "equity_value_creation.png"
    _save(fig, path)
    paths.append(path)

    sensitivity = sensitivities["Entry x Exit IRR"]
    fig, ax = plt.subplots(figsize=(7.4, 5.8))
    image = ax.imshow(sensitivity.to_numpy() * 100, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(sensitivity.columns)), [f"{value:.1f}x" for value in sensitivity.columns])
    ax.set_yticks(range(len(sensitivity.index)), [f"{value:.1f}x" for value in sensitivity.index])
    ax.set_xlabel("Exit multiple")
    ax.set_ylabel("Entry multiple")
    ax.set_title("IRR sensitivity: entry multiple × exit multiple", loc="left", fontsize=13, fontweight="bold", color=NAVY)
    for row in range(len(sensitivity.index)):
        for column in range(len(sensitivity.columns)):
            value = sensitivity.iloc[row, column] * 100
            ax.text(column, row, f"{value:.1f}%", ha="center", va="center", fontsize=9, color="#202020")
    colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label("Sponsor IRR (%)")
    path = output_dir / "irr_sensitivity_heatmap.png"
    _save(fig, path)
    paths.append(path)

    return paths
