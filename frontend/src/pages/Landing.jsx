import { useEffect, useState } from 'react'
import Site, { useConfig } from '../components/Site.jsx'
import { api, fieldErrors, kes } from '../api.js'
import MyProgress from './MyProgress.jsx'

const PHONE_RE = /^(?:\+?254|0)?[17]\d{8}$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const strip = (s) => s.replace(/[\s\-().]/g, '')

// The member stays signed in for this browser tab, including the trip to Paystack and back.
const SESSION_KEY = 'gn27_member'
const KNOWN_KEY = 'gn27_known'
const remember = (login) => {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(login)); localStorage.setItem(KNOWN_KEY, '1') } catch { /* private mode */ }
}
const recall = () => {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY)) } catch { return null }
}
const forget = () => {
  try { sessionStorage.removeItem(SESSION_KEY) } catch { /* ignore */ }
}
const isKnown = () => {
  try { return localStorage.getItem(KNOWN_KEY) === '1' } catch { return false }
}
const fetchProgress = (login) => api('/progress/', { method: 'POST', auth: false, body: login })

function validate(v) {
  const e = {}
  if (v.name.trim().split(/\s+/).filter(Boolean).length < 2) e.name = 'Please enter your full name (at least two names).'
  if (!EMAIL_RE.test(v.email.trim())) e.email = 'Enter a valid email address.'
  if (!PHONE_RE.test(strip(v.phone))) e.phone = 'Enter a valid Kenyan number, for example 0712 345 678.'
  if (!v.duration) e.duration = 'Choose how long you will be in the mission.'
  return e
}

function SignIn({ onIn }) {
  const [v, setV] = useState({ email: '', phone: '' })
  const [errors, setErrors] = useState({})
  const [general, setGeneral] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (key) => (ev) => {
    setV((old) => ({ ...old, [key]: ev.target.value }))
    if (errors[key]) setErrors((old) => ({ ...old, [key]: undefined }))
  }

  async function submit(ev) {
    ev.preventDefault()
    const found = {}
    if (!EMAIL_RE.test(v.email.trim())) found.email = 'Enter the email you registered with.'
    if (!PHONE_RE.test(strip(v.phone))) found.phone = 'Enter the phone number you registered with.'
    setErrors(found)
    setGeneral('')
    if (Object.keys(found).length) return
    setBusy(true)
    const login = { email: v.email.trim(), phone: v.phone }
    try {
      onIn(login, await fetchProgress(login))
    } catch (err) {
      setGeneral(fieldErrors(err).general)
      setBusy(false)
    }
  }

  return (
    <form className="form" onSubmit={submit} noValidate>
      <div className="field">
        <label htmlFor="in-email">Email</label>
        <input id="in-email" type="email" className="input" value={v.email} onChange={set('email')}
          autoComplete="email" placeholder="you@example.com" aria-invalid={!!errors.email} />
        {errors.email && <p className="error">{errors.email}</p>}
      </div>
      <div className="field">
        <label htmlFor="in-phone">Phone number</label>
        <input id="in-phone" type="tel" inputMode="tel" className="input" value={v.phone} onChange={set('phone')}
          autoComplete="tel" placeholder="0712 345 678" aria-invalid={!!errors.phone} />
        {errors.phone && <p className="error">{errors.phone}</p>}
      </div>
      {general && <p className="banner error" role="alert">{general}</p>}
      <button className="btn primary lg" type="submit" disabled={busy}>{busy ? 'Opening…' : 'Open my tracker'}</button>
      <p className="hint center">Please Use the same email and phone number you registered with.</p>
    </form>
  )
}

function Register({ onIn }) {
  const [v, setV] = useState({ name: '', email: '', phone: '', duration: '', website: '' })
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
    const found = validate(v)
    setErrors(found)
    if (Object.keys(found).length) return
    setBusy(true)
    try {
      await api('/register/', { method: 'POST', auth: false, body: v })
      const login = { email: v.email.trim(), phone: v.phone }
      onIn(login, await fetchProgress(login), true)
    } catch (err) {
      const { fields, general: msg } = fieldErrors(err)
      setErrors(fields)
      setGeneral(msg)
      setBusy(false)
    }
  }

  return (
    <form className="form" onSubmit={submit} noValidate>
      <div className="field">
        <label htmlFor="name">Full name</label>
        <input id="name" className="input" value={v.name} onChange={set('name')} autoComplete="name"
          placeholder="Grace Wanjiru Kamau" aria-invalid={!!errors.name} />
        {errors.name && <p className="error">{errors.name}</p>}
      </div>
      <div className="field">
        <label htmlFor="email">Email</label>
        <input id="email" type="email" className="input" value={v.email} onChange={set('email')}
          autoComplete="email" placeholder="you@example.com" aria-invalid={!!errors.email} />
        {errors.email && <p className="error">{errors.email}</p>}
      </div>
      <div className="field">
        <label htmlFor="phone">Phone number</label>
        <input id="phone" type="tel" className="input" value={v.phone} onChange={set('phone')}
          autoComplete="tel" inputMode="tel" placeholder="0712 345 678" aria-invalid={!!errors.phone} />
        {errors.phone && <p className="error">{errors.phone}</p>}
      </div>
      <fieldset className="field">
        <legend className="label">How long will you serve?</legend>
        <div className="choices" aria-invalid={!!errors.duration}>
          {[['1wk', '1 week'], ['2wks', '2 weeks']].map(([value, label]) => (
            <label className="choice" key={value}>
              <input type="radio" name="duration" value={value} checked={v.duration === value} onChange={set('duration')} />
              <span>{label}</span>
            </label>
          ))}
        </div>
        {errors.duration && <p className="error">{errors.duration}</p>}
      </fieldset>

      {/* Hidden trap for spam bots. Real people never see or fill this. */}
      <div style={{ position: 'absolute', left: '-9999px' }} aria-hidden="true">
        <input tabIndex={-1} autoComplete="off" name="website" value={v.website} onChange={set('website')} />
      </div>

      {general && <p className="banner error" role="alert">{general}</p>}
      <button className="btn primary lg" type="submit" disabled={busy}>{busy ? 'Registering…' : 'Register'}</button>
    </form>
  )
}

const tabFromHash = () => (location.hash === '#register' ? 'register' : location.hash === '#track' ? 'track' : null)

function Home({ cfg, onIn }) {
  const [tab, setTab] = useState(() => tabFromHash() || (isKnown() ? 'track' : 'register'))

  useEffect(() => {
    const onHash = () => tabFromHash() && setTab(tabFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  return (
    <section className="home">
      <div className="wrap home-in">
        <div className="home-text">
          <p className="eyebrow">SDA Church · Mount Kenya University</p>
          <h1>Gongoni Mission <span>27</span></h1>
          <p className="lead">25 Apr – 9 May 2027 · Kilifi County</p>
          <p className="intro">Register, give in instalments and track your {kes(cfg.target)} commitment.</p>
        </div>

        <div className="home-card" id={tab}>
          <div className="seg" role="tablist" aria-label="Choose">
            <button role="tab" aria-selected={tab === 'track'} onClick={() => setTab('track')}>Track my progress</button>
            <button role="tab" aria-selected={tab === 'register'} onClick={() => setTab('register')}>Register</button>
          </div>
          <div role="tabpanel">
            {tab === 'track' ? <SignIn onIn={onIn} /> : <Register onIn={onIn} />}
          </div>
        </div>
      </div>
    </section>
  )
}

export default function Landing() {
  const cfg = useConfig()
  const [me, setMe] = useState(null)
  const [restoring, setRestoring] = useState(() => !!recall())
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    const login = recall()
    if (!login) return
    fetchProgress(login).then((data) => setMe({ login, data })).catch(forget).finally(() => setRestoring(false))
  }, [])

  function signIn(login, data, isNew = false) {
    remember(login)
    setMe({ login, data, isNew })
    window.scrollTo({ top: 0 })
  }

  function signOut() {
    forget()
    setMe(null)
    history.replaceState(null, '', '/#track')
    window.scrollTo({ top: 0 })
  }

  async function refresh() {
    setRefreshing(true)
    try {
      const data = await fetchProgress(me.login)
      setMe((m) => ({ ...m, data, isNew: false }))
    } catch { /* keep what we have */ } finally {
      setRefreshing(false)
    }
  }

  if (restoring) return <Site><div className="loading" style={{ minHeight: '60vh' }}><div className="spinner big" /></div></Site>

  if (me) {
    return (
      <Site member={me.data.first_name} onSignOut={signOut}>
        <MyProgress phone={me.login.phone} data={me.data} isNew={me.isNew} onRefresh={refresh} refreshing={refreshing} />
      </Site>
    )
  }

  return (
    <Site>
      <Home cfg={cfg} onIn={signIn} />
    </Site>
  )
}
