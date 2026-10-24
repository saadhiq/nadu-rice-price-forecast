import { barChart } from "../charts.js";
import { MONTHS, MONTHS_LONG, addMonths, label, pct, rs, whatIf, ym } from "../model.js";

export default function whatIfPage(root, d) {
  const W = d.whatif;
  const D = W.defaults;
  const nextM = (D.last_month % 12) + 1;
  const lastLbl = label(d.last_date);
  const nextLbl = label(`${addMonths(ym(d.last_date), 1).y}-${String(nextM).padStart(2, "0")}`);
  const dirAcc = W.test_metrics.find((r) => r.model.startsWith("OLS")).direction_accuracy_pct;

  const num = (id, lab, value, step, hint) => `
    <div class="field"><label for="${id}">${lab}</label>
      <input id="${id}" type="number" step="${step}" value="${+value.toFixed(2)}" />
      <span class="hint">${hint}</span></div>`;
  const sw = (id, lab) => `<label class="switch" for="${id}"><span>${lab}</span><input type="checkbox" id="${id}" /></label>`;

  root.innerHTML = `
  <section class="page-head"><div class="wrap">
    <p class="eyebrow">What-if simulator</p>
    <h1>Change the conditions, see next month's price</h1>
    <p class="lead">Every input starts at its latest value (${lastLbl}), so the first result is the baseline. Move the
    exchange rate, world prices, the harvest or policy, and the model estimates the price one month later.</p>
  </div></section>

  <section class="section tight"><div class="wrap grid split-r">
    <div class="grid" style="gap:16px">
      <div class="card">
        <h3>Market &amp; currency</h3>
        <div class="grid g2" style="gap:14px; margin-top:12px">
          ${num("price", "This month's wholesale price (Rs/kg)", D.price_last, 1, `Latest: ${rs(D.price_last)}`)}
          ${num("fx", "Exchange rate next month (LKR per USD)", D.fx_last, 1, `Latest: ${D.fx_last.toFixed(2)}`)}
          ${num("thai", "Thai 5% rice price (USD/t)", D.thai_last, 5, `Latest: ${D.thai_last.toFixed(0)}`)}
          ${num("oil", "World oil price (USD/barrel)", D.oil_last, 1, `Latest: ${D.oil_last.toFixed(1)}`)}
        </div>
      </div>
      <div class="card">
        <h3>Supply, weather &amp; season</h3>
        <div class="grid g2" style="gap:14px; margin-top:12px">
          ${num("harvest", "Last season's paddy harvest ('000 t)", D.harvest_last, 10, `Latest: ${D.harvest_last.toFixed(0)} · 3-year normal: ${D.harvest_avg.toFixed(0)}`)}
          ${num("rain", "Rainfall this month (mm)", D.rain_last, 5, `Normal for ${MONTHS[D.last_month - 1]}: ${D.rain_clim[String(D.last_month)].toFixed(0)} mm`)}
          <div class="field"><label for="month">Month being predicted</label>
            <select id="month">${MONTHS_LONG.map((n, i) => `<option value="${i + 1}" ${i + 1 === nextM ? "selected" : ""}>${n}</option>`).join("")}</select>
            <span class="hint">Default: ${nextLbl}</span></div>
          ${num("duty", "Import customs duty (Rs/kg)", D.duty_last, 5, `Latest: Rs ${D.duty_last}`)}
        </div>
      </div>
      <div class="card">
        <h3>Policy &amp; shocks</h3>
        ${sw("ban", "Fertilizer import ban")}
        ${sw("ctrl", "Government price control")}
        ${sw("crisis", "Economic crisis (2022-type)")}
      </div>
    </div>

    <div class="grid sticky-col" style="gap:16px">
      <div class="card result-card" aria-live="polite">
        <p class="label" id="r-label"></p>
        <div class="big num" id="r-price"></div>
        <div class="small" id="r-delta"></div>
        <div class="meta">
          <div><span>80% range</span><b class="num" id="r-range"></b></div>
          <div><span>Direction</span><b id="r-dir"></b></div>
        </div>
      </div>
      <div class="card chart-card">
        <p class="chart-title">What is moving the price</p>
        <p class="chart-sub">Contribution of each driver to next month's change, %.</p>
        <div class="chart-box short"><canvas id="eff"></canvas></div>
      </div>
      <div class="row-between"><button class="btn btn-ghost" id="reset">Reset to latest values</button></div>
      <p class="small muted">Short-run regression on monthly changes (ARDL, Newey-West errors, R² = ${W.r2.toFixed(2)}).
      Out of sample it called the direction of change correctly in ${dirAcc.toFixed(0)}% of months (2023–2026).
      Very large shocks beyond those seen since 2000 are extrapolation.</p>
    </div>
  </div></section>`;

  const $ = (s) => root.querySelector(s);
  let chart;
  function update() {
    const inp = {
      priceLast: +$("#price").value || D.price_last, fx: +$("#fx").value || D.fx_last,
      thai: +$("#thai").value || D.thai_last, oil: +$("#oil").value || D.oil_last,
      harvest: +$("#harvest").value || D.harvest_last, rain: +$("#rain").value || 0,
      duty: +$("#duty").value || D.duty_last, month: +$("#month").value,
      fertBan: $("#ban").checked, priceControl: $("#ctrl").checked, crisis: $("#crisis").checked,
    };
    const r = whatIf(W, inp);
    $("#r-label").textContent = `Predicted wholesale price, ${MONTHS_LONG[inp.month - 1]}`;
    $("#r-price").textContent = rs(r.pred);
    $("#r-delta").textContent = `${pct(r.pct, 2)} from ${rs(inp.priceLast)}`;
    $("#r-range").textContent = `Rs ${Math.round(r.lo)} – ${Math.round(r.hi)}`;
    $("#r-dir").textContent = r.pct >= 0 ? "▲ Up" : "▼ Down";
    chart?.destroy();
    chart = barChart($("#eff"), {
      labels: r.effects.map((e) => e.name), values: r.effects.map((e) => +e.pct.toFixed(2)),
      horizontal: true, signed: true, yFormat: (v) => `${v > 0 ? "+" : ""}${(+v).toFixed(1)}%`,
    });
  }
  root.querySelectorAll("input, select").forEach((el) => el.addEventListener(el.type === "checkbox" || el.tagName === "SELECT" ? "change" : "input", update));
  $("#reset").addEventListener("click", () => {
    $("#price").value = D.price_last.toFixed(2); $("#fx").value = D.fx_last.toFixed(2); $("#thai").value = D.thai_last;
    $("#oil").value = D.oil_last; $("#harvest").value = D.harvest_last.toFixed(1); $("#rain").value = D.rain_last;
    $("#duty").value = D.duty_last; $("#month").value = nextM;
    ["#ban", "#ctrl", "#crisis"].forEach((s) => ($(s).checked = false));
    update();
  });
  update();
}
