import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api, fieldErrors, getToken, setToken } from '../api.js'

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (getToken()) return <Navigate to="/admin" replace />

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const data = await api('/auth/login/', { method: 'POST', auth: false, body: { username: username.trim(), password } })
      setToken(data.token)
      navigate('/admin', { replace: true })
    } catch (err) {
      setError(fieldErrors(err).general)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <aside className="login-art" aria-hidden="true">
        <img src={`${import.meta.env.BASE_URL}sda-logos.png`} alt="" width="190" height="64" />
        <div>
          <h2>Gongoni Mission 27</h2>
          <p>Track every member's giving, confirm payments and follow the mission's progress, all in one place.</p>
        </div>
        <ul>
          <li>Live totals and daily giving</li>
          <li>Member progress and balances</li>
          <li>Paystack payments with emailed receipts</li>
        </ul>
      </aside>

      <form className="login-card" onSubmit={submit}>
        <img className="login-logo" src={`${import.meta.env.BASE_URL}sda-logos.png`} alt="" width="190" height="64" />
        <span className="eyebrow">Admin portal</span>
        <h1>Welcome back</h1>
        <p className="sub">Sign in to manage Gongoni Mission 27.</p>
        <div className="form" style={{ marginTop: 22 }}>
          <div className="field">
            <label htmlFor="u">Username</label>
            <input id="u" className="input" value={username} onChange={(e) => setUsername(e.target.value)}
              autoComplete="username" autoCapitalize="none" spellCheck="false" autoFocus />
          </div>
          <div className="field">
            <label htmlFor="p">Password</label>
            <div className="pw">
              <input id="p" type={show ? 'text' : 'password'} className="input" value={password}
                onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
              <button type="button" className="pw-toggle" onClick={() => setShow((s) => !s)}
                aria-label={show ? 'Hide password' : 'Show password'}>{show ? 'Hide' : 'Show'}</button>
            </div>
          </div>
          {error && <p className="banner error" role="alert">{error}</p>}
          <button className="btn gold" type="submit" disabled={busy || !username || !password}>
            {busy ? <span className="spinner" /> : 'Sign in'}
          </button>
        </div>
        <p className="login-back"><Link to="/">← Back to the mission page</Link></p>
      </form>
    </div>
  )
}
