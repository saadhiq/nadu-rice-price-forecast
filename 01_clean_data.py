"""
Step 1 - Data cleaning & feature preparation for the Nadu rice wholesale price study.

Input : ../cleaned data/nadu_research_dataset_v.xlsx   (your file - never modified)
Output: data/nadu_clean_v7.csv          (cleaned, analysis-ready)
        data/cleaning_log.txt           (what was changed, for the Methodology section)

Run:  python 01_clean_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("../cleaned data/nadu_research_dataset_v.xlsx")
OUT = Path("data")
OUT.mkdir(exist_ok=True)
log = []

df = pd.read_excel(RAW)
df = df.rename(columns={
    "Maha (1 = Maha, 0 = Yala)": "maha",
    "Paddy production (000 t per month)": "paddy_prod_per_month_kt",
    "harvest_month": "is_harvest_month",          # 1 = Feb, Mar, Aug, Sep (harvest months)
    "inflation_ccpi_new_file_pct": "inflation_ccpi_pct",
})
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)
assert (df["date"].diff().dropna().dt.days.between(28, 31)).all(), "monthly gaps present"

# ---------------------------------------------------------------------------
# 1. Paddy production (DCS). Maha is labelled by the season's START year
#    (Maha 2016 = Maha 2016/17, harvested Feb-Mar 2017); the source file already
#    places Maha (t-1)/t in Jan-Mar of year t, so check that instead of fixing it.
# ---------------------------------------------------------------------------
maha_by_label = df[df["month"] == 9].set_index("year")["paddy_prod_per_month_kt"]
yala_by_label = df[df["month"] == 4].set_index("year")["paddy_prod_per_month_kt"]

jan = df[df["month"] == 1].set_index("year")["paddy_prod_per_month_kt"]
assert np.allclose(jan.iloc[1:], maha_by_label.reindex(jan.index[1:] - 1).values), \
    "Jan-Mar of year t must hold Maha (t-1)/t"
log.append("paddy_prod_per_month_kt: verified Jan-Mar of year t = Maha (t-1)/t. "
           "Jan-Mar 2000 (Maha 1999/2000) and Apr-Jun 2026 (Yala 2026) not yet available.")

# Supply actually on the market: total output of the most recently COMPLETED harvest
# (known at that time -> safe to use in forecasting).
maha_total = maha_by_label * 7
yala_total = yala_by_label * 5

def last_harvest(row):
    y, m = row["year"], row["month"]
    if 4 <= m <= 9:
        return maha_total.get(y - 1, np.nan)    # Maha (t-1)/t harvested Feb-Mar
    if m >= 10:
        return yala_total.get(y, np.nan)        # Yala t harvested Aug-Sep
    return yala_total.get(y - 1, np.nan)        # Jan-Mar: Yala (t-1)

df["last_harvest_prod_kt"] = df.apply(last_harvest, axis=1)
log.append("Added last_harvest_prod_kt = total output of the latest completed season.")

# ---------------------------------------------------------------------------
# 2. Seasonal coding: months_since_harvest contradicted is_harvest_month
#    (0 was put in Apr/Oct while harvest months are Feb-Mar / Aug-Sep).
#    Recoded so 0 = first harvest month (Feb, Aug).
# ---------------------------------------------------------------------------
df["months_since_harvest"] = (df["month"] - 2) % 6
log.append("months_since_harvest recoded: Feb/Aug = 0 ... Jan/Jul = 5 "
           "(consistent with is_harvest_month = Feb, Mar, Aug, Sep).")

# ---------------------------------------------------------------------------
# 3. Incomplete 2026 annual variables: carry last known value forward (flagged)
# ---------------------------------------------------------------------------
df["agri_labor_imputed"] = df["agri_labor_pct_prev_year"].isna().astype(int)
df["agri_labor_pct_prev_year"] = df["agri_labor_pct_prev_year"].ffill()
log.append("agri_labor_pct_prev_year: 2026 forward-filled from 2025 (flag agri_labor_imputed).")

# ---------------------------------------------------------------------------
# 4. Known data-quality issue that needs a new source (NOT auto-fixed)
# ---------------------------------------------------------------------------
df["inflation_break_flag"] = (df["date"] >= "2023-12-01").astype(int)
log.append("WARNING inflation_ccpi_pct jumps 4.0 -> 17.4 between Nov and Dec 2023: two "
           "different series were spliced. Re-take ONE definition (12-month moving average "
           "OR year-on-year) for all months from a single DCS/CBSL table.")

# ---------------------------------------------------------------------------
# 5. Transformations used by the models
# ---------------------------------------------------------------------------
df["log_wholesale"] = np.log(df["wholesale_price"])
df["dlog_wholesale"] = df["log_wholesale"].diff()
df["margin_pct"] = (df["retail_price"] / df["wholesale_price"] - 1) * 100
df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

# Columns that must NOT be used as predictors of wholesale price
log.append("Excluded from predictors: retail_price (same-month outcome -> leakage), "
           "wholesale_filled/retail_filled (data flags), oil_lkr_bbl & thai_rice_lkr_kg "
           "are products of other columns (use either USD+FX or LKR versions, not both).")

df.to_csv(OUT / "nadu_clean_v7.csv", index=False)
(OUT / "cleaning_log.txt").write_text("\n".join(log), encoding="utf-8")
print("\n".join(log))
print(f"\nSaved {OUT/'nadu_clean_v7.csv'}  shape={df.shape}")
print("Remaining missing:\n", df.isna().sum()[df.isna().sum() > 0])
