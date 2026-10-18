// API client — wraps all backend calls.
// The Vite proxy forwards /api/* requests to http://127.0.0.1:8000

import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

export const healthAPI = {
  check: () => api.get('/health'),
};

export const buildingsAPI = {
  list: () => api.get('/buildings'),
  get: (id) => api.get(`/buildings/${id}`),
  create: (data) => api.post('/buildings', data),
  update: (id, data) => api.put(`/buildings/${id}`, data),
  delete: (id) => api.delete(`/buildings/${id}`),
};

export const datasetsAPI = {
  list: () => api.get('/datasets'),
  upload: (dataType, formData) =>
    api.post(`/datasets/upload/${dataType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  delete: (id) => api.delete(`/datasets/${id}`),
};

export const auditAPI = {
  list: () => api.get('/audit'),
  start: (data) => api.post('/audit/run', data),
  get: (runId) => api.get(`/audit/${runId}`),
  getAgents: (runId) => api.get(`/audit/${runId}/agents`),
  getFindings: (runId) => api.get(`/audit/${runId}/findings`),
};

export const analyticsAPI = {
  dashboard: () => api.get('/analytics/dashboard'),
  energy: (params) => api.get('/analytics/energy', { params }),
  water: (params) => api.get('/analytics/water', { params }),
  waste: (params) => api.get('/analytics/waste', { params }),
};

export const actionsAPI = {
  list: (params) => api.get('/actions', { params }),
  get: (id) => api.get(`/actions/${id}`),
  updateStatus: (id, data) => api.patch(`/actions/${id}/status`, data),
  getHistory: (id) => api.get(`/actions/${id}/history`),
};

export const verificationAPI = {
  run: (data) => api.post('/verification/run', data),
  get: (actionId) => api.get(`/verification/${actionId}`),
};

export const reportsAPI = {
  list: () => api.get('/reports'),
  generate: (runId, campusName) =>
    api.post(`/reports/generate/${runId}`, null, { params: { campus_name: campusName } }),
  download: (reportId) => window.open(`/api/reports/download/${reportId}`, '_blank'),
};

export default api;
