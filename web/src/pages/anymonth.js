import { priceChart } from "../charts.js";
import { MONTHS_LONG, addMonths, key, label, monthsBetween, pct, project, rs, ym } from "../model.js";

export default function anyMonth(root, d) {
  const LH = d.long_horizon;
  const last = ym(d.last_date);
  const lastPrice = LH.last_price;
  const years = Array.from({ length: 2035 - last.y + 1 }, (_, i) => last.y + i);
  const state = { y: Math.min(2030, 2035), m: 8, mode: "inflation", infl: LH.inflation_target * 100, custom: 6 };

  root.innerHTML = `
  <section class="page-head"><div class="wrap">
    <p class="eyebrow">Price for any month</p>
    <h1>What will Nadu rice cost in a month you choose?</h1>
    <p class="lead">Up to 12 months ahead the forecasting model answers. Further out, the price is projected from
    today's underlying level, the growth you expect and that month's seasonal pattern — with an honest range.</p>
  </div></section>

  <section class="section tight"><div class="wrap grid split">
    <div class="card form-grid">
      <div class="grid g2" style="gap:12px">
        <div class="field"><label for="m">Month</label>
          <select id="m">${MONTHS_LONG.map((n, i) => `<option value="${i + 1}">${n}</option>`).join("")}</select></div>
        <div class="field"><label for="y">Year</label>
          <select id="y">${years.map((y) => `<option>${y}</option>`).join("")}</select></div>
      </div>
      <div class="field">
        <label>Price growth assumption</label>
        <div class="seg" role="group" aria-label="Growth assumption">
          <button data-mode="inflation">Inflation-based</button>
          <button data-mode="historical">Historical ${(LH.growth_historical * 100).toFixed(1)}%</button>
          <button data-mode="custom">Custom</button>
        </div>
      </div>
      <div class="field" id="infl-field">
        <label for="infl">Expected inflation: <span id="infl-v" class="num"></span> per year</label>
        <input id="infl" type="range" min="0" max="20" step="0.5" />
        <span class="hint">Central Bank of Sri Lanka target: 5%. Average 2000–2026: ${(LH.inflation_avg * 100).toFixed(1)}%.
        Rice's own real trend (+${(LH.real_trend * 100).toFixed(1)}%/yr) is added.</span>
      </div>
      <div class="field" id="custom-field" hidden>
        <label for="custom">Price growth: <span id="custom-v" class="num"></span> per year</label>
        <input id="custom" type="range" min="-5" max="25" step="0.5" />
      </div>
    </div>

    <div class="grid" style="gap:16px">
      <div class="card result-card" aria-live="polite">
        <p class="label" id="r-label"></p>
        <div class="big num" id="r-price"></div>
        <div id="r-delta" class="small"></div>
        <div class="meta">
          <div><span>80% range</span><b class="num" id="r-range"></b></div>
          <div><span>Months ahead</span><b class="num" id="r-h"></b></div>
          <div><span>Method</span><b id="r-method"></b></div>
        </div>
      </div>
      <div class="note" id="r-note"></div>
    </div>
  </div></section>

  <section class="section tight"><div class="wrap">
    <div class="card chart-card">
      <p class="chart-title" id="c-title"></p>
      <p class="chart-sub">Actual price since 2015 and the expected path to the chosen month, with the 80% range.</p>
      <div class="chart-box tall"><canvas id="path"></canvas></div>
    </div>
  </div></section>`;

  const $ = (s) => root.querySelector(s);
  $("#m").value = state.m;
  $("#y").value = state.y;
  $("#infl").value = state.infl;
  $("#custom").value = state.custom;
  let chart;

  const growth = () =>
    state.mode === "historical" ? LH.growth_historical
      : state.mode === "custom" ? state.custom / 100
        : state.infl / 100 + LH.real_trend;

  function update() {
    root.querySelectorAll(".seg button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === state.mode)));
    $("#infl-field").hidden = state.mode !== "inflation";
    $("#custom-field").hidden = state.mode !== "custom";
    $("#infl-v").textContent = `${(+state.infl).toFixed(1)}%`;
    $("#custom-v").textContent = `${(+state.custom).toFixed(1)}%`;

    const target = { y: +state.y, m: +state.m };
    const h = monthsBetween(last, target);
    const g = growth();
    const name = `${MONTHS_LONG[target.m - 1]} ${target.y}`;

    if (h <= 0) {
      const row = d.history.find((r) => r.date === key(target));
      $("#r-label").textContent = `Actual wholesale price, ${name}`;
      $("#r-price").textContent = row ? rs(row.wholesale_price) : "No data";
      $("#r-delta").textContent = "This month is already in the data.";
      $("#r-range").textContent = "—"; $("#r-h").textContent = "0"; $("#r-method").textContent = "Observed (HARTI)";
      $("#r-note").textContent = "Pick a month after " + label(d.last_date) + " to see a forecast.";
      chart?.destroy();
      $("#c-title").textContent = name;
      return;
    }

    let point, lo, hi, method, path;
    if (h <= 12) {
      const f = d.forecast.find((r) => r.date === key(target));
      ({ point } = f); lo = f.lo80; hi = f.hi80;
      method = "12-month model";
      path = d.forecast.slice(0, h).map((r) => ({ date: r.date, point: r.point, lo: r.lo80, hi: r.hi80 }));
    } else {
      ({ point, lo, hi } = project(LH, g, h, target.m));
      method = `Projection, ${(g * 100).toFixed(1)}%/yr`;
      path = Array.from({ length: h }, (_, i) => {
        const t = addMonths(last, i + 1);
        return { date: key(t), ...project(LH, g, i + 1, t.m) };
      });
    }

    $("#r-label").textContent = `Expected wholesale price, ${name}`;
    $("#r-price").textContent = rs(point);
    $("#r-delta").textContent = `${pct((point / lastPrice - 1) * 100)} compared with ${label(d.last_date)} (${rs(lastPrice)})`;
    $("#r-range").textContent = `Rs ${Math.round(lo)} – ${Math.round(hi)}`;
    $("#r-h").textContent = h;
    $("#r-method").textContent = method;

    if (h > 12) {
      const bt = LH.backtest;
      const near = bt.reduce((a, b) => (Math.abs(b.h - Math.min(h, 60)) < Math.abs(a.h - Math.min(h, 60)) ? b : a));
      $("#r-note").innerHTML = `<b>How reliable is this?</b> Projections made ${near.h} months ahead in 2005–2021 missed the
        actual price by ${near.MAPE_projection.toFixed(0)}% on average (assuming no change missed by ${near.MAPE_naive.toFixed(0)}%).
        Use the expected price for planning and the 80% range as the realistic spread — currency crises, droughts or
        policy changes can push prices outside it.`;
    } else {
      $("#r-note").innerHTML = `<b>Within the forecast window.</b> This month comes straight from the 12-month forecast,
        which does not depend on the growth assumption.`;
    }

    const hist = d.history.filter((r) => +r.date.slice(0, 4) >= 2015);
    const labels = [...hist.map((r) => r.date), ...path.map((p) => p.date)];
    const pad = (arr) => [...Array(hist.length - 1).fill(null), lastPrice, ...arr];
    chart?.destroy();
    chart = priceChart($("#path"), {
      labels,
      actual: [...hist.map((r) => r.wholesale_price), ...path.map(() => null)],
      forecast: pad(path.map((p) => p.point)),
      forecastLabel: "Expected",
      lo: pad(path.map((p) => p.lo)),
      hi: pad(path.map((p) => p.hi)),
    });
    $("#c-title").textContent = `${rs(point, 0)} expected in ${name}`;
  }

  $("#m").addEventListener("change", (e) => { state.m = e.target.value; update(); });
  $("#y").addEventListener("change", (e) => { state.y = e.target.value; update(); });
  $("#infl").addEventListener("input", (e) => { state.infl = e.target.value; update(); });
  $("#custom").addEventListener("input", (e) => { state.custom = e.target.value; update(); });
  root.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => { state.mode = b.dataset.mode; update(); }));
  update();
}
