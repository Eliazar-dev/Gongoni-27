import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, fieldErrors, kes, plain, when } from '../api.js'
import { Empty, MemberPicker, Modal, Pager, PaymentBadge, Spinner, useDebounce, useLoad, useToast } from '../components/ui.jsx'

const TABS = [['attention', 'Needs attention'], ['all', 'All payments'], ['log', 'Message log']]

function PayerFacts({ p }) {
  return (
    <div className="facts">
      <div><small>Payer</small><b style={{ fontSize: 15 }}>{p.payer_name || 'Unknown'}</b></div>
      <div><small>Amount</small><b>{kes(p.amount)}</b></div>
      <div><small>Payer phone</small><b style={{ fontSize: 15 }}>{p.payer_phone || 'Not shown'}</b></div>
      <div><small>M-Pesa code</small><b className="mono">{p.mpesa_code}</b></div>
    </div>
  )
}

function AssignModal({ payment, onClose, onDone }) {
  const toast = useToast()
  const [member, setMember] = useState(payment.suggested_member || null)
  const [remember, setRemember] = useState(true)
  const [busy, setBusy] = useState(false)

  async function assign() {
    setBusy(true)
    try {
      await api(`/payments/${payment.id}/assign/`, { method: 'POST', body: { member_id: member.id, remember } })
      toast(`Assigned to ${member.name}. Receipt on its way.`)
      onDone()
    } catch (err) {
      toast(fieldErrors(err).general || 'Could not assign', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="Assign payment" subtitle="Choose the member this payment is for. They will get the receipt and progress." onClose={onClose}>
      <PayerFacts p={payment} />
      {member ? (
        <div className="chosen">
          <div><b>{member.name}</b><small>{member.code} · {member.phone}</small></div>
          <button className="btn small" onClick={() => setMember(null)}>Change</button>
        </div>
      ) : <MemberPicker onPick={setMember} />}
      <label className="check"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Remember this payer, so next time it matches automatically</label>
      <div className="modal-actions">
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn primary" disabled={!member || busy} onClick={assign}>{busy ? 'Saving…' : 'Assign and notify'}</button>
      </div>
    </Modal>
  )
}

function ReverseModal({ payment, onClose, onDone }) {
  const toast = useToast()
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const recorded = payment.status === 'recorded'

  async function go() {
    setBusy(true)
    try {
      await api(`/payments/${payment.id}/reverse/`, { method: 'POST', body: { note } })
      toast(recorded ? 'Payment reversed' : 'Payment discarded')
      onDone()
    } catch (err) {
      toast(fieldErrors(err).general || 'Could not reverse', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={recorded ? 'Reverse payment' : 'Discard payment'} subtitle="The record stays in the list for the audit trail, but it no longer counts toward anyone's total." onClose={onClose}>
      <PayerFacts p={payment} />
      <div className="field">
        <label htmlFor="rev-note">Reason</label>
        <input id="rev-note" className="input" autoFocus value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. paid for the wrong person" />
      </div>
      <div className="modal-actions">
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn danger" disabled={busy} onClick={go}>{recorded ? 'Reverse payment' : 'Discard payment'}</button>
      </div>
    </Modal>
  )
}

function ManualModal({ onClose, onDone }) {
  const toast = useToast()
  const [member, setMember] = useState(null)
  const [f, setF] = useState({ amount: '', mpesa_code: '', note: '' })
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
      await api('/payments/', { method: 'POST', body: { ...f, member_id: member.id } })
      toast('Payment recorded. Receipt on its way.')
      onDone()
    } catch (err) {
      const r = fieldErrors(err)
      setErrors(r.fields)
      setGeneral(r.general)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="Record a payment" subtitle="Use this for a payment that did not arrive by message, for example cash or a missed SMS." onClose={onClose}>
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
          <div className="field"><label htmlFor="mp-code">M-Pesa code (optional)</label>
            <input id="mp-code" className="input" value={f.mpesa_code} onChange={set('mpesa_code')} placeholder="e.g. UJL11B2KXF" />
            {errors.mpesa_code && <p className="error">{errors.mpesa_code}</p>}</div>
        </div>
        <div className="field"><label htmlFor="mp-note">Note (optional)</label>
          <input id="mp-note" className="input" value={f.note} onChange={set('note')} placeholder="e.g. cash received at church" /></div>
        {general && <p className="banner error">{general}</p>}
        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" type="submit" disabled={!member || !f.amount || busy}>{busy ? 'Saving…' : 'Record and notify'}</button>
        </div>
      </form>
    </Modal>
  )
}

function PaymentsTable({ tab }) {
  const toast = useToast()
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [action, setAction] = useState(null) // { type, payment }
  const dq = useDebounce(q, 300)
  useEffect(() => setPage(1), [dq, tab])
  const status = tab === 'attention' ? 'attention' : ''
  const params = new URLSearchParams({ page: String(page), q: dq.trim(), status })
  const { data, loading, error, reload } = useLoad(`/payments/?${params}`)
  const rows = data?.results || []
  const done = () => { setAction(null); reload(); window.dispatchEvent(new Event('gn27-payments-changed')) }

  async function confirmSuggested(p) {
    try {
      await api(`/payments/${p.id}/assign/`, { method: 'POST', body: { member_id: p.suggested_member.id, remember: true } })
      toast(`Confirmed as ${p.suggested_member.name}. Receipt on its way.`)
      done()
    } catch (err) { toast(fieldErrors(err).general || 'Could not confirm', 'error') }
  }
  async function resend(p) {
    try { await api(`/payments/${p.id}/resend/`, { method: 'POST' }); toast('Message queued') } catch { toast('Could not resend', 'error') }
  }

  return (
    <>
      <div className="toolbar">
        <input className="input" type="search" placeholder="Search payer, member, M-Pesa code or receipt" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search payments" />
      </div>
      {error && <p className="banner error">{error}</p>}
      {!data ? <Spinner /> : rows.length === 0 ? (
        <div className="table-wrap"><Empty>{tab === 'attention' ? 'Nothing needs your attention. All payments are matched.' : 'No payments found.'}</Empty></div>
      ) : (
        <div className="table-wrap" style={{ opacity: loading ? 0.65 : 1 }}>
          <table>
            <thead><tr><th>Date</th><th>Payer</th><th className="num">Amount</th><th>Member</th><th>Status</th><th /></tr></thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.id}>
                  <td style={{ whiteSpace: 'nowrap' }}>{when(p.paid_at)}<div className="meta mono">{p.mpesa_code}</div></td>
                  <td><div className="main">{p.payer_name || 'Unknown'}</div><div className="meta">{p.payer_phone || 'number not shown'}</div></td>
                  <td className="num"><b>{plain(p.amount)}</b></td>
                  <td>
                    {p.member ? <><div className="main">{p.member.name}</div><div className="meta">{p.member.code}</div></>
                      : p.suggested_member ? <><div className="meta">Possibly</div><div className="main">{p.suggested_member.name}</div></>
                      : <span className="meta">None</span>}
                  </td>
                  <td><PaymentBadge status={p.status} /></td>
                  <td>
                    <div className="row-actions">
                      {p.status === 'review' && <button className="btn small primary" onClick={() => confirmSuggested(p)}>Confirm</button>}
                      {(p.status === 'review' || p.status === 'unassigned') && <button className="btn small" onClick={() => setAction({ type: 'assign', payment: p })}>{p.status === 'review' ? 'Choose other' : 'Assign'}</button>}
                      {p.status === 'recorded' && <button className="btn small" onClick={() => resend(p)}>Resend</button>}
                      {p.status === 'recorded' && <button className="btn small" onClick={() => setAction({ type: 'assign', payment: p })}>Move</button>}
                      {p.status !== 'reversed' && <button className="btn small danger" onClick={() => setAction({ type: 'reverse', payment: p })}>{p.status === 'recorded' ? 'Reverse' : 'Discard'}</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
      {action?.type === 'assign' && <AssignModal payment={action.payment} onClose={() => setAction(null)} onDone={done} />}
      {action?.type === 'reverse' && <ReverseModal payment={action.payment} onClose={() => setAction(null)} onDone={done} />}
    </>
  )
}

function MessageLog() {
  const [status, setStatus] = useState('unparsed')
  const [page, setPage] = useState(1)
  useEffect(() => setPage(1), [status])
  const { data, error } = useLoad(`/incoming/?page=${page}&status=${status}`)
  const rows = data?.results || []
  return (
    <>
      <div className="toolbar">
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter log">
          <option value="unparsed">Could not read</option>
          <option value="not_mission">Not a mission payment</option>
          <option value="duplicate">Duplicates</option>
          <option value="ignored">Other senders</option>
          <option value="">Everything</option>
        </select>
      </div>
      <p className="hint" style={{ marginBottom: 10 }}>
        Every message forwarded by the treasurer's phone is listed here. Text is kept only for messages the system could not read. The church's Utility balance is never stored.
      </p>
      {error && <p className="banner error">{error}</p>}
      {!data ? <Spinner /> : rows.length === 0 ? <div className="table-wrap"><Empty>Nothing here.</Empty></div> : (
        <div className="table-wrap"><table>
          <thead><tr><th>When</th><th>Sender</th><th>Result</th><th>Details</th></tr></thead>
          <tbody>{rows.map((m) => (
            <tr key={m.id}>
              <td style={{ whiteSpace: 'nowrap' }}>{when(m.created_at)}</td>
              <td>{m.sender || '-'}</td>
              <td><span className={`badge ${m.status === 'unparsed' ? 'red' : m.status === 'recorded' ? 'green' : 'grey'}`}>{m.status_display}</span></td>
              <td>{m.text ? <div className="rawtext">{m.text}</div> : <span className="meta mono">{m.detail}</span>}</td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
    </>
  )
}

export default function Payments() {
  const [params, setParams] = useSearchParams()
  const tab = TABS.some(([k]) => k === params.get('tab')) ? params.get('tab') : 'attention'
  const [manual, setManual] = useState(false)
  const [version, setVersion] = useState(0)
  const attention = useLoad(`/payments/?status=attention&page_size=1&v=${version}`)
  const attentionCount = attention.data?.count || 0

  useEffect(() => {
    const bump = () => setVersion((v) => v + 1)
    window.addEventListener('gn27-payments-changed', bump)
    return () => window.removeEventListener('gn27-payments-changed', bump)
  }, [])

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Payments</h1><p>Match, confirm and review mission payments</p></div>
        <button className="btn primary" onClick={() => setManual(true)}>Record a payment</button>
      </div>
      <div className="tabs" role="tablist">
        {TABS.map(([key, label]) => (
          <button key={key} role="tab" className="tab" aria-selected={tab === key} onClick={() => setParams({ tab: key })}>
            {label} {key === 'attention' && attentionCount > 0 && <span className="count">{attentionCount}</span>}
          </button>
        ))}
      </div>
      {tab === 'log' ? <MessageLog /> : <PaymentsTable key={tab} tab={tab} />}
      {manual && <ManualModal onClose={() => setManual(false)} onDone={() => { setManual(false); setVersion((v) => v + 1); window.dispatchEvent(new Event('gn27-payments-changed')) }} />}
    </div>
  )
}
