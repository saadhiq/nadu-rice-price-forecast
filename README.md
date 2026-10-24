# Nadu rice wholesale price — forecasting & what-if analysis (Sri Lanka, 2000–2026)

Data: `../cleaned data/nadu_research_dataset_v.xlsx` (HARTI prices, DCS production & CCPI, weather,
world oil, Thai 5% rice, exchange rate, rice import taxes, policy/crisis dummies).

## Run
```
pip install -r requirements-analysis.txt
python run_all.py          # steps 1-4 (≈3 min)
streamlit run app.py       # website at http://localhost:8501
```

## Pipeline
| Step | Script | Output |
|---|---|---|
| 1 Cleaning | `01_clean_data.py` | `data/nadu_clean_v7.csv`, `data/cleaning_log.txt` |
| 2 EDA & econometric tests | `02_eda_tests.py` | `figures/fig1–6`, unit root, Zivot-Andrews, cointegration, Granger tables in `results/` |
| 3 12-month forecasting | `03_forecast_models.py` | rolling-origin back-test (2 windows, 7 models), Diebold-Mariano, `results/forecast_12m.csv`, `figures/fig7–8` |
| 4 What-if model | `04_whatif_model.py` | ARDL-in-differences (HAC) + LightGBM/SHAP, `models/whatif_ols.pkl`, `figures/fig9–10` |
| 5 Any-month projection | `05_long_horizon.py` | trend + inflation + seasonal projection to 2035, back-tested at 1–5 years, `results/long_horizon_params.json`, `figures/fig11` |
| Website | `app.py` | Forecast · Price for any month · What-if · Model & data tabs |

## Known data issue
`inflation_ccpi_pct` jumps 4.0 → 17.4 between Nov and Dec 2023 (two series spliced). Re-take one
definition for all months from a single DCS/CBSL table, then `python run_all.py`.
