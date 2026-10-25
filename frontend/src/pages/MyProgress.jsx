import { kes, phoneLocal, whenDay, whenTime } from '../api.js'
import Donut from '../components/Donut.jsx'
import PaymentTimeline from '../components/PaymentTimeline.jsx'
import { PayForm } from '../components/Site.jsx'

/** What a member sees once they have signed in to their tracker. */
export default function MyProgress({ phone, data, isNew, onRefresh, refreshing }) {
  return (
    <>
      <section className="me-hero">
        <div className="wrap">
          <p className="eyebrow">My mission progress</p>
          <h1>Hi {data.first_name}</h1>
          <p className="me-sub">{data.code} · serving {data.duration.toLowerCase()}</p>
        </div>
      </section>

      <div className="wrap me-body">
        {isNew && (
          <div className="me-welcome" role="status">
            <b>You're registered!</b> Your member code is <b>{data.code}</b> and we've emailed you the details.
            Next time, open this tracker with your email and phone number.
          </div>
        )}

        <div className="me-card me-summary">
          <Donut paid={data.paid} balance={data.balance} percent={data.percent} size={150} />
          <div className="me-summary-side">
            <p className="me-togo">{data.completed ? 'Target complete. God bless you!' : <><b>{kes(data.balance)}</b> to go</>}</p>
            <div className="me-stats">
              <div><small>Paid</small><b className="ok">{kes(data.paid)}</b></div>
              <div><small>Target</small><b>{kes(data.target)}</b></div>
              <div><small>Balance</small><b className="due">{kes(data.balance)}</b></div>
            </div>
          </div>
        </div>

        <div className="me-grid">
          {!data.completed && (
            <div className="me-card me-pay">
              <h2>Make a payment</h2>
              <PayForm phone={phone} balance={data.balance} />
            </div>
          )}

          <div className="me-card me-history">
            <div className="me-card-head">
              <h2>My payments{data.payments.length > 0 && <span className="pill">{data.payments.length}</span>}</h2>
              <button className="btn small" onClick={onRefresh} disabled={refreshing}>{refreshing ? 'Updating…' : 'Refresh'}</button>
            </div>
            <PaymentTimeline payments={data.payments} target={data.target} />
          </div>

          <div className="me-card me-details">
            <h2>My details</h2>
            <dl className="info">
              <div><dt>Name</dt><dd>{data.name}</dd></div>
              <div><dt>Member code</dt><dd>{data.code}</dd></div>
              <div><dt>Phone</dt><dd>{phoneLocal(data.phone)}</dd></div>
              <div><dt>Email</dt><dd>{data.email}</dd></div>
              <div><dt>Duration</dt><dd>{data.duration}</dd></div>
              <div><dt>Registered</dt><dd>{whenDay(data.registered)}<span className="dd-time">{whenTime(data.registered)}</span></dd></div>
            </dl>
          </div>
        </div>
      </div>
    </>
  )
}
