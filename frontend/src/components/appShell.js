export function mountApp() {
  const app = document.querySelector("#app");
  // overwritethe empty div in HTML with actual HTML elements to generate UI
  app.innerHTML = `
    <div class="shell">
      <header class="topbar">
        <a class="brand" href="#/tasks" aria-label="Daymark home">
          <span class="brand-mark">D</span>
          <span>Daymark</span>
        </a>
        <nav class="nav" aria-label="Primary navigation">
          <a class="nav-link active" href="#/tasks">My tasks</a>
          <span class="task-count" id="task-count">0 tasks</span>
          <a href="#/profile">Profile</a>
          <button class="button button-quiet" type="button" data-logout>Log Out</button>
        </nav>
        <div class="status-dot"><span></span>Workspace online</div>
      </header>

      <main id="tasks" class="workspace">
        <div id="account-feedback" role="status" aria-live="polite"></div>
        <section class="intro">
          <div>
            <p class="eyebrow">Academic task manager</p>
            <h1>Make room for the work that matters.</h1>
            <p class="lede">Capture the next thing, give it a place, and keep your week moving.</p>
          </div>
          <button class="button button-primary" id="new-task-button" type="button">+ New task</button>
        </section>

        <section class="list-bar" aria-label="To-do lists">
          <div>
            <label for="list-select">Current list</label>
            <select id="list-select"><option value="">Personal</option></select>
          </div>
          <form id="new-list-form" novalidate>
            <label for="new-list-name">New collaborative list</label>
            <div class="inline-controls">
              <input id="new-list-name" maxlength="100" placeholder="e.g. Thesis group" />
              <button class="button button-secondary" type="submit">Create list</button>
            </div>
          </form>
          <p class="list-message" id="list-message" role="status" aria-live="polite"></p>
        </section>

        <section class="members-panel hidden" id="members-panel" aria-labelledby="members-title">
          <div>
            <p class="eyebrow" id="members-owner"></p>
            <h2 id="members-title">Members</h2>
          </div>
          <ul class="member-list" id="member-list"></ul>
          <form id="add-member-form" class="hidden" novalidate>
            <label for="member-email">Add a member by email</label>
            <div class="inline-controls">
              <input id="member-email" type="email" maxlength="254" placeholder="classmate@example.com" />
              <button class="button button-secondary" type="submit">Add member</button>
            </div>
          </form>
          <div class="member-actions">
            <button class="button button-danger hidden" id="delete-list" type="button">Delete list</button>
            <button class="button button-quiet hidden" id="leave-list" type="button">Leave list</button>
          </div>
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
                <h2 id="list-title">Personal tasks</h2>
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

  // collection of references to important DOM elements
  return {
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
    listSelect: document.querySelector("#list-select"),
    listTitle: document.querySelector("#list-title"),
    newListForm: document.querySelector("#new-list-form"),
    newListName: document.querySelector("#new-list-name"),
    listMessage: document.querySelector("#list-message"),
    membersPanel: document.querySelector("#members-panel"),
    membersOwner: document.querySelector("#members-owner"),
    membersTitle: document.querySelector("#members-title"),
    memberList: document.querySelector("#member-list"),
    addMemberForm: document.querySelector("#add-member-form"),
    memberEmail: document.querySelector("#member-email"),
    deleteList: document.querySelector("#delete-list"),
    leaveList: document.querySelector("#leave-list"),
  };
}