import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
    }
    return Promise.reject(error)
  }
)

// ========== V3.4 API Methods ==========

// RiskScore API
api.getRiskStatus = async function() {
  const response = await fetch(`${this.defaults.baseURL}/api/v34/risk/status`, {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to get risk status');
  return response.json();
};

api.calculateRisk = async function(context) {
  const response = await fetch(`${this.defaults.baseURL}/api/v34/risk/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(context)
  });
  if (!response.ok) throw new Error('Failed to calculate risk');
  return response.json();
};

api.resetRiskState = async function() {
  const response = await fetch(`${this.defaults.baseURL}/api/v34/risk/reset`, {
    method: 'POST',
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to reset risk state');
  return response.json();
};

// Job Queue API
api.createQueueTask = async function(taskData) {
  const response = await fetch(`${this.defaults.baseURL}/api/v34/queue/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(taskData)
  });
  if (!response.ok) throw new Error('Failed to create queue task');
  return response.json();
};

api.getQueueStatus = async function(taskId) {
  const response = await fetch(`${this.defaults.baseURL}/api/v34/queue/${taskId}`, {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to get queue status');
  return response.json();
};

api.submitHumanAction = async function(itemId, action, params = null) {
  const response = await fetch(`${this.defaults.baseURL}/api/v34/queue/${itemId}/human-action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ action, params })
  });
  if (!response.ok) throw new Error('Failed to submit human action');
  return response.json();
};

api.resumeQueueTask = async function(taskId) {
  const response = await fetch(`${this.defaults.baseURL}/api/v34/queue/${taskId}/resume`, {
    method: 'POST',
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to resume queue task');
  return response.json();
};

// Stealth Config API
api.getStealthConfig = async function() {
  const response = await fetch(`${this.defaults.baseURL}/api/v34/stealth/config`, {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to get stealth config');
  return response.json();
};

api.updateStealthConfig = async function(config) {
  const response = await fetch(`${this.defaults.baseURL}/api/v34/stealth/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(config)
  });
  if (!response.ok) throw new Error('Failed to update stealth config');
  return response.json();
};

export default api
