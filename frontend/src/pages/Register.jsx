import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PublicShell from '../components/PublicShell.jsx'
import { api, fieldErrors } from '../api.js'

const PHONE_RE = /^(?:\+?254|0)?[17]\d{8}$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const strip = (s) => s.replace(/[\s\-().]/g, '')

function validate(v, same) {
  const e = {}
  if (v.name.trim().split(/\s+/).filter(Boolean).length < 2) e.name = 'Please enter your full name (at least two names).'
  if (!EMAIL_RE.test(v.email.trim())) e.email = 'Enter a valid email address.'
  if (!PHONE_RE.test(strip(v.phone))) e.phone = 'Enter a valid Kenyan number, for example 0712 345 678.'
  if (!v.duration) e.duration = 'Choose how long you will be in the mission.'
  if (!same && !PHONE_RE.test(strip(v.mpesa_phone))) e.mpesa_phone = 'Enter the M-Pesa number you pay from.'
  return e
}

export default function Register() {
  const navigate = useNavigate()
  const [v, setV] = useState({ name: '', email: '', phone: '', duration: '', mpesa_phone: '', website: '' })
  const [same, setSame] = useState(true)
  const [errors, setErrors] = useState({})
  const [general, setGeneral] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (key) => (ev) => {
    setV((old) => ({ ...old, [key]: ev.target.value }))
    if (errors[key]) setErrors((old) => ({ ...old, [key]: undefined }))
  }

  async function submit(ev) {
    ev.preventDefault()
    if (busy) return
    setGeneral('')
    const found = validate(v, same)
    setErrors(found)
    const first = Object.keys(found)[0]
    if (first) {
      document.getElementById(first === 'duration' ? 'duration-1wk' : first)?.focus()
      return
    }
    setBusy(true)
    try {
      await api('/register/', {
        method: 'POST',
        auth: false,
        body: { ...v, mpesa_phone: same ? v.phone : v.mpesa_phone },
      })
      try { sessionStorage.setItem('gn27_name', v.name.trim()) } catch { /* ignore */ }
      navigate('/thank-you')
    } catch (err) {
      const { fields, general: msg } = fieldErrors(err)
      setErrors(fields)
      setGeneral(msg)
      const firstField = Object.keys(fields)[0]
      if (firstField) document.getElementById(firstField === 'duration' ? 'duration-1wk' : firstField)?.focus()
    } finally {
      setBusy(false)
    }
  }

  return (
    <PublicShell>
      <section className="verse" aria-label="Mission encouragement">
        <q>Go ye into all the world, and preach the gospel to every creature.</q>
        <cite>MARK 16:15</cite>
        <p>
          Thank you for saying yes to the mission. Every prayer, every shilling and every step carries the gospel to
          Kilifi. Register below and we will walk with you all the way.
        </p>
      </section>

      <section className="card" aria-labelledby="reg-title">
        <h2 id="reg-title">Register for the mission</h2>
        <p className="sub">It takes about one minute.</p>

        <form className="form" onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="name">Full name</label>
            <input id="name" className="input" value={v.name} onChange={set('name')} autoComplete="name"
              placeholder="e.g. Grace Wanjiru Kamau" aria-invalid={!!errors.name} aria-describedby="name-err" />
            {errors.name && <p className="error" id="name-err">{errors.name}</p>}
          </div>

          <div className="field">
            <label htmlFor="email">Email address</label>
            <input id="email" type="email" className="input" value={v.email} onChange={set('email')}
              autoComplete="email" inputMode="email" placeholder="you@example.com" aria-invalid={!!errors.email}
              aria-describedby="email-err" />
            {errors.email && <p className="error" id="email-err">{errors.email}</p>}
          </div>

          <div className="field">
            <label htmlFor="phone">Phone number</label>
            <input id="phone" type="tel" className="input" value={v.phone} onChange={set('phone')}
              autoComplete="tel" inputMode="tel" placeholder="0712 345 678" aria-invalid={!!errors.phone}
              aria-describedby="phone-err" />
            {errors.phone && <p className="error" id="phone-err">{errors.phone}</p>}
          </div>

          <fieldset className="field" style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
            <legend className="label">Duration you will be in the mission</legend>
            <div className="choices" aria-invalid={!!errors.duration}>
              <label className="choice">
                <input id="duration-1wk" type="radio" name="duration" value="1wk" checked={v.duration === '1wk'} onChange={set('duration')} />
                <span>1 week</span>
              </label>
              <label className="choice">
                <input id="duration-2wks" type="radio" name="duration" value="2wks" checked={v.duration === '2wks'} onChange={set('duration')} />
                <span>2 weeks</span>
              </label>
            </div>
            {errors.duration && <p className="error">{errors.duration}</p>}
          </fieldset>

          <div className="field">
            <label htmlFor="mpesa_phone">M-Pesa number</label>
            <input id="mpesa_phone" type="tel" className="input" inputMode="tel" placeholder="0712 345 678"
              value={same ? v.phone : v.mpesa_phone} onChange={set('mpesa_phone')} disabled={same}
              aria-invalid={!!errors.mpesa_phone} aria-describedby="mpesa-err" />
            <label className="check">
              <input
                type="checkbox"
                checked={same}
                onChange={(e) => {
                  setSame(e.target.checked)
                  if (!e.target.checked && !v.mpesa_phone) setV((old) => ({ ...old, mpesa_phone: old.phone }))
                }}
              />
              Same as my phone number
            </label>
            {errors.mpesa_phone && <p className="error" id="mpesa-err">{errors.mpesa_phone}</p>}
            <p className="hint">The number you will pay from. It helps us match your payments to you.</p>
          </div>

          {/* Hidden trap for spam bots. Real people never see or fill this. */}
          <div style={{ position: 'absolute', left: '-9999px' }} aria-hidden="true">
            <input tabIndex={-1} autoComplete="off" name="website" value={v.website} onChange={set('website')} />
          </div>

          {general && <p className="banner error" role="alert">{general}</p>}

          <button className="btn gold" type="submit" disabled={busy}>
            {busy ? <><span className="spinner" /> Registering…</> : 'Register me'}
          </button>
          <p className="fineprint">
            By registering you agree to receive payment receipts and progress updates by SMS and email from the church.
          </p>
        </form>
      </section>
    </PublicShell>
  )
}
