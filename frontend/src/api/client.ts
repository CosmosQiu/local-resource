import axios from "axios";
import type { AxiosInstance, AxiosRequestConfig } from "axios";
import router from "@/router";

const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor — attach access token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — handle 401 → redirect to login
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      router.push("/login");
    }
    return Promise.reject(error);
  }
);

export default client;

// --------------- Auth API ---------------
// --------------- Accounts API ---------------
export interface AIAccount {
  id: number;
  platform: string;
  account_name: string;
  status: string;
  expiration_date: string | null;
  last_verified_at: string | null;
  verification_error: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface AIAccountSecret extends AIAccount {
  username: string | null;
  password: string | null;
  api_key: string | null;
  cookie_data: string | null;
}

export const accountsApi = {
  list: (params?: { platform?: string; status?: string; skip?: number; limit?: number }) =>
    client.get("/accounts/", { params }),
  create: (data: Partial<AIAccountSecret>) =>
    client.post("/accounts/", data),
  get: (id: number) => client.get(`/accounts/${id}`),
  update: (id: number, data: Partial<AIAccountSecret>) =>
    client.put(`/accounts/${id}`, data),
  delete: (id: number) => client.delete(`/accounts/${id}`),
  getSecret: (id: number) => client.get(`/accounts/${id}/secret`),
};

// --------------- Dashboard API ---------------
export interface DashboardSummary {
  total_accounts: number;
  expiring_accounts: number;
  total_gpu_cards: number;
  avg_gpu_utilization: number;
  recent_requests: Array<{
    time: string;
    user: string;
    type: string;
    status: string;
    gpu_count: number;
  }>;
}

export const dashboardApi = {
  summary: () => client.get("/dashboard/summary"),
};

// --------------- Compute API ---------------
export interface GPUInfo {
  id: number;
  resource_id: number;
  gpu_index: number;
  gpu_name: string | null;
  gpu_uuid: string | null;
  total_memory_mb: number;
  used_memory_mb: number;
  utilization_pct: number;
  temperature_c: number | null;
  power_draw_w: number | null;
  recorded_at: string;
}

export interface ComputeResource {
  id: number;
  name: string;
  resource_type: string;
  host_ip: string | null;
  management_port: number;
  total_cpu_cores: number;
  total_memory_gb: number;
  total_disk_gb: number;
  available_cpu_cores: number;
  available_memory_gb: number;
  available_disk_gb: number;
  status: string;
  ansible_group: string | null;
  gpustack_worker_id: string | null;
  last_heartbeat: string | null;
  notes: string | null;
  gpus: GPUInfo[];
  created_at: string;
  updated_at: string;
}

export const computeApi = {
  list: (params?: { resource_type?: string; status?: string; skip?: number; limit?: number }) =>
    client.get("/compute/", { params }),
  create: (data: any) => client.post("/compute/", data),
  get: (id: number) => client.get(`/compute/${id}`),
  update: (id: number, data: any) => client.put(`/compute/${id}`, data),
  delete: (id: number) => client.delete(`/compute/${id}`),
};

// --------------- Requests API ---------------
export interface ContainerRequest {
  id: number;
  user_id: number;
  username: string | null;
  compute_resource_id: number | null;
  request_type: string;
  cpu_cores: number;
  memory_gb: number;
  disk_gb: number;
  gpu_count: number;
  gpu_memory_mb: number | null;
  exposed_ports: any;
  image_name: string | null;
  status: string;
  approved_by: number | null;
  approved_at: string | null;
  container_id: string | null;
  access_url: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export const requestsApi = {
  list: (params?: { status?: string; skip?: number; limit?: number }) =>
    client.get("/compute/requests", { params }),
  create: (data: any) => client.post("/compute/requests", data),
  get: (id: number) => client.get(`/compute/requests/${id}`),
  approve: (id: number, approved: boolean) =>
    client.post(`/compute/requests/${id}/approve`, { approved }),
  stop: (id: number) => client.post(`/compute/requests/${id}/stop`),
};

// --------------- Admin API ---------------
export const adminApi = {
  listUsers: (params?: { skip?: number; limit?: number }) =>
    client.get("/admin/users", { params }),
  assignRoles: (userId: number, roleIds: number[]) =>
    client.put(`/admin/users/${userId}/roles`, roleIds),
  listRoles: () => client.get("/admin/roles"),
  listPermissions: () => client.get("/admin/permissions"),
};

export const authApi = {
  login: (username: string, password: string) =>
    client.post("/auth/login", { username, password }),
  register: (data: {
    username: string;
    email: string;
    password: string;
    display_name?: string;
    department?: string;
  }) => client.post("/auth/register", data),
  refresh: (refreshToken: string) =>
    client.post("/auth/refresh", { refresh_token: refreshToken }),
  me: () => client.get("/auth/me"),
  changePassword: (oldPassword: string, newPassword: string) =>
    client.post("/auth/change-password", {
      old_password: oldPassword,
      new_password: newPassword,
    }),
};
