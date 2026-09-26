import {
  createTodo,
  deleteTodo,
  listTodos,
  restoreTodo,
  updateTodo,
} from "../api/todos.js";
import { clearFeedback, showFeedback, showUndoToast } from "../components/feedback.js";
import { renderLoadError, renderLoading, renderTodos } from "../components/taskList.js";
import state from "../state.js";
import { toInputDate } from "../utils/task.js";

const UNDO_FALLBACK_SECONDS = 10;

export function bindTaskHandlers(elements) {
  async function loadTodos() {
    renderLoading(elements.taskList);
    try {
      state.todos = await listTodos({
        sortBy: elements.sortBy.value,
        sortOrder: elements.sortOrder.value,
        tag: elements.tagFilter.value.trim(),
        priority: elements.priorityFilter.value,
      });
      renderTodos(state.todos, elements);
    } catch (error) {
      renderLoadError(elements, error);
    }
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
    return {
      title: elements.title.value.trim(),
      description: elements.description.value.trim() || null,
      due_date: elements.dueDate.value ? new Date(elements.dueDate.value).toISOString() : null,
      priority: elements.priority.value,
      tag: elements.tag.value.trim() || null,
    };
  }

  async function saveTask(event) {
    event.preventDefault();
    clearFeedback(elements);
    if (!elements.title.value.trim()) {
      elements.titleError.textContent = "A task title is required.";
      elements.title.classList.add("invalid");
      elements.title.focus();
      return;
    }

    elements.saveButton.disabled = true;
    try {
      if (state.editingId) {
        await updateTodo(state.editingId, formPayload());
        showFeedback(elements, "Task updated.");
      } else {
        await createTodo(formPayload());
        showFeedback(elements, "Task added to your workspace.");
      }
      resetForm();
      await loadTodos();
    } catch (error) {
      showFeedback(elements, error.message, "error");
    } finally {
      elements.saveButton.disabled = false;
    }
  }

  async function toggleTask(todo) {
    try {
      await updateTodo(todo.id, { completed: !todo.completed });
      showFeedback(elements, todo.completed ? "Task reopened." : "Task marked complete.");
      await loadTodos();
    } catch (error) {
      showFeedback(elements, error.message, "error");
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
      const { response } = await deleteTodo(todo.id);
      const undoSeconds = Number(response.headers.get("X-Undo-Window-Seconds")) || UNDO_FALLBACK_SECONDS;
      elements.deleteDialog.close();
      state.pendingDelete = null;
      await loadTodos();
      showUndoToast(elements, todo, undoSeconds, async (closeToast, deletedTodo) => {
        try {
          await restoreTodo(deletedTodo.id);
          closeToast();
          showFeedback(elements, "Task restored.");
          await loadTodos();
        } catch (error) {
          closeToast();
          showFeedback(elements, error.message, "error");
          await loadTodos();
        }
      });
    } catch (error) {
      elements.confirmDelete.disabled = false;
      showFeedback(elements, error.message, "error");
    }
  }

  function handleTaskAction(event) {
    const actionButton = event.target.closest("[data-action]");
    if (!actionButton) return;

    if (actionButton.dataset.action === "retry") {
      loadTodos();
      return;
    }
    if (actionButton.dataset.action === "new-task") {
      focusNewTask();
      return;
    }

    const card = actionButton.closest("[data-id]");
    const todo = state.todos.find((item) => item.id === Number(card?.dataset.id));
    if (!todo) return;
    if (actionButton.dataset.action === "edit") beginEdit(todo);
    if (actionButton.dataset.action === "delete") openDeleteDialog(todo);
    if (actionButton.dataset.action === "toggle") toggleTask(todo);
  }

  // add event listeners to the DOM elements
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
  [elements.tagFilter, elements.priorityFilter, elements.sortBy, elements.sortOrder]
    .forEach((element) => element.addEventListener("change", loadTodos));
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
}