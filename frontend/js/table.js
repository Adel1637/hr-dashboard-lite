// Tableau de données : recherche, tri et pagination côté serveur.
// La version Pro ajoute filtres par colonne, colonnes épinglées, vues, sélection et exports.
import { api, debounce, el, fmtNumber, t, toast } from "./core.js";
import { proHint } from "./pro.js";
import { state } from "./store.js";

const PAGE_SIZE = 50;
const DATASET = "personnel";
const tbl = { page: 1, q: "", sort: null, order: "asc", columns: [] };

export async function renderTable(view) {
  const head = el("div", { class: "page-head" }, el("div", {},
    el("div", { class: "label" }, t("nav.data")), el("h1", {}, t(`dataset.${DATASET}`))));

  if (!state.meta.datasets[DATASET]) {
    view.append(head, el("div", { class: "card empty" }, el("div", {},
      el("strong", {}, t("nav.data")), t("table.no_data"), el("br"), el("br"),
      el("a", { class: "btn primary", href: "#/import" }, t("nav.import")))));
    return;
  }

  const search = el("input", { class: "input search", type: "search", value: tbl.q,
    placeholder: t("table.search") });
  search.addEventListener("input", debounce(() => { tbl.q = search.value; tbl.page = 1; load(); }));

  view.append(head, el("div", { class: "card" },
    el("div", { class: "toolbar" }, search, proHint("pro.hint_table")),
    el("div", { class: "table-wrap" }, el("table", { class: "grid", id: "grid" },
      el("thead"), el("tbody"))),
    el("div", { class: "pager", id: "pager" })));
  await load();
}

async function load() {
  let data;
  try {
    data = await api(`/api/data/${DATASET}`, { params: {
      page: tbl.page, size: PAGE_SIZE, q: tbl.q, sort: tbl.sort, order: tbl.order } });
  } catch (err) { toast(err.message, "error"); return; }
  tbl.columns = data.columns;
  buildHead();
  buildBody(data.rows);
  buildPager(data.total);
}

function buildHead() {
  const row = el("tr", {}, tbl.columns.map((col) => el("th", {},
    el("button", { class: `sort${tbl.sort === col.key ? " on" : ""}`, type: "button",
      "aria-sort": tbl.sort === col.key ? (tbl.order === "asc" ? "ascending" : "descending") : null,
      onclick: () => {
        tbl.order = tbl.sort === col.key && tbl.order === "asc" ? "desc" : "asc";
        tbl.sort = col.key; tbl.page = 1; load();
      } }, t(`field.${col.key}`), tbl.sort === col.key ? (tbl.order === "asc" ? " ↑" : " ↓") : ""))));
  document.querySelector("#grid thead").replaceChildren(row);
}

function buildBody(rows) {
  const tbody = document.querySelector("#grid tbody");
  if (!rows.length) {
    tbody.replaceChildren(el("tr", {}, el("td", { colspan: tbl.columns.length, class: "muted",
      style: "text-align:center; padding:32px" }, t("table.empty"))));
    return;
  }
  tbody.replaceChildren(...rows.map((row) => el("tr", {}, tbl.columns.map((col) => {
    let value = row[col.key];
    if (value !== null && col.key === "sexe") value = t(value === "F" ? "label.woman" : "label.man");
    return el("td", { class: `type-${col.type}` }, value ?? t("common.no_value"));
  }))));
}

function buildPager(total) {
  const from = total ? (tbl.page - 1) * PAGE_SIZE + 1 : 0;
  const to = Math.min(tbl.page * PAGE_SIZE, total);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  document.getElementById("pager").replaceChildren(
    el("span", { class: "muted num" }, t("table.rows", { from: fmtNumber(from), to: fmtNumber(to),
      total: fmtNumber(total) })),
    el("div", { class: "prefs" },
      el("button", { class: "btn sm", type: "button", disabled: tbl.page <= 1,
        onclick: () => { tbl.page -= 1; load(); } }, t("table.prev")),
      el("span", { class: "muted num" }, `${tbl.page} / ${pages}`),
      el("button", { class: "btn sm", type: "button", disabled: tbl.page >= pages,
        onclick: () => { tbl.page += 1; load(); } }, t("table.next"))));
}
