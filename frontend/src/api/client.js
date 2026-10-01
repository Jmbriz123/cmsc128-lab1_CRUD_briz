const API_BASE = "/api";

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "Daymark",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = Array.isArray(payload.detail)
        ? payload.detail.map((error) => error.msg).join(" ")
        : payload.detail || message;
    } catch {
      // Keep the HTTP fallback when the server has no JSON error body.
    }
    const error = new Error(message);
    error.status = response.status;
    error.retryAfter = response.headers.get("Retry-After");
    if (response.status === 401 && path !== "/auth/login" && path !== "/auth/me") {
      window.dispatchEvent(new Event("auth:expired"));
    }
    throw error;
  }

  if (response.status === 204) return { data: null, response };
  return { data: await response.json(), response };
}

