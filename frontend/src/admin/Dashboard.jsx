import { Link } from 'react-router-dom'
import { kes, num, plain, when } from '../api.js'
import { Empty, Spinner, useLoad } from '../components/ui.jsx'

const short = (n) => (n >= 1000 ? `${(n / 1000).toFixed(n % 1000 === 0 ? 0 : 1)}k` : String(Math.round(n)))

function Daily({ days }) {
  const max = Math.max(...days.map((d) => num(d.total)), 1)
  return (
    <div className="bars" role="img" aria-label="Amount received per day over the last 14 days">
      {days.map((d) => {
        const total = num(d.total)
        return (
          <div className="col" key={d.date} title={`${d.date}: ${kes(total)}`}>
            <em>{total ? short(total) : ''}</em>
            <i className={total ? '' : 'zero'} style={{ height: `${Math.max((total / max) * 100, 2)}%` }} />
            <span>{Number(d.date.slice(8))}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function Dashboard() {
  const { data, loading, error } = useLoad('/dashboard/')
  if (!data) return error ? <div className="page"><p className="banner error">{error}</p></div> : <Spinner />
  const attention = data.unassigned + data.review

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Dashboard</h1><p>Gongoni Mission 27 giving at a glance {loading && '· updating…'}</p></div>
      </div>

      <div className="grid">
        {attention > 0 && (
          <div className="alert warn">
            <span><b>{attention}</b> {attention === 1 ? 'payment needs' : 'payments need'} your attention. The payer could not be matched to a member for sure.</span>
            <Link className="btn small" to="/admin/payments?tab=attention">Review now</Link>
          </div>
        )}
        {data.unparsed > 0 && (
          <div className="alert bad">
            <span><b>{data.unparsed}</b> {data.unparsed === 1 ? 'message was' : 'messages were'} received from the phone but could not be read.</span>
            <Link className="btn small" to="/admin/payments?tab=log">See messages</Link>
          </div>
        )}

        <div className="tile hero-stat">
          <small>Raised so far</small>
          <div className="big">{kes(data.raised)} <em>of {kes(data.target_total)}</em></div>
          <div className="bar" role="progressbar" aria-valuenow={data.percent} aria-valuemin="0" aria-valuemax="100"><i style={{ width: `${data.percent}%` }} /></div>
          <div className="foot"><span>{data.percent}% of the combined target</span><span>{kes(Math.max(num(data.target_total) - num(data.raised), 0))} to go</span></div>
        </div>

        <div className="grid tiles">
          <div className="tile"><small>Registered</small><b>{data.members}</b><span>{data.by_duration['1wk']} for 1 week · {data.by_duration['2wks']} for 2 weeks</span></div>
          <div className="tile gold"><small>Completed</small><b>{data.completed}</b><span>reached 100%</span></div>
          <div className="tile"><small>In progress</small><b>{data.in_progress}</b><span>paid something</span></div>
          <div className="tile"><small>Not started</small><b>{data.unpaid}</b><span>nothing paid yet</span></div>
        </div>

        <div className="grid dash-cols">
          <div className="panel">
            <h2>Last 14 days</h2>
            <Daily days={data.daily} />
          </div>
          <div className="panel">
            <h2>Latest payments</h2>
            {data.recent.length === 0 ? <Empty>No payments yet.</Empty> : (
              <div>
                {data.recent.map((p) => (
                  <div className="payrow" key={p.id}>
                    <div><b>{p.member?.name}</b><small>{when(p.paid_at)}</small></div>
                    <strong style={{ fontSize: 16 }}>{plain(p.amount)}</strong>
                  </div>
                ))}
                <p style={{ marginTop: 10 }}><Link to="/admin/payments?tab=all">All payments</Link></p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
