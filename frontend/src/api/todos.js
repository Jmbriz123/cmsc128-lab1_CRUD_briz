import { apiRequest } from "./client.js";

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