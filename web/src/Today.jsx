import { useState } from 'react'
import { fmtNum, pct, sign, timeAgo } from './fmt'
import { Delta, Masthead, Tag } from './ui'

const WINDOWS = [[24, '24h'], [72, '3 days'], [168, '7 days'], [720, '30 days']]

export default function Today({ digest, loading, error, win, setWin, onAsk, openResearch }) {
  const [custom, setCustom] = useState(false)
  const [routineOpen, setRoutineOpen] = useState(false)
  const items = digest?.items || []
  const attention = items.filter((i) => i.tier === 'attention')
  const glance = items.filter((i) => i.tier === 'glance')
  const routine = items.filter((i) => i.tier === 'routine')
  const n = digest?.counts

  return (
    <div className="screen">
      <Masthead right={digest ? `${digest.tape?.length || 0} companies · NSE` : 'NSE · EOD'} />
      <h1>What changed.</h1>
      <p className="deck">{n ? <>{n.total} filings in the window. <b style={{ fontStyle: 'normal', fontWeight: 500, color: 'var(--ink)' }}>{n.attention}</b> need your attention, {n.glance} worth a glance, {n.routine} routine and hidden.</> : 'Every filing across your portfolio, triaged. Routine paperwork hidden.'}</p>

      <div className="seg">
        {WINDOWS.map(([h, l]) => <button key={h} className={!custom && win.hours === h ? 'on' : ''} onClick={() => { setCustom(false); setWin({ hours: h }) }}>{l}</button>)}
        <button className={custom ? 'on' : ''} onClick={() => setCustom(true)}>Custom</button>
      </div>
      {custom && (
        <div className="dates">
          <input type="date" value={win.from || ''} onChange={(e) => setWin({ from: e.target.value, to: win.to || e.target.value })} />
          <input type="date" value={win.to || ''} onChange={(e) => setWin({ from: win.from || e.target.value, to: e.target.value })} />
        </div>
      )}

      {digest?.tape?.length > 0 && (
        <div className="tape">
          {[...digest.tape].sort((a, b) => b.flags.length - a.flags.length || Math.abs(b.move_pct) - Math.abs(a.move_pct)).map((t) => (
            <button key={t.symbol} className={`t ${t.flags.length ? 'flag' : ''}`} onClick={() => openResearch(t.symbol)}>
              <span className="sym">{t.symbol}</span>
              <span className={`mv ${sign(t.move_pct)}`}>{pct(t.move_pct)}</span>
              <span className="vx">{t.flags.includes('volume') ? `${t.volume_x}× vol` : `₹${fmtNum(t.close)}`}</span>
            </button>
          ))}
        </div>
      )}

      {error && <div className="err">{error}</div>}
      {loading && !digest && <><div className="skeleton" /><div className="skeleton" style={{ width: '70%' }} /><div className="skeleton" style={{ width: '85%' }} /></>}
      {digest && !digest.complete && <p className="kicker" style={{ marginTop: 12 }}><span className="pulse" />Reading {digest.pending} filings for detail</p>}

      {digest && attention.length > 0 && <h2>Needs attention <span className="count">{attention.length}</span></h2>}
      {attention.map((it) => <Entry key={it.id} it={it} onAsk={onAsk} openResearch={openResearch} />)}

      {digest && glance.length > 0 && <h2>Worth a glance <span className="count">{glance.length}</span></h2>}
      {glance.length > 0 && <div className="list">{glance.map((it) => <Row key={it.id} it={it} onAsk={onAsk} />)}</div>}

      {digest && routine.length > 0 && (
        <>
          <h2>Routine <span className="count">{routine.length}</span></h2>
          {!routineOpen ? (
            <button className="collapsed" onClick={() => setRoutineOpen(true)}><span>{routine.length} filings hidden: ESOPs, certificates, newspaper ads, meeting notices.</span><span>Show</span></button>
          ) : (
            <div className="list">{routine.map((it) => <Row key={it.id} it={it} muted onAsk={onAsk} />)}</div>
          )}
        </>
      )}
      {digest && items.length === 0 && <div className="empty">Nothing filed in this window.</div>}
      {digest?.failed_symbols?.length > 0 && <p className="note">NSE did not respond for: {digest.failed_symbols.join(', ')}</p>}
    </div>
  )
}

function Entry({ it, onAsk, openResearch }) {
  const q = it.category === 'results' ? 'Did this quarter deliver what management guided on the last call?'
    : it.category === 'management_change' ? 'What does this change mean for continuity and strategy?'
    : it.category === 'M&A' ? 'How does this deal fit the strategy and balance sheet?'
    : it.category === 'capex' ? 'Does this capex match what management guided?'
    : 'What should I make of this filing given the fundamentals?'
  return (
    <div className="entry">
      <div className="head">
        <div className="co"><button onClick={() => openResearch(it.symbol)}>{it.name}</button><small>{it.sector}</small></div>
        <span className="when">{timeAgo(it.time)}</span>
      </div>
      <div className="headline">{it.headline}</div>
      <div className="tagrow"><Tag cat={it.category} />{it.subtype === 'scheduled' && <Tag tone="grey">date set</Tag>}</div>
      {it.why && it.why !== 'Routine.' && <p className="why" style={{ marginTop: 8 }}>{it.why}</p>}
      {it.results && <Results r={it.results} />}
      {it.people && <People p={it.people} />}
      <div className="actions">
        <button onClick={() => onAsk(it.symbol, q, `${it.name}: ${it.headline}. ${it.why || ''} (${it.nse_type}, ${it.time})`)}>Ask Finn</button>
        <button className="ghost" onClick={() => openResearch(it.symbol)}>Research</button>
        {it.pdf_url && <a className="ghost" href={it.pdf_url} target="_blank" rel="noreferrer">Filing ↗</a>}
      </div>
    </div>
  )
}

function Row({ it, muted, onAsk }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="row" onClick={() => setOpen(!open)}>
      <div className="main">
        <div className="co"><b>{it.symbol}</b><Tag cat={it.category} /></div>
        <div className={`hl ${muted ? 'muted' : ''}`}>{it.headline}</div>
        {open && (
          <div style={{ marginTop: 6 }}>
            {it.why && <p className="why" style={{ margin: '0 0 6px', fontSize: 13.5, color: 'var(--ink-2)' }}>{it.why}</p>}
            <p className="note" style={{ margin: 0 }}>{it.nse_type} · {it.subject?.slice(0, 220)}</p>
            <div className="entry" style={{ padding: 0, border: 0 }}><div className="actions" style={{ marginTop: 8 }}>
              <button onClick={(e) => { e.stopPropagation(); onAsk(it.symbol, 'What should I make of this filing given the fundamentals?', `${it.name}: ${it.headline} (${it.nse_type})`) }}>Ask Finn</button>
              {it.pdf_url && <a className="ghost" href={it.pdf_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>Filing ↗</a>}
            </div></div>
          </div>
        )}
      </div>
      <span className="when">{timeAgo(it.time)}</span>
    </div>
  )
}

export function Results({ r }) {
  const [head, tail] = String(r.period || 'Quarter').split(/\s*\(/)
  return (
    <div>
      <div className="kpi">
        <span className="h">{head}</span><span className="h">₹ cr</span><span className="h">QoQ</span><span className="h">YoY</span>
        {r.rows.map((row) => <RowK key={row.metric} row={row} />)}
      </div>
      <div className="note">{tail && `${tail.replace(/\)$/, '')}. `}{r.basis && `${r.basis[0].toUpperCase()}${r.basis.slice(1)}. `}{r.rows.some((x) => x.derived) && 'EBITDA = PBT + finance cost + depreciation. '}{r.notes}</div>
    </div>
  )
}
const RowK = ({ row }) => (
  <>
    <span className="m">{row.metric}</span>
    <span className="v">{row.value == null ? '–' : fmtNum(row.value, Math.abs(row.value) < 100 ? 1 : 0)}</span>
    <Delta v={row.qoq_pct} /><Delta v={row.yoy_pct} />
  </>
)

export function People({ p }) {
  return (
    <div>
      {p.changes.map((c, i) => (
        <div className="person" key={i}>
          <div className="n">{c.person}</div>
          <div className="r">{c.event}{c.effective ? ` · ${c.effective}` : ''} · {c.role}{c.is_kmp ? ' · KMP' : ''}</div>
          {c.background && <div className="b">{c.background}</div>}
          {c.reason && <div className="b" style={{ color: 'var(--ink-3)' }}>Reason given: {c.reason}</div>}
        </div>
      ))}
      {p.so_what && <p className="why" style={{ marginTop: 8 }}>{p.so_what}</p>}
    </div>
  )
}
