// Présentation de la version Pro (désactivable avec SHOW_PRO_HINTS=false).
import { app, el, icon, t } from "./core.js";

export const proEnabled = () => Boolean(app.config?.show_pro_hints);

function proLink(label, cls = "btn primary") {
  const url = app.config?.pro_url;
  if (!url) return null;
  return el("a", { class: cls, href: url, target: "_blank", rel: "noopener" }, label);
}

/** Écran affiché à la place d'un module réservé à la version Pro. */
export function proModuleCard(moduleKey) {
  const features = t(`pro.${moduleKey}.features`).split("|");
  return el("div", { class: "card pro-card" },
    el("div", { class: "pro-badge", html: `${icon("lock")}<span>${t("pro.badge")}</span>` }),
    el("h2", {}, t(`module.${moduleKey}`)),
    el("p", { class: "muted" }, t(`pro.${moduleKey}.pitch`)),
    el("ul", { class: "pro-list" }, features.map((f) => el("li", {}, f))),
    proLink(t("pro.cta")));
}

/** Encadré discret de la barre latérale. */
export function proSidebarCard() {
  if (!proEnabled()) return null;
  return el("div", { class: "pro-side" },
    el("div", { class: "label" }, t("pro.badge")),
    el("div", { class: "muted" }, t("pro.sidebar")),
    proLink(t("pro.cta_short"), "btn sm"));
}

/** Ligne d'information sous un outil limité dans la version Lite. */
export function proHint(key) {
  if (!proEnabled()) return null;
  return el("div", { class: "pro-hint", html: icon("lock") },
    el("span", {}, t(key)), proLink(t("pro.cta_short"), "link"));
}
