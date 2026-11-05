// Coquille de l'application : session, navigation, préférences, routage par ancre (#/…).
import { api, app, boot, el, icon, prefs, session, t, toggleTheme, translatePage } from "./core.js";
import { renderDashboard } from "./dashboard.js";
import { renderImport } from "./import.js";
import { proSidebarCard } from "./pro.js";
import { refreshMeta, state } from "./store.js";
import { renderTable } from "./table.js";

if (!session.token()) location.replace("/login.html");

const config = await boot();
const user = session.user();
const view = document.getElementById("view");
const shell = document.getElementById("shell");

const ROUTES = [
  { path: "dashboard", icon: "dashboard", label: "nav.dashboard", render: renderDashboard },
  { path: "data", icon: "table", label: "nav.data", render: renderTable },
  { path: "import", icon: "upload", label: "nav.import", render: renderImport },
];

function setupChrome() {
  document.getElementById("brand-name").textContent = config.app_name;
  document.getElementById("brand-company").textContent = config.company;
  const mark = document.getElementById("brand-mark");
  if (config.logo) mark.replaceChildren(el("img", { src: config.logo, alt: "" }));
  else mark.textContent = config.app_name.charAt(0);

  document.getElementById("user-name").textContent = user.username;
  document.getElementById("user-role").textContent = t("role.admin");
  document.getElementById("user-avatar").textContent = user.username.slice(0, 2);

  document.getElementById("theme-btn").innerHTML = icon("moon");
  document.getElementById("theme-btn").addEventListener("click", toggleTheme);
  document.getElementById("menu-btn").innerHTML = icon("menu");
  document.getElementById("menu-btn").addEventListener("click", () =>
    shell.classList.toggle("nav-open"));
  // Sur téléphone, un appui en dehors du menu le referme.
  document.addEventListener("click", (e) => {
    if (shell.classList.contains("nav-open") && !e.target.closest(".sidebar, #menu-btn")) {
      shell.classList.remove("nav-open");
    }
  });

  const logout = document.getElementById("logout-btn");
  logout.innerHTML = icon("logout");
  logout.addEventListener("click", async () => {
    try { await api("/api/auth/logout", { method: "POST" }); } catch { /* déjà expiré */ }
    session.clear();
    location.replace("/login.html");
  });

  const select = document.getElementById("lang-select");
  for (const lang of config.languages) {
    select.append(el("option", { value: lang, selected: lang === app.lang }, lang.toUpperCase()));
  }
  select.addEventListener("change", () => { prefs.set({ lang: select.value }); location.reload(); });

  const nav = document.getElementById("nav");
  for (const route of ROUTES) {
    nav.append(el("a", { href: `#/${route.path}`, "data-route": route.path,
      html: `${icon(route.icon)}<span>${t(route.label)}</span>` }));
  }
  const pro = proSidebarCard();
  if (pro) document.querySelector(".sidebar-foot").prepend(pro);
  translatePage();
}

async function route() {
  const [path, ...rest] = location.hash.replace(/^#\/?/, "").split("/");
  const current = ROUTES.find((r) => r.path === path) || ROUTES[0];
  document.querySelectorAll(".nav a").forEach((a) =>
    a.classList.toggle("active", a.dataset.route === current.path));
  document.getElementById("mobile-title").textContent = t(current.label);
  shell.classList.remove("nav-open");
  view.replaceChildren(el("div", { class: "skeleton", style: "height:120px" }));
  try {
    if (!state.meta) await refreshMeta();
    view.replaceChildren();
    await current.render(view, rest);
  } catch (err) {
    view.replaceChildren(el("div", { class: "card empty" }, err.message || t("common.error")));
  }
}

setupChrome();
window.addEventListener("hashchange", route);
route();
