import { priceChart, sparkline } from "../charts.js";
import { label, pct, rs } from "../model.js";

const icon = {
  chart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 6-6"/></svg>`,
  calendar: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>`,
  sliders: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/></svg>`,
  book: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 4h7a3 3 0 0 1 3 3v14a2 2 0 0 0-2-2H2zM22 4h-7a3 3 0 0 0-3 3v14a2 2 0 0 1 2-2h8z"/></svg>`,
};

export default function home(root, d) {
  const hist = d.history;
  const last = hist.at(-1);
  const next = d.forecast[0];
  const peak = d.forecast.reduce((a, b) => (b.point > a.point ? b : a));
  const in12 = d.forecast.at(-1);
  const ens = d.backtest_summary.find((r) => r.window.startsWith("post") && r.model === "ensemble");
  const fx = d.whatif.coefficients.filter((r) => r.term.startsWith("dlog_fx")).reduce((s, r) => s + r.coef, 0);
  const seas = d.seasonal_index;
  const swing = Math.max(...seas.map((s) => s.pct)) - Math.min(...seas.map((s) => s.pct));
  const first = hist[0];

  root.innerHTML = `
  <section class="hero">
    <div class="wrap hero-grid">
      <div>
        <p class="eyebrow">Sri Lanka · Pettah wholesale market</p>
        <h1>Where is the price of <em>Nadu rice</em> heading?</h1>
        <p class="lead">Twenty-six years of prices, harvests, weather, exchange rates and policy, turned into a
        12-month forecast, a projection for any month up to 2035, and a simulator for “what if” questions.</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="#/forecast">See the forecast →</a>
          <a class="btn btn-ghost" href="#/research">Read the research</a>
        </div>
      </div>
      <div class="card price-card">
        <div class="row-between">
          <p class="label">Wholesale price, ${label(last.date)}</p>
          <span class="pill">Rs per kg</span>
        </div>
        <div class="big num">${last.wholesale_price.toFixed(2)}<small>Rs/kg</small></div>
        <div class="spark"><canvas id="spark" aria-label="Wholesale price over the last 3 years"></canvas></div>
        <div class="row">
          <div><span class="label muted small">Next month</span><b class="num">${rs(next.point)}</b>
            <span class="delta ${next.point > last.wholesale_price ? "up" : "down"}">${pct((next.point / last.wholesale_price - 1) * 100)}</span></div>
          <div><span class="label muted small">Seasonal peak</span><b class="num">${rs(peak.point)}</b>
            <span class="muted small">${label(peak.date)}</span></div>
          <div><span class="label muted small">In 12 months</span><b class="num">${rs(in12.point)}</b>
            <span class="delta ${in12.point > last.wholesale_price ? "up" : "down"}">${pct((in12.point / last.wholesale_price - 1) * 100)}</span></div>
        </div>
      </div>
    </div>
  </section>

  <section class="section tight">
    <div class="wrap">
      <p class="eyebrow">What the research found</p>
      <div class="grid g3">
        <div class="card stat">
          <div class="value num">${fx.toFixed(2)}%</div>
          <p class="what">rise in rice price for every 1% fall of the rupee</p>
          <p>The exchange rate passes through to wholesale prices within two months — the strongest external driver.</p>
        </div>
        <div class="card stat">
          <div class="value num">${swing.toFixed(0)} pts</div>
          <p class="what">seasonal swing between August and January</p>
          <p>Prices dip with the Yala and Maha harvests and peak in December–January, every year.</p>
        </div>
        <div class="card stat">
          <div class="value num">${ens.MAPE_avg_1_12.toFixed(1)}%</div>
          <p class="what">average forecast error, 1–12 months ahead</p>
          <p>Tested honestly on 2023–2025, forecasting only from data available at the time.</p>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="card chart-card">
        <div class="row-between">
          <div>
            <p class="chart-title">A price that rose ${(last.wholesale_price / first.wholesale_price).toFixed(1)}× in 26 years</p>
            <p class="chart-sub">Nadu wholesale and retail price, Rs/kg, ${label(first.date)} – ${label(last.date)}. Shaded: crisis periods.</p>
          </div>
        </div>
        <div class="chart-box tall"><canvas id="history"></canvas></div>
        <p class="source">Source: Hector Kobbekaduwa Agrarian Research and Training Institute (HARTI).</p>
      </div>
    </div>
  </section>

  <section class="section section-alt">
    <div class="wrap">
      <p class="eyebrow">Tools</p>
      <h2>Ask the data a question</h2>
      <div class="grid g4" style="margin-top:24px">
        <a class="card tool-card" href="#/forecast"><span class="icon">${icon.chart}</span><h3>12-month forecast</h3>
          <p>Month-by-month prices to ${label(in12.date)} with realistic ranges.</p><span class="go">Open forecast →</span></a>
        <a class="card tool-card" href="#/any-month"><span class="icon">${icon.calendar}</span><h3>Price for any month</h3>
          <p>Pick a month up to 2035 — say, August 2030 — and see the expected price.</p><span class="go">Pick a month →</span></a>
        <a class="card tool-card" href="#/what-if"><span class="icon">${icon.sliders}</span><h3>What-if simulator</h3>
          <p>Change the exchange rate, harvest or policy and watch next month's price respond.</p><span class="go">Try a scenario →</span></a>
        <a class="card tool-card" href="#/research"><span class="icon">${icon.book}</span><h3>The research</h3>
          <p>Questions, data, methods and findings of the study in plain language.</p><span class="go">Read summary →</span></a>
      </div>
    </div>
  </section>`;

  const recent = hist.slice(-36);
  sparkline(root.querySelector("#spark"), recent.map((r) => r.wholesale_price));
  priceChart(root.querySelector("#history"), {
    labels: hist.map((r) => r.date),
    actual: hist.map((r) => r.wholesale_price),
    actualLabel: "Wholesale",
    retail: hist.map((r) => r.retail_price),
  }, { shade: true, shadeLabels: true });
}
