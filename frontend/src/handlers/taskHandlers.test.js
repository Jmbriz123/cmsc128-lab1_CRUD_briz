import { fireEvent, screen, waitFor, within } from "@testing-library/dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mountApp } from "../components/appShell.js";
import { bindTaskHandlers } from "./taskHandlers.js";
import state from "../state.js";

function makeTodo(overrides = {}) {
  return {
    id: 1,
    title: "Read chapter",
    description: "Take notes",
    due_date: "2026-10-03T09:15:00",
    priority: "high",
    tag: "reading",
    completed: false,
    created_at: "2026-09-26T08:00:00",
    updated_at: "2026-09-26T08:00:00",
    ...overrides,
  };
}

function jsonResponse(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

function makeApi(initialTodos = []) {
  const todos = initialTodos.map((todo) => makeTodo(todo));
  const deletedTodos = new Map();
  const requests = [];
  let nextId = Math.max(0, ...todos.map((todo) => todo.id)) + 1;

  const fetchMock = vi.fn(async (input, options = {}) => {
    const url = new URL(input, "http://localhost");
    const method = options.method || "GET";
    const request = {
      url,
      method,
      body: options.body ? JSON.parse(options.body) : undefined,
    };
    requests.push(request);

    if (method === "GET" && url.pathname === "/api/todos") {
      return jsonResponse(todos);
    }
    if (method === "POST" && url.pathname === "/api/todos") {
      const todo = makeTodo({
        ...request.body,
        id: nextId++,
        completed: false,
        created_at: "2026-09-26T08:00:00",
        updated_at: "2026-09-26T08:00:00",
      });
      todos.push(todo);
      return jsonResponse(todo, 201);
    }

    const match = url.pathname.match(/^\/api\/todos\/(\d+)(\/restore)?$/);
    if (!match) return jsonResponse({ detail: "Not found" }, 404);
    const todoId = Number(match[1]);

    if (match[2] && method === "POST") {
      const todo = deletedTodos.get(todoId);
      if (!todo) return jsonResponse({ detail: "Todo cannot be restored" }, 404);
      deletedTodos.delete(todoId);
      todos.push(todo);
      return jsonResponse(todo);
    }

    const index = todos.findIndex((todo) => todo.id === todoId);
    if (index < 0) return jsonResponse({ detail: "Todo not found" }, 404);
    if (method === "PATCH") {
      Object.assign(todos[index], request.body);
      return jsonResponse(todos[index]);
    }
    if (method === "DELETE") {
      deletedTodos.set(todoId, todos[index]);
      todos.splice(index, 1);
      return new Response(null, {
        status: 204,
        headers: { "X-Undo-Window-Seconds": "10" },
      });
    }
    return jsonResponse({ detail: "Method not allowed" }, 405);
  });

  return { fetchMock, requests };
}

function renderApplication(fetchMock) {
  document.body.innerHTML = '<div id="app"></div>';
  vi.stubGlobal("fetch", fetchMock);
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
  };
  const elements = mountApp();
  bindTaskHandlers(elements);
  return elements;
}

function listRequests(requests) {
  return requests.filter(
    (request) => request.method === "GET" && request.url.pathname === "/api/todos",
  );
}

beforeEach(() => {
  state.todos = [];
  state.editingId = null;
  state.pendingDelete = null;
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("Daymark task workflows", () => {
  it("renders the application and shows the loading state while tasks load", () => {
    let resolveFetch;
    const fetchMock = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
    );

    renderApplication(fetchMock);

    expect(screen.getByRole("link", { name: "Daymark home" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Add a task" })).toBeTruthy();
    expect(screen.getByText("Loading tasks...")).toBeTruthy();

    resolveFetch(jsonResponse([]));
  });

  it("shows an empty-list state when there are no tasks", async () => {
    const api = makeApi();
    renderApplication(api.fetchMock);

    expect(await screen.findByText("Your list is clear.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Add your first task" })).toBeTruthy();
    expect(screen.getByText("0 tasks")).toBeTruthy();
  });

  it("shows a load error and retries successfully", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: "Service unavailable" }, 503))
      .mockResolvedValueOnce(jsonResponse([]));
    renderApplication(fetchMock);

    expect(await screen.findByText("Could not load tasks.")).toBeTruthy();
    expect(screen.getByText("Service unavailable")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("Your list is clear.")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("validates a required title without sending a create request", async () => {
    const api = makeApi();
    const elements = renderApplication(api.fetchMock);
    await screen.findByText("Your list is clear.");
    elements.title.value = "   ";
    fireEvent.submit(elements.form);

    expect(screen.getByText("A task title is required.")).toBeTruthy();
    expect(api.requests.filter((request) => request.method === "POST")).toHaveLength(0);
  });

  it("creates and displays a task with its optional information", async () => {
    const api = makeApi();
    const elements = renderApplication(api.fetchMock);
    await screen.findByText("Your list is clear.");
    elements.title.value = "  Prepare presentation  ";
    elements.description.value = "  Draft the outline  ";
    elements.dueDate.value = "2026-10-03T09:15";
    elements.priority.value = "high";
    elements.tag.value = "coursework";
    fireEvent.submit(elements.form);

    expect(await screen.findByRole("heading", { name: "Prepare presentation" })).toBeTruthy();
    const createRequest = api.requests.find((request) => request.method === "POST");
    expect(createRequest.body).toEqual({
      title: "Prepare presentation",
      description: "Draft the outline",
      due_date: new Date("2026-10-03T09:15").toISOString(),
      priority: "high",
      tag: "coursework",
    });
    expect(screen.getByText("Draft the outline")).toBeTruthy();
    expect(within(elements.taskList).getByText("High")).toBeTruthy();
    expect(screen.getByText("#coursework")).toBeTruthy();
    const expectedDueDate = new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(createRequest.body.due_date));
    expect(elements.taskList.textContent).toContain(expectedDueDate);
  });

  it("edits an existing task and saves the changed values", async () => {
    const api = makeApi([makeTodo()]);
    const elements = renderApplication(api.fetchMock);
    await screen.findByRole("heading", { name: "Read chapter" });
    fireEvent.click(screen.getByRole("button", { name: "Edit Read chapter" }));

    expect(elements.title.value).toBe("Read chapter");
    expect(screen.getByRole("heading", { name: "Update task" })).toBeTruthy();
    elements.title.value = "Review chapter notes";
    fireEvent.submit(elements.form);

    expect(
      await screen.findByRole("heading", { name: "Review chapter notes" }),
    ).toBeTruthy();
    const updateRequest = api.requests.find((request) => request.method === "PATCH");
    expect(updateRequest.body.title).toBe("Review chapter notes");
    expect(updateRequest.body.priority).toBe("high");
  });

  it("completes and reopens a task", async () => {
    const api = makeApi([makeTodo()]);
    renderApplication(api.fetchMock);
    await screen.findByRole("heading", { name: "Read chapter" });
    fireEvent.click(screen.getByRole("button", { name: "Mark Read chapter as complete" }));

    expect(
      await screen.findByRole("button", { name: "Mark Read chapter as active" }),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Mark Read chapter as active" }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Mark Read chapter as complete" }),
      ).toBeTruthy();
    });
    expect(
      api.requests.filter((request) => request.method === "PATCH").map((request) => request.body.completed),
    ).toEqual([true, false]);
  });

  it("deletes a task and restores it through Undo", async () => {
    const api = makeApi([makeTodo()]);
    renderApplication(api.fetchMock);
    await screen.findByRole("heading", { name: "Read chapter" });
    fireEvent.click(screen.getByRole("button", { name: "Delete Read chapter" }));
    expect(screen.getByRole("heading", { name: "Delete this task?" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Delete task" }));

    expect(await screen.findByRole("button", { name: "Undo" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Read chapter" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));

    expect(await screen.findByRole("heading", { name: "Read chapter" })).toBeTruthy();
    expect(api.requests.some((request) => request.method === "DELETE")).toBe(true);
    expect(api.requests.some((request) => request.url.pathname.endsWith("/restore"))).toBe(true);
  });

  it("applies tag and priority filters and clears all filter/sort controls", async () => {
    const api = makeApi();
    const elements = renderApplication(api.fetchMock);
    await screen.findByText("Your list is clear.");

    elements.tagFilter.value = "reading";
    fireEvent.change(elements.tagFilter);
    await waitFor(() => expect(listRequests(api.requests)).toHaveLength(2));
    expect(listRequests(api.requests)[1].url.searchParams.get("tag")).toBe("reading");

    elements.priorityFilter.value = "high";
    fireEvent.change(elements.priorityFilter);
    await waitFor(() => expect(listRequests(api.requests)).toHaveLength(3));
    expect(listRequests(api.requests)[2].url.searchParams.get("priority")).toBe("high");

    elements.sortBy.value = "due_date";
    fireEvent.change(elements.sortBy);
    await waitFor(() => expect(listRequests(api.requests)).toHaveLength(4));

    elements.sortOrder.value = "desc";
    fireEvent.change(elements.sortOrder);
    await waitFor(() => expect(listRequests(api.requests)).toHaveLength(5));
    expect(listRequests(api.requests)[4].url.searchParams.get("sort_order")).toBe("desc");

    fireEvent.click(elements.clearFilters);
    await waitFor(() => expect(listRequests(api.requests)).toHaveLength(6));
    const cleared = listRequests(api.requests)[5].url.searchParams;
    expect(cleared.get("sort_by")).toBe("date_added");
    expect(cleared.get("sort_order")).toBe("asc");
    expect(cleared.has("tag")).toBe(false);
    expect(cleared.has("priority")).toBe(false);
    expect(elements.tagFilter.value).toBe("");
    expect(elements.priorityFilter.value).toBe("");
  });

  it.each(["date_added", "due_date", "priority", "tag"])(
    "sends %s sorting in ascending and descending order",
    async (sortBy) => {
      const api = makeApi();
      const elements = renderApplication(api.fetchMock);
      await screen.findByText("Your list is clear.");
      elements.sortBy.value = sortBy;
      fireEvent.change(elements.sortBy);
      await waitFor(() => expect(listRequests(api.requests)).toHaveLength(2));
      expect(listRequests(api.requests)[1].url.searchParams.get("sort_by")).toBe(sortBy);
      expect(listRequests(api.requests)[1].url.searchParams.get("sort_order")).toBe("asc");

      elements.sortOrder.value = "desc";
      fireEvent.change(elements.sortOrder);
      await waitFor(() => expect(listRequests(api.requests)).toHaveLength(3));
      expect(listRequests(api.requests)[2].url.searchParams.get("sort_by")).toBe(sortBy);
      expect(listRequests(api.requests)[2].url.searchParams.get("sort_order")).toBe("desc");
    },
  );

  it("shows an API error when task creation fails", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ detail: "Create failed" }, 500));
    const elements = renderApplication(fetchMock);
    await screen.findByText("Your list is clear.");
    elements.title.value = "A task";
    fireEvent.submit(elements.form);

    expect(await screen.findByText("Create failed")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Add a task" })).toBeTruthy();
  });
});