import { fireEvent, screen, waitFor, within } from "@testing-library/dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mountApp } from "../components/appShell.js";
import { bindListHandlers } from "./listHandlers.js";
import { bindTaskHandlers } from "./taskHandlers.js";
import state from "../state.js";

const victor = { id: 2, email: "victor@example.com", display_name: "Victor" };

function jsonResponse(data, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// A small in-memory stand-in for the lists and todos endpoints.
function makeApi({ lists = [], members = {} } = {}) {
  const requests = [];
  let nextListId = 100;
  const fetchMock = vi.fn(async (input, options = {}) => {
    const url = new URL(input, "http://localhost");
    const method = options.method || "GET";
    const body = options.body ? JSON.parse(options.body) : undefined;
    requests.push({ url, method, body });
    const path = url.pathname.replace(/^\/api/, "");

    if (path === "/todos" && method === "GET") return jsonResponse([]);
    if (path === "/todos" && method === "POST") return jsonResponse({ id: 1, ...body }, 201);
    if (path === "/lists" && method === "GET") return jsonResponse(lists);
    if (path === "/lists" && method === "POST") {
      const created = { id: nextListId++, name: body.name, owner_name: "Victor", is_owner: true };
      lists.push(created);
      members[created.id] = [{ ...victor, is_owner: true }];
      return jsonResponse(created, 201);
    }
    const memberPath = path.match(/^\/lists\/(\d+)\/members(?:\/(\d+))?$/);
    if (memberPath && method === "GET") return jsonResponse(members[memberPath[1]] || []);
    if (memberPath && method === "POST") {
      const added = { id: 3, email: body.email, display_name: "Nikko", is_owner: false };
      members[memberPath[1]].push(added);
      return jsonResponse(added, 201);
    }
    if (memberPath && method === "DELETE") {
      const index = lists.findIndex((item) => String(item.id) === memberPath[1]);
      if (Number(memberPath[2]) === victor.id) lists.splice(index, 1);
      return jsonResponse(null, 204);
    }
    return jsonResponse({ detail: "Not found" }, 404);
  });
  return { fetchMock, requests };
}

function renderApplication(fetchMock) {
  document.body.innerHTML = '<div id="app"></div>';
  vi.stubGlobal("fetch", fetchMock);
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const elements = mountApp();
  bindTaskHandlers(elements);
  bindListHandlers(elements, victor);
  return elements;
}

const todoListRequests = (requests) => requests.filter(
  (request) => request.method === "GET" && request.url.pathname === "/api/todos",
);

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

describe("collaborative lists", () => {
  it("starts on the personal list without a list filter", async () => {
    const api = makeApi();
    const elements = renderApplication(api.fetchMock);

    await screen.findByText("Your list is clear.");
    expect(elements.listTitle.textContent).toBe("Personal tasks");
    expect(todoListRequests(api.requests)[0].url.searchParams.has("list_id")).toBe(false);
    expect(elements.membersPanel.classList.contains("hidden")).toBe(true);
  });

  it("switches to a shared list, loads its tasks, and shows member-only controls", async () => {
    const api = makeApi({
      lists: [{ id: 7, name: "Nikko's Group List", owner_name: "Nikko", is_owner: false }],
      members: { 7: [{ id: 3, email: "nikko@example.com", display_name: "Nikko", is_owner: true }, { ...victor, is_owner: false }] },
    });
    const elements = renderApplication(api.fetchMock);
    await screen.findByRole("option", { name: "Nikko's Group List (shared by Nikko)" });

    fireEvent.change(elements.listSelect, { target: { value: "7" } });

    await within(elements.memberList).findByText("nikko@example.com");
    expect(todoListRequests(api.requests).at(-1).url.searchParams.get("list_id")).toBe("7");
    expect(elements.listTitle.textContent).toBe("Nikko's Group List");
    expect(screen.getByText("Shared by Nikko")).toBeTruthy();
    expect(elements.addMemberForm.classList.contains("hidden")).toBe(true);
    expect(elements.deleteList.classList.contains("hidden")).toBe(true);
    expect(elements.leaveList.classList.contains("hidden")).toBe(false);
    expect(within(elements.memberList).queryByRole("button", { name: /Remove/ })).toBeNull();
  });

  it("creates a list, adds a member by email, and files new tasks in it", async () => {
    const api = makeApi();
    const elements = renderApplication(api.fetchMock);
    await screen.findByText("Your list is clear.");

    elements.newListName.value = "  Thesis group  ";
    fireEvent.submit(elements.newListForm);
    await screen.findByText('Created "Thesis group". Add members by email to share it.');
    expect(elements.listSelect.value).toBe("100");
    expect(elements.addMemberForm.classList.contains("hidden")).toBe(false);

    elements.memberEmail.value = "nikko@example.com";
    fireEvent.submit(elements.addMemberForm);
    await screen.findByText("Nikko can now use this list.");
    expect(api.requests.find((request) => request.url.pathname === "/api/lists/100/members"
      && request.method === "POST").body).toEqual({ email: "nikko@example.com" });

    elements.title.value = "Draft chapter 1";
    fireEvent.submit(elements.form);
    await waitFor(() => expect(api.requests.some((request) => request.method === "POST"
      && request.url.pathname === "/api/todos")).toBe(true));
    const createRequest = api.requests.find((request) => request.method === "POST" && request.url.pathname === "/api/todos");
    expect(createRequest.body.list_id).toBe(100);
  });

  it("leaves a shared list and returns to the personal list", async () => {
    const api = makeApi({
      lists: [{ id: 7, name: "Group", owner_name: "Nikko", is_owner: false }],
      members: { 7: [] },
    });
    const elements = renderApplication(api.fetchMock);
    await screen.findByRole("option", { name: "Group (shared by Nikko)" });
    fireEvent.change(elements.listSelect, { target: { value: "7" } });

    fireEvent.click(await screen.findByRole("button", { name: "Leave list" }));

    await screen.findByText("You left the list.");
    expect(api.requests.some((request) => request.method === "DELETE"
      && request.url.pathname === "/api/lists/7/members/2")).toBe(true);
    expect(elements.listSelect.value).toBe("");
    expect(elements.listTitle.textContent).toBe("Personal tasks");
    expect(screen.queryByRole("option", { name: /Group/ })).toBeNull();
  });

  it("escapes list and member names", async () => {
    const api = makeApi({
      lists: [{ id: 7, name: "<img src=x onerror=alert(1)>", owner_name: "<b>Mallory</b>", is_owner: false }],
      members: { 7: [{ id: 9, email: "m@example.com", display_name: "<script>x</script>", is_owner: true }] },
    });
    const elements = renderApplication(api.fetchMock);
    await screen.findByRole("option", { name: /Mallory/ });
    fireEvent.change(elements.listSelect, { target: { value: "7" } });
    await within(elements.memberList).findByText("<script>x</script>");

    expect(document.querySelector("img")).toBeNull();
    expect(document.querySelector("#member-list script")).toBeNull();
  });
});
