import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Site, { ProgressBar } from '../components/Site.jsx'
import { api, kes } from '../api.js'

/** Paystack sends the member here after checkout with ?reference=... */
export default function PaymentDone() {
  const [params] = useSearchParams()
  const reference = params.get('reference') || params.get('trxref') || ''
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!reference) return setError('No payment reference found.')
    api(`/pay/verify/${encodeURIComponent(reference)}/`, { auth: false }).then(setData).catch((e) => setError(e.message))
  }, [reference])

  return (
    <Site>
      <section className="section">
        <div className="wrap narrow">
          {!data && !error && <div className="loading"><div className="spinner big" /></div>}
          {error && <div className="panel-box"><p className="error">{error}</p><a className="btn" href="/#track">Back</a></div>}

          {data?.status === 'success' && (
            <div className="panel-box progress">
              <p className="eyebrow">Payment received</p>
              <h2>Thank you, {data.name.split(' ')[0]}.</h2>
              <p className="muted">{kes(data.amount)} · Receipt {data.receipt_no}. A copy is on its way to your email.</p>
              <div className="progress-head" style={{ marginTop: 24 }}><p>Your progress</p><b>{data.percent}%</b></div>
              <ProgressBar percent={data.percent} />
              <div className="facts-row tight">
                <div><small>Paid</small><b>{kes(data.paid)}</b></div>
                <div><small>Target</small><b>{kes(data.target)}</b></div>
                <div><small>Balance</small><b>{kes(data.balance)}</b></div>
              </div>
              <a className="btn" href="/">Back to home</a>
            </div>
          )}

          {data && data.status !== 'success' && (
            <div className="panel-box">
              <h2>{data.status === 'pending' ? 'Payment still processing' : 'Payment not completed'}</h2>
              <p className="muted">
                {data.status === 'pending'
                  ? 'We have not received confirmation yet. Check your progress again in a few minutes.'
                  : 'Nothing was charged. You can try again whenever you are ready.'}
              </p>
              <a className="btn primary" href="/#track">Track progress</a>
            </div>
          )}
        </div>
      </section>
    </Site>
  )
}
