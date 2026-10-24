import { priceChart } from "../charts.js";
import { label, pct, rs } from "../model.js";

const NAMES = { ensemble: "Ensemble (ETS + SARIMA + LightGBM)", sarima: "SARIMA", ets: "ETS", lgbm_direct: "LightGBM", ridge_direct: "Ridge" };

export default function forecast(root, d) {
  const hist = d.history;
  const last = hist.at(-1);
  const fc = d.forecast;
  const ranges = [["2y", 24], ["5y", 60], ["10y", 120], ["All", hist.length]];

  root.innerHTML = `
  <section class="page-head"><div class="wrap">
    <p class="eyebrow">12-month forecast</p>
    <h1>Nadu wholesale price to ${label(fc.at(-1).date)}</h1>
    <p class="lead">The forecast averages three models — exponential smoothing, seasonal ARIMA and gradient-boosted trees —
    which together had the lowest error in back-tests. Ranges come from the model's real past mistakes.</p>
  </div></section>

  <section class="section tight"><div class="wrap">
    <div class="card chart-card">
      <div class="row-between">
        <div>
          <p class="chart-title">Dip at the Yala harvest, peak in ${label(fc.reduce((a, b) => (b.point > a.point ? b : a)).date)}</p>
          <p class="chart-sub">Actual and forecast wholesale price, Rs/kg, with 80% and 90% ranges.</p>
        </div>
        <div class="seg" role="group" aria-label="History shown">
          ${ranges.map(([t, n], i) => `<button data-n="${n}" aria-pressed="${i === 1}">${t}</button>`).join("")}
        </div>
      </div>
      <div class="chart-box tall"><canvas id="fc"></canvas></div>
      <p class="source">Model: ${NAMES[d.best_model] ?? d.best_model}. Data: HARTI, to ${label(last.date)}.</p>
    </div>
  </div></section>

  <section class="section tight"><div class="wrap grid g2" style="align-items:start">
    <div>
      <div class="row-between" style="margin-bottom:12px">
        <h2 style="margin:0">Month by month</h2>
        <button class="btn btn-ghost" id="csv">Download CSV</button>
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Month</th><th class="r">Forecast</th><th class="r">vs ${label(last.date)}</th><th class="r">80% range</th><th class="r">90% range</th></tr></thead>
        <tbody>${fc.map((r) => `<tr><td>${label(r.date)}</td><td class="r"><b>${rs(r.point)}</b></td>
          <td class="r">${pct((r.point / last.wholesale_price - 1) * 100)}</td>
          <td class="r">${Math.round(r.lo80)}–${Math.round(r.hi80)}</td><td class="r">${Math.round(r.lo90)}–${Math.round(r.hi90)}</td></tr>`).join("")}</tbody>
      </table></div>
    </div>
    <div class="grid" style="gap:16px">
      <div class="card flat">
        <h3>How to read the ranges</h3>
        <p class="muted">About 8 in 10 future prices should fall inside the 80% range, and 9 in 10 inside the 90% range.
        They widen with time because more can happen — a weak harvest, a currency move or a policy change.</p>
      </div>
      <div class="card flat">
        <h3>How good is it?</h3>
        <p class="muted">In 25 forecasts made from mid-2023 to mid-2025, the ensemble missed by
        ${d.backtest_summary.find((r) => r.window.startsWith("post") && r.model === "ensemble").MAPE_h1.toFixed(1)}% one month ahead
        and ${d.backtest_summary.find((r) => r.window.startsWith("post") && r.model === "ensemble").MAPE_avg_1_12.toFixed(1)}% on average over 12 months.
        It beats “no change” on average, but not by a statistically significant margin.</p>
        <a href="#/methods">See the model comparison →</a>
      </div>
      <div class="note">Need a month beyond ${label(fc.at(-1).date)}? Use <a href="#/any-month">Price for any month</a>.</div>
    </div>
  </div></section>`;

  let chart;
  const draw = (n) => {
    chart?.destroy();
    const h = hist.slice(-n);
    const labels = [...h.map((r) => r.date), ...fc.map((r) => r.date)];
    const pad = (arr) => [...Array(h.length - 1).fill(null), last.wholesale_price, ...arr];
    chart = priceChart(root.querySelector("#fc"), {
      labels,
      actual: [...h.map((r) => r.wholesale_price), ...fc.map(() => null)],
      forecast: pad(fc.map((r) => r.point)),
      lo: pad(fc.map((r) => r.lo80)),
      hi: pad(fc.map((r) => r.hi80)),
      lo2: pad(fc.map((r) => r.lo90)), hi2: pad(fc.map((r) => r.hi90)),
    }, { shade: n > 60 });
  };
  draw(60);
  root.querySelectorAll(".seg button").forEach((b) =>
    b.addEventListener("click", () => {
      root.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      draw(+b.dataset.n);
    }));

  root.querySelector("#csv").addEventListener("click", () => {
    const rows = [["month", "forecast_rs_kg", "lo80", "hi80", "lo90", "hi90"], ...fc.map((r) => [r.date, r.point, r.lo80, r.hi80, r.lo90, r.hi90])];
    const a = Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(new Blob([rows.map((r) => r.join(",")).join("\n")], { type: "text/csv" })),
      download: "nadu_wholesale_forecast_12m.csv",
    });
    a.click();
    URL.revokeObjectURL(a.href);
  });
}
