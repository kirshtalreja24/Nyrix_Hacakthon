const BASE = '/api';

async function handleResponse(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

// ─── Data Sources ───────────────────────────────────────────────────────────

export async function getStatus() {
  const res = await fetch(`${BASE}/sources/status`);
  return handleResponse(res);
}

export async function uploadCSV(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/sources/upload-csv`, { method: 'POST', body: form });
  return handleResponse(res);
}

export async function connectPostgres(config = {}) {
  const res = await fetch(`${BASE}/sources/connect-postgres`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return handleResponse(res);
}

export async function getSourcePreview(sourceType = 'csv') {
  const res = await fetch(`${BASE}/sources/preview?source=${sourceType}`);
  return handleResponse(res);
}

export async function clearCSV() {
  const res = await fetch(`${BASE}/sources/clear-csv`, { method: 'POST' });
  return handleResponse(res);
}

export async function disconnectPostgres() {
  const res = await fetch(`${BASE}/sources/disconnect-postgres`, { method: 'POST' });
  return handleResponse(res);
}

// ─── Query ──────────────────────────────────────────────────────────────────

export async function runQuery(question, sessionId = null) {
  const body = { question };
  if (sessionId) body.session_id = sessionId;
  const res = await fetch(`${BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return handleResponse(res);
}

// ─── Executive Summary ──────────────────────────────────────────────────────

export async function getExecutiveSummary() {
  const res = await fetch(`${BASE}/executive-summary`);
  return handleResponse(res);
}

// ─── Anomalies ──────────────────────────────────────────────────────────────

export async function getAnomalies() {
  const res = await fetch(`${BASE}/anomalies`);
  return handleResponse(res);
}

export async function getSuggestions(sessionId = null) {
  const url = sessionId ? `${BASE}/suggestions?session_id=${sessionId}` : `${BASE}/suggestions`;
  const res = await fetch(url);
  return handleResponse(res);
}

// ─── Reports ────────────────────────────────────────────────────────────────

export async function exportReport(scope, branch = null) {
  const res = await fetch(`${BASE}/reports/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scope, branch }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Export failed');
  }
  return res.blob();
}
