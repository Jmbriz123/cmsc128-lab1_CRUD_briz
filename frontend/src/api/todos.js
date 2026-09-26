const API_BASE = "/api";

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
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
    throw new Error(message);
  }

  if (response.status === 204) return { data: null, response };
  return { data: await response.json(), response };
}

export async function listTodos(filters) {
  const params = new URLSearchParams({
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
  });
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.priority) params.set("priority", filters.priority);

  const { data } = await apiRequest(`/todos?${params.toString()}`);
  return data;
}

export async function createTodo(payload) {
  return apiRequest("/todos", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateTodo(todoId, payload) {
  return apiRequest(`/todos/${todoId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteTodo(todoId) {
  return apiRequest(`/todos/${todoId}`, { method: "DELETE" });
}

export async function restoreTodo(todoId) {
  return apiRequest(`/todos/${todoId}/restore`, { method: "POST" });
}