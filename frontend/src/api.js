const TOKEN_KEY = 'gn27_token'
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export const getToken = () => {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
export const setToken = (t) => {
  try { localStorage.setItem(TOKEN_KEY, t) } catch { /* private mode: stays signed in for this page only */ }
}
export const clearToken = () => {
  try { localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ }
}

export class ApiError extends Error {
  constructor(status, data) {
    super(data?.detail || 'Request failed')
    this.status = status
    this.data = data
  }
}

export async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (auth && token) headers.Authorization = `Token ${token}`
  let res
  try {
    res = await fetch(`${API_BASE_URL}/api${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined })
  } catch {
    throw new ApiError(0, { detail: 'No connection. Please check your internet and try again.' })
  }
  if (res.status === 204) return null
  let data = null
  try { data = await res.json() } catch { /* empty body */ }
  if (!res.ok) {
    if (res.status === 401 && auth) {
      clearToken()
      if (!location.pathname.startsWith('/admin/login')) location.assign('/admin/login')
    }
    throw new ApiError(res.status, data)
  }
  return data
}

export async function download(path, fallbackName) {
  const res = await fetch(`${API_BASE_URL}/api${path}`, { headers: { Authorization: `Token ${getToken()}` } })
  if (!res.ok) throw new ApiError(res.status, { detail: 'Download failed' })
  const match = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') || '')
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = match ? match[1] : fallbackName
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

/** Turn a DRF error body into { field: 'message' } plus a general message. */
export function fieldErrors(err) {
  const out = { fields: {}, general: '' }
  const data = err?.data
  if (!data || typeof data !== 'object') {
    out.general = err?.message || 'Something went wrong. Please try again.'
    return out
  }
  for (const [key, value] of Object.entries(data)) {
    const text = Array.isArray(value) ? value[0] : String(value)
    if (key === 'detail' || key === 'non_field_errors') out.general = text
    else out.fields[key] = text
  }
  if (!out.general && Object.keys(out.fields).length === 0) out.general = 'Something went wrong. Please try again.'
  return out
}

export const num = (v) => Number(v || 0)
export const kes = (v) => 'KES ' + num(v).toLocaleString('en-KE', { maximumFractionDigits: 2 })
export const plain = (v) => num(v).toLocaleString('en-KE', { maximumFractionDigits: 2 })
export const when = (iso) =>
  new Date(iso).toLocaleString('en-KE', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
export const whenDate = (iso) => new Date(iso).toLocaleDateString('en-KE', { day: 'numeric', month: 'short', year: 'numeric' })
