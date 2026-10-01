import * as auth from "./api/auth.js";
import { accountShell, renderAccountPage } from "./components/accountViews.js";
import { mountApp } from "./components/appShell.js";
import { bindTaskHandlers } from "./handlers/taskHandlers.js";
import { clearFeedbackTimers } from "./components/feedback.js";
import state from "./state.js";

const routes = new Set(["login", "register", "profile", "tasks", "forgot-password", "reset-password"]);
const protectedRoutes = new Set(["profile", "tasks"]);

export function createAccountApp() {
  let user = null;
  let currentRoute = "";
  let resetToken = null;
  let version = 0;
  let stopTasks = null;
  let stopped = false;
  const dirtyForms = new Set();
  const root = document.querySelector("#app");
  const events = new AbortController();

  function readRoute() {
    const [path, query = ""] = location.hash.replace(/^#\/?/, "").split("?");
    const token = new URLSearchParams(query).get("token");
    if (path === "reset-password" && token) {
      resetToken = token;
      history.replaceState(null, "", "#/reset-password");
    }
    return routes.has(path) ? path : (user ? "profile" : "login");
  }

  function clearTasks() {
    stopTasks?.();
    stopTasks = null;
    clearFeedbackTimers();
    Object.assign(state, { todos: [], editingId: null, pendingDelete: null });
  }

  function message(text, error = false) {
    const target = document.querySelector("#account-feedback");
    if (target) {
      target.textContent = text;
      target.className = error ? "account-message error" : "account-message success";
    }
  }

  function mayLeave() {
    return !dirtyForms.size || window.confirm("Discard your unsaved account changes?");
  }

  function render(route, notice = "") {
    clearTasks();
    dirtyForms.clear();
    if (route !== "reset-password") resetToken = null;
    currentRoute = route;
    history.replaceState(null, "", `#/${route}`);
    if (route === "tasks") {
      const elements = mountApp();
      stopTasks = bindTaskHandlers(elements);
    } else {
      renderAccountPage(route, user);
      if (route === "reset-password" && !resetToken) {
        message("This reset link is missing. Request a new link using the option below.", true);
        document.querySelector("#reset-form button[type=submit]").disabled = true;
      }
    }
    if (notice) message(notice);
    document.querySelector("h1")?.setAttribute("tabindex", "-1");
    document.querySelector("h1")?.focus({ preventScroll: true });
  }

  function expire() {
    version += 1;
    user = null;
    render("login", "Your session has ended. Please log in again.");
  }

  async function verifyAndRender({ preserve = false } = {}) {
    const route = readRoute();
    const operation = ++version;
    const previousUser = user;
    try {
      const nextUser = await auth.currentUser();
      if (operation !== version || stopped) return;
      user = nextUser;
    } catch (error) {
      if (operation !== version || stopped) return;
      if (error.status === 401) user = null;
      else {
        if (!preserve || !currentRoute) {
          clearTasks();
          root.innerHTML = accountShell('<section class="account-panel"><h1>Cannot reach your account</h1><p>Your session has not been cleared. Check your connection and retry.</p><button class="button button-primary" data-retry>Retry</button></section>');
        } else {
          message("Could not check your session. Your changes are still here; retry when connected.", true);
        }
        return;
      }
    }
    if (operation !== version || stopped) return;
    if (preserve && route === currentRoute && user && user.id === previousUser?.id) return;
    const destination = !user && protectedRoutes.has(route) ? "login"
      : user && ["login", "register"].includes(route) ? "profile" : route;
    render(destination);
  }

  async function navigate(route, notice = "", force = false) {
    if (!force && !mayLeave()) return;
    dirtyForms.clear();
    version += 1;
    history.pushState(null, "", `#/${route}`);
    if (force) render(route, notice);
    else await verifyAndRender();
  }

  function showFormError(form, error) {
    const target = form.querySelector(".form-result");
    target.className = "form-result error";
    target.textContent = error.status === 429
      ? `${error.message} Retry in ${error.retryAfter || "a few"} seconds.`
      : error.message || "Could not save. Please try again.";
  }

  function validate(form) {
    let firstInvalid = null;
    for (const input of form.querySelectorAll("input")) {
      const error = document.getElementById(`${input.id}-error`);
      input.setCustomValidity("");
      if (["display_name", "email"].includes(input.name) && !input.value.trim()) input.setCustomValidity("This field is required.");
      if (input.name === "confirm_password") {
        const original = form.elements.namedItem("new_password") || form.elements.namedItem("password");
        if (input.value !== original.value) input.setCustomValidity("Passwords do not match.");
      }
      if (input.autocomplete === "new-password"
          && (Array.from(input.value).length < 15 || Array.from(input.value).length > 128)) {
        input.setCustomValidity("Use 15–128 characters.");
      }
      const invalid = !input.checkValidity();
      error.textContent = invalid ? input.validationMessage : "";
      input.setAttribute("aria-invalid", String(invalid));
      if (invalid && !firstInvalid) firstInvalid = input;
    }
    firstInvalid?.focus();
    return !firstInvalid;
  }

  async function submit(event) {
    const form = event.target.closest(".account-form");
    if (!form) return;
    event.preventDefault();
    if (!validate(form)) return;
    if (form.id === "password-form" && dirtyForms.has("profile-form") && !mayLeave()) return;
    const payload = Object.fromEntries(new FormData(form));
    delete payload.confirm_password;
    const button = form.querySelector("button[type=submit]");
    if (button.disabled) return;
    button.disabled = true;
    form.setAttribute("aria-busy", "true");
    form.querySelector(".form-result").textContent = "Saving…";
    const operation = version;
    try {
      switch (form.id) {
        case "register-form":
          await auth.register(payload);
          if (operation !== version) return;
          await navigate("login", "Account created. Log in to continue.", true);
          break;
        case "login-form": {
          const authenticated = await auth.login(payload);
          if (operation !== version) return;
          user = authenticated;
          await navigate("profile", "", true);
          break;
        }
        case "profile-form": {
          const updated = await auth.updateProfile({
            email: payload.email.trim(), display_name: payload.display_name.trim(),
            ...(payload.current_password ? { current_password: payload.current_password } : {}),
          });
          if (operation !== version) return;
          user = updated;
          // Update only this form so unsaved password-form input is preserved.
          form.elements.namedItem("display_name").value = user.display_name;
          form.elements.namedItem("email").value = user.email;
          form.elements.namedItem("current_password").value = "";
          document.querySelector("#greeting-name").textContent = user.display_name;
          document.querySelector(".signed-in").textContent = user.display_name;
          dirtyForms.delete(form.id);
          form.querySelector(".form-result").textContent = "Profile saved.";
          break;
        }
        case "password-form":
          await auth.changePassword({ current_password: payload.old_password, new_password: payload.new_password });
          if (operation !== version) return;
          user = null;
          await navigate("login", "Password changed. Log in with your new password.", true);
          break;
        case "forgot-form": {
          const result = await auth.forgotPassword(payload);
          if (operation !== version) return;
          form.querySelector(".form-result").textContent = result.detail;
          break;
        }
        case "reset-form":
          await auth.resetPassword({ token: resetToken, new_password: payload.new_password });
          if (operation !== version) return;
          user = null;
          await navigate("login", "Password reset. Log in with your new password.", true);
          break;
      }
    } catch (error) {
      if (operation === version && form.isConnected) showFormError(form, error);
    } finally {
      button.disabled = false;
      form.removeAttribute("aria-busy");
    }
  }

  async function click(event) {
    const target = event.target.closest("a, button");
    if (!target) return;
    if (target.matches("[data-toggle-password]")) {
      const input = document.getElementById(target.dataset.togglePassword);
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      target.setAttribute("aria-pressed", String(show));
      target.textContent = target.textContent.replace(show ? /^Show/ : /^Hide/, show ? "Hide" : "Show");
    } else if (target.matches("[data-logout]")) {
      if (!mayLeave() || target.disabled) return;
      target.disabled = true;
      try {
        await auth.logout();
        user = null;
        await navigate("login", "You have logged out.", true);
      } catch {
        message("Could not log out. Please check your connection and try again.", true);
      } finally { target.disabled = false; }
    } else if (target.matches("[data-retry]")) {
      await verifyAndRender();
    } else if (target.matches("[data-discard-profile]")) {
      if (dirtyForms.has("profile-form") && !window.confirm("Discard your unsaved profile changes?")) return;
      const form = document.querySelector("#profile-form");
      form.elements.namedItem("display_name").value = user.display_name;
      form.elements.namedItem("email").value = user.email;
      form.elements.namedItem("current_password").value = "";
      dirtyForms.delete("profile-form");
      form.querySelectorAll(".field-error, .form-result").forEach((node) => { node.textContent = ""; });
    } else if (target.matches('a[href^="#/"]')) {
      event.preventDefault();
      await navigate(target.getAttribute("href").slice(2));
    }
  }

  const listen = (node, event, fn) => node.addEventListener(event, fn, { signal: events.signal });
  return {
    async start() {
      root.innerHTML = accountShell('<p role="status">Checking your session…</p>');
      listen(root, "submit", submit);
      listen(root, "click", click);
      listen(root, "input", (event) => {
        const form = event.target.closest("form");
        if (["profile-form", "password-form"].includes(form?.id)) dirtyForms.add(form.id);
      });
      listen(window, "auth:expired", expire);
      listen(window, "hashchange", () => {
        if (!mayLeave()) { history.replaceState(null, "", `#/${currentRoute}`); return; }
        dirtyForms.clear();
        verifyAndRender();
      });
      listen(window, "pageshow", (event) => { if (event.persisted) verifyAndRender({ preserve: true }); });
      listen(document, "visibilitychange", () => {
        if (document.visibilityState === "visible") verifyAndRender({ preserve: true });
      });
      listen(window, "beforeunload", (event) => {
        if (dirtyForms.size) { event.preventDefault(); event.returnValue = ""; }
      });
      await verifyAndRender();
    },
    stop() { stopped = true; version += 1; events.abort(); clearTasks(); },
  };
}
