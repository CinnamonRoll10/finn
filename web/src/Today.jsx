import { useState } from 'react'
import { fmtCr, fmtNum, pct, sign, timeAgo } from './fmt'
import { Delta, Pill } from './ui'

const WINDOWS = [[24, '24h'], [72, '3d'], [168, '7d'], [720, '30d']]

export default function Today({ digest, loading, error, win, setWin, onAsk, openResearch }) {
  const [custom, setCustom] = useState(false)
  const [routineOpen, setRoutineOpen] = useState(false)
  const items = digest?.items || []
  const attention = items.filter((i) => i.tier === 'attention')
  const glance = items.filter((i) => i.tier === 'glance')
  const routine = items.filter((i) => i.tier === 'routine')
  const today = new Date().toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })

  return (
    <div className="screen">
      <div className="topbar"><span className="wordmark">FI<span>NN</span></span><span className="date">{today}</span></div>
      <h1>What changed</h1>
      <p className="sub">{digest ? `${digest.counts.total} filings across your portfolio · ${digest.counts.attention} need attention · ${digest.counts.routine} routine hidden` : 'Filings, prioritised. Routine paperwork hidden.'}</p>

      <div className="chips">
        {WINDOWS.map(([h, l]) => <button key={h} className={`chip ${!custom && win.hours === h ? 'on' : ''}`} onClick={() => { setCustom(false); setWin({ hours: h }) }}>{l}</button>)}
        <button className={`chip ${custom ? 'on' : ''}`} onClick={() => setCustom(true)}>Custom</button>
      </div>
      {custom && (
        <div style={{ display: 'flex', gap: 8, margin: '4px 0 10px' }}>
          <input type="date" value={win.from || ''} onChange={(e) => setWin({ from: e.target.value, to: win.to || e.target.value })} />
          <input type="date" value={win.to || ''} onChange={(e) => setWin({ from: win.from || e.target.value, to: e.target.value })} />
        </div>
      )}

      {digest?.tape?.length > 0 && (
        <div className="tape">
          {[...digest.tape].sort((a, b) => b.flags.length - a.flags.length || Math.abs(b.move_pct) - Math.abs(a.move_pct)).map((t) => (
            <button key={t.symbol} className={`t ${t.flags.length ? 'flag' : ''}`} onClick={() => openResearch(t.symbol)}>
              <span className="sym">{t.symbol}</span>
              <span className={`mv num ${sign(t.move_pct)}`}>{pct(t.move_pct)}</span>
              <span className="vx num">{t.flags.includes('volume') ? `vol ${t.volume_x}×` : `₹${fmtNum(t.close)}`}</span>
            </button>
          ))}
        </div>
      )}

      {error && <div className="err">{error}</div>}
      {loading && !digest && <><div className="skeleton" /><div className="skeleton" style={{ width: '70%' }} /><div className="skeleton" style={{ width: '85%' }} /></>}
      {loading && digest && <p className="sub">Refreshing…</p>}
      {digest && !digest.complete && <p className="sub"><span className="dot" style={{ display: 'inline-block', width: 6, height: 6, borderRadius: 3, background: 'var(--accent)', marginRight: 6 }} />Reading {digest.pending} filings for detail…</p>}

      {digest && attention.length > 0 && <h2>Needs attention <span className="count">{attention.length}</span></h2>}
      {attention.map((it) => <Card key={it.id} it={it} onAsk={onAsk} openResearch={openResearch} />)}

      {digest && glance.length > 0 && <h2>Worth a glance <span className="count">{glance.length}</span></h2>}
      {glance.length > 0 && <div className="list">{glance.map((it) => <Row key={it.id} it={it} onAsk={onAsk} />)}</div>}

      {digest && routine.length > 0 && (
        <>
          <h2>Routine</h2>
          {!routineOpen ? (
            <button className="collapsed" onClick={() => setRoutineOpen(true)}><span>{routine.length} routine filings hidden — ESOPs, certificates, newspaper ads, meeting notices</span><span>Show</span></button>
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

function Card({ it, onAsk, openResearch }) {
  const q = it.category === 'results' ? 'Did this quarter deliver what management guided on the last call?'
    : it.category === 'management_change' ? 'What does this change mean for continuity and strategy?'
    : it.category === 'M&A' ? 'How does this deal fit the strategy and balance sheet?'
    : it.category === 'capex' ? 'Does this capex match what management guided?'
    : 'What should I make of this filing given the fundamentals?'
  return (
    <div className="card">
      <div className="head">
        <div className="co"><button onClick={() => openResearch(it.symbol)}>{it.name}</button><small>{it.sector}</small></div>
        <span className="when">{timeAgo(it.time)}</span>
      </div>
      <Pill cat={it.category} />{it.subtype === 'scheduled' && <Pill tone="grey">date set</Pill>}
      <div className="headline">{it.headline}</div>
      {it.why && it.why !== 'Routine.' && <p className="why">{it.why}</p>}
      {it.results && <Results r={it.results} />}
      {it.people && <People p={it.people} />}
      <div className="actions">
        {it.pdf_url && <a href={it.pdf_url} target="_blank" rel="noreferrer">Filing ↗</a>}
        <button onClick={() => onAsk(it.symbol, q, `${it.name}: ${it.headline}. ${it.why || ''} (${it.nse_type}, ${it.time})`)}>Ask FINN</button>
        <button className="ghost" onClick={() => openResearch(it.symbol)}>Research</button>
      </div>
    </div>
  )
}

function Row({ it, muted, onAsk }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="row" onClick={() => setOpen(!open)}>
      <div className="main">
        <div className="co"><b style={{ color: 'var(--ink)' }}>{it.symbol}</b><Pill cat={it.category} /></div>
        <div className={`hl ${muted ? 'muted' : ''}`}>{it.headline}</div>
        {open && (
          <div style={{ marginTop: 6 }}>
            {it.why && <p className="why" style={{ margin: '0 0 6px', fontSize: 13 }}>{it.why}</p>}
            <p className="note" style={{ margin: 0 }}>{it.nse_type} · {it.subject?.slice(0, 220)}</p>
            <div className="actions" style={{ marginTop: 6 }}>
              {it.pdf_url && <a href={it.pdf_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>Filing ↗</a>}
              <button onClick={(e) => { e.stopPropagation(); onAsk(it.symbol, 'What should I make of this filing given the fundamentals?', `${it.name}: ${it.headline} (${it.nse_type})`) }}>Ask FINN</button>
            </div>
          </div>
        )}
      </div>
      <span className="when">{timeAgo(it.time)}</span>
    </div>
  )
}

export function Results({ r }) {
  return (
    <div>
      <div className="kpi">
        <span className="h">{r.period || 'Quarter'}</span><span className="h" style={{ textAlign: 'right' }}>{r.unit?.replace('Rs', '₹') || '₹ cr'}</span><span className="h" style={{ textAlign: 'right' }}>QoQ</span><span className="h" style={{ textAlign: 'right' }}>YoY</span>
        {r.rows.map((row) => (
          <RowK key={row.metric} row={row} />
        ))}
      </div>
      <div className="note">{r.basis && `${r.basis}. `}{r.rows.some((x) => x.derived) && 'EBITDA derived as PBT + finance cost + depreciation. '}{r.notes}{r.source === 'screener' ? '' : ' Source: results filing.'}</div>
    </div>
  )
}
const RowK = ({ row }) => (
  <>
    <span className="m">{row.metric}</span>
    <span className="v num">{row.value == null ? '–' : fmtNum(row.value, Math.abs(row.value) < 100 ? 1 : 0)}</span>
    <Delta v={row.qoq_pct} /><Delta v={row.yoy_pct} />
  </>
)

export function People({ p }) {
  return (
    <div>
      {p.changes.map((c, i) => (
        <div className="person" key={i}>
          <div className="n">{c.person} <span className="r">· {c.event}{c.effective ? ` · ${c.effective}` : ''}</span></div>
          <div className="r">{c.role}{c.is_kmp ? ' · KMP' : ''}</div>
          {c.background && <div className="b">{c.background}</div>}
          {c.reason && <div className="b" style={{ color: 'var(--muted)' }}>Reason: {c.reason}</div>}
        </div>
      ))}
      {p.so_what && <p className="why" style={{ marginTop: 6 }}>{p.so_what}</p>}
    </div>
  )
}
