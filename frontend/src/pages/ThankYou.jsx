import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PublicShell from '../components/PublicShell.jsx'
import { api } from '../api.js'

const FALLBACK = { mission_name: 'Gongoni Mission 27', target: 3500, paybill: '7108831', account_text: 'Mission Commitment' }

function Copy({ text, label }) {
  const [done, setDone] = useState(false)
  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      const t = document.createElement('textarea')
      t.value = text
      document.body.appendChild(t)
      t.select()
      document.execCommand('copy')
      t.remove()
    }
    setDone(true)
    setTimeout(() => setDone(false), 1800)
  }
  return (
    <button type="button" className="btn small" onClick={copy} aria-label={`Copy ${label}`}>
      {done ? 'Copied' : 'Copy'}
    </button>
  )
}

export default function ThankYou() {
  const [cfg, setCfg] = useState(FALLBACK)
  let name = ''
  try { name = sessionStorage.getItem('gn27_name') || '' } catch { /* ignore */ }
  const first = name.split(' ')[0]

  useEffect(() => {
    api('/config/', { auth: false }).then(setCfg).catch(() => {})
  }, [])

  return (
    <PublicShell hero={false}>
      <section className="card thanks" style={{ marginTop: 26 }} aria-live="polite">
        <div className="tick" aria-hidden="true">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#1F8A53" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12.5l4.5 4.5L19 7.5" />
          </svg>
        </div>
        <h2>Thank you{first ? `, ${first}` : ''}!</h2>
        <p>
          You are registered for <b>{cfg.mission_name}</b>. See you soon! As we track your progress, you will be
          notified by email and SMS after every payment.
        </p>

        <div className="paybox">
          <h3>When you are ready to give</h3>
          <div className="payrow">
            <div><small>Paybill number</small><strong>{cfg.paybill}</strong></div>
            <Copy text={cfg.paybill} label="Paybill number" />
          </div>
          <div className="payrow">
            <div><small>Account number</small><strong>{cfg.account_text}</strong></div>
            <Copy text={cfg.account_text} label="account number" />
          </div>
          <div className="payrow">
            <div><small>Your target</small><strong>KES {Number(cfg.target).toLocaleString('en-KE')}</strong></div>
          </div>
        </div>

        <ol className="steps">
          <li data-n="1">Pay from the M-Pesa number you registered, in as many instalments as you like.</li>
          <li data-n="2">Each time, we send you a receipt, the percentage you have paid and your balance.</li>
          <li data-n="3">Keep going until you reach 100%. God bless you!</li>
        </ol>

        <p style={{ marginTop: 18 }}>
          <Link className="btn" to="/">Register another person</Link>
        </p>
      </section>
    </PublicShell>
  )
}
