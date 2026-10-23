import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, Navigate, Outlet, useNavigate } from 'react-router-dom'
import { api, clearToken, getToken } from '../api.js'
import { ToastCtx } from '../components/ui.jsx'

export default function AdminLayout() {
  const navigate = useNavigate()
  const [me, setMe] = useState('')
  const [toast, setToast] = useState(null)
  const timer = useRef()

  const notify = useCallback((text, type = 'ok') => {
    setToast({ text, type })
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setToast(null), 3200)
  }, [])

  useEffect(() => {
    if (getToken()) api('/auth/me/').then((d) => setMe(d.username)).catch(() => {})
  }, [])

  if (!getToken()) return <Navigate to="/admin/login" replace />

  async function logout() {
    await api('/auth/logout/', { method: 'POST' }).catch(() => {})
    clearToken()
    navigate('/admin/login', { replace: true })
  }

  return (
    <ToastCtx.Provider value={notify}>
      <header className="topbar">
        <div className="topbar-in">
          <span className="brand">
            <span className="dot" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 64 64"><circle cx="32" cy="28" r="11" fill="#F2B230" /><path d="M6 38q13-8 26 0t26 0v14H6z" fill="#0E4568" /></svg>
            </span>
            <span>Gongoni 27<small>Treasurer</small></span>
          </span>
          <nav className="nav" aria-label="Main">
            <NavLink to="/admin" end>Dashboard</NavLink>
            <NavLink to="/admin/members">Members</NavLink>
            <NavLink to="/admin/payments">Payments</NavLink>
          </nav>
          {me && <span className="who">{me}</span>}
          <button className="btn small" onClick={logout}>Sign out</button>
        </div>
      </header>
      <Outlet />
      {toast && <div className={`toast ${toast.type === 'error' ? 'error' : ''}`} role="status">{toast.text}</div>}
    </ToastCtx.Provider>
  )
}
