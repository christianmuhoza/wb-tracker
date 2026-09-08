const configuredBase = import.meta.env.VITE_API_URL?.replace(/\/+$/, '');
const API_BASE = configuredBase ? `${configuredBase}/api` : '/api';

let _token = localStorage.getItem('wb-token');

export function setToken(token) {
  _token = token;
  if (token) {
    localStorage.setItem('wb-token', token);
  } else {
    localStorage.removeItem('wb-token');
  }
}

export function getToken() {
  return _token;
}

function authHeaders() {
  const h = {};
  if (_token) h['Authorization'] = `Bearer ${_token}`;
  return h;
}

export function apiUrl(path, params = {}) {
  // Accept legacy /api paths while keeping a single production API origin.
  const normalizedPath = path === '/api' ? '' : path.replace(/^\/api(?=\/|$)/, '');
  const url = new URL(`${API_BASE}${normalizedPath}`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== '' && v !== null && v !== undefined && v !== false) url.searchParams.append(k, v);
  });
  return url.toString();
}

export async function apiGet(path, params = {}) {
  const res = await fetch(apiUrl(path, params), { headers: authHeaders() });
  if (res.status === 401) {
    setToken(null);
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`);
  return res.json();
}

export async function apiPost(path, body = null, params = {}) {
  const headers = { ...authHeaders() };
  const opts = { method: 'POST', headers };
  if (body) {
    headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(apiUrl(path, params), opts);
  if (res.status === 401) {
    setToken(null);
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`);
  return res.json();
}

export async function apiPut(path, body = null) {
  const opts = {
    method: 'PUT',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(apiUrl(path), opts);
  if (res.status === 401) {
    setToken(null);
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`);
  return res.json();
}

export async function apiDelete(path) {
  const res = await fetch(apiUrl(path), {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (res.status === 401) {
    setToken(null);
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`);
  return res.json();
}
