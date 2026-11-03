import { ApiError, api, boot, session, t, translatePage } from "./core.js";

const config = await boot();
translatePage();

document.getElementById("brand-name").textContent = config.app_name;
document.getElementById("brand-company").textContent = config.company;
document.getElementById("form-brand").textContent = config.app_name;
document.getElementById("year").textContent = `© ${new Date().getFullYear()} ${config.company}`;
if (config.logo) {
  const img = document.createElement("img");
  img.src = config.logo;
  img.alt = "";
  document.getElementById("brand-mark").replaceChildren(img);
} else {
  document.getElementById("brand-mark").textContent = config.app_name.charAt(0);
}

const form = document.getElementById("login-form");
const error = document.getElementById("login-error");

if (new URLSearchParams(location.search).has("expired")) {
  error.textContent = t("common.session_expired");
  error.hidden = false;
}
if (session.token()) location.replace("/");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  error.hidden = true;
  const button = form.querySelector("button");
  button.disabled = true;
  try {
    const data = await api("/api/auth/login", {
      method: "POST",
      body: { username: form.username.value.trim(), password: form.password.value },
    });
    session.save(data.access_token, data.user);
    location.replace("/");
  } catch (err) {
    error.textContent = err instanceof ApiError && err.status === 429
      ? t("login.locked") : t("login.error");
    error.hidden = false;
    form.password.value = "";
    form.password.focus();
  } finally {
    button.disabled = false;
  }
});

