import { useEffect, useState } from 'react'
import { api, download, fieldErrors, kes, plain, when, whenDate } from '../api.js'
import { Empty, MemberBadge, MiniProgress, Modal, PaymentBadge, Pager, Spinner, useDebounce, useLoad, useToast } from '../components/ui.jsx'

function MemberModal({ id, onClose, onChanged }) {
  const toast = useToast()
  const { data, reload } = useLoad(`/members/${id}/`)
  const [form, setForm] = useState(null)
  const [errors, setErrors] = useState({})
  const [general, setGeneral] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (data) {
      setForm({
        name: data.name, email: data.email, phone: data.phone, mpesa_phone: data.mpesa_phone,
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
      onChanged()
    } catch (err) {
      const r = fieldErrors(err)
      setErrors(r.fields)
      setGeneral(r.general)
    } finally {
      setBusy(false)
    }
  }

  const Err = ({ k }) => (errors[k] ? <p className="error">{errors[k]}</p> : null)

  return (
    <Modal title={data?.name || 'Member'} subtitle={data ? `${data.code} · registered ${whenDate(data.created_at)}` : ''} onClose={onClose}>
      {!data || !form ? <Spinner /> : (
        <>
          <div className="facts">
            <div><small>Paid</small><b>{kes(data.paid)}</b></div>
            <div><small>Balance</small><b>{kes(data.balance)}</b></div>
          </div>
          <MiniProgress percent={data.percent} />

          <form className="form" onSubmit={save} style={{ marginTop: 16 }}>
            <div className="two">
              <div className="field"><label htmlFor="m-name">Full name</label><input id="m-name" className="input" value={form.name} onChange={set('name')} /><Err k="name" /></div>
              <div className="field"><label htmlFor="m-email">Email</label><input id="m-email" className="input" value={form.email} onChange={set('email')} /><Err k="email" /></div>
              <div className="field"><label htmlFor="m-phone">Phone</label><input id="m-phone" className="input" value={form.phone} onChange={set('phone')} /><Err k="phone" /></div>
              <div className="field"><label htmlFor="m-mp">M-Pesa number</label><input id="m-mp" className="input" value={form.mpesa_phone} onChange={set('mpesa_phone')} /><Err k="mpesa_phone" /></div>
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

          <h3 className="subhead">Payments</h3>
          {data.payments.length === 0 ? <Empty>No payments yet.</Empty> : (
            <div className="table-wrap"><table>
              <thead><tr><th>Receipt</th><th>Date</th><th className="num">Amount</th><th>Status</th></tr></thead>
              <tbody>{data.payments.map((p) => (
                <tr key={p.id}><td className="mono">{p.receipt_no}</td><td>{when(p.paid_at)}</td><td className="num">{plain(p.amount)}</td><td><PaymentBadge status={p.status} /></td></tr>
              ))}</tbody>
            </table></div>
          )}

          <h3 className="subhead">Messages sent</h3>
          {data.notifications.length === 0 ? <p className="hint">Nothing sent yet.</p> : (
            <div className="table-wrap"><table>
              <thead><tr><th>When</th><th>Type</th><th>Channel</th><th>Result</th></tr></thead>
              <tbody>{data.notifications.map((n) => (
                <tr key={n.id}><td>{when(n.created_at)}</td><td>{n.kind}</td><td>{n.channel}</td>
                  <td><span className={`badge ${n.status === 'sent' ? 'green' : n.status === 'failed' ? 'red' : 'grey'}`}>{n.status}</span>{n.error && <div className="meta">{n.error}</div>}</td></tr>
              ))}</tbody>
            </table></div>
          )}
        </>
      )}
    </Modal>
  )
}

export default function Members() {
  const toast = useToast()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [duration, setDuration] = useState('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(null)
  const dq = useDebounce(q, 300)

  useEffect(() => setPage(1), [dq, status, duration])

  const params = new URLSearchParams({ page: String(page), q: dq.trim(), status, duration })
  const { data, loading, error, reload } = useLoad(`/members/?${params}`)
  const rows = data?.results || []

  async function exportFile() {
    try { await download('/export/', 'gongoni27.xlsx'); toast('Excel file downloaded') } catch { toast('Download failed', 'error') }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Members</h1><p>Everyone registered for the mission {data && `· ${data.count}`}</p></div>
        <button className="btn" onClick={exportFile}>Download Excel</button>
      </div>

      <div className="toolbar">
        <input className="input" type="search" placeholder="Search name, phone, email or code" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search members" />
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by progress">
          <option value="">All progress</option><option value="completed">Completed</option><option value="in_progress">In progress</option><option value="unpaid">Not started</option>
        </select>
        <select className="input" value={duration} onChange={(e) => setDuration(e.target.value)} aria-label="Filter by duration">
          <option value="">Any duration</option><option value="1wk">1 week</option><option value="2wks">2 weeks</option>
        </select>
      </div>

      {error && <p className="banner error">{error}</p>}
      {!data ? <Spinner /> : rows.length === 0 ? <div className="table-wrap"><Empty>No members found.</Empty></div> : (
        <div className="table-wrap" style={{ opacity: loading ? 0.65 : 1 }}>
          <table>
            <thead><tr><th>Member</th><th>Duration</th><th className="num">Paid (KES)</th><th>Progress</th><th className="num">Balance</th><th>Status</th></tr></thead>
            <tbody>
              {rows.map((m) => (
                <tr key={m.id} className="click" onClick={() => setOpen(m.id)}>
                  <td>
                    <button className="btn link main" onClick={(e) => { e.stopPropagation(); setOpen(m.id) }} style={{ textDecoration: 'none', fontWeight: 600, textAlign: 'left' }}>{m.name}</button>
                    <div className="meta">{m.code} · {m.phone}</div>
                  </td>
                  <td>{m.duration_display}</td>
                  <td className="num">{plain(m.paid)}</td>
                  <td><MiniProgress percent={m.percent} /></td>
                  <td className="num">{plain(m.balance)}</td>
                  <td><MemberBadge status={m.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
      {open && <MemberModal id={open} onClose={() => setOpen(null)} onChanged={reload} />}
    </div>
  )
}
