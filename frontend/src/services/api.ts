import axios from 'axios';
import { User, CaseAnalysis, Precedent, SavedCase, SystemStats, CorpusStatistics } from '../types';

const API_BASE = (import.meta as any).env?.VITE_API_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('jurist_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jurist_token');
      localStorage.removeItem('jurist_user');
      if (window.location.pathname.startsWith('/dashboard')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Auth
  register: async (data: { name: string; email: string; password: string }) => {
    const res = await apiClient.post('/auth/register', data);
    return res.data.data;
  },
  login: async (data: { email: string; password: string }) => {
    const res = await apiClient.post('/auth/login', data);
    return res.data.data;
  },
  logout: async () => {
    const res = await apiClient.post('/auth/logout');
    return res.data;
  },
  getMe: async (): Promise<User> => {
    const res = await apiClient.get('/auth/me');
    return res.data.data;
  },
  updateProfile: async (data: { name?: string }) => {
    const res = await apiClient.patch('/users/me', data);
    return res.data.data;
  },
  updatePassword: async (data: { currentPassword: string; newPassword: string }) => {
    const res = await apiClient.patch('/users/me/password', data);
    return res.data;
  },

  // Cases
  createCase: async (formData: FormData) => {
    const res = await apiClient.post('/cases', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data.data;
  },
  getCases: async (params?: { page?: number; limit?: number; search?: string; category?: string }) => {
    const res = await apiClient.get('/cases', { params });
    return res.data;
  },
  getCaseById: async (id: string) => {
    const res = await apiClient.get(`/cases/${id}`);
    return res.data.data;
  },
  deleteCase: async (id: string) => {
    const res = await apiClient.delete(`/cases/${id}`);
    return res.data;
  },

  // Analysis
  createAnalysis: async (formData: FormData) => {
    const res = await apiClient.post('/analysis', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data.data;
  },
  getAnalyses: async (params?: { page?: number; limit?: number; search?: string; category?: string }) => {
    const res = await apiClient.get('/analysis', { params });
    return res.data;
  },
  getAnalysisById: async (id: string): Promise<CaseAnalysis> => {
    const res = await apiClient.get(`/analysis/${id}`);
    return res.data.data;
  },
  updateAnalysis: async (
    id: string,
    payload: { researchNotes?: string; editedDrafts?: Record<string, string>; caseTitle?: string }
  ): Promise<CaseAnalysis> => {
    const res = await apiClient.patch(`/analysis/${id}`, payload);
    return res.data.data;
  },
  deleteAnalysis: async (id: string) => {
    const res = await apiClient.delete(`/analysis/${id}`);
    return res.data;
  },

  // Precedents
  getPrecedents: async (params?: { page?: number; limit?: number; search?: string; category?: string; court?: string }) => {
    const res = await apiClient.get('/precedents', { params });
    return res.data;
  },
  getPrecedentById: async (id: string): Promise<Precedent> => {
    const res = await apiClient.get(`/precedents/${id}`);
    return res.data.data;
  },

  // Bookmarks / Saved Authorities
  saveCase: async (data: Partial<SavedCase>) => {
    const res = await apiClient.post('/saved-cases', data);
    return res.data.data;
  },
  getSavedCases: async (): Promise<SavedCase[]> => {
    const res = await apiClient.get('/saved-cases');
    return res.data.data;
  },
  updateSavedCaseNotes: async (id: string, notes: string): Promise<SavedCase> => {
    const res = await apiClient.patch(`/saved-cases/${id}`, { notes });
    return res.data.data;
  },
  deleteSavedCase: async (id: string) => {
    const res = await apiClient.delete(`/saved-cases/${id}`);
    return res.data;
  },

  // Admin
  getAdminUsers: async (): Promise<User[]> => {
    const res = await apiClient.get('/admin/users');
    return res.data.data;
  },
  getAdminStats: async (): Promise<SystemStats> => {
    const res = await apiClient.get('/admin/stats');
    return res.data.data;
  },

  // Corpus Statistics
  getCorpusStats: async (): Promise<CorpusStatistics> => {
    const res = await apiClient.get('/precedents/stats');
    return res.data.data;
  },

  // Translation & Multilingual Intelligence
  detectLanguage: async (text: string) => {
    const res = await apiClient.post('/translation/detect-language', { text });
    return res.data.data;
  },
  translateDocument: async (data: {
    text: string;
    sourceLanguage?: 'en' | 'hi' | 'auto';
    targetLanguage: 'en' | 'hi';
    consentExternalService?: boolean;
    preserveCitations?: boolean;
  }) => {
    const res = await apiClient.post('/translation/translate', data);
    return res.data.data;
  },

  // Health
  getHealth: async () => {
    const res = await apiClient.get('/health');
    return res.data;
  }
};
