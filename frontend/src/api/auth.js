import { apiRequest } from "./client.js";

const post = (path, payload) => apiRequest(path, {
  method: "POST",
  ...(payload ? { body: JSON.stringify(payload) } : {}),
});

export const currentUser = async () => (await apiRequest("/auth/me")).data;
export const register = (payload) => post("/auth/register", payload);
export const login = async (payload) => (await post("/auth/login", payload)).data;
export const logout = () => post("/auth/logout");
export const updateProfile = async (payload) => (await apiRequest("/users/me", {
  method: "PATCH", body: JSON.stringify(payload),
})).data;
export const changePassword = (payload) => post("/auth/change-password", payload);
export const forgotPassword = async (payload) => (await post("/auth/forgot-password", payload)).data;
export const resetPassword = (payload) => post("/auth/reset-password", payload);
