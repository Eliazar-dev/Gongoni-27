import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { api, fieldErrors, getToken, setToken } from '../api.js'

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (getToken()) return <Navigate to="/admin" replace />

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const data = await api('/auth/login/', { method: 'POST', auth: false, body: { username, password } })
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
      <form className="login-card" onSubmit={submit}>
        <img src={`${import.meta.env.BASE_URL}sda-logos.png`} alt="" width="190" height="64" />
        <h1>Treasurer sign in</h1>
        <p className="sub">Gongoni Mission 27</p>
        <div className="form" style={{ marginTop: 18 }}>
          <div className="field">
            <label htmlFor="u">Username</label>
            <input id="u" className="input" value={username} onChange={(e) => setUsername(e.target.value)}
              autoComplete="username" autoCapitalize="none" autoFocus />
          </div>
          <div className="field">
            <label htmlFor="p">Password</label>
            <input id="p" type="password" className="input" value={password}
              onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </div>
          {error && <p className="banner error" role="alert">{error}</p>}
          <button className="btn gold" type="submit" disabled={busy || !username || !password}>
            {busy ? <span className="spinner" /> : 'Sign in'}
          </button>
        </div>
      </form>
    </div>
  )
}
