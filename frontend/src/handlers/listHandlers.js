import {
  addMember,
  createList,
  deleteList,
  listLists,
  listMembers,
  removeMember,
} from "../api/lists.js";
import { escapeHtml } from "../utils/task.js";

// Manages the list picker and member panel. The picker's value is the shared
// contract with the task handlers: changing it (and firing "change") makes the
// task view reload for that list. Hiding owner controls here is only for
// clarity; the server enforces every ownership and membership rule.
export function bindListHandlers(elements, user) {
  let active = true;
  let lists = [];

  const selected = () => lists.find((item) => String(item.id) === elements.listSelect.value) || null;

  function message(text, error = false) {
    elements.listMessage.textContent = text;
    elements.listMessage.className = error ? "list-message error" : "list-message";
  }

  function renderOptions(selectedId) {
    elements.listSelect.innerHTML = '<option value="">Personal</option>' + lists.map((item) => `
      <option value="${item.id}">${escapeHtml(item.is_owner ? item.name : `${item.name} (shared by ${item.owner_name})`)}</option>
    `).join("");
    const keep = lists.some((item) => String(item.id) === String(selectedId));
    elements.listSelect.value = keep ? String(selectedId) : "";
  }

  async function refreshLists(selectedId) {
    try {
      const nextLists = await listLists();
      if (!active) return;
      lists = nextLists;
      renderOptions(selectedId);
    } catch (error) {
      if (active) message(error.message, true);
    }
  }

  async function switchTo(listId) {
    await refreshLists(listId);
    if (!active) return;
    elements.listSelect.dispatchEvent(new Event("change"));
  }

  function memberRow(member, viewerOwnsList) {
    const badge = member.is_owner
      ? '<span class="member-role">Owner</span>'
      : viewerOwnsList
        ? `<button class="icon-button danger-text" type="button" data-remove-member="${member.id}" aria-label="Remove ${escapeHtml(member.display_name)}">Remove</button>`
        : "";
    return `<li><span><strong>${escapeHtml(member.display_name)}</strong> <span class="member-email">${escapeHtml(member.email)}</span></span>${badge}</li>`;
  }

  async function showSelectedList() {
    const taskList = selected();
    elements.listTitle.textContent = taskList ? taskList.name : "Personal tasks";
    elements.membersPanel.classList.toggle("hidden", !taskList);
    if (!taskList) return;
    elements.membersOwner.textContent = taskList.is_owner ? "Your collaborative list" : `Shared by ${taskList.owner_name}`;
    elements.membersTitle.textContent = `Members of ${taskList.name}`;
    elements.addMemberForm.classList.toggle("hidden", !taskList.is_owner);
    elements.deleteList.classList.toggle("hidden", !taskList.is_owner);
    elements.leaveList.classList.toggle("hidden", taskList.is_owner);
    elements.memberList.innerHTML = '<li class="member-email">Loading members...</li>';
    try {
      const members = await listMembers(taskList.id);
      // Ignore a slow response for a list the user has already left.
      if (!active || selected()?.id !== taskList.id) return;
      elements.memberList.innerHTML = members.map((member) => memberRow(member, taskList.is_owner)).join("");
    } catch (error) {
      if (!active) return;
      elements.memberList.innerHTML = "";
      message(error.message, true);
    }
  }

  async function submitNewList(event) {
    event.preventDefault();
    const name = elements.newListName.value.trim();
    if (!name) {
      message("Give the list a name.", true);
      elements.newListName.focus();
      return;
    }
    try {
      const created = await createList(name);
      if (!active) return;
      elements.newListName.value = "";
      await switchTo(created.id);
      message(`Created "${created.name}". Add members by email to share it.`);
    } catch (error) {
      if (active) message(error.message, true);
    }
  }

  async function submitMember(event) {
    event.preventDefault();
    const taskList = selected();
    const email = elements.memberEmail.value.trim();
    if (!taskList || !email) return;
    try {
      const member = await addMember(taskList.id, email);
      if (!active) return;
      elements.memberEmail.value = "";
      message(`${member.display_name} can now use this list.`);
      await showSelectedList();
    } catch (error) {
      if (active) message(error.message, true);
    }
  }

  async function removeClicked(event) {
    const button = event.target.closest("[data-remove-member]");
    const taskList = selected();
    if (!button || !taskList || !window.confirm("Remove this member from the list?")) return;
    try {
      await removeMember(taskList.id, button.dataset.removeMember);
      if (!active) return;
      message("Member removed.");
      await showSelectedList();
    } catch (error) {
      if (active) message(error.message, true);
    }
  }

  async function leaveOrDelete(action) {
    const taskList = selected();
    if (!taskList) return;
    const prompt = action === "delete"
      ? `Delete "${taskList.name}" and all of its tasks for every member?`
      : `Leave "${taskList.name}"? You will lose access to its tasks.`;
    if (!window.confirm(prompt)) return;
    try {
      if (action === "delete") await deleteList(taskList.id);
      else await removeMember(taskList.id, user.id);
      if (!active) return;
      await switchTo("");
      message(action === "delete" ? "List deleted." : "You left the list.");
    } catch (error) {
      if (active) message(error.message, true);
    }
  }

  elements.listSelect.addEventListener("change", () => {
    message("");
    showSelectedList();
  });
  elements.newListForm.addEventListener("submit", submitNewList);
  elements.addMemberForm.addEventListener("submit", submitMember);
  elements.memberList.addEventListener("click", removeClicked);
  elements.deleteList.addEventListener("click", () => leaveOrDelete("delete"));
  elements.leaveList.addEventListener("click", () => leaveOrDelete("leave"));

  refreshLists("");
  return () => { active = false; };
}
