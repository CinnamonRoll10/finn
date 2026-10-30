import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import { fmtNum, pct, sign } from './fmt'
import { Bars, Bullet } from './ui'

const SECTIONS = [['snapshot', 'Snapshot'], ['trajectory', 'Trajectory'], ['balance', 'Balance & cash'], ['story', 'Story vs numbers'], ['guidance', 'Guidance'], ['bullbear', 'Bull / Bear']]

export default function Research({ symbol, setSymbol, onAsk }) {
  const [companies, setCompanies] = useState([])
  const [query, setQuery] = useState('')
  useEffect(() => { api.companies().then(setCompanies).catch(() => {}) }, [symbol])
  const go = (s) => { const v = s.trim().toUpperCase(); if (v) { setSymbol(v); setQuery('') } }

  return (
    <div className="screen">
      <div className="topbar"><span className="wordmark">FI<span>NN</span></span><span className="date">primary sources only</span></div>
      {!symbol && <><h1>Research</h1><p className="sub">Any NSE company. Built from its annual report and the last four earnings calls — no news, no broker notes.</p></>}
      <form onSubmit={(e) => { e.preventDefault(); go(query) }}>
        <input type="search" placeholder="NSE symbol, e.g. POLYCAB" value={query} onChange={(e) => setQuery(e.target.value)} autoCapitalize="characters" />
      </form>
      <div className="chips" style={{ marginTop: 8 }}>
        {companies.map((c) => <button key={c.symbol} className={`chip small ${c.symbol === symbol ? 'on' : ''}`} onClick={() => go(c.symbol)}>{c.research_ready && <span className="dot" />}{c.symbol}</button>)}
      </div>
      {symbol && <Company key={symbol} symbol={symbol} onAsk={onAsk} meta={companies.find((c) => c.symbol === symbol)} />}
    </div>
  )
}

function Company({ symbol, onAsk, meta }) {
  const [res, setRes] = useState(null)
  const [err, setErr] = useState(null)
  const [tab, setTab] = useState('story')
  const timer = useRef(null)

  const poll = async () => {
    try {
      const r = await api.research(symbol)
      setRes(r)
      if (r.status === 'building') timer.current = setTimeout(poll, 2500)
      if (r.status === 'error') setErr(r.progress?.error)
    } catch (e) { setErr(e.message) }
  }
  useEffect(() => { poll(); return () => clearTimeout(timer.current) }, [symbol]) // eslint-disable-line
  const build = async (force = false) => { setErr(null); await api.buildResearch(symbol, force); poll() }

  if (!res) return <div className="skeleton" />
  if (res.status !== 'ready') {
    const p = res.progress || {}
    return (
      <div className="card" style={{ marginTop: 14 }}>
        <div className="hero"><div className="nm">{meta?.name || symbol}</div><div className="meta">{meta?.sector}</div></div>
        {res.status === 'building' ? (
          <>
            <div className="progress"><i style={{ width: `${p.progress || 5}%` }} /></div>
            <p className="sub">{p.step || 'Starting'}…</p>
            <p className="note">Reads 4 transcripts + the annual report with a cheap model, then one strong-model pass. First build takes 1–3 minutes; after that it's instant.</p>
          </>
        ) : (
          <>
            {err && <div className="err">{err}</div>}
            <p className="sub">No research built yet for {symbol}.</p>
            <button className="btn wide" onClick={() => build(false)}>Build research</button>
          </>
        )}
      </div>
    )
  }

  const d = res.data, s = d.sections, f = d.facts, t = meta?.tape
  const top = d.top || {}
  return (
    <div>
      <div className="hero">
        <div className="nm">{d.name}</div>
        <div className="meta">
          {t && <span><b className="num">₹{fmtNum(t.close)}</b> <span className={sign(t.move_pct)}>{pct(t.move_pct)}</span></span>}
          {top['Market Cap'] && <span>Mcap <b>{top['Market Cap'].replace('₹ ', '₹')}</b></span>}
          {top['Stock P/E'] && <span>P/E <b>{top['Stock P/E']}</b></span>}
          {top['ROCE'] && <span>ROCE <b>{top['ROCE']}</b></span>}
          {top['ROE'] && <span>ROE <b>{top['ROE']}</b></span>}
        </div>
      </div>
      {s.one_liner && <p className="one">{s.one_liner}</p>}
      <div className="tabs">{SECTIONS.map(([k, l]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>)}</div>

      {tab === 'snapshot' && <>
        <h2 style={{ marginTop: 0 }}>Business</h2><ul className="bullets card">{(s.business || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
        <h2>Financial snapshot</h2><ul className="bullets card">{(s.financial_snapshot || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
        <Quarters f={f} />
      </>}
      {tab === 'trajectory' && <>
        <div className="card">
          <Bars title="Revenue (₹ cr)" labels={f.years.slice(-6)} values={f.annual.revenue.slice(-6)} fmt={(v) => fmtNum(v)} />
          <Bars title="PAT (₹ cr)" labels={f.years.slice(-6)} values={f.annual.pat.slice(-6)} fmt={(v) => fmtNum(v)} />
          <Bars title="Operating margin" labels={f.years.slice(-6)} values={f.annual.opm_pct.slice(-6)} unit="%" />
          <div className="meta" style={{ display: 'flex', gap: 14, fontSize: 12, color: 'var(--muted)', marginTop: 10 }}>
            <span>Rev CAGR 3y <b className="num" style={{ color: 'var(--ink)' }}>{pct(f.revenue_cagr_3y)}</b></span>
            <span>5y <b className="num" style={{ color: 'var(--ink)' }}>{pct(f.revenue_cagr_5y)}</b></span>
            <span>PAT CAGR 3y <b className="num" style={{ color: 'var(--ink)' }}>{pct(f.pat_cagr_3y)}</b></span>
          </div>
        </div>
        <ul className="bullets card">{(s.trajectory || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
      </>}
      {tab === 'balance' && <>
        {f.balance && <div className="card">
          <Bars title="Borrowings (₹ cr)" labels={f.balance.years.slice(-6)} values={f.balance.borrowings.slice(-6)} fmt={(v) => fmtNum(v)} />
          {f.cash && <Bars title="Free cash flow (₹ cr)" labels={f.cash.years.slice(-6)} values={f.cash.fcf.slice(-6)} fmt={(v) => fmtNum(v)} />}
          <div style={{ display: 'flex', gap: 14, fontSize: 12, color: 'var(--muted)', marginTop: 10, flexWrap: 'wrap' }}>
            <span>D/E <b className="num" style={{ color: 'var(--ink)' }}>{f.de_latest ?? '–'}</b></span>
            <span>CFO/PAT 3y <b className="num" style={{ color: 'var(--ink)' }}>{f.cfo_to_pat_3y ?? '–'}×</b></span>
            {f.ccc && <span>Cash cycle <b className="num" style={{ color: 'var(--ink)' }}>{f.ccc.latest}d</b> <span className="num">(was {f.ccc['3y_ago']}d)</span></span>}
            {f.roce && <span>ROCE <b className="num" style={{ color: 'var(--ink)' }}>{f.roce.latest}%</b></span>}
          </div>
        </div>}
        <h2>Balance sheet</h2><ul className="bullets card">{(s.balance_sheet || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
        <h2>Cash quality</h2><ul className="bullets card">{(s.cash_quality || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
      </>}
      {tab === 'story' && <>
        <p className="sub" style={{ marginTop: 0 }}>What management promised on each call, against what the next quarter actually printed.</p>
        <div className="ledger">
          {(s.ledger || []).map((r, i) => (
            <div className="lrow" key={i}>
              <span className="p">{r.period}</span>
              <div className="q"><b>Promised</b>{r.promised}</div>
              <span className={`verdict v ${r.verdict}`}>{r.verdict}</span>
              <div className="q" style={{ gridColumn: '1 / -1' }}><b>Delivered</b>{r.delivered}</div>
            </div>
          ))}
        </div>
        <h2>Narrative vs numbers</h2><ul className="bullets card">{(s.narrative_vs_numbers || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
        <div className="chips">{d.transcripts.map((tx) => <span key={tx.label} className="chip small" title={tx.tone_evidence}>{tx.quarter || tx.label} · {tx.tone}</span>)}</div>
      </>}
      {tab === 'guidance' && <>
        <ul className="bullets card">{(s.guidance || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
        {d.transcripts.map((tx) => (
          <div key={tx.label} className="card">
            <div className="co" style={{ fontWeight: 600 }}>{tx.quarter || tx.label} call <span className="note">· tone {tx.tone}</span></div>
            <ul className="bullets">{(tx.guidance || []).slice(0, 5).map((g, i) => <li key={i}><b style={{ fontWeight: 600 }}>{g.metric}:</b> {g.statement}{g.quote && <span className="note"> “{g.quote}”</span>}</li>)}</ul>
            {tx.analyst_pushback?.length > 0 && <p className="note" style={{ marginTop: 8 }}>Analysts pressed on: {tx.analyst_pushback[0]}</p>}
            <div className="actions"><a href={tx.url} target="_blank" rel="noreferrer">Transcript ↗</a></div>
          </div>
        ))}
      </>}
      {tab === 'bullbear' && <>
        <div className="two">
          <div className="card bull"><h3>Bull</h3><ul className="bullets">{(s.bull || []).map((b, i) => <Bullet key={i} text={b} />)}</ul></div>
          <div className="card bear"><h3>Bear</h3><ul className="bullets">{(s.bear || []).map((b, i) => <Bullet key={i} text={b} />)}</ul></div>
        </div>
        <h2>Ask management</h2>
        <div className="suggest">{(s.questions || []).map((q, i) => <button key={i} onClick={() => onAsk(symbol, q)}>{q}</button>)}</div>
      </>}

      <div className="actions" style={{ marginTop: 14, display: 'flex', gap: 10 }}>
        <button className="btn" onClick={() => onAsk(symbol, '')}>Ask about {symbol}</button>
        <button className="btn secondary" onClick={() => build(true)}>Rebuild</button>
      </div>
      <p className="note" style={{ marginTop: 14 }}>
        Sources: <a href={d.sources.screener} target="_blank" rel="noreferrer">screener.in</a>
        {d.sources.annual_report && <> · <a href={d.sources.annual_report.url} target="_blank" rel="noreferrer">Annual report {d.sources.annual_report.year}</a>{d.annual_report?.mda_page && ` (MD&A p.${d.annual_report.mda_page})`}</>}
        {' · '}{d.sources.transcripts.length} transcripts · {d.basis}. Built {d.built_at.slice(0, 16).replace('T', ' ')} with {d.model.fast} → {d.model.smart}.
      </p>
      {d.errors?.length > 0 && <p className="note">Skipped: {d.errors.join('; ')}</p>}
    </div>
  )
}

function Quarters({ f }) {
  if (!f.quarters?.length) return null
  return (
    <div className="card">
      <table className="qtable">
        <thead><tr><th>Quarter</th><th>Revenue</th><th>YoY</th><th>PAT</th><th>YoY</th><th>OPM</th></tr></thead>
        <tbody>{f.quarters.slice(-5).reverse().map((q) => (
          <tr key={q.q}><td>{q.q}</td><td className="num">{fmtNum(q.revenue)}</td><td className={`num ${sign(q.rev_yoy)}`}>{pct(q.rev_yoy)}</td><td className="num">{fmtNum(q.pat)}</td><td className={`num ${sign(q.pat_yoy)}`}>{pct(q.pat_yoy)}</td><td className="num">{q.opm_pct ?? '–'}%</td></tr>
        ))}</tbody>
      </table>
    </div>
  )
}
