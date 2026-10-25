import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, fieldErrors, kes, phoneLocal, when, whenDay, whenTime } from '../api.js'
import Donut from '../components/Donut.jsx'
import { BackLink, PaymentBadge, Spinner, useLoad, useToast } from '../components/ui.jsx'

const method = (p) => (p.source === 'manual' ? 'Entered by treasurer' : (p.channel || 'Paystack').replace('_', ' '))

export default function PaymentDetail() {
  const { id } = useParams()
  const toast = useToast()
  const { data, error, reload } = useLoad(`/payments/${id}/`)
  const [reversing, setReversing] = useState(false)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  async function resend() {
    try { await api(`/payments/${id}/resend/`, { method: 'POST' }); toast('Receipt sent') } catch { toast('Could not resend', 'error') }
  }

  async function reverse() {
    setBusy(true)
    try {
      await api(`/payments/${id}/reverse/`, { method: 'POST', body: { note } })
      toast('Payment reversed')
      setReversing(false)
      reload()
    } catch (err) {
      toast(fieldErrors(err).general || 'Could not reverse', 'error')
    } finally {
      setBusy(false)
    }
  }

  if (!data) {
    return <div className="page"><BackLink to="/admin/payments" />{error ? <p className="banner error">{error}</p> : <Spinner />}</div>
  }
  const m = data.member

  return (
    <div className="page">
      <BackLink to="/admin/payments" />
      <div className="page-head">
        <div>
          <h1>{kes(data.amount)}</h1>
          <p>Receipt {data.receipt_no} · {when(data.paid_at || data.created_at)}</p>
        </div>
        <PaymentBadge status={data.status} />
      </div>

      <div className="grid detail-cols">
        <div className="panel">
          <h2>Payment details</h2>
          <dl className="info">
            <div><dt>Amount</dt><dd>{kes(data.amount)}</dd></div>
            <div><dt>Status</dt><dd><PaymentBadge status={data.status} /></dd></div>
            <div><dt>Receipt no.</dt><dd className="mono">{data.receipt_no}</dd></div>
            <div><dt>Reference</dt><dd className="mono">{data.reference}</dd></div>
            <div><dt>Method</dt><dd style={{ textTransform: 'capitalize' }}>{method(data)}</dd></div>
            <div><dt>Started</dt><dd>{when(data.created_at)}</dd></div>
            <div><dt>Paid on</dt><dd>{data.paid_at ? `${whenDay(data.paid_at)}, ${whenTime(data.paid_at)}` : '—'}</dd></div>
            {data.note && <div><dt>Note</dt><dd style={{ whiteSpace: 'pre-line' }}>{data.note}</dd></div>}
          </dl>

          {data.status === 'success' && (
            <div className="detail-actions">
              <button className="btn" onClick={resend}>Resend receipt</button>
              {!reversing && <button className="btn danger" onClick={() => setReversing(true)}>Reverse payment</button>}
            </div>
          )}
          {reversing && (
            <div className="reverse-box">
              <p>The record stays in the list, but it will no longer count toward {m.name.split(' ')[0]}'s total.</p>
              <div className="field">
                <label htmlFor="rev-note">Reason</label>
                <input id="rev-note" className="input" autoFocus value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. refunded" />
              </div>
              <div className="detail-actions">
                <button className="btn" onClick={() => setReversing(false)}>Cancel</button>
                <button className="btn danger" disabled={busy} onClick={reverse}>{busy ? 'Reversing…' : 'Confirm reverse'}</button>
              </div>
            </div>
          )}
        </div>

        <div className="panel">
          <h2>Member</h2>
          <p className="member-line"><Link to={`/admin/members/${m.id}`}><b>{m.name}</b></Link><span className="muted"> · {m.code}</span></p>
          <Donut paid={m.paid} balance={m.balance} percent={m.percent} size={150} />
          <dl className="info">
            <div><dt>Target</dt><dd>{kes(m.target)}</dd></div>
            <div><dt>Phone</dt><dd>{phoneLocal(m.phone)}</dd></div>
            <div><dt>Email</dt><dd>{m.email}</dd></div>
            <div><dt>Duration</dt><dd>{m.duration_display}</dd></div>
          </dl>
        </div>
      </div>
    </div>
  )
}
