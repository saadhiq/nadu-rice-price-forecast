"""
Step 6 - Export every result the website needs into one JSON file.

Output: web/public/data/site.json   (read by the static website in web/)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import MODELS, RES, load

OUT = Path(__file__).parent / "web" / "public" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


df = load().reset_index()
fc = pd.read_csv(RES / "forecast_12m.csv", parse_dates=["date"])
meta = json.load(open(MODELS / "whatif_meta.json"))
lh = json.load(open(RES / "long_horizon_params.json"))
coefs = pd.read_csv(RES / "whatif_ols_coefficients.csv", index_col=0)
seas = pd.read_csv(RES / "seasonal_index.csv")

hist = df[["date", "wholesale_price", "retail_price"]].copy()
hist["date"] = hist["date"].dt.strftime("%Y-%m")
fc_out = fc[["date", "point", "lo80", "hi80", "lo90", "hi90"]].copy()
fc_out["date"] = fc_out["date"].dt.strftime("%Y-%m")

site = {
    "updated": pd.Timestamp.now().strftime("%Y-%m-%d"),
    "last_date": df["date"].iloc[-1].strftime("%Y-%m"),
    "best_model": fc["best_model"].iloc[0],
    "history": records(hist.round(2)),
    "forecast": records(fc_out.round(2)),
    "seasonal_index": records(seas.rename(columns={"mean": "pct", "sem": "se"}).round(3)),
    "backtest_summary": records(pd.read_csv(RES / "backtest_summary.csv")),
    "backtest_by_horizon": records(pd.read_csv(RES / "backtest_metrics.csv").round(3)),
    "diebold_mariano": records(pd.read_csv(RES / "diebold_mariano.csv")),
    "unit_roots": records(pd.read_csv(RES / "unit_root_tests.csv")),
    "structural_breaks": records(pd.read_csv(RES / "structural_breaks.csv")),
    "cointegration": records(pd.read_csv(RES / "cointegration.csv").replace({np.nan: None})),
    "granger": records(pd.read_csv(RES / "granger_causality.csv")),
    "descriptive": records(pd.read_csv(RES / "descriptive_stats.csv").rename(columns={"Unnamed: 0": "variable"})),
    "stl_strength": pd.read_csv(RES / "stl_strength.csv", index_col=0).iloc[:, 0].to_dict(),
    "whatif": {
        "params": meta["params"], "resid_sd": meta["resid_sd"], "defaults": meta["defaults"],
        "r2": meta["r2"], "test_metrics": meta["test_metrics"],
        "coefficients": records(coefs.reset_index().rename(columns={"index": "term"}).round(4)),
        "shap": records(pd.read_csv(RES / "whatif_shap_importance.csv").rename(
            columns={"Unnamed: 0": "feature"}).round(5)),
    },
    "long_horizon": lh,
}
def clean(x):
    """NaN/inf -> null so the file is valid JSON for the browser."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean(v) for v in x]
    if isinstance(x, float) and not np.isfinite(x):
        return None
    return x


(OUT / "site.json").write_text(json.dumps(clean(site), allow_nan=False), encoding="utf-8")
print(f"Wrote {OUT / 'site.json'} ({(OUT / 'site.json').stat().st_size / 1024:.0f} KB)")
