"""
Step 5 - Long-horizon projection: wholesale price for ANY future month (e.g. August 2030).

Beyond 12 months no model can know the exchange rate, harvests or policy, so we project:
    log P(T) = trend level now + g * years ahead + seasonal effect of month(T)
  trend level now = average de-seasonalised log price of the last 3 months
  g               = expected inflation + real trend of rice prices (user assumption in the website)
  uncertainty     = empirical spread of h-month de-seasonalised changes, 2000-2026,
                    plus +/-5 pp/yr uncertainty in g (calibrated on the back-test)

Back-test: projections made from every origin 2005-2021 at 12, 24, 36, 48 and 60 months,
with g estimated only from data up to the origin, compared with the naive (no-change) forecast.

Outputs: results/long_horizon_params.json, long_horizon_backtest.csv, figures/fig11_long_horizon.png
"""
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import BLUE, FIG, MUTED, ORANGE, RES, load, mape, style

style()
df = load()
lp = np.log(df["wholesale_price"])

# Seasonal effect by month (centred so the 12 months sum to zero)
seas = pd.read_csv(RES / "seasonal_index.csv", index_col=0)["mean"] / 100
seas = seas - seas.mean()
ds = lp - df["month"].map(seas)  # de-seasonalised log price


def trend_growth(series):
    """Annual log growth = OLS slope of de-seasonalised log price on time."""
    return float(np.polyfit(np.arange(len(series)), series.values, 1)[0] * 12)


g_hist = trend_growth(ds)
infl_avg = float(df["inflation_ccpi_pct"].mean() / 100)
real_trend = g_hist - infl_avg

# Uncertainty: sd of de-seasonalised h-month log changes around their mean, made non-decreasing in h
sd = {}
for h in range(1, 121):
    ch = (ds.shift(-h) - ds).dropna()
    sd[h] = float(ch.std())
sd = pd.Series(sd).cummax()
# Growth itself is uncertain (inflation regimes change): +/-5 pp/yr, calibrated so the 80% range
# covers ~80% of outcomes at 2-5 years in the back-test below.
SD_GROWTH = 0.05
sd = np.sqrt(sd ** 2 + (SD_GROWTH * sd.index / 12) ** 2)

# ------------------------------------------------------------------ back-test of the projection method
rows = []
origins = pd.date_range("2005-01-01", "2021-06-01", freq="MS")
for origin in origins:
    hist = ds[:origin]
    g = trend_growth(hist)
    base = hist.iloc[-3:].mean()
    for h in (12, 24, 36, 48, 60):
        t = origin + pd.DateOffset(months=h)
        if t > df.index[-1]:
            continue
        proj = np.exp(base + g * h / 12 + seas[t.month])
        rows.append({"origin": origin, "h": h, "actual": df.loc[t, "wholesale_price"], "projection": proj,
                     "naive": df.loc[origin, "wholesale_price"]})
bt = pd.DataFrame(rows)
summary = bt.groupby("h")[["actual", "projection", "naive"]].apply(lambda g: pd.Series({
    "n_origins": len(g),
    "MAPE_projection": mape(g.actual, g.projection),
    "MAPE_naive": mape(g.actual, g.naive),
    "coverage_80pct": float(np.mean(np.abs(np.log(g.actual / g.projection)) <= 1.2816 * sd[g.name]) * 100),
})).round(2)
summary.to_csv(RES / "long_horizon_backtest.csv")
print(f"Historical trend growth {g_hist:.2%}/yr; mean inflation {infl_avg:.2%}; real trend {real_trend:.2%}/yr")
print(summary.to_string())

# ------------------------------------------------------------------ parameters for the website
last = df.index[-1]
params = {
    "last_date": str(last.date()),
    "last_price": float(df["wholesale_price"].iloc[-1]),
    "base_log_level": float(ds.iloc[-3:].mean()),
    "growth_historical": g_hist,
    "real_trend": real_trend,
    "inflation_avg": infl_avg,
    "inflation_target": 0.05,
    "seasonal": {int(m): float(v) for m, v in seas.items()},
    "sd_by_h": {int(h): float(v) for h, v in sd.items()},
    "backtest": summary.reset_index().to_dict(orient="records"),
}
json.dump(params, open(RES / "long_horizon_params.json", "w"), indent=2)

# ------------------------------------------------------------------ figure: projection to 2035
dates = pd.date_range(last + pd.DateOffset(months=1), "2035-12-01", freq="MS")
h = np.arange(1, len(dates) + 1)
sdh = np.array([sd[min(k, 120)] for k in h])
fig, ax = plt.subplots(figsize=(10, 4.2))
hist = df["wholesale_price"]["2015":]
ax.plot(hist.index, hist, color=BLUE, label="Actual")
for g, colr, lab in [(params["inflation_target"] + real_trend, ORANGE, "5% inflation + real trend"),
                     (g_hist, MUTED, f"Historical trend ({g_hist:.1%}/yr)")]:
    centre = np.exp(params["base_log_level"] + g * h / 12 + np.array([seas[d.month] for d in dates]))
    if colr == ORANGE:
        ax.fill_between(dates, centre * np.exp(-1.2816 * sdh), centre * np.exp(1.2816 * sdh),
                        color=ORANGE, alpha=0.18, lw=0, label="80% range")
    ax.plot(dates, centre, color=colr, lw=2 if colr == ORANGE else 1.6, ls="-" if colr == ORANGE else "--", label=lab)
ax.set_ylabel("Rs per kg"); ax.set_title("Long-horizon projection of Nadu wholesale price to 2035")
ax.legend(loc="upper left")
fig.savefig(FIG / "fig11_long_horizon.png"); plt.close(fig)
