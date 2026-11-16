import { useEffect, useState } from 'react'
import { api } from './api'
import { timeAgo } from './fmt'
import { Tag } from './ui'

/** How well you know someone, 1 to 5, as five ticks. */
export const Tie = ({ n, title }) => (
  <span className="tie" title={title || `Tie strength ${n} of 5`} aria-label={`Tie strength ${n} of 5`}>
    {[1, 2, 3, 4, 5].map((i) => <i key={i} className={i <= n ? 'on' : ''} />)}
  </span>
)

/** One contact, with the reason they matter here. The whole row opens their sheet. */
export function PersonRow({ p, onOpen, compact }) {
  return (
    <button className={`prow ${compact ? 'compact' : ''}`} onClick={() => onOpen(p.id)}>
      <span className="top">
        <span className="n">{p.name}</span>
        <Tie n={p.strength} />
      </span>
      {p.label && <span className="kicker">{p.label}{p.cold ? ` · last spoke ${p.ago}` : ''}</span>}
      {p.why && <span className="w">{p.why}</span>}
      {!compact && p.knows && <span className="k">Would know: {p.knows}</span>}
      {p.ask && <span className="q">Ask: {p.ask}</span>}
      {p.caution && <span className="caution">{p.caution}</span>}
    </button>
  )
}

/** Inside a pushed filing: the one person best placed to explain it. */
export function Pointer({ net, onOpen }) {
  if (!net?.lead) return null
  const l = net.lead
  return (
    <button className="pointer" onClick={() => onOpen(l.id)}>
      <span className="kicker">In your network · {l.label.toLowerCase()}</span>
      <span className="who"><b>{l.name}</b><Tie n={l.strength} /></span>
      <span className="w">{l.why}</span>
      <span className="q">Ask: {net.ask}</span>
      <span className="foot">Last spoke {l.ago}{net.more > 0 && ` · ${net.more} more`}</span>
    </button>
  )
}

/** Routes from you to a person named in a filing, each with the evidence it rests on. */
export function Routes({ link, onOpen }) {
  if (!link) return null
  const last = link.person.replace(/^(Mr|Ms|Mrs|Dr|Prof|Shri)\.?\s+/i, '').split(' ').slice(-1)[0]
  if (link.direct) {
    return <button className="pointer" onClick={() => onOpen(link.direct.id)}><span className="kicker">In your network</span><span className="w">{link.note} {link.direct.how}.</span></button>
  }
  if (!link.links.length && !link.you) return link.note ? <div className="routes none">{link.note}</div> : null
  return (
    <div className="routes">
      <span className="kicker">Routes to {last}</span>
      {link.you && <div className="route you"><span className="via">You · {link.you.via.toLowerCase()}</span><span className="w">{link.you.detail}</span></div>}
      {link.links.map((l) => (
        <button className="route" key={l.id} onClick={() => onOpen(l.id)}>
          <span className="top"><b>{l.name}</b><Tie n={l.strength} title={`Chain strength ${l.strength} of 5: you know ${l.name.split(' ')[0]} ${l.tie}/5`} /></span>
          <span className={`via ${l.confirmed ? 'ok' : ''}`}>{l.via}{l.confirmed ? '' : ' · unconfirmed'}</span>
          <span className="w">{l.detail}</span>
        </button>
      ))}
    </div>
  )
}

/** The week's filings turned into the few calls worth making. */
export function CallSheet({ sheet, windowLabel, onOpen, max = 3 }) {
  const [copied, setCopied] = useState(null)
  if (!sheet?.length) return null
  const copy = (c) => { navigator.clipboard?.writeText(c.opener); setCopied(c.id); setTimeout(() => setCopied(null), 1600) }
  return (
    <>
      <h2>Call sheet <span className="count">{windowLabel || 'this window'}</span></h2>
      <div className="sheet-list">
        {sheet.slice(0, max).map((c, i) => (
          <div className="call" key={c.id}>
            <span className="no">{String(i + 1).padStart(2, '0')}</span>
            <div className="body">
              <button className="who" onClick={() => onOpen(c.id)}><b>{c.name}</b><Tie n={c.strength} /></button>
              <div className="because"><Tag cat={c.category} /><span>{c.symbol} · {c.headline}</span></div>
              <p className="w">{c.why}</p>
              {c.ask && <p className="q">Ask: {c.ask}</p>}
              <div className="actions">
                <button onClick={() => copy(c)}>{copied === c.id ? 'Copied' : 'Copy opener'}</button>
                <button className="ghost" onClick={() => onOpen(c.id)}>Profile</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

/** Bottom sheet: everything FINN holds about one contact, and why they matter this week. */
export function PersonSheet({ id, onClose, openResearch, onChanged }) {
  const [p, setP] = useState(null)
  const [err, setErr] = useState(null)
  const [copied, setCopied] = useState(false)
  const [confirm, setConfirm] = useState(false)
  useEffect(() => { setP(null); setErr(null); setConfirm(false); api.person(id).then(setP).catch((e) => setErr(e.message)) }, [id])
  useEffect(() => {
    const k = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k); document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', k); document.body.style.overflow = '' }
  }, [onClose])
  const log = async () => { setP(await api.logContact(id)); onChanged?.() }
  const forget = async () => { await api.forget(id); onChanged?.(); onClose() }
  const copy = (t) => { navigator.clipboard?.writeText(t); setCopied(true); setTimeout(() => setCopied(false), 1600) }

  return (
    <div className="scrim" onClick={onClose}>
      <div className="psheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <button className="grab" onClick={onClose} aria-label="Close" />
        {err && <div className="err">{err}</div>}
        {!p && !err && <><div className="skeleton" /><div className="skeleton" style={{ width: '70%' }} /></>}
        {p && <>
          <div className="nm">{p.name}</div>
          <div className="now">{p.now}{p.city ? ` · ${p.city}` : ''}</div>
          <p className="how">{p.how}.</p>
          <div className="stats">
            <span><span className="k">Tie</span><b><Tie n={p.strength} /></b></span>
            <span><span className="k">Last spoke</span><b className={p.cold ? 'down' : 'num'}>{p.ago}</b></span>
            <span><span className="k">Source</span><b className="num">{p.source}</b></span>
          </div>

          {p.live.length > 0 && <>
            <h2>Why now</h2>
            {p.live.map((l) => (
              <div className="why-now" key={l.item_id}>
                <div className="because"><Tag cat={l.category} /><span>{l.symbol} · {timeAgo(l.time)} · {l.tie} employer</span></div>
                <div className="hl">{l.headline}</div>
              </div>
            ))}
            <div className="opener">
              <span className="kicker">A way in</span>
              <p>{p.live[0].opener}</p>
              <button onClick={() => copy(p.live[0].opener)}>{copied ? 'Copied' : 'Copy'}</button>
            </div>
          </>}
          {p.caution && <div className="caution block">{p.caution}</div>}

          <h2>Career</h2>
          <div className="career">
            {p.career.map((c, i) => (
              <div className="job" key={i}>
                <span className="yr">{c.from}–{c.to ? String(c.to).slice(2) : 'now'}</span>
                <div>
                  <div className="role">{c.role}</div>
                  <div className="org">{c.org}{c.in_book && <button onClick={() => { onClose(); openResearch(c.symbol) }}>{c.symbol} ↗</button>}</div>
                  {c.knows && <div className="knows">{c.knows}</div>}
                </div>
              </div>
            ))}
            {p.education.map((e, i) => (
              <div className="job" key={`e${i}`}><span className="yr">{e.year}</span><div><div className="role">{e.degree}</div><div className="org">{e.inst}</div></div></div>
            ))}
          </div>

          {(p.shared.length > 0 || p.mutual.length > 0) && <>
            <h2>What connects you</h2>
            <ul className="bullets">
              {p.shared.map((s, i) => <li key={i}>{s}</li>)}
              {p.mutual.map((m) => <li key={m.id}>Also knows {m.name}: {m.detail}</li>)}
            </ul>
          </>}

          <div className="sheet-actions">
            <button className="btn" onClick={log}>{p.days_since === 0 ? 'Logged today' : 'I spoke to them today'}</button>
            {!confirm ? <button className="btn secondary" onClick={() => setConfirm(true)}>Forget</button>
              : <button className="btn danger" onClick={forget}>Erase {p.name.split(' ')[0]}</button>}
          </div>
          <p className="sources">{p.provenance}</p>
        </>}
      </div>
    </div>
  )
}
