import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, fieldErrors } from '../api.js'
import { BackLink, MemberPicker, useToast } from '../components/ui.jsx'

export default function RecordPayment() {
  const navigate = useNavigate()
  const toast = useToast()
  const [member, setMember] = useState(null)
  const [f, setF] = useState({ amount: '', note: '' })
  const [errors, setErrors] = useState({})
  const [general, setGeneral] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF((o) => ({ ...o, [k]: e.target.value }))

  async function save(e) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setGeneral('')
    try {
      const payment = await api('/payments/', { method: 'POST', body: { ...f, member_id: member.id } })
      toast('Payment recorded. Receipt sent.')
      navigate(`/admin/payments/${payment.id}`, { replace: true })
    } catch (err) {
      const r = fieldErrors(err)
      setErrors(r.fields)
      setGeneral(r.general)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page">
      <BackLink to="/admin/payments" />
      <div className="page-head">
        <div><h1>Record a payment</h1><p>For money received outside Paystack, for example cash.</p></div>
      </div>
      <div className="panel" style={{ maxWidth: 640 }}>
        <form className="form" onSubmit={save}>
          {member ? (
            <div className="chosen">
              <div><b>{member.name}</b><small>{member.code} · {member.phone}</small></div>
              <button type="button" className="btn small" onClick={() => setMember(null)}>Change</button>
            </div>
          ) : <MemberPicker onPick={setMember} />}
          <div className="two">
            <div className="field"><label htmlFor="mp-amount">Amount (KES)</label>
              <input id="mp-amount" type="number" min="1" step="1" className="input" value={f.amount} onChange={set('amount')} />
              {errors.amount && <p className="error">{errors.amount}</p>}</div>
            <div className="field"><label htmlFor="mp-note">Note (optional)</label>
              <input id="mp-note" className="input" value={f.note} onChange={set('note')} placeholder="e.g. cash received at church" /></div>
          </div>
          {general && <p className="banner error">{general}</p>}
          <div className="modal-actions">
            <button type="button" className="btn" onClick={() => navigate('/admin/payments')}>Cancel</button>
            <button className="btn primary" type="submit" disabled={!member || !f.amount || busy}>{busy ? 'Saving…' : 'Record and notify'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
