import { Chart, registerables } from "chart.js";
import { label } from "./model.js";

Chart.register(...registerables);

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
export const colors = () => ({
  c1: css("--chart-1"), c2: css("--chart-2"), c3: css("--chart-3"),
  band: css("--chart-band"), band2: css("--chart-band-2"),
  grid: css("--chart-grid"), text: css("--chart-text"), shade: css("--chart-shade"),
  ink: css("--ink"), card: css("--card"), line: css("--line"),
});

// Every chart created on the current page, destroyed on navigation.
const live = new Set();
export function destroyAll() {
  live.forEach((c) => c.destroy());
  live.clear();
}

export const CRISES = [
  ["2007-11", "2008-12", "2008 food crisis"],
  ["2020-03", "2021-12", "COVID-19"],
  ["2021-05", "2021-11", "Fertilizer ban"],
  ["2022-01", "2023-06", "2022 crisis"],
];

/** Shades crisis periods behind the data (category x-axis of "YYYY-MM" labels). */
const shadePlugin = {
  id: "shade",
  beforeDatasetsDraw(chart, _args, opts) {
    if (!opts?.ranges?.length) return;
    const { ctx, chartArea: a, scales: { x } } = chart;
    const labels = chart.data.labels;
    ctx.save();
    for (const [from, to, name] of opts.ranges) {
      const i0 = labels.indexOf(from), i1 = labels.indexOf(to);
      if (i0 < 0 || i1 < 0) continue;
      const x0 = x.getPixelForValue(i0), x1 = x.getPixelForValue(i1);
      ctx.fillStyle = opts.color;
      ctx.fillRect(x0, a.top, Math.max(x1 - x0, 2), a.bottom - a.top);
      if (opts.labels) {
        ctx.fillStyle = opts.textColor;
        ctx.font = "500 11px 'Inter Variable', sans-serif";
        ctx.fillText(name, x0 + 4, a.top + 14 + 14 * (opts.labels.indexOf(name) % 3));
      }
    }
    ctx.restore();
  },
};
Chart.register(shadePlugin);

function base(c, { yTitle, yFormat = (v) => v, xYearsOnly = true } = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 500 },
    interaction: { mode: "index", intersect: false },
    font: { family: "'Inter Variable', sans-serif" },
    plugins: {
      legend: {
        position: "top", align: "start",
        labels: {
          color: c.text, usePointStyle: true, boxWidth: 28, padding: 16,
          font: { size: 12, family: "'Inter Variable', sans-serif" },
          filter: (item) => !item.text.startsWith("_"),
        },
      },
      tooltip: {
        backgroundColor: c.card, titleColor: c.ink, bodyColor: c.ink, borderColor: c.line, borderWidth: 1,
        padding: 12, cornerRadius: 10, boxPadding: 4, usePointStyle: true,
        titleFont: { weight: "600", family: "'Inter Variable', sans-serif" },
        bodyFont: { family: "'Inter Variable', sans-serif" },
        filter: (item) => !item.dataset.label.startsWith("_") && item.raw != null,
        callbacks: {
          title: (items) => (items.length && /^\d{4}-\d{2}$/.test(items[0].label) ? label(items[0].label) : items[0]?.label),
          label: (item) => ` ${item.dataset.label}: ${yFormat(item.raw)}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { color: c.grid },
        ticks: {
          color: c.text, maxRotation: 0, autoSkip: !xYearsOnly,
          font: { size: 11, family: "'Inter Variable', sans-serif" },
          callback(v) {
            const l = this.getLabelForValue(v);
            if (!xYearsOnly || !/^\d{4}-\d{2}$/.test(l)) return l;
            const n = this.chart.data.labels.length;
            const step = n > 200 ? 4 : n > 80 ? 2 : 1;
            return l.endsWith("-01") && +l.slice(0, 4) % step === 0 ? l.slice(0, 4) : null;
          },
        },
      },
      y: {
        grid: { color: c.grid }, border: { display: false },
        ticks: { color: c.text, font: { size: 11, family: "'Inter Variable', sans-serif" }, callback: yFormat },
        title: yTitle ? { display: true, text: yTitle, color: c.text, font: { size: 12 } } : undefined,
      },
    },
  };
}

function make(canvas, config) {
  const chart = new Chart(canvas, config);
  live.add(chart);
  const destroy = chart.destroy.bind(chart);
  chart.destroy = () => { live.delete(chart); destroy(); };
  return chart;
}

const rsFmt = (v) => (v == null ? "" : `Rs ${Math.round(v)}`);

/**
 * Time-series chart: actual line + optional forecast line with a band.
 * series: {labels, actual, forecast?, lo?, hi?, lo2?, hi2?, forecastLabel?, extra?: [{label, data, color, dash}]}
 */
export function priceChart(canvas, s, { shade = false, shadeLabels = false } = {}) {
  const c = colors();
  const ds = [];
  if (s.hi2) {
    ds.push({ label: "_lo90", data: s.lo2, borderWidth: 0, pointRadius: 0, fill: false });
    ds.push({ label: "90% range", data: s.hi2, borderWidth: 0, pointRadius: 0, fill: "-1", backgroundColor: c.band2, pointStyle: "rect" });
  }
  if (s.hi) {
    ds.push({ label: "_lo80", data: s.lo, borderWidth: 0, pointRadius: 0, fill: false });
    ds.push({ label: "80% range", data: s.hi, borderWidth: 0, pointRadius: 0, fill: "-1", backgroundColor: c.band, pointStyle: "rect" });
  }
  const line = { pointRadius: 0, pointStyle: "line" };
  ds.push({ ...line, label: s.actualLabel ?? "Actual", data: s.actual, borderColor: c.c1, backgroundColor: c.c1, borderWidth: 2.2, tension: 0.2 });
  if (s.retail) ds.push({ ...line, label: "Retail", data: s.retail, borderColor: c.c2, backgroundColor: c.c2, borderWidth: 1.4, tension: 0.2 });
  if (s.forecast) ds.push({ ...line, label: s.forecastLabel ?? "Forecast", data: s.forecast, borderColor: c.c2, backgroundColor: c.c2, borderWidth: 2.4, tension: 0.25 });
  for (const e of s.extra ?? []) ds.push({ ...line, borderWidth: 1.8, tension: 0.25, ...e });
  const opts = base(c, { yFormat: rsFmt });
  opts.plugins.shade = { ranges: shade ? CRISES : [], color: c.shade, textColor: c.text, labels: shadeLabels ? CRISES.map((r) => r[2]) : null };
  return make(canvas, { type: "line", data: { labels: s.labels, datasets: ds }, options: opts });
}

export function sparkline(canvas, values) {
  const c = colors();
  return make(canvas, {
    type: "line",
    data: { labels: values.map((_, i) => i), datasets: [{ data: values, borderColor: c.c1, borderWidth: 2, pointRadius: 0, tension: 0.3, fill: { target: "origin" }, backgroundColor: "transparent" }] },
    options: { responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend: { display: false }, tooltip: { enabled: false } }, scales: { x: { display: false }, y: { display: false } } },
  });
}

/** Vertical bars; values may be signed. highlight(i) -> use accent colour. */
export function barChart(canvas, { labels, values, highlight = () => false, yFormat = (v) => v, horizontal = false, signed = false, errors }) {
  const c = colors();
  const opts = base(c, { yFormat, xYearsOnly: false });
  opts.plugins.legend.display = false;
  opts.interaction = { mode: "nearest", intersect: true };
  opts.plugins.tooltip.callbacks.label = (item) => ` ${yFormat(item.raw)}${errors ? `  (±${errors[item.dataIndex].toFixed(1)})` : ""}`;
  if (horizontal) {
    opts.indexAxis = "y";
    [opts.scales.x, opts.scales.y] = [opts.scales.y, opts.scales.x];
    opts.scales.x.grid = { color: c.grid };
    opts.scales.y.grid = { display: false };
  }
  const bg = values.map((v, i) => (signed ? (v >= 0 ? c.c2 : c.c1) : highlight(i) ? c.c2 : c.c1));
  return make(canvas, {
    type: "bar",
    data: { labels, datasets: [{ label: "value", data: values, backgroundColor: bg, borderRadius: 6, borderSkipped: false, maxBarThickness: 46 }] },
    options: opts,
  });
}

/** Lines across categorical x (e.g. forecast horizon). series: [{label, data, color, dash}] */
export function lineChart(canvas, { labels, series, yFormat = (v) => v, xTitle }) {
  const c = colors();
  const opts = base(c, { yFormat, xYearsOnly: false });
  if (xTitle) opts.scales.x.title = { display: true, text: xTitle, color: c.text, font: { size: 12 } };
  const pal = [c.c1, c.c2, c.c3];
  return make(canvas, {
    type: "line",
    data: {
      labels,
      datasets: series.map((s, i) => ({
        label: s.label, data: s.data, borderColor: s.color ?? pal[i], backgroundColor: s.color ?? pal[i], pointStyle: "line",
        borderWidth: s.dash ? 1.8 : 2.4, borderDash: s.dash ? [6, 4] : [], pointRadius: 3, pointHoverRadius: 5, tension: 0.25,
      })),
    },
    options: opts,
  });
}
