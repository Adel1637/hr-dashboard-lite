// Composants d'interface réutilisables : liste à choix multiples, rendu Plotly.
import { app, cssVar, el, icon, t } from "./core.js";

/**
 * Liste déroulante à choix multiples avec recherche.
 * options : [{ value, label }] ; selected : tableau de valeurs ; onChange(values)
 */
export function multiSelect({ label, options, selected = [], onChange }) {
  const chosen = new Set(selected);
  const wrap = el("div", { class: "field ms" });
  const button = el("button", { class: "btn ms-btn", type: "button", "aria-haspopup": "true" });
  const pop = el("div", { class: "popover", hidden: true });
  const search = el("input", { class: "input", placeholder: t("table.filter") });
  const list = el("div", { class: "ms-list" });

  function caption() {
    const text = chosen.size === 0 ? t("filters.all")
      : chosen.size === 1 ? options.find((o) => chosen.has(o.value))?.label ?? [...chosen][0]
        : t("filters.selected", { n: chosen.size });
    button.replaceChildren(el("span", {}, text), el("span", { class: "caret", html: icon("chevron") }));
    button.querySelector(".caret svg").setAttribute("width", "16");
    button.classList.toggle("on", chosen.size > 0);
  }

  function fill() {
    const needle = search.value.trim().toLowerCase();
    list.replaceChildren(...options
      .filter((o) => !needle || o.label.toLowerCase().includes(needle))
      .map((o) => {
        const box = el("input", { type: "checkbox", checked: chosen.has(o.value) });
        box.addEventListener("change", () => {
          if (box.checked) chosen.add(o.value); else chosen.delete(o.value);
          caption();
          onChange([...chosen]);
        });
        return el("label", {}, box, el("span", {}, o.label));
      }));
  }

  const clear = el("button", { class: "btn ghost sm", type: "button", onclick: () => {
    chosen.clear(); fill(); caption(); onChange([]);
  } }, t("filters.reset"));
  const close = el("button", { class: "btn sm", type: "button",
    onclick: () => { pop.hidden = true; } }, t("common.close"));

  pop.append(search, list, el("div", { class: "ms-foot" }, clear, close));
  search.addEventListener("input", fill);
  button.addEventListener("click", () => {
    pop.hidden = !pop.hidden;
    if (!pop.hidden) { fill(); search.focus(); }
  });
  document.addEventListener("click", (event) => {
    if (!wrap.contains(event.target)) pop.hidden = true;
  });
  wrap.addEventListener("keydown", (event) => {
    if (event.key === "Escape") { pop.hidden = true; button.focus(); }
  });

  caption();
  wrap.append(el("span", { class: "label" }, label), button, pop);
  wrap.disabled = options.length === 0;
  button.disabled = options.length === 0;
  return wrap;
}

/** Affiche une figure Plotly envoyée par l'API, avec les couleurs du thème courant. */
export function plot(node, figure) {
  const text = cssVar("--text-2");
  const grid = cssVar("--grid");
  const layout = structuredClone(figure.layout || {});
  const family = cssVar("--font");
  layout.font = { ...(layout.font || {}), family, color: text };
  layout.separators = app.lang === "fr" ? ", " : ".,";
  for (const key of Object.keys(layout)) {
    if (/^[xy]axis\d*$/.test(key)) {
      layout[key] = { ...layout[key], gridcolor: grid, linecolor: grid, tickfont: { color: text } };
    }
  }
  if (!layout.xaxis) layout.xaxis = { gridcolor: grid };
  if (!layout.yaxis) layout.yaxis = { gridcolor: grid };
  layout.legend = { ...(layout.legend || {}), font: { color: text } };
  layout.hoverlabel = { ...(layout.hoverlabel || {}), bgcolor: cssVar("--surface"),
    bordercolor: cssVar("--border-strong"), font: { family, color: cssVar("--text") } };
  layout.autosize = true;
  window.Plotly.react(node, figure.data, layout, {
    displaylogo: false,
    responsive: true,
    modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"],
    toImageButtonOptions: { format: "png", scale: 2 },
  });
}
