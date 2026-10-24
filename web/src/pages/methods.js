const MODEL_NAMES = { ensemble: "Ensemble", sarima: "SARIMA", ets: "ETS", lgbm_direct: "LightGBM (direct)", ridge_direct: "Ridge (direct)", naive: "Naive", seasonal_naive: "Seasonal naive" };
const VAR_NAMES = {
  log_wholesale: "Wholesale price (log)", log_retail: "Retail price (log)", log_lkr_per_usd: "Exchange rate (log)",
  log_thai_rice_usd: "Thai rice, USD (log)", log_thai_rice_lkr: "Thai rice, LKR (log)", log_oil_lkr: "Oil, LKR (log)",
  log_last_harvest: "Last harvest (log)", rain_mm: "Rainfall", inflation_ccpi_pct: "CCPI inflation",
};
const TERM_NAMES = {
  dlog_fx: "Δ exchange rate (t)", dlog_fx_lag1: "Δ exchange rate (t−1)", dlog_thai_usd: "Δ Thai rice price",
  dlog_oil_usd: "Δ oil price", dev_from_ma12_lag1: "Deviation from 12-month average (t−1)", dlog_price_lag1: "Δ price (t−1)",
  harvest_gap: "Harvest gap", rain_anom_lag1: "Rainfall anomaly (t−1, per 100 mm)", dlog_duty: "Δ customs duty",
  fertilizer_ban: "Fertilizer ban", crisis_2008: "2008 crisis", crisis_2022: "2022 crisis", price_control: "Price control",
  covid_2020_21: "COVID-19",
};
const f = (v, d = 3) => (v == null ? "—" : (+v).toFixed(d));
const p = (v) => (v == null ? "—" : v < 0.001 ? "<0.001" : (+v).toFixed(3));

export default function methods(root, d) {
  const ur = d.unit_roots;
  const dm = d.diebold_mariano.filter((r) => ["ensemble", "sarima", "ets", "lgbm_direct"].includes(r.model));
  const lhbt = d.long_horizon.backtest;

  root.innerHTML = `
  <section class="page-head"><div class="wrap">
    <p class="eyebrow">Data &amp; methods</p>
    <h1>How the numbers are made</h1>
    <p class="lead">Every figure on this site comes from a reproducible Python pipeline. Re-running it after a data
    update rebuilds the tests, models, forecasts and this website's data.</p>
  </div></section>

  <section class="section tight"><div class="wrap">
    <div class="steps">
      <div class="card"><h3>Clean</h3><p>Fill 9 price gaps (2020) by interpolation; align Maha/Yala production to harvest dates; build “last completed harvest”.</p></div>
      <div class="card"><h3>Diagnose</h3><p>STL decomposition, ADF/KPSS unit roots, Zivot-Andrews breaks, Johansen and Engle-Granger cointegration, Granger causality.</p></div>
      <div class="card"><h3>Forecast</h3><p>Seven models compared by rolling-origin back-tests in two windows; Diebold-Mariano significance tests.</p></div>
      <div class="card"><h3>Explain</h3><p>ARDL in first differences with Newey-West errors; LightGBM with SHAP for comparison.</p></div>
      <div class="card"><h3>Project</h3><p>Trend + inflation + seasonal projection to 2035, with ranges calibrated on 2005–2021 back-tests.</p></div>
    </div>
  </div></section>

  <section class="section tight"><div class="wrap grid" style="gap:40px">
    <div>
      <h2>Unit-root tests</h2>
      <p class="muted">ADF null: unit root. KPSS null: stationary. Levels tested with trend, differences with a constant.</p>
      <div class="table-wrap"><table>
        <thead><tr><th>Series</th><th>Form</th><th class="r">ADF p</th><th class="r">KPSS p</th><th>Verdict</th></tr></thead>
        <tbody>${ur.map((r) => `<tr><td>${VAR_NAMES[r.variable] ?? r.variable}</td><td>${r.form}</td><td class="r">${p(r.ADF_p)}</td><td class="r">${p(r.KPSS_p)}</td><td>${r.verdict}</td></tr>`).join("")}</tbody>
      </table></div>
    </div>

    <div class="grid g2" style="align-items:start">
      <div>
        <h2>Structural breaks</h2>
        <div class="table-wrap"><table>
          <thead><tr><th>Series</th><th class="r">Zivot-Andrews</th><th class="r">p</th><th>Break</th></tr></thead>
          <tbody>${d.structural_breaks.map((r) => `<tr><td>${VAR_NAMES[r.variable] ?? r.variable}</td><td class="r">${f(r.ZA_stat, 2)}</td><td class="r">${p(r.p_value)}</td><td>${r.break_date}</td></tr>`).join("")}</tbody>
        </table></div>
      </div>
      <div>
        <h2>Granger causality</h2>
        <div class="table-wrap"><table>
          <thead><tr><th>Cause → Δ wholesale</th><th class="r">Lag</th><th class="r">F</th><th class="r">p</th></tr></thead>
          <tbody>${d.granger.map((r) => `<tr><td>${VAR_NAMES[r.cause] ?? r.cause}</td><td class="r">${r.best_lag}</td><td class="r">${f(r.F, 2)}</td><td class="r">${p(r.p_value)}</td></tr>`).join("")}</tbody>
        </table></div>
      </div>
    </div>

    <div>
      <h2>Cointegration</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Test</th><th>System</th><th class="r">Statistic</th><th class="r">p / 5% critical</th></tr></thead>
        <tbody>${d.cointegration.map((r) => `<tr><td>${r.test}</td><td>${r.system.replaceAll("log_", "")}</td><td class="r">${f(r.stat, 2)}</td><td class="r">${r.p_value != null ? p(r.p_value) : f(r.crit_5pct, 2)}</td></tr>`).join("")}</tbody>
      </table></div>
    </div>

    <div>
      <h2>Forecast back-test (MAPE, %)</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Window</th><th>Model</th><th class="r">h=1</th><th class="r">h=3</th><th class="r">h=6</th><th class="r">h=12</th><th class="r">Avg 1–12</th><th class="r">RMSE (Rs)</th></tr></thead>
        <tbody>${d.backtest_summary.map((r) => `<tr class="${r.model === d.best_model ? "hl" : ""}"><td>${r.window}</td><td>${MODEL_NAMES[r.model] ?? r.model}</td>
          <td class="r">${f(r.MAPE_h1, 2)}</td><td class="r">${f(r.MAPE_h3, 2)}</td><td class="r">${f(r.MAPE_h6, 2)}</td><td class="r">${f(r.MAPE_h12, 2)}</td>
          <td class="r">${f(r.MAPE_avg_1_12, 2)}</td><td class="r">${f(r.RMSE_avg_1_12, 2)}</td></tr>`).join("")}</tbody>
      </table></div>
    </div>

    <div class="grid g2" style="align-items:start">
      <div>
        <h2>Diebold-Mariano vs naive</h2>
        <p class="muted">Negative statistic = more accurate than naive. None is significant at 5%.</p>
        <div class="table-wrap"><table>
          <thead><tr><th>Window</th><th class="r">h</th><th>Model</th><th class="r">DM</th><th class="r">p</th></tr></thead>
          <tbody>${dm.map((r) => `<tr><td>${r.window.split(" ")[0]}</td><td class="r">${r.h}</td><td>${MODEL_NAMES[r.model]}</td><td class="r">${f(r.DM_stat, 2)}</td><td class="r">${p(r.p_value)}</td></tr>`).join("")}</tbody>
        </table></div>
      </div>
      <div>
        <h2>Short-run model (ARDL)</h2>
        <p class="muted">Full sample, Newey-West standard errors. R² = ${d.whatif.r2.toFixed(3)}. Month dummies not shown.</p>
        <div class="table-wrap"><table>
          <thead><tr><th>Term</th><th class="r">Coef.</th><th class="r">SE</th><th class="r">p</th></tr></thead>
          <tbody>${d.whatif.coefficients.filter((r) => TERM_NAMES[r.term]).map((r) => `<tr><td>${TERM_NAMES[r.term]}</td><td class="r">${f(r.coef)}</td><td class="r">${f(r.std_err_HAC)}</td><td class="r">${p(r.p_value)}</td></tr>`).join("")}</tbody>
        </table></div>
      </div>
    </div>

    <div class="grid g2" style="align-items:start">
      <div>
        <h2>Long-horizon projection back-test</h2>
        <p class="muted">198 projections from origins 2005–2021, growth estimated only from data before each origin.</p>
        <div class="table-wrap"><table>
          <thead><tr><th class="r">Months ahead</th><th class="r">MAPE projection</th><th class="r">MAPE naive</th><th class="r">80% range hit rate</th></tr></thead>
          <tbody>${lhbt.map((r) => `<tr><td class="r">${r.h}</td><td class="r">${f(r.MAPE_projection, 1)}%</td><td class="r">${f(r.MAPE_naive, 1)}%</td><td class="r">${f(r.coverage_80pct, 0)}%</td></tr>`).join("")}</tbody>
        </table></div>
      </div>
      <div>
        <h2>Data notes</h2>
        <ul class="muted">
          <li>Wholesale and retail prices: HARTI, Pettah market, monthly average, Rs/kg.</li>
          <li>Paddy production: DCS, by season; Maha labelled by its start year and placed in its harvest months.</li>
          <li>VAT and PAL are the rates applied to rice specifically.</li>
          <li>CCPI inflation combines two definitions from December 2023; a consistent series will replace it.</li>
          <li>Retail price is never used to predict wholesale price (same-month leakage).</li>
        </ul>
        <p><a href="https://github.com/saadhiq/nadu-rice-price-forecast" target="_blank" rel="noopener">Code and results on GitHub →</a></p>
      </div>
    </div>
  </div></section>`;
}
