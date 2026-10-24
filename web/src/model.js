// Browser versions of the website's two calculators. They mirror app.py / 04_whatif_model.py /
// 05_long_horizon.py exactly, using the coefficients exported to data/site.json.

export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August",
  "September", "October", "November", "December"];

const Z80 = 1.2816;

export const ym = (s) => ({ y: +s.slice(0, 4), m: +s.slice(5, 7) });
export const label = (s) => `${MONTHS[ym(s).m - 1]} ${ym(s).y}`;
export const monthsBetween = (from, to) => (to.y - from.y) * 12 + (to.m - from.m);
export const addMonths = ({ y, m }, k) => {
  const t = y * 12 + (m - 1) + k;
  return { y: Math.floor(t / 12), m: (t % 12) + 1 };
};
export const key = ({ y, m }) => `${y}-${String(m).padStart(2, "0")}`;

/** One-month-ahead scenario price from the ARDL-in-differences model. */
export function whatIf(W, inp) {
  const D = W.defaults;
  const logP = Math.log(inp.priceLast);
  const x = {
    const: 1,
    dlog_price_lag1: Math.log(inp.priceLast / D.price_prev),
    dev_from_ma12_lag1: logP - (D.ma12_log + (logP - Math.log(D.price_last)) / 12),
    dlog_fx: Math.log(inp.fx / D.fx_last),
    dlog_fx_lag1: D.dlog_fx_last,
    dlog_thai_usd: Math.log(inp.thai / D.thai_last),
    dlog_oil_usd: Math.log(inp.oil / D.oil_last),
    harvest_gap: Math.log(inp.harvest / D.harvest_avg),
    rain_anom_lag1: (inp.rain - D.rain_clim[String(D.last_month)]) / 100,
    dlog_duty: Math.log(inp.duty / D.duty_last),
    fertilizer_ban: inp.fertBan ? 1 : 0,
    price_control: inp.priceControl ? 1 : 0,
    crisis_2008: 0,
    crisis_2022: inp.crisis ? 1 : 0,
    covid_2020_21: 0,
  };
  for (let m = 2; m <= 12; m++) x[`m${m}`] = inp.month === m ? 1 : 0;

  const contrib = {};
  let dlog = 0;
  for (const [k, b] of Object.entries(W.params)) {
    contrib[k] = b * (x[k] ?? 0);
    dlog += contrib[k];
  }
  const groups = {
    "Exchange rate": ["dlog_fx", "dlog_fx_lag1"],
    "Thai rice price": ["dlog_thai_usd"],
    "Oil price": ["dlog_oil_usd"],
    "Harvest size": ["harvest_gap"],
    "Rainfall": ["rain_anom_lag1"],
    "Import duty": ["dlog_duty"],
    "Policy & crisis": ["fertilizer_ban", "price_control", "crisis_2022"],
    "Seasonality": ["const", ...Array.from({ length: 11 }, (_, i) => `m${i + 2}`)],
    "Price momentum": ["dlog_price_lag1", "dev_from_ma12_lag1"],
  };
  const effects = Object.entries(groups)
    .map(([name, ks]) => ({ name, pct: (Math.exp(ks.reduce((s, k) => s + (contrib[k] ?? 0), 0)) - 1) * 100 }))
    .sort((a, b) => b.pct - a.pct);
  const se = W.resid_sd;
  return {
    pred: inp.priceLast * Math.exp(dlog),
    lo: inp.priceLast * Math.exp(dlog - Z80 * se),
    hi: inp.priceLast * Math.exp(dlog + Z80 * se),
    pct: (Math.exp(dlog) - 1) * 100,
    effects,
  };
}

/** Long-horizon projection k months ahead for calendar month m, at annual log growth g. */
export function project(LH, g, k, m) {
  const centre = Math.exp(LH.base_log_level + (g * k) / 12 + LH.seasonal[String(m)]);
  const sd = LH.sd_by_h[String(Math.min(k, 120))];
  return { point: centre, lo: centre * Math.exp(-Z80 * sd), hi: centre * Math.exp(Z80 * sd) };
}

export const rs = (v, d = 2) => `Rs ${v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d })}`;
export const pct = (v, d = 1) => `${v > 0 ? "+" : ""}${v.toFixed(d)}%`;
