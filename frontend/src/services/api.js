// V3.4 API Methods

// RiskScore API
async getRiskStatus() {
  const response = await fetch('/api/v34/risk/status', {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to get risk status');
  return response.json();
},

async calculateRisk(context) {
  const response = await fetch('/api/v34/risk/calculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(context)
  });
  if (!response.ok) throw new Error('Failed to calculate risk');
  return response.json();
},

async resetRiskState() {
  const response = await fetch('/api/v34/risk/reset', {
    method: 'POST',
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to reset risk state');
  return response.json();
},

// Job Queue API
async createQueueTask(taskData) {
  const response = await fetch('/api/v34/queue/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(taskData)
  });
  if (!response.ok) throw new Error('Failed to create queue task');
  return response.json();
},

async getQueueStatus(taskId) {
  const response = await fetch(`/api/v34/queue/${taskId}`, {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to get queue status');
  return response.json();
},

async submitHumanAction(itemId, action, params = null) {
  const response = await fetch(`/api/v34/queue/${itemId}/human-action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ action, params })
  });
  if (!response.ok) throw new Error('Failed to submit human action');
  return response.json();
},

async resumeQueueTask(taskId) {
  const response = await fetch(`/api/v34/queue/${taskId}/resume`, {
    method: 'POST',
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to resume queue task');
  return response.json();
},

// Stealth Config API
async getStealthConfig() {
  const response = await fetch('/api/v34/stealth/config', {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to get stealth config');
  return response.json();
},

async updateStealthConfig(config) {
  const response = await fetch('/api/v34/stealth/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(config)
  });
  if (!response.ok) throw new Error('Failed to update stealth config');
  return response.json();
},