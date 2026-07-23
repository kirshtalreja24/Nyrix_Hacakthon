const BASE = '/api';

async function handleResponse(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

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

export async function runQuery(question) {
  const res = await fetch(`${BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  return handleResponse(res);
}

export async function getExecutiveSummary() {
  const res = await fetch(`${BASE}/executive-summary`);
  return handleResponse(res);
}

export async function getSchema() {
  const res = await fetch(`${BASE}/schema`);
  return handleResponse(res);
}
