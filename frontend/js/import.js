// Import : dépôt du fichier, assistant de correspondance des colonnes, rapport.
import { api, el, fmtDate, fmtNumber, icon, mount, t, toast } from "./core.js";
import { proHint } from "./pro.js";
import { refreshMeta, state } from "./store.js";

const dataset = "personnel"; // la version Pro ajoute le fichier de formation

export async function renderImport(view) {
  const work = el("div", { class: "card card-body", id: "import-work" });
  const side = el("aside", { class: "card card-body dataset-meta", id: "import-side" });
  view.append(
    el("div", { class: "page-head" }, el("div", {},
      el("div", { class: "label" }, t("nav.import")), el("h1", {}, t("import.title")))),
    el("div", { class: "import-grid" }, work, side));
  renderSide(side);
  renderDrop(work);
}

function renderSide(side) {
  mount(side, el("div", { class: "label" }, t("import.current")),
    ...Object.entries(state.meta.datasets).map(([key, meta]) => el("div", { class: "row" },
      el("strong", {}, t(`dataset.${key}`)),
      el("span", { class: "muted" }, meta ? t("import.meta", { rows: fmtNumber(meta.rows),
        file: meta.filename, date: fmtDate(meta.imported_at) }) : t("import.none")))),
    proHint("pro.hint_import"));
}

function renderDrop(work) {
  const input = el("input", { type: "file", accept: ".xlsx,.csv", hidden: true });
  const zone = el("label", { class: "dropzone", tabindex: "0" },
    el("span", { html: icon("file") }), el("strong", {}, t("import.drop")),
    el("span", { class: "muted" }, ".xlsx · .csv"), input);

  zone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") input.click(); });
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault(); zone.classList.remove("over");
    if (e.dataTransfer.files[0]) upload(work, e.dataTransfer.files[0]);
  });
  input.addEventListener("change", () => input.files[0] && upload(work, input.files[0]));

  work.replaceChildren(
    el("p", { class: "muted", style: "margin-top:0" }, t("import.intro")),
    zone);
}

async function upload(work, file, sheet = null) {
  work.replaceChildren(el("div", { class: "skeleton", style: "height:200px" }),
    el("p", { class: "muted" }, t("import.uploading")));
  const form = new FormData();
  form.append("file", file);
  if (sheet) form.append("sheet", sheet);
  try {
    const data = await api(`/api/datasets/${dataset}/upload`, { method: "POST", body: form });
    renderMapping(work, data, file);
  } catch (err) {
    toast(err.message, "error");
    renderDrop(work);
  }
}

function renderMapping(work, data, file) {
  const options = (selected) => [el("option", { value: "" }, t("import.not_mapped")),
    ...data.columns.map((c) => el("option", { value: c, selected: c === selected }, c))];
  const selects = {};
  const rows = data.fields.map((f) => {
    const select = el("select", { class: "input" }, options(data.mapping[f.key]));
    selects[f.key] = select;
    const tr = el("tr", {}, el("td", {}, t(`field.${f.key}`),
      f.required ? el("span", { class: "req" }, "*") : null), el("td", {}, select));
    const check = () => tr.classList.toggle("missing", f.required && !select.value);
    select.addEventListener("change", check);
    check();
    return tr;
  });

  const sheetPicker = data.sheets.length > 1 ? el("label", { class: "field" },
    el("span", { class: "label" }, t("import.sheet")),
    el("select", { class: "input", onchange: (e) => upload(work, file, e.target.value) },
      data.sheets.map((s) => el("option", { value: s, selected: s === data.sheet }, s)))) : null;

  const confirm = el("button", { class: "btn primary", type: "button", onclick: async () => {
    const mapping = Object.fromEntries(Object.entries(selects).map(([k, s]) => [k, s.value || null]));
    confirm.disabled = true;
    try {
      const result = await api(`/api/datasets/${dataset}/confirm`, { method: "POST",
        body: { upload_id: data.upload_id, mapping } });
      await refreshMeta();
      renderSide(document.getElementById("import-side"));
      renderReport(work, result.report);
    } catch (err) {
      toast(err.message, "error");
      confirm.disabled = false;
    }
  } }, t("import.confirm"));

  mount(work,
    el("div", { class: "card-title" }, `${t("import.mapping")} — ${data.filename}`),
    el("p", { class: "muted" }, t("import.mapping_intro"), " ",
      el("span", { class: "num" }, `(${t("import.rows", { n: fmtNumber(data.rows) })})`)),
    data.mapping_reused ? el("div", { class: "notice", style: "margin-bottom:12px" }, t("import.reused")) : null,
    sheetPicker,
    el("table", { class: "map-table" }, el("tbody", {}, rows)),
    el("div", { class: "label", style: "margin:20px 0 8px" }, t("import.preview")),
    el("div", { class: "preview" }, el("table", { class: "grid" },
      el("thead", {}, el("tr", {}, data.columns.map((c) => el("th", {}, c)))),
      el("tbody", {}, data.preview.map((r) => el("tr", {}, r.map((v) => el("td", {}, v))))))),
    el("div", { class: "prefs", style: "margin-top:18px; justify-content:flex-end" },
      el("button", { class: "btn", type: "button", onclick: () => renderDrop(work) }, t("import.cancel")),
      confirm));
}

function renderReport(work, report) {
  const errors = report.errors.length ? [
    el("div", { class: "label", style: "margin:18px 0 8px" }, t("import.errors")),
    el("div", { class: "preview", style: "max-height:320px" }, el("table", { class: "grid" },
      el("thead", {}, el("tr", {}, ["import.row", "import.field", "import.value", "import.message"]
        .map((k) => el("th", {}, t(k))))),
      el("tbody", {}, report.errors.map((e) => el("tr", {},
        el("td", { class: "type-number" }, e.row), el("td", {}, t(`field.${e.field}`)),
        el("td", {}, e.value), el("td", {}, e.message)))))),
  ] : [];
  mount(work,
    el("div", { class: "card-title" }, t("import.done")),
    el("div", { class: "stat-line" },
      el("span", { class: "badge good" }, t("import.accepted", { n: fmtNumber(report.rows_accepted) })),
      report.rows_rejected ? el("span", { class: "badge bad" },
        t("import.rejected", { n: fmtNumber(report.rows_rejected) })) : null),
    ...report.warnings.map((w) => el("div", { class: "notice", style: "margin-bottom:8px" }, w)),
    ...errors,
    el("div", { class: "prefs", style: "margin-top:18px" },
      el("a", { class: "btn primary", href: "#/dashboard" }, t("nav.dashboard")),
      el("button", { class: "btn", type: "button", onclick: () => renderDrop(work) }, t("import.title"))));
}
