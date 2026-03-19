import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor - attach auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem("solfoundry-auth-token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

// Response interceptor - handle errors globally
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - clear auth state
      localStorage.removeItem("solfoundry-auth-token");
      localStorage.removeItem("solfoundry-auth-user");
      window.location.href = "/";
    }

    const message =
      error.response?.data?.detail ??
      error.response?.data?.message ??
      error.message ??
      "An unexpected error occurred";

    return Promise.reject(new Error(message));
  },
);

// Typed helpers
export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const res = await apiClient.get<T>(url, { params });
  return res.data;
}

export async function post<T>(url: string, data?: unknown): Promise<T> {
  const res = await apiClient.post<T>(url, data);
  return res.data;
}

export async function put<T>(url: string, data?: unknown): Promise<T> {
  const res = await apiClient.put<T>(url, data);
  return res.data;
}

export async function del<T>(url: string): Promise<T> {
  const res = await apiClient.delete<T>(url);
  return res.data;
}
