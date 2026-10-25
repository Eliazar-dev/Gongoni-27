import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, kes, phoneLocal, plain, when } from '../api.js'
import { Empty, Pager, PaymentBadge, Spinner, useDebounce, useLoad, useToast } from '../components/ui.jsx'

const TABS = [['success', 'Paid'], ['pending,failed', 'Pending & failed'], ['', 'All']]

function Summary({ s }) {
  const percent = Number(s.target) ? Math.min(100, Math.floor((Number(s.paid) / Number(s.target)) * 100)) : 0
  return (
    <div className="grid tiles" style={{ marginBottom: 16 }}>
      <div className="tile gold"><small>Total paid</small><b>{kes(s.paid)}</b><span>{percent}% of all targets</span></div>
      <div className="tile"><small>Total balance</small><b style={{ color: 'var(--amber)' }}>{kes(s.balance)}</b><span>still to be paid</span></div>
      <div className="tile"><small>Combined target</small><b>{kes(s.target)}</b><span>all active members</span></div>
      <div className="tile"><small>In this list</small><b>{kes(s.shown_amount)}</b><span>{s.shown_count} {s.shown_count === 1 ? 'payment' : 'payments'}</span></div>
    </div>
  )
}

export default function Payments() {
  const toast = useToast()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const status = TABS.some(([k]) => k === params.get('status')) ? params.get('status') : 'success'
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const dq = useDebounce(q, 300)
  useEffect(() => setPage(1), [dq, status])

  const query = new URLSearchParams({ page: String(page), q: dq.trim(), status })
  const { data, loading, error } = useLoad(`/payments/?${query}`)
  const rows = data?.results || []

  async function resend(e, p) {
    e.stopPropagation()
    try { await api(`/payments/${p.id}/resend/`, { method: 'POST' }); toast('Receipt sent') } catch { toast('Could not resend', 'error') }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Payments</h1><p>Paystack and manual mission payments</p></div>
        <div className="head-actions">
          <Link className="btn gold" to="/admin/request">Request payment</Link>
          <Link className="btn primary" to="/admin/payments/new">Record a payment</Link>
        </div>
      </div>
      {data?.summary && <Summary s={data.summary} />}
      <div className="tabs" role="tablist">
        {TABS.map(([key, label]) => (
          <button key={key || 'all'} role="tab" className="tab" aria-selected={status === key} onClick={() => setParams({ status: key })}>{label}</button>
        ))}
      </div>
      <div className="toolbar">
        <input className="input" type="search" placeholder="Search member, reference or receipt" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search payments" />
      </div>

      {error && <p className="banner error">{error}</p>}
      {!data ? <Spinner /> : rows.length === 0 ? <div className="table-wrap"><Empty>No payments found.</Empty></div> : (
        <div className="table-wrap" style={{ opacity: loading ? 0.65 : 1 }}>
          <table className="cards payments-t">
            <thead><tr><th>Date</th><th>Member</th><th className="num">Amount</th><th>Method</th><th>Status</th><th /></tr></thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.id} className="click" onClick={() => navigate(`/admin/payments/${p.id}`)}>
                  <td className="c-date" style={{ whiteSpace: 'nowrap' }}>{when(p.paid_at || p.created_at)}<div className="meta mono">{p.receipt_no}</div></td>
                  <td className="c-who"><div className="main">{p.member.name}</div><div className="meta">{p.member.code} · {phoneLocal(p.member.phone)}</div></td>
                  <td className="num c-amount"><b>{plain(p.amount)}</b></td>
                  <td className="c-method">{p.source === 'manual' ? 'Manual' : (p.channel || 'Paystack').replace('_', ' ')}<div className="meta mono">{p.reference}</div></td>
                  <td className="c-status"><PaymentBadge status={p.status} /></td>
                  <td className="c-actions">
                    <div className="row-actions">
                      {p.status === 'success' && <button className="btn small" onClick={(e) => resend(e, p)}>Resend</button>}
                      <Link className="btn small" to={`/admin/payments/${p.id}`} onClick={(e) => e.stopPropagation()}>View</Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
    </div>
  )
}
