"""
Step 4 - "What-if" (scenario) model: next month's wholesale price given user-chosen conditions.

Because log price is I(1) and not cointegrated with FX / Thai price (step 2), a levels regression
would be spurious. We model the monthly log change (an ARDL in differences with a mean-reversion
term), which gives short-run elasticities:

  dlog P_t = a + month_t + rho*dlog P_{t-1} + lambda*(log P_{t-1} - MA12_{t-1})
             + b1*dlog FX_t + b2*dlog FX_{t-1} + b3*dlog Thai_t + b4*dlog Oil_t
             + b5*harvest_gap_t + b6*rain_anom_{t-1} + b7*dlog Duty_t + policy dummies + e_t

Models: OLS with Newey-West (HAC) errors (interpretable, used by the website) vs LightGBM (+SHAP).
Train 2001-01..2023-06, test 2023-07..2026-06, then refit on all data.

Outputs: results/whatif_ols_coefficients.csv, whatif_test_metrics.csv, whatif_shap_importance.csv
         models/whatif_ols.pkl, models/whatif_meta.json, figures/fig9_*, fig10_*
"""
import json
import pickle
import warnings

import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import statsmodels.api as sm

from common import BLUE, FIG, MODELS, MUTED, ORANGE, RES, load, mape, rmse, style

warnings.filterwarnings("ignore")
style()
df = load()

lp = np.log(df["wholesale_price"])
harvest_avg = df["last_harvest_prod_kt"].rolling(36, min_periods=12).mean()  # ~3-year normal
rain_clim = df.groupby("month")["rain_mm"].transform("mean")

F = pd.DataFrame(index=df.index)
F["dlog_price_lag1"] = lp.diff().shift(1)
F["dev_from_ma12_lag1"] = (lp - lp.rolling(12).mean()).shift(1)
F["dlog_fx"] = np.log(df["lkr_per_usd"]).diff()
F["dlog_fx_lag1"] = F["dlog_fx"].shift(1)
F["dlog_thai_usd"] = np.log(df["thai_rice_usd_t"]).diff()
F["dlog_oil_usd"] = np.log(df["oil_usd_bbl"]).diff()
F["harvest_gap"] = np.log(df["last_harvest_prod_kt"] / harvest_avg)
F["rain_anom_lag1"] = ((df["rain_mm"] - rain_clim) / 100).shift(1)  # per 100 mm
F["dlog_duty"] = np.log(df["customs_duty_rs_kg"]).diff()
for c in ["fertilizer_ban", "price_control", "crisis_2008", "crisis_2022", "covid_2020_21"]:
    F[c] = df[c]
MONTHS = [f"m{m}" for m in range(2, 13)]
for m in range(2, 13):
    F[f"m{m}"] = (df["month"] == m).astype(int)
y = lp.diff().rename("dlog_price")

data = pd.concat([y, F], axis=1).dropna()
FEATS = list(F.columns)
split = pd.Timestamp("2023-07-01")
tr, te = data[data.index < split], data[data.index >= split]


def to_price(dlog_pred, idx):
    return df["wholesale_price"].shift(1).loc[idx] * np.exp(dlog_pred)


# ------------------------------------------------------------------ OLS (HAC)
ols = sm.OLS(tr["dlog_price"], sm.add_constant(tr[FEATS])).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
p_ols = ols.predict(sm.add_constant(te[FEATS], has_constant="add"))

# ------------------------------------------------------------------ LightGBM
gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.02, num_leaves=8, min_child_samples=15,
                        subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1, random_state=42)
gbm.fit(tr[FEATS], tr["dlog_price"])
p_gbm = gbm.predict(te[FEATS])

actual = df["wholesale_price"].loc[te.index]
res = []
for name, p in [("no-change (naive)", np.zeros(len(te))), ("OLS-ARDL (HAC)", p_ols.values), ("LightGBM", p_gbm)]:
    price = to_price(p, te.index)
    hit = np.mean(np.sign(p) == np.sign(te["dlog_price"])) * 100 if name != "no-change (naive)" else np.nan
    res.append({"model": name, "MAPE": mape(actual, price), "RMSE": rmse(actual, price),
                "direction_accuracy_pct": hit})
metrics = pd.DataFrame(res).round(3)
metrics.to_csv(RES / "whatif_test_metrics.csv", index=False)
print("Test 2023-07..2026-06 (one month ahead, given that month's conditions)\n", metrics.to_string(index=False))

# ------------------------------------------------------------------ final fit on all data (website)
ols_full = sm.OLS(data["dlog_price"], sm.add_constant(data[FEATS])).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
coef = pd.DataFrame({"coef": ols_full.params, "std_err_HAC": ols_full.bse, "t": ols_full.tvalues,
                     "p_value": ols_full.pvalues})
coef["pct_effect"] = (np.exp(coef["coef"]) - 1) * 100
coef.round(4).to_csv(RES / "whatif_ols_coefficients.csv")
print(f"\nFull-sample OLS: R2={ols_full.rsquared:.3f}, adj R2={ols_full.rsquared_adj:.3f}, n={int(ols_full.nobs)}")
print(coef.drop(index=MONTHS).round(3).to_string())

with open(MODELS / "whatif_ols.pkl", "wb") as f:
    pickle.dump(ols_full, f)
last = df.iloc[-1]
meta = {
    "features": FEATS,
    "last_date": str(df.index[-1].date()),
    "defaults": {
        "price_last": float(last["wholesale_price"]),
        "price_prev": float(df["wholesale_price"].iloc[-2]),
        "ma12_log": float(lp.iloc[-12:].mean()),
        "last_month": int(last["month"]),
        "dlog_fx_last": float(F["dlog_fx"].iloc[-1]),
        "fx_last": float(last["lkr_per_usd"]), "thai_last": float(last["thai_rice_usd_t"]),
        "oil_last": float(last["oil_usd_bbl"]), "duty_last": float(last["customs_duty_rs_kg"]),
        "harvest_last": float(df["last_harvest_prod_kt"].dropna().iloc[-1]),
        "harvest_avg": float(harvest_avg.dropna().iloc[-1]),
        "rain_last": float(last["rain_mm"]),
        "rain_clim": {int(m): float(v) for m, v in df.groupby("month")["rain_mm"].mean().items()},
    },
    "params": ols_full.params.to_dict(), "resid_sd": float(np.sqrt(ols_full.scale)),
    "r2": ols_full.rsquared, "test_metrics": metrics.to_dict(orient="records"),
}
json.dump(meta, open(MODELS / "whatif_meta.json", "w"), indent=2)

# ------------------------------------------------------------------ SHAP for LightGBM (refit on all data)
gbm.fit(data[FEATS], data["dlog_price"])
sv = shap.TreeExplainer(gbm).shap_values(data[FEATS])
imp = pd.Series(np.abs(sv).mean(axis=0), index=FEATS)
imp = pd.concat([imp.drop(MONTHS), pd.Series({"month (11 dummies)": imp[MONTHS].sum()})]).sort_values()
imp.rename("mean_abs_shap").to_csv(RES / "whatif_shap_importance.csv")

fig, ax = plt.subplots(figsize=(7, 5))
ax.barh(imp.index, imp.values * 100, color=BLUE, height=0.6)
ax.set_xlabel("Mean |SHAP| (percentage points of monthly price change)")
ax.set_title("What drives monthly price changes (LightGBM + SHAP)")
fig.savefig(FIG / "fig9_shap_importance.png"); plt.close(fig)

# ------------------------------------------------------------------ test-period fit plot
fig, ax = plt.subplots(figsize=(10, 3.8))
ax.plot(actual.index, actual, color=BLUE, label="Actual")
ax.plot(actual.index, to_price(p_ols.values, te.index), color=ORANGE, label="OLS-ARDL")
ax.plot(actual.index, to_price(p_gbm, te.index), color=MUTED, lw=1.4, ls="--", label="LightGBM")
ax.set_ylabel("Rs per kg"); ax.set_title("What-if model, out-of-sample test (one month ahead)")
ax.legend(loc="lower right")
fig.savefig(FIG / "fig10_whatif_test.png"); plt.close(fig)
