import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, fieldErrors, kes, num, phoneLocal } from '../api.js'
import { BackLink, MemberPicker, MiniProgress, useToast } from '../components/ui.jsx'

/** Admin asks a member to pay: an email with a Paystack link, plus an optional M-Pesa prompt. */
export default function RequestPayment() {
  const navigate = useNavigate()
  const toast = useToast()
  const [params] = useSearchParams()
  const preset = params.get('member')
  const [member, setMember] = useState(null)
  const [amount, setAmount] = useState('')
  const [message, setMessage] = useState('')
  const [mpesa, setMpesa] = useState(true)
  const [errors, setErrors] = useState({})
  const [general, setGeneral] = useState('')
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(null)

  useEffect(() => {
    if (preset) api(`/members/${preset}/`).then(setMember).catch(() => {})
  }, [preset])

  useEffect(() => {
    if (member && !amount && num(member.balance) > 0) setAmount(String(Math.round(num(member.balance))))
  }, [member]) // eslint-disable-line react-hooks/exhaustive-deps

  async function send(e) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setGeneral('')
    try {
      const result = await api('/payments/request/', { method: 'POST', body: { member_id: member.id, amount, message, mpesa } })
      setSent({ ...result, member, amount })
      toast('Payment request sent')
    } catch (err) {
      const r = fieldErrors(err)
      setErrors(r.fields)
      setGeneral(r.general)
    } finally {
      setBusy(false)
    }
  }

  function again() {
    setSent(null)
    setMember(null)
    setAmount('')
    setMessage('')
  }

  const back = preset ? `/admin/members/${preset}` : '/admin'
  const quick = member ? [500, 1000, Math.round(num(member.balance))].filter((v, i, all) => v >= 10 && all.indexOf(v) === i) : []

  return (
    <div className="page">
      <BackLink to={back}>{preset ? 'Back to member' : 'Back to dashboard'}</BackLink>
      <div className="page-head">
        <div><h1>Request payment</h1><p>Send a member a link to pay, and an M-Pesa prompt to their phone.</p></div>
      </div>

      <div className="panel req-panel">
        {sent ? (
          <div className="req-done">
            <div className="req-tick" aria-hidden="true">✓</div>
            <h2>Request sent to {sent.member.name.split(' ')[0]}</h2>
            <ul className="req-results">
              <li className="ok"><b>Email sent</b><span>Pay link for {kes(sent.amount)} sent to {sent.emailed}</span></li>
              {sent.mpesa && (
                <li className={sent.mpesa.sent ? 'ok' : 'bad'}>
                  <b>{sent.mpesa.sent ? 'M-Pesa prompt sent' : 'M-Pesa prompt failed'}</b>
                  <span>{sent.mpesa.sent ? `${phoneLocal(sent.member.phone)}: ${sent.mpesa.detail}` : `${sent.mpesa.detail}. The email link still works.`}</span>
                </li>
              )}
            </ul>
            <p className="hint">The payment shows as Pending until the member pays. You'll see it confirmed in Payments, and they'll get a receipt.</p>
            <div className="detail-actions">
              <Link className="btn primary" to={`/admin/members/${sent.member.id}`}>View member</Link>
              <button className="btn" onClick={again}>Send another</button>
            </div>
          </div>
        ) : (
          <form className="form" onSubmit={send}>
            <div className="field">
              <span className="label">Member</span>
              {member ? (
                <div className="req-member">
                  <span className="avatar" aria-hidden="true">{member.name.slice(0, 1)}</span>
                  <div className="req-member-info">
                    <b>{member.name}</b>
                    <small>{member.code} · {phoneLocal(member.phone)}</small>
                    <MiniProgress percent={member.percent} />
                  </div>
                  <div className="req-bal"><small>Balance</small><b>{kes(member.balance)}</b></div>
                  {!preset && <button type="button" className="btn small" onClick={() => { setMember(null); setAmount('') }}>Change</button>}
                </div>
              ) : <MemberPicker onPick={setMember} />}
            </div>

            {member && (
              <>
                <div className="field">
                  <label htmlFor="rq-amount">Amount to request (KES)</label>
                  <input id="rq-amount" className="input" type="number" min="10" inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} />
                  {errors.amount && <p className="error">{errors.amount}</p>}
                  <div className="chips">
                    {quick.map((v) => (
                      <button type="button" key={v} className="chip" onClick={() => setAmount(String(v))}>
                        {v === Math.round(num(member.balance)) ? `Full balance · ${kes(v)}` : kes(v)}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="field">
                  <label htmlFor="rq-msg">Message (optional)</label>
                  <textarea id="rq-msg" className="input textarea" rows="3" maxLength="500" value={message} onChange={(e) => setMessage(e.target.value)}
                    placeholder="e.g. Kindly clear your balance before the end of the month." />
                </div>

                <label className="req-option">
                  <input type="checkbox" checked={mpesa} onChange={(e) => setMpesa(e.target.checked)} />
                  <span>
                    <b>Also send an M-Pesa prompt</b>
                    <small>{member.name.split(' ')[0]} gets a PIN prompt on {phoneLocal(member.phone)}</small>
                  </span>
                </label>

                {general && <p className="banner error" role="alert">{general}</p>}
                <div className="modal-actions">
                  <button type="button" className="btn" onClick={() => navigate(back)}>Cancel</button>
                  <button className="btn primary" type="submit" disabled={busy || num(amount) < 10}>
                    {busy ? 'Sending…' : `Send request · ${kes(amount)}`}
                  </button>
                </div>
              </>
            )}
          </form>
        )}
      </div>
    </div>
  )
}
