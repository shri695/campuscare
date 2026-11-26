const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'

export async function api(path, options = {}) {
  const token = localStorage.getItem('mediconnect_token')
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`)
  return payload
}

export async function login(email, password) {
  return api('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
}
export async function register(full_name, email, password, consent) {
  return api('/api/auth/register', { method: 'POST', body: JSON.stringify({ full_name, email, password, consent }) })
}
