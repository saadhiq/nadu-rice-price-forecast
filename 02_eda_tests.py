"""
Step 2 - Exploratory analysis and econometric diagnostics.

Outputs
  figures/fig1_price_history.png ... fig6_correlations.png
  results/descriptive_stats.csv, unit_root_tests.csv, structural_breaks.csv,
  results/cointegration.csv, granger_causality.csv
"""
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller, coint, grangercausalitytests, kpss, zivot_andrews
from statsmodels.tsa.vector_ar.vecm import coint_johansen

from common import AQUA, BLUE, FIG, MUTED, ORANGE, RES, load, shade_crises, style

warnings.filterwarnings("ignore")
style()
df = load()

# Log-transformed series used throughout (prices are multiplicative / trending)
L = pd.DataFrame({
    "log_wholesale": np.log(df["wholesale_price"]),
    "log_retail": np.log(df["retail_price"]),
    "log_lkr_per_usd": np.log(df["lkr_per_usd"]),
    "log_thai_rice_usd": np.log(df["thai_rice_usd_t"]),
    "log_thai_rice_lkr": np.log(df["thai_rice_lkr_kg"]),
    "log_oil_lkr": np.log(df["oil_lkr_bbl"]),
    "log_last_harvest": np.log(df["last_harvest_prod_kt"]),
    "rain_mm": df["rain_mm"],
    "inflation_ccpi_pct": df["inflation_ccpi_pct"],
})

# ---------------------------------------------------------------- descriptive
desc_cols = ["wholesale_price", "retail_price", "margin_pct", "last_harvest_prod_kt", "rain_mm",
             "tmean_c", "oil_usd_bbl", "thai_rice_usd_t", "lkr_per_usd", "thai_rice_lkr_kg",
             "customs_duty_rs_kg", "fert_subsidy_prev_year_rs_mn", "inflation_ccpi_pct"]
desc = df[desc_cols].describe().T[["count", "mean", "std", "min", "50%", "max"]]
desc["cv_pct"] = desc["std"] / desc["mean"] * 100
desc.round(2).to_csv(RES / "descriptive_stats.csv")

# ---------------------------------------------------------------- Fig 1 price history
fig, ax = plt.subplots(figsize=(10, 4.2))
shade_crises(ax)
ax.plot(df.index, df["retail_price"], color=ORANGE, lw=1.6, label="Retail")
ax.plot(df.index, df["wholesale_price"], color=BLUE, label="Wholesale (Pettah, HARTI)")
ax.set_ylabel("Rs per kg")
ax.set_title("Nadu rice prices, Jan 2000 - Jun 2026")
ax.legend(loc="upper left", bbox_to_anchor=(0, 0.9))
fig.savefig(FIG / "fig1_price_history.png"); plt.close(fig)

# ---------------------------------------------------------------- Fig 2 seasonal profile
trend = np.log(df["wholesale_price"]).rolling(12, center=True).mean()
seas = ((np.log(df["wholesale_price"]) - trend) * 100).groupby(df["month"]).agg(["mean", "sem"])
fig, ax = plt.subplots(figsize=(8, 3.8))
harvest = df.groupby("month")["is_harvest_month"].first()
colors = [ORANGE if harvest[m] else BLUE for m in seas.index]
ax.bar(seas.index, seas["mean"], color=colors, width=0.7, yerr=1.96 * seas["sem"],
       error_kw=dict(ecolor=MUTED, lw=1, capsize=2))
ax.axhline(0, color=MUTED, lw=0.8)
ax.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
ax.set_ylabel("% deviation from 12-month trend")
ax.set_title("Seasonal pattern of wholesale price (orange = harvest months)")
fig.savefig(FIG / "fig2_seasonality.png"); plt.close(fig)
seas.round(3).to_csv(RES / "seasonal_index.csv")

# ---------------------------------------------------------------- Fig 3 drivers (indexed, log scale)
idx = df[["wholesale_price", "thai_rice_lkr_kg", "lkr_per_usd"]].div(
    df[["wholesale_price", "thai_rice_lkr_kg", "lkr_per_usd"]].iloc[:12].mean()) * 100
fig, ax = plt.subplots(figsize=(10, 4.2))
shade_crises(ax, label=False)
ax.plot(idx.index, idx["wholesale_price"], color=BLUE, label="Nadu wholesale")
ax.plot(idx.index, idx["thai_rice_lkr_kg"], color=ORANGE, lw=1.6, label="Thai 5% rice (LKR/kg)")
ax.plot(idx.index, idx["lkr_per_usd"], color=AQUA, lw=1.6, label="LKR per USD")
ax.set_yscale("log"); ax.set_ylabel("Index, 2000 = 100 (log scale)")
ax.set_title("Domestic price vs import-parity drivers")
ax.legend(loc="upper left")
fig.savefig(FIG / "fig3_drivers_indexed.png"); plt.close(fig)

# ---------------------------------------------------------------- Fig 4 STL decomposition
stl = STL(L["log_wholesale"], period=12, robust=True).fit()
fig, axes = plt.subplots(4, 1, figsize=(10, 7), sharex=True)
for ax, s, name in zip(axes, [stl.observed, stl.trend, stl.seasonal, stl.resid],
                       ["Observed (log)", "Trend", "Seasonal", "Remainder"]):
    ax.plot(s.index, s, color=BLUE, lw=1.4); ax.set_ylabel(name, fontsize=9)
axes[0].set_title("STL decomposition of log wholesale price")
fig.savefig(FIG / "fig4_stl.png"); plt.close(fig)
strength_season = max(0, 1 - stl.resid.var() / (stl.resid + stl.seasonal).var())
strength_trend = max(0, 1 - stl.resid.var() / (stl.resid + stl.trend).var())

# ---------------------------------------------------------------- Fig 5 marketing margin
fig, ax = plt.subplots(figsize=(10, 3.5))
shade_crises(ax, label=False)
ax.plot(df.index, df["margin_pct"], color=BLUE, lw=1.4)
ax.set_ylabel("Retail over wholesale, %"); ax.set_title("Wholesale-retail marketing margin")
fig.savefig(FIG / "fig5_margin.png"); plt.close(fig)

# ---------------------------------------------------------------- Fig 6 correlations of monthly changes
D = L.diff().dropna().drop(columns=["log_retail"])
D.columns = [c.replace("log_", "Δlog ") if c.startswith("log_") else "Δ " + c for c in D.columns]
corr = D.corr()
cmap = LinearSegmentedColormap.from_list("div", [ORANGE, "#f2f1ee", BLUE])
fig, ax = plt.subplots(figsize=(7.5, 6))
im = ax.imshow(corr, cmap=cmap, vmin=-1, vmax=1)
ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right", fontsize=8)
ax.set_yticks(range(len(corr)), corr.columns, fontsize=8); ax.grid(False)
for i in range(len(corr)):
    for j in range(len(corr)):
        ax.text(j, i, f"{corr.iat[i, j]:.2f}", ha="center", va="center", fontsize=7)
fig.colorbar(im, ax=ax, shrink=0.8)
ax.set_title("Correlation of monthly changes")
fig.savefig(FIG / "fig6_correlations.png"); plt.close(fig)

# ---------------------------------------------------------------- unit-root tests
rows = []
for c in L.columns:
    for form, s in [("level", L[c]), ("first difference", L[c].diff())]:
        s = s.dropna()
        adf = adfuller(s, autolag="AIC", regression="ct" if form == "level" else "c")
        kp = kpss(s, regression="ct" if form == "level" else "c", nlags="auto")
        rows.append({"variable": c, "form": form, "ADF_stat": adf[0], "ADF_p": adf[1],
                     "KPSS_stat": kp[0], "KPSS_p": kp[1],
                     "verdict": "stationary" if adf[1] < 0.05 and kp[1] > 0.05
                     else "non-stationary" if adf[1] >= 0.05 and kp[1] <= 0.05 else "inconclusive"})
ur = pd.DataFrame(rows).round(4)
ur.to_csv(RES / "unit_root_tests.csv", index=False)

# ---------------------------------------------------------------- structural break (Zivot-Andrews)
za_rows = []
for c in ["log_wholesale", "log_thai_rice_lkr", "log_lkr_per_usd"]:
    s = L[c].dropna()
    stat, p, _, _, bp = zivot_andrews(s, regression="ct", autolag="AIC")
    za_rows.append({"variable": c, "ZA_stat": stat, "p_value": p, "break_date": s.index[bp].strftime("%Y-%m")})
za = pd.DataFrame(za_rows).round(4)
za.to_csv(RES / "structural_breaks.csv", index=False)

# ---------------------------------------------------------------- cointegration
co_rows = []
for x in ["log_thai_rice_lkr", "log_lkr_per_usd", "log_oil_lkr", "log_retail"]:
    t, p, _ = coint(L["log_wholesale"], L[x], trend="c")
    co_rows.append({"test": "Engle-Granger", "system": f"log_wholesale ~ {x}", "stat": t, "p_value": p,
                    "rank": np.nan})
sysvars = ["log_wholesale", "log_lkr_per_usd", "log_thai_rice_usd"]
jo = coint_johansen(L[sysvars].dropna(), det_order=0, k_ar_diff=2)
rank = int(np.sum(jo.lr1 > jo.cvt[:, 1]))
for r in range(len(sysvars)):
    co_rows.append({"test": "Johansen trace", "system": " + ".join(sysvars) + f" (H0: rank<={r})",
                    "stat": jo.lr1[r], "p_value": np.nan, "rank": rank,
                    "crit_5pct": jo.cvt[r, 1]})
co = pd.DataFrame(co_rows).round(4)
co.to_csv(RES / "cointegration.csv", index=False)

# ---------------------------------------------------------------- Granger causality (on changes)
g_rows = []
for x in ["log_lkr_per_usd", "log_thai_rice_usd", "log_oil_lkr", "log_last_harvest", "rain_mm"]:
    d = pd.concat([L["log_wholesale"].diff(), L[x].diff()], axis=1).dropna()
    res = grangercausalitytests(d, maxlag=6)
    best = min(res, key=lambda k: res[k][0]["ssr_ftest"][1])
    g_rows.append({"cause": x, "effect": "Δlog_wholesale", "best_lag": best,
                   "F": res[best][0]["ssr_ftest"][0], "p_value": res[best][0]["ssr_ftest"][1],
                   "p_lag3": res[3][0]["ssr_ftest"][1], "p_lag6": res[6][0]["ssr_ftest"][1]})
gc = pd.DataFrame(g_rows).round(4)
gc.to_csv(RES / "granger_causality.csv", index=False)

# ---------------------------------------------------------------- summary
print(f"STL strength: trend={strength_trend:.3f}, seasonal={strength_season:.3f}")
print("\nUnit roots\n", ur[["variable", "form", "ADF_p", "KPSS_p", "verdict"]].to_string(index=False))
print("\nZivot-Andrews\n", za.to_string(index=False))
print("\nCointegration\n", co.to_string(index=False))
print("\nGranger\n", gc.to_string(index=False))
print("\nSeasonal index (% vs trend)\n", seas["mean"].round(2).to_string())
pd.Series({"stl_trend_strength": strength_trend, "stl_seasonal_strength": strength_season}).to_csv(
    RES / "stl_strength.csv")
