import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import { fmtNum, pct, sign } from './fmt'
import { Bars, Bullet, Masthead, Stat } from './ui'

const SECTIONS = [['story', 'Story vs numbers'], ['snapshot', 'Snapshot'], ['trajectory', 'Trajectory'], ['balance', 'Balance & cash'], ['guidance', 'Guidance'], ['bullbear', 'Bull / Bear']]

export default function Research({ symbol, setSymbol, onAsk }) {
  const [companies, setCompanies] = useState([])
  const [query, setQuery] = useState('')
  useEffect(() => { api.companies().then(setCompanies).catch(() => {}) }, [symbol])
  const go = (s) => { const v = s.trim().toUpperCase(); if (v) { setSymbol(v); setQuery('') } }

  return (
    <div className="screen">
      <Masthead right="primary sources" />
      {!symbol && <><h1>Research.</h1><p className="deck">Any NSE company, from its annual report and the last four earnings calls. No news, no broker notes.</p></>}
      <form onSubmit={(e) => { e.preventDefault(); go(query) }} style={{ marginTop: symbol ? 10 : 4 }}>
        <input type="search" placeholder="Type an NSE symbol, e.g. POLYCAB" value={query} onChange={(e) => setQuery(e.target.value)} autoCapitalize="characters" />
      </form>
      <div className="chips">
        {companies.map((c) => <button key={c.symbol} className={`chip ${c.symbol === symbol ? 'on' : ''}`} onClick={() => go(c.symbol)}>{c.research_ready && <span className="dot" />}{c.symbol}</button>)}
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
      <div>
        <div className="hero"><div className="nm">{meta?.name || symbol}</div><p className="kicker" style={{ marginTop: 6 }}>{meta?.sector}</p></div>
        {res.status === 'building' ? (
          <>
            <div className="progress"><i style={{ width: `${p.progress || 5}%` }} /></div>
            <p className="kicker"><span className="pulse" />{p.step || 'Starting'}</p>
            <p className="note">Four transcripts and the annual report are read by a cheap model, then one strong-model pass. First build takes one to three minutes; after that it is instant.</p>
          </>
        ) : (
          <>
            {err && <div className="err">{err}</div>}
            <p className="deck">Not read yet.</p>
            <button className="btn wide" onClick={() => build(false)}>Build research for {symbol}</button>
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
          {t && <Stat k="Close" v={<>₹{fmtNum(t.close)} <span className={sign(t.move_pct)} style={{ fontSize: 11 }}>{pct(t.move_pct)}</span></>} />}
          {top['Market Cap'] && <Stat k="Mkt cap" v={top['Market Cap'].replace('₹ ', '₹').replace(' Cr.', 'cr')} />}
          {top['Stock P/E'] && <Stat k="P/E" v={top['Stock P/E']} />}
          {top['ROCE'] && <Stat k="ROCE" v={top['ROCE'].replace(' ', '')} />}
        </div>
      </div>
      {s.one_liner && <p className="one">{s.one_liner}</p>}
      <div className="tabs">{SECTIONS.map(([k, l]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>)}</div>

      {tab === 'snapshot' && <>
        <h2 style={{ marginTop: 4 }}>Business</h2><ul className="bullets">{(s.business || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
        <h2>Financial snapshot</h2><ul className="bullets">{(s.financial_snapshot || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
        <Quarters f={f} />
      </>}
      {tab === 'trajectory' && <>
        <Bars title="Revenue, ₹ cr" labels={f.years.slice(-6)} values={f.annual.revenue.slice(-6)} fmt={(v) => fmtNum(v)} />
        <Bars title="Profit after tax, ₹ cr" labels={f.years.slice(-6)} values={f.annual.pat.slice(-6)} fmt={(v) => fmtNum(v)} />
        <Bars title="Operating margin" labels={f.years.slice(-6)} values={f.annual.opm_pct.slice(-6)} unit="%" />
        <div className="stats">
          <Stat k="Rev CAGR 3y" v={pct(f.revenue_cagr_3y)} />
          <Stat k="Rev CAGR 5y" v={pct(f.revenue_cagr_5y)} />
          <Stat k="PAT CAGR 3y" v={pct(f.pat_cagr_3y)} />
        </div>
        <h2>Direction</h2><ul className="bullets">{(s.trajectory || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
      </>}
      {tab === 'balance' && <>
        {f.balance && <>
          <Bars title="Borrowings, ₹ cr" labels={f.balance.years.slice(-6)} values={f.balance.borrowings.slice(-6)} fmt={(v) => fmtNum(v)} />
          {f.cash && <Bars title="Free cash flow, ₹ cr" labels={f.cash.years.slice(-6)} values={f.cash.fcf.slice(-6)} fmt={(v) => fmtNum(v)} />}
          <div className="stats">
            <Stat k="Debt / equity" v={f.de_latest} />
            <Stat k="CFO / PAT 3y" v={f.cfo_to_pat_3y != null ? `${f.cfo_to_pat_3y}×` : null} />
            {f.ccc && <Stat k="Cash cycle" v={`${f.ccc.latest}d`} />}
            {f.roce && <Stat k="ROCE" v={`${f.roce.latest}%`} />}
          </div>
        </>}
        <h2>Balance sheet</h2><ul className="bullets">{(s.balance_sheet || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
        <h2>Cash quality</h2><ul className="bullets">{(s.cash_quality || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
      </>}
      {tab === 'story' && <>
        <p className="sub" style={{ marginTop: 0, fontFamily: 'var(--serif)', fontStyle: 'italic', fontSize: 15 }}>What management promised on each call, against what the next quarter printed.</p>
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
        <h2>Narrative vs numbers</h2><ul className="bullets">{(s.narrative_vs_numbers || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
        <div className="chips">{d.transcripts.map((tx) => <span key={tx.label} className="chip" title={tx.tone_evidence}>{tx.quarter || tx.label} · {tx.tone}</span>)}</div>
      </>}
      {tab === 'guidance' && <>
        <ul className="bullets">{(s.guidance || []).map((b, i) => <Bullet key={i} text={b} />)}</ul>
        {d.transcripts.map((tx) => (
          <div key={tx.label}>
            <h2>{tx.quarter || tx.label} call <span className="count">tone · {tx.tone}</span></h2>
            <ul className="bullets">{(tx.guidance || []).slice(0, 5).map((g, i) => <li key={i}><span className="kicker">{g.metric}</span><br />{g.statement}{g.quote && <span className="note" style={{ display: 'block', fontStyle: 'italic', fontFamily: 'var(--serif)' }}>“{g.quote}”</span>}</li>)}</ul>
            {tx.analyst_pushback?.length > 0 && <p className="note">Analysts pressed on: {tx.analyst_pushback[0]}</p>}
            <div className="entry" style={{ padding: '6px 0 0', border: 0 }}><div className="actions" style={{ marginTop: 0 }}><a href={tx.url} target="_blank" rel="noreferrer">Transcript ↗</a></div></div>
          </div>
        ))}
      </>}
      {tab === 'bullbear' && <>
        <div className="two">
          <div className="bull"><h3>Bull</h3><ul className="bullets">{(s.bull || []).map((b, i) => <Bullet key={i} text={b} />)}</ul></div>
          <div className="bear"><h3>Bear</h3><ul className="bullets">{(s.bear || []).map((b, i) => <Bullet key={i} text={b} />)}</ul></div>
        </div>
        <h2>Ask management</h2>
        <div className="suggest">{(s.questions || []).map((q, i) => <button key={i} onClick={() => onAsk(symbol, q)}>{q}</button>)}</div>
      </>}

      <div style={{ marginTop: 18, display: 'flex', gap: 10 }}>
        <button className="btn" onClick={() => onAsk(symbol, '')}>Ask about {symbol}</button>
        <button className="btn secondary" onClick={() => build(true)}>Rebuild</button>
      </div>
      <p className="sources">
        Sources: <a href={d.sources.screener} target="_blank" rel="noreferrer">screener.in</a>
        {d.sources.annual_report && <> · <a href={d.sources.annual_report.url} target="_blank" rel="noreferrer">Annual report {d.sources.annual_report.year}</a>{d.annual_report?.mda_page && ` (MD&A p.${d.annual_report.mda_page})`}</>}
        {' · '}{d.sources.transcripts.length} transcripts · {d.basis}. Built {d.built_at.slice(0, 16).replace('T', ' ')} with {d.model.fast} → {d.model.smart}.
        {d.errors?.length > 0 && <> Skipped: {d.errors.join('; ')}</>}
      </p>
    </div>
  )
}

function Quarters({ f }) {
  if (!f.quarters?.length) return null
  return (
    <table className="qtable">
      <thead><tr><th>Quarter</th><th>Revenue</th><th>YoY</th><th>PAT</th><th>YoY</th><th>OPM</th></tr></thead>
      <tbody>{f.quarters.slice(-5).reverse().map((q) => (
        <tr key={q.q}><td>{q.q}</td><td>{fmtNum(q.revenue)}</td><td className={sign(q.rev_yoy)}>{pct(q.rev_yoy)}</td><td>{fmtNum(q.pat)}</td><td className={sign(q.pat_yoy)}>{pct(q.pat_yoy)}</td><td>{q.opm_pct ?? '–'}%</td></tr>
      ))}</tbody>
    </table>
  )
}
