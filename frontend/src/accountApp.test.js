import { fireEvent, screen, waitFor, within } from "@testing-library/dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import * as auth from "./api/auth.js";
import { createAccountApp } from "./accountApp.js";
import state from "./state.js";

vi.mock("./api/auth.js", () => ({
  currentUser: vi.fn(), register: vi.fn(), login: vi.fn(), logout: vi.fn(),
  updateProfile: vi.fn(), changePassword: vi.fn(), forgotPassword: vi.fn(), resetPassword: vi.fn(),
}));
vi.mock("./api/todos.js", () => ({ listTodos: vi.fn().mockResolvedValue([]), createTodo: vi.fn(), updateTodo: vi.fn(), deleteTodo: vi.fn(), restoreTodo: vi.fn() }));
const user = { id: 1, email: "student@example.com", display_name: "Student" };
const password = "a sufficiently long password";
let app;

beforeEach(() => {
  vi.clearAllMocks();
  document.body.innerHTML = '<div id="app"></div>';
  history.replaceState(null, "", "#/login");
  auth.currentUser.mockRejectedValue(Object.assign(new Error("Unauthorized"), { status: 401 }));
  vi.spyOn(window, "confirm").mockReturnValue(true);
});
afterEach(() => { app?.stop(); vi.restoreAllMocks(); });

async function start(route = "login", authenticated = false) {
  history.replaceState(null, "", `#/${route}`);
  if (authenticated) auth.currentUser.mockResolvedValue(user);
  app = createAccountApp();
  await app.start();
}
function input(label, value) { fireEvent.input(screen.getByLabelText(label), { target: { value } }); }

it("restores the session before showing the profile greeting", async () => {
  await start("profile", true);
  expect(screen.getByRole("heading", { name: "Hello, Student" })).toBeTruthy();
  expect(auth.currentUser).toHaveBeenCalledOnce();
});

it("redirects unauthenticated task navigation to login", async () => {
  await start("tasks");
  expect(location.hash).toBe("#/login");
  expect(screen.getByRole("heading", { name: "Log in to Daymark" })).toBeTruthy();
});

it("logs in and opens the profile", async () => {
  auth.login.mockResolvedValue(user);
  await start();
  input("Email address", user.email);
  input("Password", password);
  fireEvent.submit(document.querySelector("#login-form"));
  await screen.findByRole("heading", { name: "Hello, Student" });
  expect(auth.login).toHaveBeenCalledWith({ email: user.email, password });
});

it("validates confirmation and registers without keeping passwords", async () => {
  auth.register.mockResolvedValue({});
  await start("register");
  input("Display name", "Student"); input("Email address", user.email);
  input("Password", password); input("Confirm password", "different long password");
  fireEvent.submit(document.querySelector("#register-form"));
  expect(auth.register).not.toHaveBeenCalled();
  expect(screen.getByText("Passwords do not match.")).toBeTruthy();
  input("Confirm password", password);
  fireEvent.submit(document.querySelector("#register-form"));
  await screen.findByRole("heading", { name: "Log in to Daymark" });
  expect(screen.getByText("Account created. Log in to continue.")).toBeTruthy();
  expect(screen.getByLabelText("Password").value).toBe("");
});

it("preserves dirty profile changes when navigation is cancelled", async () => {
  await start("profile", true);
  input("Display name", "Unsaved");
  window.confirm.mockReturnValue(false);
  fireEvent.click(screen.getByRole("link", { name: "Shared tasks" }));
  expect(window.confirm).toHaveBeenCalledOnce();
  expect(location.hash).toBe("#/profile");
  expect(screen.getByLabelText("Display name").value).toBe("Unsaved");
});

it("saves profile data without discarding unsaved password fields", async () => {
  auth.updateProfile.mockResolvedValue({ ...user, display_name: "Updated" });
  await start("profile", true);
  input("New password", "unsaved new password");
  input("Display name", "Updated");
  fireEvent.submit(document.querySelector("#profile-form"));
  await screen.findByText("Profile saved.");
  expect(screen.getByRole("heading", { name: "Hello, Updated" })).toBeTruthy();
  expect(screen.getByLabelText("New password").value).toBe("unsaved new password");
});

it("logs out and clears protected task state", async () => {
  auth.logout.mockResolvedValue({});
  await start("profile", true);
  state.todos = [{ title: "private" }];
  fireEvent.click(screen.getByRole("button", { name: "Log Out" }));
  await screen.findByRole("heading", { name: "Log in to Daymark" });
  expect(state.todos).toEqual([]);
  expect(screen.queryByText("Hello, Student")).toBeNull();
});

it("rechecks a page restored from browser history", async () => {
  await start("profile", true);
  auth.currentUser.mockRejectedValue(Object.assign(new Error("Expired"), { status: 401 }));
  window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
  await screen.findByRole("heading", { name: "Log in to Daymark" });
});

it("distinguishes a network outage from logout and offers retry", async () => {
  auth.currentUser.mockRejectedValue(new TypeError("Network down"));
  app = createAccountApp(); await app.start();
  expect(screen.getByRole("heading", { name: "Cannot reach your account" })).toBeTruthy();
  auth.currentUser.mockResolvedValue(user);
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("heading", { name: "Hello, Student" });
});

it("removes reset tokens from the address bar and submits them only in the body", async () => {
  auth.resetPassword.mockResolvedValue({});
  await start("reset-password?token=" + "x".repeat(43));
  expect(location.hash).toBe("#/reset-password");
  input("New password", password); input("Confirm password", password);
  fireEvent.submit(document.querySelector("#reset-form"));
  await screen.findByRole("heading", { name: "Log in to Daymark" });
  expect(auth.resetPassword).toHaveBeenCalledWith({ token: "x".repeat(43), new_password: password });
  expect(localStorage.length).toBe(0);
});

it("disables reset submission without a token", async () => {
  await start("reset-password");
  expect(screen.getByRole("button", { name: "Reset password" }).disabled).toBe(true);
});

it("prevents duplicate pending submissions and displays rate-limit guidance", async () => {
  let reject;
  auth.login.mockReturnValue(new Promise((_, fail) => { reject = fail; }));
  await start(); input("Email address", user.email); input("Password", password);
  const form = document.querySelector("#login-form");
  fireEvent.submit(form); fireEvent.submit(form);
  expect(auth.login).toHaveBeenCalledOnce();
  expect(within(form).getByRole("button", { name: "Log in" }).disabled).toBe(true);
  reject(Object.assign(new Error("Too many attempts."), { status: 429, retryAfter: "30" }));
  await waitFor(() => expect(screen.getByText(/Retry in 30 seconds/)).toBeTruthy());
});
