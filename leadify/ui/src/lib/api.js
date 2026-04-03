const BASE = import.meta.env.VITE_API_URL || '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// ── Queue ──
export const getQueue = () => request('/queue');
export const getQueueStats = () => request('/queue/stats');
export const approveDraft = (id) => request(`/queue/${id}/approve`, { method: 'POST' });
export const skipDraft = (id) => request(`/queue/${id}/skip`, { method: 'POST' });
export const editDraft = (id, data) =>
  request(`/queue/${id}/edit`, { method: 'POST', body: JSON.stringify(data) });

// ── Leads ──
export const getLeads = (status) =>
  request(`/leads${status ? `?status=${status}` : ''}`);
export const createLead = (data) =>
  request('/leads', { method: 'POST', body: JSON.stringify(data) });
export const getLead = (id) => request(`/leads/${id}`);
export const updateLead = (id, data) =>
  request(`/leads/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
export const getLeadHistory = (id) => request(`/leads/${id}/history`);

// ── Auth ──
export const getGmailStatus = () => request('/auth/gmail/status');
export const getGmailAuthUrl = () => request('/auth/gmail');
export const disconnectGmail = () => request('/auth/gmail/disconnect', { method: 'DELETE' });

// ── Agents ──
export const runAgents = () => request('/agents/run', { method: 'POST' });
export const getAgentStatus = () => request('/agents/status');
