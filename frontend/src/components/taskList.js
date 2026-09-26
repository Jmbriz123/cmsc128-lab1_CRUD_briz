import { escapeHtml, formatDate, priorityLabel } from "../utils/task.js";

export function renderLoading(taskList) {
  taskList.innerHTML = `<div class="loading-state"><span class="spinner"></span>Loading tasks...</div>`;
}

export function renderLoadError(elements, error) {
  elements.taskList.innerHTML = `<div class="empty-state error-state"><strong>Could not load tasks.</strong><span>${escapeHtml(error.message)}</span><button class="button button-quiet" type="button" data-action="retry">Try again</button></div>`;
  elements.resultLabel.textContent = "Unavailable";
}

export function renderTodos(todos, elements) {
  const count = todos.length;
  elements.taskCount.textContent = `${count} ${count === 1 ? "task" : "tasks"}`;
  elements.resultLabel.textContent = count === 0 ? "Nothing here yet" : `${count} shown`;

  if (count === 0) {
    elements.taskList.innerHTML = `
      <div class="empty-state">
        <div class="empty-mark">+</div>
        <strong>Your list is clear.</strong>
        <span>Add a task to give your next move a home.</span>
        <button class="button button-secondary" type="button" data-action="new-task">Add your first task</button>
      </div>
    `;
    return;
  }

  elements.taskList.innerHTML = todos.map((todo) => `
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