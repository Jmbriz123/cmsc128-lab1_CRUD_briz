import { afterEach, expect, it, vi } from "vitest";
import { apiRequest } from "./client.js";

afterEach(() => vi.unstubAllGlobals());

it("sends the security header and same-origin cookies", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetch);
  expect((await apiRequest("/auth/logout", { method: "POST" })).data).toBeNull();
  expect(fetch).toHaveBeenCalledWith("/api/auth/logout", expect.objectContaining({
    credentials: "same-origin", headers: expect.objectContaining({ "X-Requested-With": "Daymark" }),
  }));
});

it("preserves statuses and expires authentication only on protected requests", async () => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => new Response(JSON.stringify({ detail: "Login required" }), { status: 401 })));
  const listener = vi.fn();
  window.addEventListener("auth:expired", listener);
  try {
    await expect(apiRequest("/auth/login")).rejects.toMatchObject({ status: 401 });
    expect(listener).not.toHaveBeenCalled();
    await expect(apiRequest("/todos")).rejects.toMatchObject({ status: 401 });
    expect(listener).toHaveBeenCalledTimes(1);
  } finally {
    window.removeEventListener("auth:expired", listener);
  }
});

it("preserves retry guidance and distinguishes network errors", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Slow down" }), { status: 429, headers: { "Retry-After": "30" } })));
  await expect(apiRequest("/auth/login")).rejects.toMatchObject({ status: 429, retryAfter: "30" });
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Network unavailable")));
  await expect(apiRequest("/auth/me")).rejects.toMatchObject({ message: "Network unavailable" });
});
