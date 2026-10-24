"""
Nadu rice wholesale price - forecasting & what-if website.

Run:  streamlit run app.py
Reads the outputs of steps 1-4 (re-run those scripts after updating the data).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
BLUE, ORANGE, MUTED = "#2a78d6", "#eb6834", "#8a8984"
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

st.set_page_config(page_title="Nadu Rice Price Forecast", page_icon="🌾", layout="wide")


@st.cache_data
def load_data():
    hist = pd.read_csv(ROOT / "data" / "nadu_clean_v7.csv", parse_dates=["date"])
    fc = pd.read_csv(ROOT / "results" / "forecast_12m.csv", parse_dates=["date"])
    summary = pd.read_csv(ROOT / "results" / "backtest_summary.csv")
    coefs = pd.read_csv(ROOT / "results" / "whatif_ols_coefficients.csv", index_col=0)
    return hist, fc, summary, coefs


@st.cache_data
def load_model():
    meta = json.load(open(ROOT / "models" / "whatif_meta.json"))
    lh = json.load(open(ROOT / "results" / "long_horizon_params.json"))
    return pd.Series(meta["params"]), meta, lh


hist, fc, summary, coefs = load_data()
params, meta, LH = load_model()
D = meta["defaults"]
best = fc["best_model"].iloc[0]

st.title("🌾 Nadu Rice Wholesale Price — Sri Lanka")
st.caption(f"Pettah wholesale market (HARTI), Rs/kg · data to {pd.Timestamp(meta['last_date']):%B %Y}")

tab_fc, tab_any, tab_wi, tab_about = st.tabs(
    ["📈 12-month forecast", "📅 Price for any month", "🔧 What-if price predictor", "ℹ️ Model & data"])

# =====================================================================  FORECAST
with tab_fc:
    last_price = hist["wholesale_price"].iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest price", f"Rs {last_price:.2f}", help=f"{hist['date'].iloc[-1]:%b %Y}")
    c2.metric("Next month", f"Rs {fc['point'].iloc[0]:.2f}", f"{(fc['point'].iloc[0] / last_price - 1) * 100:+.1f}%")
    peak = fc.loc[fc["point"].idxmax()]
    c3.metric("Forecast peak", f"Rs {peak['point']:.2f}", f"{peak['date']:%b %Y}", delta_color="off")
    c4.metric("In 12 months", f"Rs {fc['point'].iloc[-1]:.2f}", f"{(fc['point'].iloc[-1] / last_price - 1) * 100:+.1f}%")

    start = st.select_slider("Show history from", options=list(range(2000, 2026)), value=2019)
    h = hist[hist["date"].dt.year >= start]
    x_fc = [hist["date"].iloc[-1], *fc["date"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[*fc["date"], *fc["date"][::-1]], y=[*fc["hi90"], *fc["lo90"][::-1]],
                             fill="toself", fillcolor="rgba(235,104,52,0.13)", line=dict(width=0),
                             name="90% interval", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[*fc["date"], *fc["date"][::-1]], y=[*fc["hi80"], *fc["lo80"][::-1]],
                             fill="toself", fillcolor="rgba(235,104,52,0.25)", line=dict(width=0),
                             name="80% interval", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=h["date"], y=h["wholesale_price"], name="Actual", line=dict(color=BLUE, width=2),
                             hovertemplate="%{x|%b %Y}: Rs %{y:.2f}<extra>Actual</extra>"))
    fig.add_trace(go.Scatter(x=x_fc, y=[last_price, *fc["point"]], name=f"Forecast ({best})",
                             line=dict(color=ORANGE, width=2),
                             hovertemplate="%{x|%b %Y}: Rs %{y:.2f}<extra>Forecast</extra>"))
    fig.update_layout(height=430, hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10),
                      yaxis_title="Rs per kg", legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig, width="stretch")

    tbl = fc[["date", "point", "lo80", "hi80", "lo90", "hi90"]].copy()
    tbl["date"] = tbl["date"].dt.strftime("%b %Y")
    tbl.columns = ["Month", "Forecast (Rs/kg)", "80% low", "80% high", "90% low", "90% high"]
    st.dataframe(tbl.set_index("Month").style.format("{:.2f}"), width="stretch")
    st.download_button("Download forecast (CSV)", tbl.to_csv(index=False), "nadu_forecast_12m.csv")
    st.info("Intervals are built from the model's real errors in past forecasts (rolling back-tests), so about "
            "8 in 10 future prices should fall inside the 80% band. Shocks like policy changes or "
            "currency crises can push prices outside it.")

# =====================================================================  ANY MONTH
with tab_any:
    st.markdown("Pick any month and year to get the expected wholesale price. Up to 12 months ahead the "
                "forecasting model is used; further ahead the price is **projected** from the long-run trend, "
                "your inflation assumption and the month's seasonal pattern.")
    last_date = pd.Timestamp(LH["last_date"])
    a, b, c = st.columns([1, 1, 2])
    year = a.selectbox("Year", range(last_date.year, 2036), index=min(4, 2035 - last_date.year))
    month = b.selectbox("Month", range(1, 13), index=7, format_func=lambda m: MONTH_NAMES[m - 1], key="any_month")
    with c:
        mode = st.radio("Annual price growth assumption",
                        ["Inflation-based (recommended)", f"Historical trend ({LH['growth_historical']:.1%}/yr)",
                         "Custom"], horizontal=True)
        if mode.startswith("Inflation"):
            infl = st.slider("Expected average inflation (% per year)", 0.0, 20.0,
                             LH["inflation_target"] * 100, 0.5,
                             help="Central Bank of Sri Lanka target: 5%. 2000–2026 average: "
                                  f"{LH['inflation_avg']:.1%}.")
            g = infl / 100 + LH["real_trend"]
        elif mode.startswith("Historical"):
            g = LH["growth_historical"]
        else:
            g = st.slider("Price growth (% per year)", -5.0, 25.0, 6.0, 0.5) / 100

    target = pd.Timestamp(year=year, month=month, day=1)
    h = (target.year - last_date.year) * 12 + target.month - last_date.month
    last_price = LH["last_price"]

    def projection(k, m):
        centre = np.exp(LH["base_log_level"] + g * k / 12 + LH["seasonal"][str(m)])
        sd = LH["sd_by_h"][str(min(k, 120))]
        return centre, centre * np.exp(-1.2816 * sd), centre * np.exp(1.2816 * sd)

    if h <= 0:
        row = hist[hist["date"] == target]
        st.metric(f"Actual price, {MONTH_NAMES[month - 1]} {year}", f"Rs {row['wholesale_price'].iloc[0]:.2f}")
    else:
        if h <= 12:
            r = fc[fc["date"] == target].iloc[0]
            point, lo, hi, method = r["point"], r["lo80"], r["hi80"], f"12-month forecast model ({best})"
            path = fc[fc["date"] <= target]
            px, pc, pl, ph = path["date"], path["point"], path["lo80"], path["hi80"]
        else:
            point, lo, hi = projection(h, month)
            method = f"long-horizon projection ({g:.1%} per year)"
            px = pd.date_range(last_date + pd.DateOffset(months=1), target, freq="MS")
            pts = [projection(k, d.month) for k, d in enumerate(px, start=1)]
            pc, pl, ph = [p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts]

        m1, m2, m3 = st.columns(3)
        m1.metric(f"Expected price, {MONTH_NAMES[month - 1]} {year}", f"Rs {point:.2f}",
                  f"{(point / last_price - 1) * 100:+.1f}% vs {last_date:%b %Y}")
        m2.metric("80% range", f"Rs {lo:.0f} – {hi:.0f}")
        m3.metric("Months ahead", f"{h}", help=f"Method: {method}")

        h0 = hist[hist["date"].dt.year >= 2015]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[*px, *px[::-1]], y=[*ph, *pl[::-1]], fill="toself",
                                 fillcolor="rgba(235,104,52,0.18)", line=dict(width=0), name="80% range",
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=h0["date"], y=h0["wholesale_price"], name="Actual",
                                 line=dict(color=BLUE, width=2),
                                 hovertemplate="%{x|%b %Y}: Rs %{y:.2f}<extra>Actual</extra>"))
        fig.add_trace(go.Scatter(x=[last_date, *px], y=[last_price, *pc], name="Expected",
                                 line=dict(color=ORANGE, width=2),
                                 hovertemplate="%{x|%b %Y}: Rs %{y:.2f}<extra>Expected</extra>"))
        fig.add_trace(go.Scatter(x=[target], y=[point], mode="markers+text", marker=dict(color=ORANGE, size=12),
                                 text=[f"Rs {point:.0f}"], textposition="top center", showlegend=False,
                                 hoverinfo="skip"))
        fig.update_layout(height=420, hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10),
                          yaxis_title="Rs per kg", legend=dict(orientation="h", y=1.08))
        st.plotly_chart(fig, width="stretch")

        if h > 12:
            bt = pd.DataFrame(LH["backtest"]).set_index("h")
            near = bt.index[np.argmin(np.abs(bt.index - min(h, 60)))]
            st.info(f"How reliable is this? Projections made {near} months ahead in 2005–2021 missed the actual "
                    f"price by {bt.loc[near, 'MAPE_projection']:.0f}% on average (vs "
                    f"{bt.loc[near, 'MAPE_naive']:.0f}% for assuming no change). Treat the expected price as a "
                    "planning figure and the 80% range as the realistic spread — exchange-rate crises, droughts "
                    "or policy changes can move prices outside it.")

# =====================================================================  WHAT-IF
with tab_wi:
    st.markdown("Set the conditions for the **coming month** and see the predicted wholesale price. "
                "Defaults are the latest observed values, so leaving everything unchanged gives the baseline.")
    next_month = D["last_month"] % 12 + 1
    a, b, c = st.columns(3)
    with a:
        st.subheader("Market & currency")
        price_last = st.number_input("This month's wholesale price (Rs/kg)", 50.0, 600.0, D["price_last"], 1.0)
        fx = st.number_input("Exchange rate next month (LKR per USD)", 100.0, 700.0, D["fx_last"], 1.0,
                             help=f"Latest: {D['fx_last']:.2f}")
        thai = st.number_input("Thai 5% rice price (USD/t)", 150.0, 1500.0, D["thai_last"], 5.0,
                               help=f"Latest: {D['thai_last']:.0f}")
        oil = st.number_input("World oil price (USD/barrel)", 10.0, 250.0, D["oil_last"], 1.0,
                              help=f"Latest: {D['oil_last']:.1f}")
    with b:
        st.subheader("Supply & weather")
        harvest = st.number_input("Last season's paddy harvest ('000 t)", 500.0, 4000.0, D["harvest_last"], 10.0,
                                  help=f"Latest completed season: {D['harvest_last']:.0f}; "
                                       f"3-year normal: {D['harvest_avg']:.0f}")
        rain = st.number_input("Rainfall this month (mm)", 0.0, 900.0, D["rain_last"], 5.0,
                               help=f"Normal for {MONTH_NAMES[D['last_month'] - 1]}: "
                                    f"{D['rain_clim'][str(D['last_month'])]:.0f} mm")
        month = st.selectbox("Month being predicted", range(1, 13), index=next_month - 1,
                             format_func=lambda m: MONTH_NAMES[m - 1])
    with c:
        st.subheader("Policy & shocks")
        duty = st.number_input("Import customs duty (Rs/kg)", 1.0, 300.0, D["duty_last"], 5.0)
        fert_ban = st.toggle("Fertilizer import ban")
        price_ctrl = st.toggle("Government price control")
        crisis = st.toggle("Economic crisis (2022-type)")

    log_p = np.log(price_last)
    x = {
        "const": 1.0,
        "dlog_price_lag1": np.log(price_last / D["price_prev"]),
        "dev_from_ma12_lag1": log_p - (D["ma12_log"] + (log_p - np.log(D["price_last"])) / 12),
        "dlog_fx": np.log(fx / D["fx_last"]),
        "dlog_fx_lag1": D["dlog_fx_last"],
        "dlog_thai_usd": np.log(thai / D["thai_last"]),
        "dlog_oil_usd": np.log(oil / D["oil_last"]),
        "harvest_gap": np.log(harvest / D["harvest_avg"]),
        "rain_anom_lag1": (rain - D["rain_clim"][str(D["last_month"])]) / 100,
        "dlog_duty": np.log(duty / D["duty_last"]),
        "fertilizer_ban": int(fert_ban), "price_control": int(price_ctrl),
        "crisis_2008": 0, "crisis_2022": int(crisis), "covid_2020_21": 0,
    }
    for m in range(2, 13):
        x[f"m{m}"] = int(month == m)
    xv = pd.Series(x)[params.index]
    contrib = xv * params
    dlog = contrib.sum()
    pred = price_last * np.exp(dlog)
    se = meta["resid_sd"]
    lo, hi = price_last * np.exp(dlog - 1.28 * se), price_last * np.exp(dlog + 1.28 * se)

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Predicted price ({MONTH_NAMES[month - 1]})", f"Rs {pred:.2f}", f"{(pred / price_last - 1) * 100:+.2f}%")
    m2.metric("80% range", f"Rs {lo:.0f} – {hi:.0f}")
    m3.metric("Direction", "▲ Up" if dlog > 0 else "▼ Down",
              help="Out-of-sample, the model got the direction right ~70% of months (2023-2026).")

    groups = {
        "Exchange rate": ["dlog_fx", "dlog_fx_lag1"], "Thai rice price": ["dlog_thai_usd"],
        "Oil price": ["dlog_oil_usd"], "Harvest size": ["harvest_gap"], "Rainfall": ["rain_anom_lag1"],
        "Import duty": ["dlog_duty"], "Policy & crisis": ["fertilizer_ban", "price_control", "crisis_2022"],
        "Seasonality": [f"m{m}" for m in range(2, 13)] + ["const"],
        "Price momentum": ["dlog_price_lag1", "dev_from_ma12_lag1"],
    }
    eff = pd.Series({g: (np.exp(contrib[v].sum()) - 1) * 100 for g, v in groups.items()}).sort_values()
    bar = go.Figure(go.Bar(x=eff.values, y=eff.index, orientation="h",
                           marker_color=[ORANGE if v > 0 else BLUE for v in eff.values],
                           hovertemplate="%{y}: %{x:+.2f}%<extra></extra>"))
    bar.update_layout(height=360, title="What is pushing the price (% contribution)",
                      xaxis_title="% change in price", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(bar, width="stretch")
    st.caption("Model: dynamic regression on monthly log changes (ARDL in differences, Newey-West errors). "
               "Effects are short-run (one month). Very large changes beyond those seen in 2000-2026 are "
               "extrapolation.")

# =====================================================================  ABOUT
with tab_about:
    st.subheader("Forecast model comparison (rolling-origin back-test)")
    st.dataframe(summary.set_index(["window", "model"]), width="stretch")
    st.markdown(
        f"- **Chosen model:** `{best}` — lowest average 1–12 month MAPE after the 2022 crisis.\n"
        "- Diebold-Mariano tests: no model is *significantly* more accurate than the naive "
        "(last value) forecast at 5% — typical for commodity prices; gains are mainly at 2–9 months.\n"
        "- Seasonality: prices peak in Dec–Jan (pre-Maha harvest) and bottom in Aug–Sep (Yala harvest).")
    st.subheader("What-if model: short-run effects")
    show = coefs.loc[[i for i in coefs.index if not i.startswith("m") or i in ("month",)]]
    st.dataframe(show[["coef", "std_err_HAC", "p_value", "pct_effect"]].style.format("{:.3f}"),
                 width="stretch")
    st.markdown(
        "**Data sources:** wholesale & retail prices — HARTI; paddy production — Department of Census and "
        "Statistics (DCS); CCPI inflation — DCS; weather — 7 rain-zone averages; exchange rate, oil, Thai 5% "
        "rice benchmark — international series; customs duty, CESS, VAT, PAL on rice — official tariff records.")
