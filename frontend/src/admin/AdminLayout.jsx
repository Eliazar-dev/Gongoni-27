import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, Navigate, Outlet, useNavigate } from 'react-router-dom'
import { api, clearToken, getToken } from '../api.js'
import { ToastCtx } from '../components/ui.jsx'

const icon = {
  dashboard: <path d="M3 13h8V3H3zm10 8h8V11h-8zM3 21h8v-6H3zm10-18v6h8V3z" />,
  members: <path d="M16 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm-8 0a3 3 0 1 0-3-3 3 3 0 0 0 3 3zm0 2c-2.7 0-8 1.3-8 4v3h8v-3c0-1.1.5-2.1 1.4-3A11 11 0 0 0 8 13zm8 0c-2.7 0-8 1.3-8 4v3h16v-3c0-2.7-5.3-4-8-4z" />,
  payments: <path d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 14H4v-6h16zm0-10H4V6h16z" />,
  logout: <path d="M10 17l1.4-1.4-2.6-2.6H20v-2H8.8l2.6-2.6L10 7l-5 5zM4 5h8V3H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8v-2H4z" />,
}
const Icon = ({ name }) => <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">{icon[name]}</svg>

const links = [
  { to: '/admin', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/admin/members', label: 'Members', icon: 'members' },
  { to: '/admin/payments', label: 'Payments', icon: 'payments' },
]

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
      <div className="shell">
        <aside className="side">
          <span className="brand">
            <span className="dot" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 64 64"><circle cx="32" cy="28" r="11" fill="#F2B230" /><path d="M6 38q13-8 26 0t26 0v14H6z" fill="#0E4568" /></svg>
            </span>
            <span>Gongoni 27<small>Admin portal</small></span>
          </span>
          <nav className="side-nav" aria-label="Main">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end}><Icon name={l.icon} /><span>{l.label}</span></NavLink>
            ))}
          </nav>
          <div className="side-foot">
            {me && (
              <div className="me">
                <span className="avatar" aria-hidden="true">{me.slice(0, 1).toUpperCase()}</span>
                <span><b>{me}</b><small>Administrator</small></span>
              </div>
            )}
            <button className="side-out" onClick={logout}><Icon name="logout" /><span>Sign out</span></button>
          </div>
        </aside>
        <main className="main-area">
          <Outlet />
        </main>
      </div>
      {toast && <div className={`toast ${toast.type === 'error' ? 'error' : ''}`} role="status">{toast.text}</div>}
    </ToastCtx.Provider>
  )
}
