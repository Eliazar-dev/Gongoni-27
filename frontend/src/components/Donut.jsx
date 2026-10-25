import { kes, num } from '../api.js'

/** Pie (donut) chart of paid vs balance, with the percentage in the middle. */
export default function Donut({ paid, balance, percent, size = 180 }) {
  const r = 70
  const c = 2 * Math.PI * r
  const total = num(paid) + num(balance)
  const share = total ? num(paid) / total : 0
  const done = percent >= 100
  return (
    <div className="donut-wrap">
      <svg className="donut" width={size} height={size} viewBox="0 0 180 180" role="img"
        aria-label={`${percent}% paid: ${kes(paid)} paid, ${kes(balance)} balance`}>
        <circle cx="90" cy="90" r={r} fill="none" stroke="var(--donut-rest)" strokeWidth="22" />
        {share > 0 && (
          <circle cx="90" cy="90" r={r} fill="none" stroke={done ? 'var(--green)' : 'var(--donut-paid)'} strokeWidth="22"
            strokeDasharray={`${c * share} ${c}`} strokeLinecap={share < 1 ? 'round' : 'butt'} transform="rotate(-90 90 90)" />
        )}
        <text x="90" y="88" textAnchor="middle" className="donut-pct">{percent}%</text>
        <text x="90" y="112" textAnchor="middle" className="donut-cap">{done ? 'complete' : 'paid'}</text>
      </svg>
      <ul className="donut-legend">
        <li><i style={{ background: done ? 'var(--green)' : 'var(--donut-paid)' }} /><span>Paid</span><b>{kes(paid)}</b></li>
        <li><i style={{ background: 'var(--donut-rest)' }} /><span>Balance</span><b>{kes(balance)}</b></li>
      </ul>
    </div>
  )
}
