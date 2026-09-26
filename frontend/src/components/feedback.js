let undoTimer = null;

export function showFeedback(elements, message, type = "success") {
  elements.feedback.textContent = message;
  elements.feedback.className = `feedback ${type}`;
  if (type === "success") {
    window.setTimeout(() => {
      elements.feedback.textContent = "";
      elements.feedback.className = "feedback";
    }, 4200);
  }
}

export function clearFeedback(elements) {
  elements.feedback.textContent = "";
  elements.feedback.className = "feedback";
}

export function showUndoToast(elements, todo, seconds, onUndo) {
  window.clearInterval(undoTimer);
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
    window.clearInterval(undoTimer);
    elements.toastRegion.innerHTML = "";
  };

  undoButton.addEventListener("click", async () => {
    undoButton.disabled = true;
    await onUndo(closeToast, todo);
  });

  undoTimer = window.setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      closeToast();
    } else {
      countdown.textContent = `${remaining}s`;
    }
  }, 1000);
}