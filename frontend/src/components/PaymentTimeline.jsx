import { kes, num, whenDay, whenTime } from '../api.js'

const LABEL = { pending: 'Pending', failed: 'Failed', reversed: 'Reversed' }

/**
 * Every payment on its own line with the day it was made, newest first.
 * "Total after" counts only successful payments, so it shows how the member's total grew.
 */
export default function PaymentTimeline({ payments, target, onOpen }) {
  const oldestFirst = [...payments].sort((a, b) => new Date(a.paid_at || a.created_at) - new Date(b.paid_at || b.created_at))
  let running = 0
  const rows = oldestFirst.map((p) => {
    if (p.status === 'success') running += num(p.amount)
    return { ...p, after: running }
  }).reverse()

  if (rows.length === 0) return <p className="timeline-empty">No payments yet. Your first payment will appear here with its date.</p>

  return (
    <ol className="timeline">
      {rows.map((p) => {
        const ok = p.status === 'success'
        const date = p.paid_at || p.created_at
        const Row = onOpen ? 'button' : 'div'
        return (
          <li key={p.receipt_no || p.id} className={ok ? '' : 'off'}>
            <span className="tl-dot" aria-hidden="true" />
            <Row className="tl-card" {...(onOpen ? { type: 'button', onClick: () => onOpen(p) } : {})}>
              <div className="tl-when">
                <b>{whenDay(date)}</b>
                <span className="tl-time">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
                  {whenTime(date)}
                </span>
                <small>{p.receipt_no}{p.method || p.channel ? ` · ${(p.method || p.channel).replace('_', ' ')}` : ''}</small>
              </div>
              <div className="tl-amount">
                <b>{ok ? '+ ' : ''}{kes(p.amount)}</b>
                {ok
                  ? <small>Total {kes(p.after)}{target ? ` · ${Math.min(100, Math.floor((p.after / num(target)) * 100))}%` : ''}</small>
                  : <small className={`tl-status ${p.status}`}>{LABEL[p.status] || p.status} · not counted</small>}
              </div>
            </Row>
          </li>
        )
      })}
    </ol>
  )
}
