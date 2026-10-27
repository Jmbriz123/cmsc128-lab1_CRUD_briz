import { apiRequest } from "./client.js";

const send = (path, method, payload) => apiRequest(path, {
  method,
  ...(payload ? { body: JSON.stringify(payload) } : {}),
});

export const listLists = async () => (await apiRequest("/lists")).data;
export const createList = async (name) => (await send("/lists", "POST", { name })).data;
export const deleteList = (listId) => send(`/lists/${listId}`, "DELETE");
export const listMembers = async (listId) => (await apiRequest(`/lists/${listId}/members`)).data;
export const addMember = async (listId, email) => (await send(`/lists/${listId}/members`, "POST", { email })).data;
export const removeMember = (listId, memberId) => send(`/lists/${listId}/members/${memberId}`, "DELETE");
