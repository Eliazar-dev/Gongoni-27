import { useEffect, useState } from 'react'
import { api, kes, num } from '../api.js'

const LINKS = [['register', 'Register', 'Register'], ['track', 'Track my progress', 'My tracker']]

/** Public page frame: sticky navbar and a quiet footer. */
export default function Site({ children, member, onSignOut }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="site">
      <header className="nav-bar">
        <div className="wrap nav-in">
          <a className="logo" href="/#top" onClick={() => setOpen(false)}>Gongoni<span>27</span></a>
          {member ? (
            <div className="me-nav">
              <span className="me-avatar" aria-hidden="true">{member.slice(0, 1)}</span>
              <span className="me-name">{member}</span>
              <button className="btn small" onClick={onSignOut}>Sign out</button>
            </div>
          ) : (
            <>
              <button className="menu" aria-label="Menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
                <i /><i />
              </button>
              <nav className={`links ${open ? 'open' : ''}`} aria-label="Main">
                {LINKS.map(([id, label, short]) => (
                  <a key={id} href={`/#${id}`} onClick={() => setOpen(false)} className={id === 'track' ? 'cta' : ''}>
                    <span className="long">{label}</span><span className="short">{short}</span>
                  </a>
                ))}
              </nav>
            </>
          )}
        </div>
      </header>
      <main id="top">{children}</main>
      <footer className="foot">
        <div className="wrap foot-in">
          <span>Seventh-day Adventist Church · Mount Kenya University</span>
          <span>Kambire Dhunia · Go tell the world</span>
        </div>
      </footer>
    </div>
  )
}

export function useConfig() {
  const [cfg, setCfg] = useState({ mission_name: 'Gongoni Mission 27', target: 3500 })
  useEffect(() => { api('/config/', { auth: false }).then(setCfg).catch(() => {}) }, [])
  return cfg
}

export function ProgressBar({ percent }) {
  return (
    <div className="bar" role="progressbar" aria-valuenow={percent} aria-valuemin="0" aria-valuemax="100">
      <i style={{ width: `${Math.max(percent, 1)}%` }} />
    </div>
  )
}

/** Amount input that sends the member to Paystack checkout. */
export function PayForm({ phone, balance }) {
  const [amount, setAmount] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const quick = [500, 1000, num(balance)].filter((v, i, all) => v >= 10 && all.indexOf(v) === i)

  async function pay(e) {
    e.preventDefault()
    if (num(amount) < 10) return setError('Enter at least KES 10.')
    setBusy(true)
    setError('')
    try {
      const { authorization_url } = await api('/pay/', { method: 'POST', auth: false, body: { phone, amount } })
      window.location.assign(authorization_url)
    } catch (err) {
      setError(err.data?.amount?.[0] || err.data?.phone?.[0] || err.message)
      setBusy(false)
    }
  }

  return (
    <form className="pay" onSubmit={pay} noValidate>
      <label htmlFor="pay-amount">Amount to give (KES)</label>
      <div className="pay-row">
        <input id="pay-amount" className="input" type="number" inputMode="numeric" min="10" placeholder="e.g. 1000"
          value={amount} onChange={(e) => setAmount(e.target.value)} />
        <button className="btn primary" type="submit" disabled={busy}>{busy ? 'Opening…' : 'Pay now'}</button>
      </div>
      {quick.length > 0 && (
        <div className="chips">
          {quick.map((v) => (
            <button type="button" key={v} className="chip" onClick={() => setAmount(String(v))}>
              {v === num(balance) ? `Full balance · ${kes(v)}` : kes(v)}
            </button>
          ))}
        </div>
      )}
      {error && <p className="error">{error}</p>}
      <p className="hint">Secure checkout by Paystack. Pay with M-Pesa or card.</p>
    </form>
  )
}
