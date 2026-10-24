"""Shared helpers: data loading, feature lists and plot style used by every step."""
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "nadu_clean_v7.csv"
FIG = ROOT / "figures"
RES = ROOT / "results"
MODELS = ROOT / "models"
for p in (FIG, RES, MODELS):
    p.mkdir(exist_ok=True)

TARGET = "wholesale_price"
HORIZON = 12

# Validated categorical palette (dataviz reference, light mode)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, SHADE = "#0b0b0b", "#52514e", "#e4e3df", "#d9d8d3"

CRISES = {  # shaded on time-series figures
    "2008 food crisis": ("2007-11-01", "2008-12-01"),
    "COVID-19": ("2020-03-01", "2021-12-01"),
    "Fertilizer ban": ("2021-05-01", "2021-11-01"),
    "2022 economic crisis": ("2022-01-01", "2023-06-01"),
}


def load():
    df = pd.read_csv(DATA, parse_dates=["date"]).set_index("date")
    df.index.freq = "MS"
    return df


def style():
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 300, "savefig.bbox": "tight",
        "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
        "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False,
        "lines.linewidth": 2, "legend.frameon": False,
    })


def shade_crises(ax, label=True):
    for i, (name, (a, b)) in enumerate(CRISES.items()):
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=SHADE, alpha=0.6, lw=0, zorder=0)
        if label:
            ax.text(pd.Timestamp(a), 0.03 + 0.06 * [0, 0, 1, 2][i], name, transform=ax.get_xaxis_transform(),
                    fontsize=7, color=MUTED, va="bottom")


def mape(y, p):
    y, p = np.asarray(y), np.asarray(p)
    return float(np.mean(np.abs((y - p) / y)) * 100)


def rmse(y, p):
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))
