// Socle commun : appels API, session, traductions, formats, thème, notifications.

const TOKEN_KEY = "kit.token";
const USER_KEY = "kit.user";
const PREFS_KEY = "kit.prefs";

// ---- Préférences locales (thème, langue) -------------------------
export const prefs = {
  get() {
    try { return JSON.parse(localStorage.getItem(PREFS_KEY)) || {}; } catch { return {}; }
  },
  set(patch) {
    const next = { ...prefs.get(), ...patch };
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(next)); } catch { /* stockage indisponible */ }
    return next;
  },
};

// ---- Session --------------------------------------------------------
export const session = {
  token: () => sessionStorage.getItem(TOKEN_KEY),
  user: () => { try { return JSON.parse(sessionStorage.getItem(USER_KEY)); } catch { return null; } },
  save(token, user) {
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() { sessionStorage.removeItem(TOKEN_KEY); sessionStorage.removeItem(USER_KEY); },
};

// ---- API ------------------------------------------------------------
export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

export async function api(path, { method = "GET", body, params, raw = false } = {}) {
  const url = new URL(path, location.origin);
  for (const [key, value] of Object.entries(params || {})) {
    if (Array.isArray(value)) value.forEach((v) => url.searchParams.append(key, v));
    else if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  }
  const headers = {};
  const token = session.token();
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload = body;
  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(url, { method, headers, body: payload });
  if (res.status === 401 && !path.startsWith("/api/auth/login")) {
    session.clear();
    location.replace("/login.html?expired=1");
    throw new ApiError(401, t("common.session_expired"));
  }
  if (!res.ok) {
    let message = t("common.error");
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
    } catch { /* corps non JSON */ }
    throw new ApiError(res.status, message);
  }
  return raw ? res : res.json();
}

// ---- Configuration publique & traductions ----------------------------
export const app = { config: null, lang: "fr", strings: {} };

export async function boot() {
  app.config = await fetch("/api/config").then((r) => r.json());
  const langs = app.config.languages;
  const wanted = prefs.get().lang;
  app.lang = langs.includes(wanted) ? wanted : app.config.default_lang;
  app.strings = await fetch(`/locales/${app.lang}.json`).then((r) => r.json());
  document.documentElement.lang = app.lang;
  document.documentElement.style.setProperty("--accent", app.config.accent);
  applyTheme(prefs.get().theme);
  document.title = app.config.app_name;
  return app.config;
}

export function t(key, vars = {}) {
  let text = app.strings[key] ?? key;
  for (const [name, value] of Object.entries(vars)) text = text.replaceAll(`{${name}}`, value);
  return text;
}

export function translatePage(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  root.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
    el.setAttribute("aria-label", el.title);
  });
}

// ---- Formats ------------------------------------------------------
const locale = () => (app.lang === "fr" ? "fr-FR" : "en-US");

export function fmtNumber(value, digits = 0) {
  if (value === null || value === undefined) return t("common.no_value");
  return new Intl.NumberFormat(locale(), { maximumFractionDigits: digits,
    minimumFractionDigits: digits }).format(value);
}

export function fmtDate(iso, opts = { day: "2-digit", month: "short", year: "numeric" }) {
  if (!iso) return t("common.no_value");
  return new Intl.DateTimeFormat(locale(), opts).format(new Date(`${iso.slice(0, 10)}T00:00:00`));
}

export function fmtKpi(kpi) {
  const v = kpi.value;
  if (v === null || v === undefined) return { text: t("common.no_value"), unit: "" };
  switch (kpi.format) {
    case "pct": return { text: fmtNumber(v, 1), unit: "%" };
    case "dec": return { text: fmtNumber(v, 1), unit: "" };
    case "years": return { text: fmtNumber(v, 1), unit: t("label.years") };
    default: return { text: fmtNumber(v, 0), unit: "" };
  }
}

// ---- Thème ---------------------------------------------------------
export function applyTheme(theme) {
  const resolved = theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = resolved;
  return resolved;
}

export function toggleTheme() {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  prefs.set({ theme: next });
  applyTheme(next);
  window.dispatchEvent(new CustomEvent("themechange"));
}

export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// ---- Notifications et utilitaires DOM --------------------------------
export function toast(message, type = "info") {
  let box = document.querySelector(".toasts");
  if (!box) { box = el("div", { class: "toasts" }); document.body.append(box); }
  const node = el("div", { class: `toast ${type}`, role: "status" }, message);
  box.append(node);
  setTimeout(() => node.remove(), 4500);
}

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key === "class") node.className = value;
    else if (key === "html") node.innerHTML = value; // réservé aux icônes internes
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

/** Remplace le contenu d'un nœud en ignorant les enfants null/false. */
export function mount(node, ...children) {
  node.replaceChildren(...children.flat().filter((c) => c !== null && c !== undefined && c !== false));
  return node;
}

export function debounce(fn, ms = 300) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

// Icônes SVG internes (trait 1.8, couleur héritée).
const ICON_PATHS = {
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  table: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18M9 4v16"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>',
  shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  logout: '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="M10 17l-5-5 5-5M5 12h11"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  pin: '<path d="M9 4h6l-1 5 3 3H7l3-3z"/><path d="M12 12v8"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
  chevron: '<path d="M6 9l6 6 6-6"/>',
};

export function icon(name) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_PATHS[name] || ""}</svg>`;
}
