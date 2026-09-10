import "./styles.css";

const API_BASE = "/api";
const UNDO_FALLBACK_SECONDS = 10;

const state = {
  todos: [],
  editingId: null,
  pendingDelete: null,
  undoTimer: null,
};

const app = document.querySelector("#app");

app.innerHTML = `
  <div class="shell">
    <header class="topbar">
      <a class="brand" href="#tasks" aria-label="Daymark home">
        <span class="brand-mark">D</span>
        <span>Daymark</span>
      </a>
      <nav class="nav" aria-label="Primary navigation">
        <a class="nav-link active" href="#tasks">All tasks</a>
        <span class="task-count" id="task-count">0 tasks</span>
      </nav>
      <div class="status-dot"><span></span>Workspace online</div>
    </header>

    <main id="tasks" class="workspace">
      <section class="intro">
        <div>
          <p class="eyebrow">Academic task manager</p>
          <h1>Make room for the work that matters.</h1>
          <p class="lede">Capture the next thing, give it a place, and keep your week moving.</p>
        </div>
        <button class="button button-primary" id="new-task-button" type="button">+ New task</button>
      </section>

      <section class="content-grid">
        <aside class="task-editor" aria-labelledby="editor-title">
          <div class="panel-heading">
            <div>
              <p class="eyebrow" id="editor-kicker">Quick capture</p>
              <h2 id="editor-title">Add a task</h2>
            </div>
            <span class="step-mark">01</span>
          </div>
          <form id="task-form" novalidate>
            <label for="title">Task title <span aria-hidden="true">*</span></label>
            <input id="title" name="title" maxlength="255" required placeholder="e.g. Finish literature review" />
            <p class="field-error" id="title-error"></p>

            <label for="description">Details <span class="optional">Optional</span></label>
            <textarea id="description" name="description" rows="3" placeholder="Add a useful note or next step"></textarea>

            <div class="form-row">
              <div>
                <label for="due-date">Due date <span class="optional">Optional</span></label>
                <input id="due-date" name="due_date" type="datetime-local" />
              </div>
              <div>
                <label for="priority">Priority</label>
                <select id="priority" name="priority">
                  <option value="low">Low</option>
                  <option value="medium" selected>Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>

            <label for="tag">Tag <span class="optional">Optional</span></label>
            <input id="tag" name="tag" maxlength="100" placeholder="e.g. research" />
            <p class="form-note">Use tags to group related work.</p>

            <div class="form-actions">
              <button class="button button-primary" type="submit" id="save-button">Add task</button>
              <button class="button button-quiet hidden" type="button" id="cancel-edit-button">Cancel</button>
            </div>
          </form>
        </aside>

        <section class="task-area" aria-labelledby="list-title">
          <div class="list-heading">
            <div>
              <p class="eyebrow">Your workspace</p>
              <h2 id="list-title">All tasks</h2>
            </div>
            <span class="result-label" id="result-label">Loading...</span>
          </div>

          <div class="filters" aria-label="Task filters and sorting">
            <div class="filter-search">
              <label for="tag-filter">Filter by tag</label>
              <input id="tag-filter" placeholder="All tags" />
            </div>
            <div>
              <label for="priority-filter">Priority</label>
              <select id="priority-filter">
                <option value="">All priorities</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label for="sort-by">Sort by</label>
              <select id="sort-by">
                <option value="date_added">Date added</option>
                <option value="due_date">Due date</option>
                <option value="priority">Priority</option>
                <option value="tag">Tag</option>
              </select>
            </div>
            <div>
              <label for="sort-order">Order</label>
              <select id="sort-order">
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </div>
            <button class="clear-filters" id="clear-filters" type="button">Clear</button>
          </div>

          <div class="feedback" id="feedback" role="status" aria-live="polite"></div>
          <div class="task-list" id="task-list" aria-live="polite"></div>
        </section>
      </section>
    </main>

    <div class="toast-region" id="toast-region" aria-live="assertive" aria-atomic="true"></div>

    <dialog class="confirm-dialog" id="delete-dialog" aria-labelledby="delete-dialog-title">
      <div class="dialog-icon">!</div>
      <h2 id="delete-dialog-title">Delete this task?</h2>
      <p id="delete-dialog-copy">This task will leave your list. You will have a few seconds to undo it.</p>
      <div class="dialog-actions">
        <button class="button button-quiet" id="cancel-delete" type="button">Keep task</button>
        <button class="button button-danger" id="confirm-delete" type="button">Delete task</button>
      </div>
    </dialog>
  </div>
`;

const elements = {
  form: document.querySelector("#task-form"),
  title: document.querySelector("#title"),
  titleError: document.querySelector("#title-error"),
  description: document.querySelector("#description"),
  dueDate: document.querySelector("#due-date"),
  priority: document.querySelector("#priority"),
  tag: document.querySelector("#tag"),
  editorTitle: document.querySelector("#editor-title"),
  editorKicker: document.querySelector("#editor-kicker"),
  saveButton: document.querySelector("#save-button"),
  cancelEdit: document.querySelector("#cancel-edit-button"),
  newTask: document.querySelector("#new-task-button"),
  taskList: document.querySelector("#task-list"),
  taskCount: document.querySelector("#task-count"),
  resultLabel: document.querySelector("#result-label"),
  feedback: document.querySelector("#feedback"),
  tagFilter: document.querySelector("#tag-filter"),
  priorityFilter: document.querySelector("#priority-filter"),
  sortBy: document.querySelector("#sort-by"),
  sortOrder: document.querySelector("#sort-order"),
  clearFilters: document.querySelector("#clear-filters"),
  deleteDialog: document.querySelector("#delete-dialog"),
  deleteDialogCopy: document.querySelector("#delete-dialog-copy"),
  cancelDelete: document.querySelector("#cancel-delete"),
  confirmDelete: document.querySelector("#confirm-delete"),
  toastRegion: document.querySelector("#toast-region"),
};

function showFeedback(message, type = "success") {
  elements.feedback.textContent = message;
  elements.feedback.className = `feedback ${type}`;
  if (type === "success") {
    window.setTimeout(() => {
      elements.feedback.textContent = "";
      elements.feedback.className = "feedback";
    }, 4200);
  }
}

function clearFeedback() {
  elements.feedback.textContent = "";
  elements.feedback.className = "feedback";
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
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

function formatDate(dateValue, includeTime = false) {
  if (!dateValue) return "No due date";
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return "Invalid date";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...(includeTime ? { hour: "numeric", minute: "2-digit" } : {}),
  }).format(date);
}

function toInputDate(dateValue) {
  if (!dateValue) return "";
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16);
}

function priorityLabel(priority) {
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}

function buildQuery() {
  const params = new URLSearchParams({
    sort_by: elements.sortBy.value,
    sort_order: elements.sortOrder.value,
  });
  if (elements.tagFilter.value.trim()) params.set("tag", elements.tagFilter.value.trim());
  if (elements.priorityFilter.value) params.set("priority", elements.priorityFilter.value);
  return `?${params.toString()}`;
}

async function loadTodos() {
  elements.taskList.innerHTML = `<div class="loading-state"><span class="spinner"></span>Loading tasks...</div>`;
  try {
    const { data } = await apiRequest(`/todos${buildQuery()}`);
    state.todos = data;
    renderTodos();
  } catch (error) {
    elements.taskList.innerHTML = `<div class="empty-state error-state"><strong>Could not load tasks.</strong><span>${escapeHtml(error.message)}</span><button class="button button-quiet" id="retry-load" type="button">Try again</button></div>`;
    document.querySelector("#retry-load")?.addEventListener("click", loadTodos);
    elements.resultLabel.textContent = "Unavailable";
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderTodos() {
  const count = state.todos.length;
  elements.taskCount.textContent = `${count} ${count === 1 ? "task" : "tasks"}`;
  elements.resultLabel.textContent = count === 0 ? "Nothing here yet" : `${count} shown`;

  if (count === 0) {
    elements.taskList.innerHTML = `
      <div class="empty-state">
        <div class="empty-mark">+</div>
        <strong>Your list is clear.</strong>
        <span>Add a task to give your next move a home.</span>
        <button class="button button-secondary" id="empty-add-task" type="button">Add your first task</button>
      </div>
    `;
    document.querySelector("#empty-add-task")?.addEventListener("click", focusNewTask);
    return;
  }

  elements.taskList.innerHTML = state.todos.map((todo) => `
    <article class="task-card ${todo.completed ? "is-complete" : ""}" data-id="${todo.id}">
      <button class="check-button" type="button" data-action="toggle" aria-label="Mark ${escapeHtml(todo.title)} as ${todo.completed ? "active" : "complete"}" aria-pressed="${todo.completed}">
        ${todo.completed ? "✓" : ""}
      </button>
      <div class="task-main">
        <div class="task-title-line">
          <h3>${escapeHtml(todo.title)}</h3>
          <span class="priority priority-${todo.priority}">${priorityLabel(todo.priority)}</span>
        </div>
        ${todo.description ? `<p class="task-description">${escapeHtml(todo.description)}</p>` : ""}
        <div class="task-meta">
          <span class="meta-item ${todo.due_date ? "" : "muted"}"><span class="meta-icon">DUE</span>${todo.due_date ? escapeHtml(formatDate(todo.due_date, true)) : "No due date"}</span>
          ${todo.tag ? `<span class="tag">#${escapeHtml(todo.tag)}</span>` : ""}
          <span class="meta-item muted">Added ${escapeHtml(formatDate(todo.created_at))}</span>
        </div>
      </div>
      <div class="task-actions">
        <button class="icon-button" type="button" data-action="edit" aria-label="Edit ${escapeHtml(todo.title)}">Edit</button>
        <button class="icon-button danger-text" type="button" data-action="delete" aria-label="Delete ${escapeHtml(todo.title)}">Delete</button>
      </div>
    </article>
  `).join("");
}

function resetForm() {
  state.editingId = null;
  elements.form.reset();
  elements.priority.value = "medium";
  elements.editorKicker.textContent = "Quick capture";
  elements.editorTitle.textContent = "Add a task";
  elements.saveButton.textContent = "Add task";
  elements.cancelEdit.classList.add("hidden");
  elements.titleError.textContent = "";
  elements.title.classList.remove("invalid");
}

function focusNewTask() {
  resetForm();
  elements.title.focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function beginEdit(todo) {
  state.editingId = todo.id;
  elements.editorKicker.textContent = "Editing task";
  elements.editorTitle.textContent = "Update task";
  elements.saveButton.textContent = "Save changes";
  elements.cancelEdit.classList.remove("hidden");
  elements.title.value = todo.title;
  elements.description.value = todo.description || "";
  elements.dueDate.value = toInputDate(todo.due_date);
  elements.priority.value = todo.priority;
  elements.tag.value = todo.tag || "";
  elements.title.focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function formPayload() {
  const payload = {
    title: elements.title.value.trim(),
    description: elements.description.value.trim() || null,
    due_date: elements.dueDate.value ? new Date(elements.dueDate.value).toISOString() : null,
    priority: elements.priority.value,
    tag: elements.tag.value.trim() || null,
  };
  return payload;
}

async function saveTask(event) {
  event.preventDefault();
  clearFeedback();
  const title = elements.title.value.trim();
  if (!title) {
    elements.titleError.textContent = "A task title is required.";
    elements.title.classList.add("invalid");
    elements.title.focus();
    return;
  }

  elements.saveButton.disabled = true;
  try {
    const payload = formPayload();
    if (state.editingId) {
      await apiRequest(`/todos/${state.editingId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      showFeedback("Task updated.");
    } else {
      await apiRequest("/todos", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showFeedback("Task added to your workspace.");
    }
    resetForm();
    await loadTodos();
  } catch (error) {
    showFeedback(error.message, "error");
  } finally {
    elements.saveButton.disabled = false;
  }
}

async function toggleTask(todo) {
  try {
    await apiRequest(`/todos/${todo.id}`, {
      method: "PATCH",
      body: JSON.stringify({ completed: !todo.completed }),
    });
    showFeedback(todo.completed ? "Task reopened." : "Task marked complete.");
    await loadTodos();
  } catch (error) {
    showFeedback(error.message, "error");
  }
}

function openDeleteDialog(todo) {
  state.pendingDelete = todo;
  elements.deleteDialogCopy.textContent = `“${todo.title}” will leave your list. You will have a few seconds to undo it.`;
  elements.deleteDialog.showModal();
}

async function confirmDelete() {
  if (!state.pendingDelete) return;
  const todo = state.pendingDelete;
  elements.confirmDelete.disabled = true;
  try {
    const { response } = await apiRequest(`/todos/${todo.id}`, { method: "DELETE" });
    const undoSeconds = Number(response.headers.get("X-Undo-Window-Seconds")) || UNDO_FALLBACK_SECONDS;
    elements.deleteDialog.close();
    state.pendingDelete = null;
    await loadTodos();
    showUndoToast(todo, undoSeconds);
  } catch (error) {
    elements.confirmDelete.disabled = false;
    showFeedback(error.message, "error");
  }
}

function showUndoToast(todo, seconds) {
  window.clearTimeout(state.undoTimer);
  let remaining = seconds;
  elements.toastRegion.innerHTML = `
    <div class="toast">
      <span><strong>Task deleted.</strong> Undo available for <span id="undo-countdown">${remaining}s</span>.</span>
      <button class="toast-action" id="undo-delete" type="button">Undo</button>
    </div>
  `;
  const countdown = document.querySelector("#undo-countdown");
  const undoButton = document.querySelector("#undo-delete");
  const closeToast = () => {
    window.clearInterval(state.undoTimer);
    elements.toastRegion.innerHTML = "";
  };
  undoButton.addEventListener("click", async () => {
    undoButton.disabled = true;
    try {
      await apiRequest(`/todos/${todo.id}/restore`, { method: "POST" });
      closeToast();
      showFeedback("Task restored.");
      await loadTodos();
    } catch (error) {
      closeToast();
      showFeedback(error.message, "error");
      await loadTodos();
    }
  });
  state.undoTimer = window.setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      closeToast();
    } else {
      countdown.textContent = `${remaining}s`;
    }
  }, 1000);
}

function handleTaskAction(event) {
  const actionButton = event.target.closest("[data-action]");
  if (!actionButton) return;
  const card = actionButton.closest("[data-id]");
  const todo = state.todos.find((item) => item.id === Number(card.dataset.id));
  if (!todo) return;
  if (actionButton.dataset.action === "edit") beginEdit(todo);
  if (actionButton.dataset.action === "delete") openDeleteDialog(todo);
  if (actionButton.dataset.action === "toggle") toggleTask(todo);
}

elements.form.addEventListener("submit", saveTask);
elements.title.addEventListener("input", () => {
  elements.titleError.textContent = "";
  elements.title.classList.remove("invalid");
});
elements.cancelEdit.addEventListener("click", resetForm);
elements.newTask.addEventListener("click", focusNewTask);
elements.taskList.addEventListener("click", handleTaskAction);
elements.cancelDelete.addEventListener("click", () => {
  state.pendingDelete = null;
  elements.deleteDialog.close();
});
elements.confirmDelete.addEventListener("click", confirmDelete);
[elements.tagFilter, elements.priorityFilter, elements.sortBy, elements.sortOrder].forEach((element) => {
  element.addEventListener(element === elements.tagFilter ? "change" : "change", loadTodos);
});
elements.tagFilter.addEventListener("keydown", (event) => {
  if (event.key === "Enter") loadTodos();
});
elements.clearFilters.addEventListener("click", () => {
  elements.tagFilter.value = "";
  elements.priorityFilter.value = "";
  elements.sortBy.value = "date_added";
  elements.sortOrder.value = "asc";
  loadTodos();
});
elements.deleteDialog.addEventListener("cancel", () => {
  state.pendingDelete = null;
});

loadTodos();
