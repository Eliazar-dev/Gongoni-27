import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, fieldErrors, kes, phoneLocal, when, whenDay, whenTime } from '../api.js'
import Donut from '../components/Donut.jsx'
import PaymentTimeline from '../components/PaymentTimeline.jsx'
import { BackLink, MemberBadge, Spinner, useLoad, useToast } from '../components/ui.jsx'

export default function MemberDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { data, error, reload } = useLoad(`/members/${id}/`)
  const [form, setForm] = useState(null)
  const [errors, setErrors] = useState({})
  const [general, setGeneral] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (data) {
      setForm({
        name: data.name, email: data.email, phone: data.phone,
        duration: data.duration, target: String(Number(data.target)), is_active: data.is_active,
      })
    }
  }, [data?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  async function save(e) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setGeneral('')
    try {
      await api(`/members/${id}/`, { method: 'PATCH', body: form })
      toast('Member saved')
      reload()
    } catch (err) {
      const r = fieldErrors(err)
      setErrors(r.fields)
      setGeneral(r.general)
    } finally {
      setBusy(false)
    }
  }

  const Err = ({ k }) => (errors[k] ? <p className="error">{errors[k]}</p> : null)

  if (!data) {
    return <div className="page"><BackLink to="/admin/members" />{error ? <p className="banner error">{error}</p> : <Spinner />}</div>
  }

  return (
    <div className="page">
      <BackLink to="/admin/members" />
      <div className="page-head">
        <div>
          <h1>{data.name}</h1>
          <p>{data.code} · registered {when(data.created_at)}</p>
        </div>
        <div className="head-actions">
          <MemberBadge status={data.status} />
          {data.status !== 'completed' && data.is_active && (
            <Link className="btn gold" to={`/admin/request?member=${data.id}`}>Request payment</Link>
          )}
        </div>
      </div>

      <div className="grid detail-cols">
        <div className="panel">
          <h2>Progress</h2>
          <Donut paid={data.paid} balance={data.balance} percent={data.percent} />
          <dl className="info">
            <div><dt>Target</dt><dd>{kes(data.target)}</dd></div>
            <div><dt>Registered</dt><dd>{whenDay(data.created_at)}<span className="dd-time">{whenTime(data.created_at)}</span></dd></div>
            <div><dt>Duration</dt><dd>{data.duration_display}</dd></div>
            <div><dt>Phone</dt><dd>{phoneLocal(data.phone)}</dd></div>
            <div><dt>Email</dt><dd>{data.email}</dd></div>
            <div><dt>Status</dt><dd>{data.is_active ? 'Active' : 'Inactive'}</dd></div>
          </dl>
        </div>

        <div className="panel">
          <h2>Edit details</h2>
          {form && (
            <form className="form" onSubmit={save}>
              <div className="two">
                <div className="field"><label htmlFor="m-name">Full name</label><input id="m-name" className="input" value={form.name} onChange={set('name')} /><Err k="name" /></div>
                <div className="field"><label htmlFor="m-email">Email</label><input id="m-email" className="input" value={form.email} onChange={set('email')} /><Err k="email" /></div>
                <div className="field"><label htmlFor="m-phone">Phone</label><input id="m-phone" className="input" value={form.phone} onChange={set('phone')} /><Err k="phone" /></div>
                <div className="field"><label htmlFor="m-dur">Duration</label>
                  <select id="m-dur" className="input" value={form.duration} onChange={set('duration')}><option value="1wk">1 week</option><option value="2wks">2 weeks</option></select>
                </div>
                <div className="field"><label htmlFor="m-target">Target (KES)</label><input id="m-target" type="number" min="1" className="input" value={form.target} onChange={set('target')} /><Err k="target" /></div>
              </div>
              <label className="check"><input type="checkbox" checked={form.is_active} onChange={set('is_active')} /> Active member (untick to remove from lists and totals)</label>
              {general && <p className="banner error" role="alert">{general}</p>}
              <div className="modal-actions" style={{ marginTop: 4 }}>
                <button className="btn primary" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save changes'}</button>
              </div>
            </form>
          )}
        </div>
      </div>

      <h3 className="subhead">Payment history · {data.payments.length}</h3>
      <div className="panel">
        <PaymentTimeline payments={data.payments} target={data.target} onOpen={(p) => navigate(`/admin/payments/${p.id}`)} />
      </div>
    </div>
  )
}
