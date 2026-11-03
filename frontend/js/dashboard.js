// Tableau de bord : onglets des modules, filtres globaux, KPI et graphiques.
import { api, el, fmtDate, fmtKpi, fmtNumber, t } from "./core.js";
import { multiSelect, plot } from "./components.js";
import { proModuleCard } from "./pro.js";
import { state } from "./store.js";

const FILTERS = ["site", "service", "categorie", "type_contrat", "sexe"];
const PERIODS = [3, 6, 12, 24, 36];

// Filtres conservés pendant la navigation entre les pages.
const dash = { module: null, refDate: null, userRefDate: false, months: 12, values: {}, last: null };

export async function renderDashboard(view, [moduleKey]) {
  const meta = state.meta;
  const modules = meta.modules;
  dash.module = modules.find((m) => m.key === moduleKey)?.key || dash.module || modules[0]?.key;
  if (!dash.userRefDate) dash.refDate = meta.suggested_ref_date;

  const tabs = el("div", { class: "tabs", role: "tablist" }, modules.map((m) =>
    el("button", { class: `tab${m.key === dash.module ? " active" : ""}`, role: "tab",
      "aria-selected": m.key === dash.module ? "true" : "false",
      onclick: () => { location.hash = `#/dashboard/${m.key}`; } },
    t(`module.${m.key}`), m.pro ? el("span", { class: "pro-tag" }, "PRO")
      : m.ready ? null : el("span", { class: "dot", title: "!" }))));

  const head = el("div", { class: "page-head" },
    el("div", {}, el("div", { class: "label" }, t("nav.dashboard")),
      el("h1", {}, t(`module.${dash.module}`))),
    tabs);

  const body = el("div");
  if (modules.find((m) => m.key === dash.module)?.pro) {
    view.append(head, proModuleCard(dash.module));
    return;
  }
  view.append(head, filterBar(() => load(body)), body);
  await load(body);
}

function filterBar(onChange) {
  const options = state.meta.filters;
  const bar = el("div", { class: "card filterbar" });
  const note = el("div", { class: "period-note", id: "period-note" });

  const date = el("input", { class: "input num", type: "date", value: dash.refDate });
  date.addEventListener("change", () => {
    if (date.value) { dash.refDate = date.value; dash.userRefDate = true; onChange(); }
  });

  const period = el("select", { class: "input" }, PERIODS.map((n) =>
    el("option", { value: n, selected: n === dash.months }, t("filters.months_value", { n }))));
  period.addEventListener("change", () => { dash.months = Number(period.value); onChange(); });

  bar.append(
    el("label", { class: "field" }, el("span", { class: "label" }, t("filters.ref_date")), date),
    el("label", { class: "field" }, el("span", { class: "label" }, t("filters.months")), period),
  );
  for (const key of FILTERS) {
    const opts = (options[key] || []).map((v) => ({ value: v,
      label: key === "sexe" ? t(v === "F" ? "label.women" : "label.men") : v }));
    bar.append(multiSelect({ label: t(`filters.${key}`), options: opts,
      selected: dash.values[key] || [],
      onChange: (values) => { dash.values[key] = values; onChange(); } }));
  }
  const reset = el("button", { class: "btn ghost sm", type: "button", onclick: () => {
    dash.values = {}; dash.months = 12; dash.userRefDate = false;
    location.hash = `#/dashboard/${dash.module}`;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  } }, t("filters.reset"));
  bar.append(el("div", { class: "filter-foot" }, note, reset));
  return bar;
}

let requestId = 0;
async function load(body) {
  const status = state.meta.modules.find((m) => m.key === dash.module);
  if (!status?.ready) {
    const names = status.missing.map((d) => t(`dataset.${d}`)).join(", ");
    body.replaceChildren(el("div", { class: "card empty" }, el("div", {},
      el("strong", {}, t(`module.${dash.module}`)),
      t("module.missing", { datasets: names }), el("br"), el("br"),
      el("a", { class: "btn primary", href: "#/import" }, t("nav.import")))));
    return;
  }

  const id = ++requestId;
  body.style.opacity = body.childElementCount ? "0.55" : "";
  if (!body.childElementCount) body.append(el("div", { class: "skeleton", style: "height:420px" }));
  const params = { ref_date: dash.refDate, months: dash.months, lang: document.documentElement.lang };
  for (const key of FILTERS) params[key] = dash.values[key] || [];

  let data;
  try {
    data = await api(`/api/modules/${dash.module}`, { params });
  } catch (err) {
    body.style.opacity = "";
    body.replaceChildren(el("div", { class: "card empty" }, err.message));
    return;
  }
  if (id !== requestId) return; // une requête plus récente est en cours
  dash.last = data;
  body.style.opacity = "";
  document.getElementById("period-note").textContent = t("filters.period", {
    start: fmtDate(data.period.start), end: fmtDate(data.period.end) });
  body.replaceChildren(kpiRow(data.kpis), chartGrid(data.charts));
}

function kpiRow(kpis) {
  return el("div", { class: "kpis" }, kpis.map((k) => {
    const value = fmtKpi(k);
    let meta = k.hint ? t(k.hint) : "";
    let delta = null;
    if (k.delta !== null && k.delta !== undefined) {
      const sign = k.delta > 0 ? "+" : "";
      delta = el("span", { class: `delta ${k.delta > 0 ? "up" : k.delta < 0 ? "down" : ""}` },
        `${sign}${fmtNumber(k.delta, 1)} %`);
      meta = ` ${t("kpi.delta_vs")}`;
    }
    return el("div", { class: "card kpi", title: k.hint ? t(k.hint) : null },
      el("div", { class: "label" }, t(`kpi.${k.key}`)),
      el("div", { class: "value" }, value.text, value.unit ? el("span", { class: "unit" }, value.unit) : null),
      el("div", { class: "meta" }, delta, meta));
  }));
}

function chartGrid(charts) {
  const grid = el("div", { class: "charts" });
  for (const c of charts) {
    const node = el("div", { class: "chart" });
    grid.append(el("section", { class: `card${c.wide ? " wide" : ""}` },
      el("div", { class: "card-head" },
        el("div", { class: "card-title" }, t(`chart.${dash.module}.${c.key}`))),
      el("div", { class: "card-body" }, node)));
    requestAnimationFrame(() => plot(node, c.figure));
  }
  return grid;
}

// Changement de thème : on redessine les graphiques avec les nouvelles couleurs.
window.addEventListener("themechange", () => {
  const nodes = document.querySelectorAll(".charts .chart");
  if (!dash.last || !nodes.length) return;
  dash.last.charts.forEach((c, i) => nodes[i] && plot(nodes[i], c.figure));
});
