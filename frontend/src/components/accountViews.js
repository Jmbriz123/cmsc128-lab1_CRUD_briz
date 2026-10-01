import { escapeHtml } from "../utils/task.js";

function field(name, label, { type = "text", value = "", autocomplete = "", required = true, min, max } = {}) {
  return `<div class="account-field">
    <label for="${name}">${label}</label>
    <input id="${name}" name="${name}" type="${type}" value="${escapeHtml(value)}"
      autocomplete="${autocomplete}" ${required ? "required" : ""}
      ${min ? `minlength="${min}"` : ""} ${max ? `maxlength="${max}"` : ""}
      aria-describedby="${name}-error" />
    ${type === "password" ? `<button class="password-toggle" type="button" data-toggle-password="${name}" aria-controls="${name}" aria-pressed="false">Show ${label.toLowerCase()}</button>` : ""}
    <p class="field-error" id="${name}-error"></p>
  </div>`;
}

const email = (value = "") => field("email", "Email address", { type: "email", value, autocomplete: "username", max: 254 });
const name = (value = "") => field("display_name", "Display name", { value, autocomplete: "nickname", max: 100 });
const password = (id = "password", label = "Password", fresh = false, required = true) => field(id, label, {
  type: "password", autocomplete: fresh ? "new-password" : "current-password", min: fresh ? 15 : 1, max: 128, required,
});
const hint = '<p class="form-note">Use 15–128 characters. Spaces and Unicode are welcome.</p>';
const form = (id, body, button) => `<form id="${id}" class="account-form" novalidate>${body}<button class="button button-primary" type="submit">${button}</button><p class="form-result" role="status" aria-live="polite"></p></form>`;

export function accountShell(content, user = null) {
  return `<div class="shell"><header class="topbar">
    <a class="brand" href="#/${user ? "profile" : "login"}"><span class="brand-mark">D</span>Daymark</a>
    <nav class="nav" aria-label="Primary navigation">${user
      ? '<a href="#/profile">Profile</a><a href="#/tasks">Shared tasks</a><button class="button button-quiet" type="button" data-logout>Log Out</button>'
      : '<a href="#/login">Log in</a><a href="#/register">Create account</a>'}</nav>
    ${user ? `<span class="signed-in">${escapeHtml(user.display_name)}</span>` : ""}
  </header><main class="account-workspace">
    <div id="account-feedback" role="status" aria-live="polite"></div>${content}
  </main></div>`;
}

export function renderAccountPage(route, user) {
  let content;
  switch (route) {
    case "register":
      content = `<section class="account-panel"><p class="eyebrow">Get started</p><h1>Create your account</h1>
        ${form("register-form", name() + email() + password("password", "Password", true) + hint + password("confirm_password", "Confirm password", true), "Create account")}
        <p>Already registered? <a href="#/login">Log in</a></p></section>`;
      break;
    case "forgot-password":
      content = `<section class="account-panel"><h1>Forgot your password?</h1><p>Enter your registered email and we’ll send you a reset link.</p>
        ${form("forgot-form", email(), "Send reset link")}<a href="#/login">Back to login</a></section>`;
      break;
    case "reset-password":
      content = `<section class="account-panel"><h1>Choose a new password</h1>
        ${form("reset-form", password("new_password", "New password", true) + hint + password("confirm_password", "Confirm password", true), "Reset password")}
        <a href="#/forgot-password">Request a new reset link</a></section>`;
      break;
    case "profile":
      content = `<section class="account-intro"><p class="eyebrow">Your account</p><h1>Hello, <span id="greeting-name">${escapeHtml(user.display_name)}</span></h1>
        <p>Manage your account, or open the <a href="#/tasks">shared task workspace</a>.</p></section>
        <div class="account-grid"><section class="account-panel"><h2>Profile details</h2>
        ${form("profile-form", name(user.display_name) + email(user.email) + password("current_password", "Current password", false, false) + '<p class="form-note">Your current password is required only when changing your email address.</p>', "Save profile")}
        <button class="button button-quiet" type="button" data-discard-profile>Discard profile edits</button></section>
        <section class="account-panel"><h2>Change password</h2><p>You’ll log in again on all devices after changing your password.</p>
        ${form("password-form", password("old_password", "Current password for password change") + password("new_password", "New password", true) + hint + password("confirm_password", "Confirm password", true), "Change password")}
        </section></div>`;
      break;
    default:
      content = `<section class="account-panel"><p class="eyebrow">Welcome back</p><h1>Log in to Daymark</h1>
        ${form("login-form", email() + password(), "Log in")}
        <p><a href="#/forgot-password">Forgot password?</a></p><p>New here? <a href="#/register">Create an account</a></p></section>`;
  }
  document.querySelector("#app").innerHTML = accountShell(content, user);
}
