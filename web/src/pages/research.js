import { barChart, lineChart } from "../charts.js";
import { MONTHS } from "../model.js";

const MODEL_NAMES = { ensemble: "Ensemble", sarima: "SARIMA", ets: "ETS", lgbm_direct: "LightGBM", ridge_direct: "Ridge", naive: "Naive (no change)", seasonal_naive: "Seasonal naive" };

export default function research(root, d) {
  const seas = d.seasonal_index;
  const co = d.cointegration.filter((r) => r.test.startsWith("Johansen"))[0];
  const eg = d.cointegration.find((r) => r.system.includes("thai_rice_lkr"));
  const coef = Object.fromEntries(d.whatif.coefficients.map((r) => [r.term, r]));
  const fx = coef.dlog_fx.coef + coef.dlog_fx_lag1.coef;
  const post = d.backtest_summary.filter((r) => r.window.startsWith("post"));
  const stable = d.backtest_summary.filter((r) => r.window.startsWith("stable"));
  const ens = (w) => w.find((r) => r.model === "ensemble");
  const nai = (w) => w.find((r) => r.model === "naive");
  const g = Object.fromEntries(d.granger.map((r) => [r.cause, r]));
  const hi = seas.reduce((a, b) => (b.pct > a.pct ? b : a));
  const lo = seas.reduce((a, b) => (b.pct < a.pct ? b : a));

  root.innerHTML = `
  <section class="page-head"><div class="wrap">
    <p class="eyebrow">Research summary</p>
    <h1>Forecasting Nadu rice wholesale prices in Sri Lanka</h1>
    <p class="lead">An econometric and machine-learning study of 318 months of prices, from January 2000 to June 2026,
    covering the 2008 food crisis, COVID-19, the 2021 fertilizer ban and the 2022 economic crisis.</p>
  </div></section>

  <section class="section tight"><div class="wrap article">
    <nav class="toc" aria-label="On this page">
      <a href="#why">Why it matters</a><a href="#questions">Research questions</a><a href="#data">Data</a>
      <a href="#findings">Key findings</a><a href="#season">Seasonality</a><a href="#links">Long-run links</a>
      <a href="#forecasting">Forecast accuracy</a><a href="#drivers">Short-run drivers</a>
      <a href="#policy">Policy implications</a><a href="#limits">Limitations</a>
    </nav>
    <article class="prose">
      <h2 id="why">Why it matters</h2>
      <p>Rice is Sri Lanka's staple food, and its price is one of the most politically sensitive in the country. Nadu is
      the most widely eaten variety in towns and cities. Farmers decide when to sell, millers how much to stock, and the
      government when to import or release stocks — all based on where they think the price is going. Yet earlier
      Sri Lankan studies used short samples, a single model, or no honest out-of-sample test.</p>

      <h2 id="questions">Research questions</h2>
      <ol class="qa">
        <li>Does the Nadu wholesale price share a long-run relationship with the exchange rate and the world (Thai) rice price?</li>
        <li>Which forecasting method is most accurate 1–12 months ahead, and is it significantly better than a naive forecast?</li>
        <li>How strongly do exchange-rate, world-price, supply and policy shocks pass through to the wholesale price in the short run?</li>
      </ol>

      <h2 id="data">Data</h2>
      <p>Monthly observations for 35 variables, assembled from official sources:</p>
      <div class="table-wrap"><table>
        <thead><tr><th>Group</th><th>Variables</th><th>Source</th></tr></thead>
        <tbody>
          <tr><td>Prices</td><td>Nadu wholesale (Pettah) and retail, Rs/kg</td><td>HARTI</td></tr>
          <tr><td>Supply</td><td>Maha and Yala paddy production; harvest calendar</td><td>Dept. of Census and Statistics</td></tr>
          <tr><td>Weather</td><td>Rainfall, rainy days, temperature, humidity, hot days</td><td>7 rain-zone averages</td></tr>
          <tr><td>External</td><td>Exchange rate, Thai 5% rice, crude oil</td><td>International series</td></tr>
          <tr><td>Policy</td><td>Customs duty, CESS, VAT, PAL on rice; fertilizer subsidy and ban; price control</td><td>Official records</td></tr>
          <tr><td>Macro &amp; shocks</td><td>CCPI inflation; agricultural labour share; crisis periods</td><td>DCS; constructed</td></tr>
        </tbody>
      </table></div>

      <h2 id="findings">Key findings</h2>
      <div class="card flat">
        <div class="finding"><span class="n">1</span><div><b>No long-run link to world rice prices.</b>
          <span class="muted">Johansen and Engle-Granger tests find no cointegration with the exchange rate or the Thai price — consistent with a self-sufficient, import-controlled market.</span></div></div>
        <div class="finding"><span class="n">2</span><div><b>A strong, regular seasonal cycle.</b>
          <span class="muted">${hi.pct.toFixed(1)}% above trend in ${MONTHS[hi.month - 1]}, ${Math.abs(lo.pct).toFixed(1)}% below in ${MONTHS[lo.month - 1]} — tied to the Maha and Yala harvests.</span></div></div>
        <div class="finding"><span class="n">3</span><div><b>The ensemble forecasts best, but not by a significant margin.</b>
          <span class="muted">Average 1–12 month error of ${ens(post).MAPE_avg_1_12.toFixed(1)}% after the crisis (naive: ${nai(post).MAPE_avg_1_12.toFixed(1)}%). Diebold-Mariano tests find no significant difference.</span></div></div>
        <div class="finding"><span class="n">4</span><div><b>The exchange rate is the main external driver.</b>
          <span class="muted">A 1% depreciation raises the wholesale price by about ${fx.toFixed(2)}% within two months.</span></div></div>
      </div>

      <h2 id="season">Seasonality: the harvest sets the rhythm</h2>
      <p>Removing the long-run trend reveals a cycle that repeats every year. Prices are lowest at the Yala harvest
      (August–September) and the Maha harvest (March), and highest in December–January, before the main harvest arrives.
      Trend strength is ${d.stl_strength.stl_trend_strength.toFixed(2)} and seasonal strength ${d.stl_strength.stl_seasonal_strength.toFixed(2)} (STL decomposition).</p>
      <div class="card chart-card">
        <p class="chart-title">Prices peak in ${MONTHS[hi.month - 1]} and bottom out in ${MONTHS[lo.month - 1]}</p>
        <p class="chart-sub">Average deviation from the 12-month trend, %. Gold bars: harvest months.</p>
        <div class="chart-box short"><canvas id="seas"></canvas></div>
      </div>

      <h2 id="links">Long-run links: a domestic market</h2>
      <p>The wholesale price, exchange rate and Thai rice price all trend without a fixed mean (unit-root tests). If rice
      followed import parity, they would move together in the long run. They do not: the Johansen trace statistic is
      ${co.stat.toFixed(1)} against a 5% critical value of ${co.crit_5pct.toFixed(1)}, and the Engle-Granger test with
      the Thai price in rupees gives p = ${eg.p_value.toFixed(3)}. In the short run, changes in the exchange rate
      (p = ${g.log_lkr_per_usd.p_value.toFixed(3)}) and in the last harvest (p &lt; 0.001) help predict price changes,
      while Thai rice (p = ${g.log_thai_rice_usd.p_value.toFixed(2)}) and oil prices do not.</p>

      <h2 id="forecasting">Forecast accuracy</h2>
      <p>Seven methods were tested by repeatedly “standing” at a past month, forecasting 12 months ahead with only the
      data available then, and comparing with what actually happened — 48 times in 2015–2018 and 25 times in 2023–2025.</p>
      <div class="card chart-card">
        <p class="chart-title">The ensemble leads at 2–9 months ahead</p>
        <p class="chart-sub">Forecast error (MAPE, %) by horizon, post-crisis window 2023–2025.</p>
        <div class="chart-box"><canvas id="mape"></canvas></div>
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Model</th><th class="r">Stable 2015–18</th><th class="r">Post-crisis 2023–25</th></tr></thead>
        <tbody>${post.slice().sort((a, b) => a.MAPE_avg_1_12 - b.MAPE_avg_1_12).map((p) => {
          const s = stable.find((r) => r.model === p.model);
          return `<tr class="${p.model === "ensemble" ? "hl" : ""}"><td>${MODEL_NAMES[p.model] ?? p.model}</td><td class="r">${s.MAPE_avg_1_12.toFixed(2)}%</td><td class="r">${p.MAPE_avg_1_12.toFixed(2)}%</td></tr>`;
        }).join("")}</tbody>
      </table></div>
      <p class="small muted">Average MAPE over horizons 1–12. Machine-learning models did well at short horizons but
      degraded beyond six months, as is common with about 300 observations.</p>

      <h2 id="drivers">Short-run drivers</h2>
      <p>A dynamic regression on monthly changes (an ARDL in first differences, with Newey-West errors) measures how much
      of each shock reaches the wholesale price.</p>
      <div class="card chart-card">
        <p class="chart-title">The exchange rate has the largest pass-through</p>
        <p class="chart-sub">Percentage change in the wholesale price after a 10% rise in each driver (or while a policy is in force).</p>
        <div class="chart-box short"><canvas id="elas"></canvas></div>
      </div>

      <h2 id="policy">Policy implications</h2>
      <ul>
        <li><b>Exchange-rate policy is food-price policy.</b> A 10% depreciation implies roughly a ${(fx * 10).toFixed(0)}% rise in wholesale rice prices within two months.</li>
        <li><b>Imports are a safety valve, not an anchor.</b> Timely import decisions in shortages matter more than permanent tariff changes.</li>
        <li><b>The seasonal swing is large and predictable.</b> Farmer-level storage and warehouse receipts could let farmers, not only large millers, gain from it.</li>
        <li><b>Input policy shows up in consumer prices.</b> The 2021 fertilizer ban is associated with faster monthly price increases.</li>
      </ul>

      <h2 id="limits">Limitations</h2>
      <p>The CCPI inflation series combines two definitions from December 2023 and will be re-extracted from DCS.
      Seasonal production is spread evenly across months, and about 300 observations limit complex models. Forecasts
      cannot know future exchange rates or harvests, so long-range figures are projections with wide ranges.</p>
      <p><a class="btn btn-ghost" href="#/methods">Full data &amp; methods →</a></p>
    </article>
  </div></section>`;

  barChart(root.querySelector("#seas"), {
    labels: seas.map((s) => MONTHS[s.month - 1]), values: seas.map((s) => +s.pct.toFixed(2)),
    highlight: (i) => [2, 3, 8, 9].includes(seas[i].month), yFormat: (v) => `${v > 0 ? "+" : ""}${(+v).toFixed(1)}%`,
  });

  const byH = d.backtest_by_horizon.filter((r) => r.window.startsWith("post"));
  const series = ["ensemble", "sarima", "naive"].map((m) => ({
    label: MODEL_NAMES[m], data: byH.filter((r) => r.model === m).sort((a, b) => a.h - b.h).map((r) => +r.MAPE.toFixed(2)),
    dash: m === "naive",
  }));
  lineChart(root.querySelector("#mape"), {
    labels: Array.from({ length: 12 }, (_, i) => `${i + 1}`), series, xTitle: "Months ahead", yFormat: (v) => `${(+v).toFixed(1)}%`,
  });

  const eff = [
    ["Exchange rate (2 months)", (Math.exp(fx * Math.log(1.1)) - 1) * 100],
    ["Thai rice price", (Math.exp(coef.dlog_thai_usd.coef * Math.log(1.1)) - 1) * 100],
    ["World oil price", (Math.exp(coef.dlog_oil_usd.coef * Math.log(1.1)) - 1) * 100],
    ["Import duty", (Math.exp(coef.dlog_duty.coef * Math.log(1.1)) - 1) * 100],
    ["Fertilizer ban (per month)", (Math.exp(coef.fertilizer_ban.coef) - 1) * 100],
  ];
  barChart(root.querySelector("#elas"), {
    labels: eff.map((e) => e[0]), values: eff.map((e) => +e[1].toFixed(2)), horizontal: true,
    highlight: (i) => i === 0, yFormat: (v) => `+${(+v).toFixed(1)}%`,
  });
}
