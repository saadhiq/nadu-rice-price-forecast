"""
Step 3 - 12-month-ahead forecasting: rolling-origin back-test + final forecast.

Every model only uses information available at the forecast origin (no look-ahead).
Models
  naive, seasonal_naive        benchmarks
  ets                          Holt-Winters on log price (damped trend, additive seasonality)
  sarima                       order chosen once by auto_arima on pre-test data, re-estimated each origin
  ridge_direct, lgbm_direct    one model per horizon h=1..12 on lagged price + driver features
  ensemble                     mean of ets, sarima, lgbm_direct

Outputs
  results/backtest_errors.csv, backtest_metrics.csv, diebold_mariano.csv
  results/forecast_12m.csv            (used by the website)
  figures/fig7_backtest_mape.png, fig8_forecast.png
"""
import json
import warnings

import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pmdarima as pm
from scipy import stats
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

from common import AQUA, BLUE, FIG, HORIZON, MUTED, ORANGE, RES, load, mape, rmse, style

warnings.filterwarnings("ignore")
style()
df = load()
logp = np.log(df["wholesale_price"])

WINDOWS = {  # forecast origins (last observed month) for the back-test
    "stable 2015-2018": pd.date_range("2015-01-01", "2018-12-01", freq="MS"),
    "post-crisis 2023-2025": pd.date_range("2023-06-01", "2025-06-01", freq="MS"),
}


# ------------------------------------------------------------------ features (known at origin t)
def build_features(d):
    lp = np.log(d["wholesale_price"])
    dl = lp.diff()
    X = pd.DataFrame(index=d.index)
    for k in (1, 2, 3, 6, 12):
        X[f"dlog_p_lag{k - 1}"] = dl.shift(k - 1)
    X["mom_3"] = lp - lp.shift(3)
    X["mom_12"] = lp - lp.shift(12)
    X["dev_ma12"] = lp - lp.rolling(12).mean()
    X["dlog_fx"] = np.log(d["lkr_per_usd"]).diff()
    X["dlog_fx_3"] = np.log(d["lkr_per_usd"]).diff(3)
    X["dlog_thai_lkr_3"] = np.log(d["thai_rice_lkr_kg"]).diff(3)
    X["dlog_oil_lkr_3"] = np.log(d["oil_lkr_bbl"]).diff(3)
    X["log_last_harvest"] = np.log(d["last_harvest_prod_kt"]).bfill()
    X["dlog_last_harvest"] = X["log_last_harvest"].diff(6)
    X["rain_3m"] = d["rain_mm"].rolling(3).mean()
    X["inflation"] = d["inflation_ccpi_pct"]
    X["crisis"] = d[["crisis_2008", "crisis_2022", "fertilizer_ban", "covid_2020_21"]].max(axis=1)
    X["month_sin"], X["month_cos"] = d["month_sin"], d["month_cos"]
    return X


X_all = build_features(df)
FEATS = list(X_all.columns)


def direct_dataset(h):
    """Rows = origins t; target = log p(t+h) - log p(t); plus the calendar of the target month."""
    X = X_all.copy()
    tgt_month = (df["month"] - 1 + h) % 12 + 1
    X["tgt_month_sin"] = np.sin(2 * np.pi * tgt_month / 12)
    X["tgt_month_cos"] = np.cos(2 * np.pi * tgt_month / 12)
    y = logp.shift(-h) - logp
    return X, y


def fit_direct(kind, origin):
    """Train one model per horizon on rows whose target is fully observed by `origin`."""
    preds = []
    for h in range(1, HORIZON + 1):
        X, y = direct_dataset(h)
        train = X.index <= origin - pd.DateOffset(months=h)
        Xt, yt = X[train].iloc[13:], y[train].iloc[13:]  # first 13 rows have incomplete lags
        if kind == "ridge":
            m = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20)))
            m.fit(Xt.fillna(0), yt)
            preds.append(m.predict(X.loc[[origin]].fillna(0))[0])
        else:
            m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=8, min_child_samples=12,
                                  subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
                                  verbose=-1, random_state=42)
            m.fit(Xt, yt)
            preds.append(m.predict(X.loc[[origin]])[0])
    return logp[origin] + np.array(preds)


# ------------------------------------------------------------------ SARIMA order (selected once, pre-test)
first_origin = min(w[0] for w in WINDOWS.values())
auto = pm.auto_arima(logp[:first_origin], seasonal=True, m=12, d=1, information_criterion="aic",
                     stepwise=True, suppress_warnings=True, error_action="ignore", max_p=3, max_q=3)
SAR_ORDER, SAR_SORDER = auto.order, auto.seasonal_order
print("SARIMA order:", SAR_ORDER, SAR_SORDER)


def forecast_all(origin):
    """Return {model: array of 12 log forecasts} using data up to and including origin."""
    hist = logp[:origin]
    out = {"naive": np.repeat(hist.iloc[-1], HORIZON),
           "seasonal_naive": hist.iloc[-12:].values + (hist.iloc[-1] - hist.iloc[-13])}
    ets = ExponentialSmoothing(hist, trend="add", damped_trend=True, seasonal="add",
                               seasonal_periods=12).fit()
    out["ets"] = ets.forecast(HORIZON).values
    sar = SARIMAX(hist, order=SAR_ORDER, seasonal_order=SAR_SORDER).fit(disp=False)
    out["sarima"] = sar.forecast(HORIZON).values
    out["ridge_direct"] = fit_direct("ridge", origin)
    out["lgbm_direct"] = fit_direct("lgbm", origin)
    out["ensemble"] = np.mean([out["ets"], out["sarima"], out["lgbm_direct"]], axis=0)
    return out


# ------------------------------------------------------------------ rolling-origin back-test
rows = []
for wname, origins in WINDOWS.items():
    for i, origin in enumerate(origins):
        fc = forecast_all(origin)
        for model, f in fc.items():
            for h in range(1, HORIZON + 1):
                t = origin + pd.DateOffset(months=h)
                rows.append({"window": wname, "origin": origin, "target_date": t, "h": h, "model": model,
                             "actual": df.loc[t, "wholesale_price"], "forecast": float(np.exp(f[h - 1]))})
        print(f"  {wname}: {i + 1}/{len(origins)}", end="\r")
    print()
bt = pd.DataFrame(rows)
bt["ape"] = (bt["forecast"] / bt["actual"] - 1).abs() * 100
bt["log_err"] = np.log(bt["forecast"] / bt["actual"])
bt.to_csv(RES / "backtest_errors.csv", index=False)

metrics = (bt.groupby(["window", "model", "h"])
           .apply(lambda g: pd.Series({"MAPE": mape(g.actual, g.forecast), "RMSE": rmse(g.actual, g.forecast)}))
           .reset_index())
metrics.to_csv(RES / "backtest_metrics.csv", index=False)
summary = (bt.groupby(["window", "model"])
           .apply(lambda g: pd.Series({
               "MAPE_h1": g.loc[g.h == 1, "ape"].mean(), "MAPE_h3": g.loc[g.h == 3, "ape"].mean(),
               "MAPE_h6": g.loc[g.h == 6, "ape"].mean(), "MAPE_h12": g.loc[g.h == 12, "ape"].mean(),
               "MAPE_avg_1_12": g["ape"].mean(), "RMSE_avg_1_12": rmse(g.actual, g.forecast)}))
           .round(2).reset_index())
summary.to_csv(RES / "backtest_summary.csv", index=False)
print(summary.to_string(index=False))


# ------------------------------------------------------------------ Diebold-Mariano vs naive
def dm_test(e1, e2, h):
    d = np.abs(e1) - np.abs(e2)  # absolute-error loss
    n = len(d)
    gamma = [np.mean((d[k:] - d.mean()) * (d[:n - k] - d.mean())) for k in range(h)]
    var = (gamma[0] + 2 * sum(gamma[1:])) / n
    stat = d.mean() / np.sqrt(var) if var > 0 else np.nan
    stat *= np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)  # Harvey-Leybourne-Newbold correction
    return stat, 2 * stats.t.sf(abs(stat), df=n - 1)


dm_rows = []
for wname in WINDOWS:
    for h in (1, 3, 6, 12):
        sub = bt[(bt.window == wname) & (bt.h == h)].pivot(index="origin", columns="model", values="log_err")
        for model in sub.columns.drop("naive"):
            s, p = dm_test(sub[model].values, sub["naive"].values, h)
            dm_rows.append({"window": wname, "h": h, "model": model, "DM_stat": s, "p_value": p,
                            "better_than_naive": bool(s < 0 and p < 0.05)})
pd.DataFrame(dm_rows).round(4).to_csv(RES / "diebold_mariano.csv", index=False)

# ------------------------------------------------------------------ Fig 7: MAPE by horizon (recent window)
recent = "post-crisis 2023-2025"
avg = summary.set_index(["window", "model"]).loc[recent, "MAPE_avg_1_12"].sort_values()
best = avg.drop(["naive", "seasonal_naive"]).index[0]
show = [best] + [m for m in ("ensemble", "sarima", "lgbm_direct", "ets") if m != best][:1] + ["naive"]
colors = dict(zip(show, [BLUE, ORANGE, MUTED]))
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
for ax, wname in zip(axes, WINDOWS):
    m = metrics[metrics.window == wname]
    for model in show:
        s = m[m.model == model]
        ax.plot(s.h, s.MAPE, color=colors[model], lw=1.6 if model == "naive" else 2,
                ls="--" if model == "naive" else "-", marker="o", ms=4, label=model)
    ax.set_title(wname); ax.set_xlabel("Forecast horizon (months)"); ax.set_xticks(range(1, 13))
axes[0].set_ylabel("MAPE, %"); axes[0].legend()
fig.suptitle("Back-test forecast error by horizon", fontweight="bold")
fig.savefig(FIG / "fig7_backtest_mape.png"); plt.close(fig)

# ------------------------------------------------------------------ final 12-month forecast
last = logp.index[-1]
final = forecast_all(last)
dates = pd.date_range(last + pd.DateOffset(months=1), periods=HORIZON, freq="MS")
fc = pd.DataFrame({m: np.exp(v) for m, v in final.items()}, index=dates)

# Empirical prediction intervals: log-error quantiles of the chosen model by horizon,
# pooled over both back-test windows (honest, model-agnostic).
err = bt[bt.model == best].groupby("h")["log_err"]
q = err.quantile([0.05, 0.10, 0.90, 0.95]).unstack()
fc["best_model"] = best
fc["point"] = fc[best]
fc["lo80"] = fc["point"] * np.exp(-q[0.90].values)
fc["hi80"] = fc["point"] * np.exp(-q[0.10].values)
fc["lo90"] = fc["point"] * np.exp(-q[0.95].values)
fc["hi90"] = fc["point"] * np.exp(-q[0.05].values)
fc.index.name = "date"
fc.round(2).to_csv(RES / "forecast_12m.csv")
json.dump({"best_model": best, "sarima_order": list(SAR_ORDER), "sarima_seasonal_order": list(SAR_SORDER),
           "last_observed": str(last.date()), "features": FEATS},
          open(RES / "forecast_meta.json", "w"), indent=2)

fig, ax = plt.subplots(figsize=(10, 4))
hist = df["wholesale_price"]["2021-01":]
ax.plot(hist.index, hist, color=BLUE, label="Actual")
ax.fill_between(fc.index, fc.lo90, fc.hi90, color=ORANGE, alpha=0.15, lw=0, label="90% interval")
ax.fill_between(fc.index, fc.lo80, fc.hi80, color=ORANGE, alpha=0.25, lw=0, label="80% interval")
ax.plot([last, *fc.index], [df["wholesale_price"].iloc[-1], *fc.point], color=ORANGE,
        label=f"Forecast ({best})")
ax.set_ylabel("Rs per kg"); ax.set_title("Nadu wholesale price: 12-month forecast")
ax.legend(loc="upper left")
fig.savefig(FIG / "fig8_forecast.png"); plt.close(fig)
print(f"\nBest model (post-crisis avg MAPE): {best}")
print(fc[["point", "lo80", "hi80"]].round(1).to_string())
