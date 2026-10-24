import "./style.css";
import { destroyAll } from "./charts.js";
import { label } from "./model.js";
import home from "./pages/home.js";
import research from "./pages/research.js";
import forecast from "./pages/forecast.js";
import anyMonth from "./pages/anymonth.js";
import whatIf from "./pages/whatif.js";
import methods from "./pages/methods.js";

const routes = {
  "/": [home, "Nadu Rice Price Monitor · Sri Lanka"],
  "/research": [research, "Research summary · Nadu Rice Price Monitor"],
  "/forecast": [forecast, "12-month forecast · Nadu Rice Price Monitor"],
  "/any-month": [anyMonth, "Price for any month · Nadu Rice Price Monitor"],
  "/what-if": [whatIf, "What-if simulator · Nadu Rice Price Monitor"],
  "/methods": [methods, "Data & methods · Nadu Rice Price Monitor"],
};

const main = document.getElementById("main");
const nav = document.getElementById("nav");
const toggle = document.querySelector(".nav-toggle");
let data;

toggle.addEventListener("click", () => {
  const open = nav.classList.toggle("open");
  toggle.setAttribute("aria-expanded", String(open));
});

function render() {
  const path = location.hash.replace(/^#/, "") || "/";
  const [page, title] = routes[path] ?? routes["/"];
  destroyAll();
  document.title = title;
  nav.querySelectorAll("a").forEach((a) => a.toggleAttribute("aria-current", a.getAttribute("href") === `#${path}`));
  nav.querySelectorAll("a[aria-current]").forEach((a) => a.setAttribute("aria-current", "page"));
  nav.classList.remove("open");
  toggle.setAttribute("aria-expanded", "false");
  main.innerHTML = "";
  const view = document.createElement("div");
  view.className = "fade-in";
  main.append(view);
  page(view, data);
  window.scrollTo({ top: 0 });
}

async function start() {
  main.innerHTML = `<div class="loading">Loading price data…</div>`;
  try {
    [data] = await Promise.all([
      fetch("/data/site.json").then((r) => r.json()),
      // Charts measure their labels once, so wait for the web fonts first.
      document.fonts.load("500 12px 'Inter Variable'"),
      document.fonts.load("600 16px 'Fraunces Variable'"),
    ]);
  } catch {
    main.innerHTML = `<div class="loading">Could not load the data. Please refresh the page.</div>`;
    return;
  }
  document.getElementById("data-stamp").textContent =
    `Data to ${label(data.last_date)} · results generated ${data.updated}`;
  window.addEventListener("hashchange", render);
  render();
}

start();
