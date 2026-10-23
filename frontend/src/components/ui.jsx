import { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../api.js'

export const ToastCtx = createContext(() => {})
export const useToast = () => useContext(ToastCtx)

export function useDebounce(value, ms = 300) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

/** Load a GET path. Keeps the old data on screen while a new request runs. */
export function useLoad(path) {
  const [state, setState] = useState({ data: null, loading: true, error: '' })
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let alive = true
    if (!path) return undefined
    setState((s) => ({ ...s, loading: true, error: '' }))
    api(path)
      .then((data) => alive && setState({ data, loading: false, error: '' }))
      .catch((e) => alive && setState((s) => ({ ...s, loading: false, error: e.message || 'Could not load' })))
    return () => { alive = false }
  }, [path, tick])
  return { ...state, reload: () => setTick((t) => t + 1) }
}

export function Spinner() {
  return <div className="loading"><div className="spinner big" /></div>
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>
}

const MEMBER_STATUS = {
  completed: ['Completed', 'green'],
  in_progress: ['In progress', ''],
  unpaid: ['Not started', 'grey'],
}
const PAYMENT_STATUS = {
  recorded: ['Recorded', 'green'],
  review: ['Confirm match', 'amber'],
  unassigned: ['Unassigned', 'red'],
  reversed: ['Reversed', 'grey'],
}

export function MemberBadge({ status }) {
  const [label, tone] = MEMBER_STATUS[status] || [status, '']
  return <span className={`badge ${tone}`}>{label}</span>
}

export function PaymentBadge({ status }) {
  const [label, tone] = PAYMENT_STATUS[status] || [status, '']
  return <span className={`badge ${tone}`}>{label}</span>
}

export function MiniProgress({ percent }) {
  return (
    <div className="mini" title={`${percent}% paid`}>
      <div className="track"><i className={percent >= 100 ? 'full' : ''} style={{ width: `${Math.max(percent, 2)}%` }} /></div>
      <b>{percent}%</b>
    </div>
  )
}

export function Pager({ page, count, pageSize = 50, onPage }) {
  const pages = Math.max(1, Math.ceil(count / pageSize))
  if (count <= pageSize) return <p className="pager"><span>{count} {count === 1 ? 'result' : 'results'}</span></p>
  return (
    <div className="pager">
      <span>Page {page} of {pages} · {count} results</span>
      <div>
        <button className="btn small" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
        <button className="btn small" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
      </div>
    </div>
  )
}

export function Modal({ title, subtitle, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [onClose])
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
          <button className="x" onClick={onClose} aria-label="Close">×</button>
        </div>
        {children}
      </div>
    </div>
  )
}

/** Search for a member by name, phone or code and pick one. */
export function MemberPicker({ onPick, autoFocus = true }) {
  const [q, setQ] = useState('')
  const dq = useDebounce(q, 250)
  const { data, loading } = useLoad(`/members/?page_size=8&ordering=name&q=${encodeURIComponent(dq.trim())}`)
  const rows = data?.results || []
  return (
    <div>
      <input className="input" autoFocus={autoFocus} value={q} onChange={(e) => setQ(e.target.value)}
        placeholder="Search member by name, phone or code" aria-label="Search member" />
      <div className="picker-list" role="listbox" aria-label="Members">
        {loading && !data && <div className="empty">Loading…</div>}
        {data && rows.length === 0 && <div className="empty">No member found.</div>}
        {rows.map((m) => (
          <button key={m.id} type="button" className="picker-item" role="option" onClick={() => onPick(m)}>
            <b>{m.name}</b>
            <small>{m.code} · {m.phone} · {m.percent}% paid</small>
          </button>
        ))}
      </div>
    </div>
  )
}
