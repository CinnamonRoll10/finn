import { useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { Masthead } from './ui'
import { PersonRow, Routes, Tie } from './net'

const RING = { 5: 46, 4: 78, 3: 110, 2: 140, 1: 158 }
const ASKS = ['Who should I reconnect with?', 'Who do I know at Swiggy?', 'Go-to people for rural lending?']

export default function Network({ openPerson, version, openResearch }) {
  const [net, setNet] = useState(null)
  const [err, setErr] = useState(null)
  const [theme, setTheme] = useState(null)
  const [allThemes, setAllThemes] = useState(false)
  const [q, setQ] = useState('')
  const [ans, setAns] = useState(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.network().then(setNet).catch((e) => setErr(e.message)) }, [version])

  const ask = async (text) => {
    if (!text.trim()) return
    setBusy(true); setQ(text)
    try { setAns(await api.networkAsk(text)) } catch (e) { setAns({ answer: e.message, people: [] }) } finally { setBusy(false) }
  }
  const s = net?.stats
  const themed = useMemo(() => (net && theme ? net.people.filter((p) => p.themes.includes(theme)).sort((a, b) => b.level + b.strength - a.level - a.strength) : []), [net, theme])

  return (
    <div className="screen">
      <Masthead right={net ? `${s.people} people · mock network` : 'your network'} />
      <h1>Who knows.</h1>
      <p className="deck">{net ? <>This week's filings touch <b>{s.lit}</b> of the {s.people} people you know. {s.uncovered.length === 0 ? `Every one of your ${s.book} companies has someone you can call.` : `${s.covered} of your ${s.book} companies have someone you can call.`}</> : 'The people you already know, mapped against what just happened.'}</p>

      <form onSubmit={(e) => { e.preventDefault(); ask(q) }}>
        <input type="search" placeholder="A company, a theme, or a name from a filing" value={q} onChange={(e) => { setQ(e.target.value); if (!e.target.value) setAns(null) }} />
      </form>
      {!ans && !busy && <div className="chips">{ASKS.map((a) => <button key={a} className="chip" onClick={() => ask(a)}>{a}</button>)}</div>}
      {busy && <div className="skeleton" />}
      {ans && !busy && (
        <div className="answer">
          <p className="one" style={{ marginTop: 10 }}>{ans.answer}</p>
          {ans.link && <Routes link={ans.link} onOpen={openPerson} />}
          <div className="plist">{ans.people.map((p) => <PersonRow key={p.id} p={p} onOpen={openPerson} />)}</div>
          <button className="clear" onClick={() => { setAns(null); setQ('') }}>Clear</button>
        </div>
      )}

      {err && <div className="err">{err}</div>}
      {!net && !err && <div className="skeleton" style={{ height: 200 }} />}
      {net && !ans && <>
        <Map people={net.people} theme={theme} onOpen={openPerson} />
        <div className="legend">
          <span><i className="lit" />employer filed this week</span>
          <span><i />quiet</span>
          <span><i className="cold" />not spoken in 5 months</span>
          <span>closer to centre = closer to you</span>
        </div>

        <h2>Expertise <span className="count">tap to light the map</span></h2>
        <div className="chips wrap">
          {net.themes.slice(0, allThemes ? 99 : 10).map((t) => <button key={t.theme} className={`chip ${theme === t.theme ? 'on' : ''}`} onClick={() => setTheme(theme === t.theme ? null : t.theme)}>{t.theme} · {t.count}</button>)}
          {!allThemes && net.themes.length > 10 && <button className="chip more" onClick={() => setAllThemes(true)}>+{net.themes.length - 10} more</button>}
        </div>
        {theme && <div className="plist">{themed.map((p) => <PersonRow key={p.id} compact p={{ ...p, label: p.org_now, why: p.now }} onOpen={openPerson} />)}</div>}

        {net.reconnect.length > 0 && <>
          <h2>A reason to call <span className="count">{net.reconnect.length}</span></h2>
          <p className="sub" style={{ marginTop: 8 }}>People you have not spoken to in five months, whose employer just filed something.</p>
          <div className="plist">{net.reconnect.map((p) => <PersonRow key={p.id} compact p={{ ...p, label: `${p.symbol} · last spoke ${p.ago}`, cold: false, why: p.headline }} onOpen={openPerson} />)}</div>
        </>}

        {s.uncovered.length > 0 && <>
          <h2>Blind spots <span className="count">{s.uncovered.length}</span></h2>
          <p className="sub" style={{ marginTop: 8 }}>You hold or follow these and know nobody near them.</p>
          <div className="chips wrap">{s.uncovered.map((x) => <button key={x} className="chip" onClick={() => openResearch(x)}>{x}</button>)}</div>
        </>}

        <h2>What Finn was given</h2>
        <ul className="bullets">{net.investor.gave_finn.map((g, i) => <li key={i}>{g}</li>)}</ul>
        <p className="sources">
          Every profile here is synthetic. Matching is plain code over careers and dates: no model is shown a contact, and nothing about your network leaves this server.
          {net.forgotten > 0 && <> {net.forgotten} erased. <button className="linkish" onClick={() => api.restoreNetwork().then(() => api.network().then(setNet))}>Restore demo data</button></>}
        </p>
      </>}
    </div>
  )
}

/** You at the centre; a ring per tie strength; themes share an arc; a filled node means their employer just filed. */
function Map({ people, theme, onOpen }) {
  const nodes = useMemo(() => {
    const order = [...people].sort((a, b) => a.theme.localeCompare(b.theme) || a.name.localeCompare(b.name))
    return order.map((p, i) => {
      const a = (i / order.length) * Math.PI * 2 - Math.PI / 2
      const r = RING[p.strength] || 150
      return { ...p, x: 170 + r * Math.cos(a), y: 170 + r * Math.sin(a), a }
    })
  }, [people])
  return (
    <svg className="netmap" viewBox="0 0 340 340" role="img" aria-label="Map of your network">
      {[46, 78, 110, 140].map((r) => <circle key={r} cx="170" cy="170" r={r} className="ring" />)}
      {nodes.map((n) => {
        const on = !theme || n.themes.includes(theme)
        return (
          <g key={n.id} className={`node ${n.live ? 'lit' : ''} ${n.cold ? 'cold' : ''} ${on ? '' : 'dim'}`} onClick={() => onOpen(n.id)}>
            {n.live > 0 && on && <line x1="170" y1="170" x2={n.x} y2={n.y} className="spoke" />}
            <circle cx={n.x} cy={n.y} r="15" className="hit" />
            {n.cold && n.live > 0 && <circle cx={n.x} cy={n.y} r={6.5 + n.level * 0.7} className="halo" />}
            <circle cx={n.x} cy={n.y} r={3 + n.level * 0.7} className="dot" />
          </g>
        )
      })}
      {nodes.map((n) => {
        const on = !theme || n.themes.includes(theme)
        const right = Math.cos(n.a) >= 0
        return (theme ? on : n.live > 0) && <text key={n.id} x={n.x + (right ? 10 : -10)} y={n.y + 3} textAnchor={right ? 'start' : 'end'}>{n.name.split(' ')[0]}</text>
      })}
      <circle cx="170" cy="170" r="13" className="me" /><text x="170" y="173" textAnchor="middle" className="me-t">You</text>
    </svg>
  )
}
