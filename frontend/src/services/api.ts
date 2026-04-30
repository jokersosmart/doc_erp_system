/**
 * Axios base client with JWT injection, 401 redirect, and request ID propagation.
 * Tokens are stored in memory (NOT localStorage) for XSS protection.
 */
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

let accessToken: string | null = null;

export const setAccessToken = (token: string | null): void => {
  accessToken = token;
};

export const getAccessToken = (): string | null => accessToken;

const api: AxiosInstance = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// Request interceptor — inject JWT + generate request ID
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  config.headers["X-Request-ID"] = crypto.randomUUID();
  return config;
});

// Response interceptor — 401 → clear token and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      setAccessToken(null);
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export default api;
