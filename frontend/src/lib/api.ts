import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // If 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = useAuthStore.getState().refreshToken;
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        // Try to refresh the token
        const response = await axios.post(`${API_URL}/api/auth/refresh/`, {
          refresh: refreshToken,
        });

        const { access } = response.data;
        useAuthStore.getState().setTokens(access, refreshToken);

        // Retry the original request
        originalRequest.headers.Authorization = `Bearer ${access}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout user
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// API helper functions
export const authApi = {
  register: (data: { email: string; password: string; password_confirm: string }) =>
    api.post('/auth/register/', data),

  login: (data: { email: string; password: string }) =>
    api.post('/auth/login/', data),

  refresh: (refreshToken: string) =>
    api.post('/auth/refresh/', { refresh: refreshToken }),

  me: () => api.get('/auth/me/'),

  updateProfile: (data: { first_name?: string; last_name?: string; company_name?: string }) =>
    api.patch('/auth/profile/', data),

  updateApiKeys: (data: { anthropic_api_key?: string; openai_api_key?: string }) =>
    api.put('/auth/api-keys/', data),

  changePassword: (data: { old_password: string; new_password: string; new_password_confirm: string }) =>
    api.post('/auth/change-password/', data),

  getSkillApiKeys: () => api.get('/auth/skill-api-keys/'),

  updateSkillApiKeys: (keys: Record<string, string | null>) => {
    console.log('API updateSkillApiKeys called with:', keys);
    console.log('Request payload:', { keys });
    return api.put('/auth/skill-api-keys/', { keys });
  },
};

export const workspaceApi = {
  list: () => api.get('/workspaces/'),

  get: (id: number) => api.get(`/workspaces/${id}/`),

  create: (data: { name: string; description?: string; selected_model?: string }) =>
    api.post('/workspaces/', data),

  update: (id: number, data: Partial<{ name: string; description: string; selected_model: string }>) =>
    api.patch(`/workspaces/${id}/`, data),

  delete: (id: number) => api.delete(`/workspaces/${id}/`),

  deploy: (id: number) => api.post(`/workspaces/${id}/deploy/`),

  stop: (id: number) => api.post(`/workspaces/${id}/stop/`),

  status: (id: number) => api.get(`/workspaces/${id}/status_check/`),

  logs: (id: number, lines = 100) => api.get(`/workspaces/${id}/logs/?lines=${lines}`),

  // Agent configuration
  getAgentConfig: (id: number) => api.get(`/workspaces/${id}/agent_config/`),

  updateAgentConfig: (id: number, data: {
    system_prompt?: string;
    agent_name?: string;
    agent_description?: string;
    welcome_message?: string;
    temperature?: number;
    selected_model?: string;
    max_tokens?: number;
  }) => api.patch(`/workspaces/${id}/agent_config/`, data),

  testMessage: (id: number, message: string) =>
    api.post(`/workspaces/${id}/test_message/`, { message }),

  skillStatus: (id: number) => api.get(`/workspaces/${id}/skill_status/`),

  uninstallSkill: (workspaceId: number, installedSkillId: number) =>
    api.delete(`/workspaces/${workspaceId}/skills/${installedSkillId}/`),
};

export const knowledgeApi = {
  list: (workspaceId: number) =>
    api.get(`/workspaces/${workspaceId}/knowledge/`),

  get: (workspaceId: number, id: number) =>
    api.get(`/workspaces/${workspaceId}/knowledge/${id}/`),

  create: (workspaceId: number, data: {
    name: string;
    resource_type: string;
    content?: string;
    source_url?: string;
    question?: string;
    answer?: string;
  }) => api.post(`/workspaces/${workspaceId}/knowledge/`, data),

  update: (workspaceId: number, id: number, data: object) =>
    api.patch(`/workspaces/${workspaceId}/knowledge/${id}/`, data),

  delete: (workspaceId: number, id: number) =>
    api.delete(`/workspaces/${workspaceId}/knowledge/${id}/`),
};

export const agentTaskApi = {
  list: (workspaceId: number) =>
    api.get(`/workspaces/${workspaceId}/tasks/`),

  get: (workspaceId: number, taskId: number) =>
    api.get(`/workspaces/${workspaceId}/tasks/${taskId}/`),

  create: (workspaceId: number, data: {
    name: string;
    instructions: string;
    schedule?: string;
    enabled_tools?: string[];
  }) => api.post(`/workspaces/${workspaceId}/tasks/`, data),

  update: (workspaceId: number, taskId: number, data: object) =>
    api.patch(`/workspaces/${workspaceId}/tasks/${taskId}/`, data),

  delete: (workspaceId: number, taskId: number) =>
    api.delete(`/workspaces/${workspaceId}/tasks/${taskId}/`),

  run: (workspaceId: number, taskId: number) =>
    api.post(`/workspaces/${workspaceId}/tasks/${taskId}/run/`),

  pause: (workspaceId: number, taskId: number) =>
    api.post(`/workspaces/${workspaceId}/tasks/${taskId}/pause/`),

  resume: (workspaceId: number, taskId: number) =>
    api.post(`/workspaces/${workspaceId}/tasks/${taskId}/resume/`),

  getResults: (workspaceId: number, taskId: number) =>
    api.get(`/workspaces/${workspaceId}/tasks/${taskId}/results/`),

  getRuns: (workspaceId: number, taskId: number) =>
    api.get(`/workspaces/${workspaceId}/tasks/${taskId}/runs/`),
};

export const channelApi = {
  list: (workspaceId: number) =>
    api.get(`/workspaces/${workspaceId}/channels/`),

  create: (workspaceId: number, data: { channel_type: string; name: string; credentials?: object }) =>
    api.post(`/workspaces/${workspaceId}/channels/`, data),

  update: (workspaceId: number, channelId: number, data: object) =>
    api.patch(`/workspaces/${workspaceId}/channels/${channelId}/`, data),

  delete: (workspaceId: number, channelId: number) =>
    api.delete(`/workspaces/${workspaceId}/channels/${channelId}/`),

  setupTelegram: (workspaceId: number, botToken: string) =>
    api.post(`/workspaces/${workspaceId}/channels/telegram/setup/`, { bot_token: botToken }),

  initiateSlackOAuth: (workspaceId: number) =>
    api.post(`/workspaces/${workspaceId}/channels/slack/oauth/`),
};

export const skillApi = {
  list: (params?: { search?: string; category?: string }) =>
    api.get('/skills/', { params }),

  get: (slug: string) => api.get(`/skills/${slug}/`),

  featured: () => api.get('/skills/featured/'),

  categories: () => api.get('/skills/categories/'),

  install: (slug: string, workspaceId: number, config?: object) =>
    api.post(`/skills/${slug}/install/`, { workspace_id: workspaceId, config }),

  rate: (slug: string, rating: number, review?: string) =>
    api.post(`/skills/${slug}/ratings/`, { rating, review }),
};

export const billingApi = {
  plans: () => api.get('/billing/plans/'),

  subscription: () => api.get('/billing/subscription/'),

  createCheckout: (data: { plan_id: number; interval: string; success_url: string; cancel_url: string }) =>
    api.post('/billing/checkout/', data),

  createPortal: (returnUrl: string) =>
    api.post('/billing/portal/', { return_url: returnUrl }),

  cancel: () => api.post('/billing/cancel/'),

  usage: () => api.get('/billing/usage/'),

  invoices: () => api.get('/billing/invoices/'),
};

// Job Auto-Apply API
export const jobApplyApi = {
  // Dashboard
  dashboard: () => api.get('/jobapply/dashboard/'),

  // Resumes
  listResumes: () => api.get('/jobapply/resumes/'),
  getResume: (id: number) => api.get(`/jobapply/resumes/${id}/`),
  uploadResume: (formData: FormData) =>
    api.post('/jobapply/resumes/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  deleteResume: (id: number) => api.delete(`/jobapply/resumes/${id}/`),
  parseResume: (id: number) => api.post(`/jobapply/resumes/${id}/parse/`),
  setPrimaryResume: (id: number) => api.post(`/jobapply/resumes/${id}/set_primary/`),

  // Preferences
  getPreferences: () => api.get('/jobapply/preferences/'),
  updatePreferences: (data: object) => api.patch('/jobapply/preferences/', data),

  // Job Listings
  listListings: (params?: { min_score?: number; source?: string; hours?: number; page_size?: number }) =>
    api.get('/jobapply/listings/', { params }),
  listStartupListings: (params?: { min_score?: number; hours?: number; page_size?: number }) =>
    api.get('/jobapply/listings/', { params: { ...params, source: 'hn_hiring,remoteok' } }),
  getListing: (id: number) => api.get(`/jobapply/listings/${id}/`),
  applyToListing: (id: number) => api.post(`/jobapply/listings/${id}/apply/`),
  dismissListing: (id: number) => api.post(`/jobapply/listings/${id}/dismiss/`),
  searchNow: () => api.post('/jobapply/listings/search_now/'),
  searchStartups: () => api.post('/jobapply/listings/search_startups/'),

  // Applications
  listApplications: (params?: { status?: string }) =>
    api.get('/jobapply/applications/', { params }),
  getApplication: (id: number) => api.get(`/jobapply/applications/${id}/`),
  updateApplication: (id: number, data: object) =>
    api.patch(`/jobapply/applications/${id}/`, data),
  regenerateCover: (id: number) => api.post(`/jobapply/applications/${id}/regenerate_cover/`),
  retryApplication: (id: number) => api.post(`/jobapply/applications/${id}/retry/`),
};

export default api;
