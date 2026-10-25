import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { download, phoneLocal, plain } from '../api.js'
import { Empty, MemberBadge, MiniProgress, Pager, Spinner, useDebounce, useLoad, useToast } from '../components/ui.jsx'

export default function Members() {
  const toast = useToast()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [duration, setDuration] = useState('')
  const [page, setPage] = useState(1)
  const navigate = useNavigate()
  const dq = useDebounce(q, 300)

  useEffect(() => setPage(1), [dq, status, duration])

  const params = new URLSearchParams({ page: String(page), q: dq.trim(), status, duration })
  const { data, loading, error } = useLoad(`/members/?${params}`)
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
          <table className="cards members-t">
            <thead><tr><th>Member</th><th>Duration</th><th className="num">Paid (KES)</th><th>Progress</th><th className="num">Balance</th><th>Status</th></tr></thead>
            <tbody>
              {rows.map((m) => (
                <tr key={m.id} className="click" onClick={() => navigate(`/admin/members/${m.id}`)}>
                  <td className="c-who">
                    <Link className="main" to={`/admin/members/${m.id}`} onClick={(e) => e.stopPropagation()} style={{ textDecoration: 'none' }}>{m.name}</Link>
                    <div className="meta">{m.code} · {phoneLocal(m.phone)} <span className="only-mobile">· {m.duration_display}</span></div>
                  </td>
                  <td className="c-dur">{m.duration_display}</td>
                  <td className="num c-paid" data-label="Paid">{plain(m.paid)}</td>
                  <td className="c-prog"><MiniProgress percent={m.percent} /></td>
                  <td className="num c-bal" data-label="Balance">{plain(m.balance)}</td>
                  <td className="c-status"><MemberBadge status={m.status} /></td>
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
