import { useEffect, useState } from 'react'
import { CAT_LABEL, fmtNum, timeAgo } from './fmt'
import { Pill, Spark } from './ui'

const ALERTABLE = ['results', 'M&A', 'management_change', 'fund_raise', 'litigation', 'credit_rating', 'pledging', 'capex', 'dividend', 'bonus_split', 'insider_trading', 'press_release']

export default function Alerts({ digest, settings, saveSettings, reload, onAsk, openResearch, markSeen }) {
  const [th, setTh] = useState(settings?.thresholds || { price_move_pct: 4, volume_multiple: 2, lookback_days: 20 })
  const [cats, setCats] = useState(new Set(settings?.alert_categories || []))
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  useEffect(() => { markSeen() }, [digest]) // eslint-disable-line
  useEffect(() => { if (settings) { setTh(settings.thresholds); setCats(new Set(settings.alert_categories)) } }, [settings])

  const alerts = digest?.alerts || []
  const tape = Object.fromEntries((digest?.tape || []).map((t) => [t.symbol, t]))
  const save = async () => {
    setSaving(true)
    await saveSettings({ thresholds: th, alert_categories: [...cats] })
    setDirty(false); setSaving(false); reload()
  }
  const upd = (k, v) => { setTh({ ...th, [k]: v }); setDirty(true) }
  const toggle = (c) => { const n = new Set(cats); n.has(c) ? n.delete(c) : n.add(c); setCats(n); setDirty(true) }

  return (
    <div className="screen">
      <div className="topbar"><span className="wordmark">FI<span>NN</span></span><span className="date">watching {settings?.portfolio?.length || 0} companies</span></div>
      <h1>Alerts</h1>
      <p className="sub">You decide what "unusual" means. FINN watches end-of-day data and every filing for it.</p>

      <div className="card">
        <div className="field"><label><span>Price move beyond</span><b>±{Number(th.price_move_pct).toFixed(1)}%</b></label>
          <input type="range" min="1" max="15" step="0.5" value={th.price_move_pct} onChange={(e) => upd('price_move_pct', +e.target.value)} /></div>
        <div className="field"><label><span>Volume above</span><b>{Number(th.volume_multiple).toFixed(1)}× avg</b></label>
          <input type="range" min="1.2" max="6" step="0.1" value={th.volume_multiple} onChange={(e) => upd('volume_multiple', +e.target.value)} /></div>
        <div className="field"><label><span>Average over</span><b>{th.lookback_days} days</b></label>
          <input type="range" min="5" max="60" step="5" value={th.lookback_days} onChange={(e) => upd('lookback_days', +e.target.value)} /></div>
        <div className="field"><label><span>Filing types that alert immediately</span></label>
          <div className="chips" style={{ flexWrap: 'wrap' }}>
            {ALERTABLE.map((c) => <button key={c} className={`chip small ${cats.has(c) ? 'on' : ''}`} onClick={() => toggle(c)}>{CAT_LABEL[c]}</button>)}
          </div></div>
        <button className="btn wide" disabled={!dirty || saving} onClick={save}>{saving ? 'Saving…' : dirty ? 'Save & re-scan' : 'Saved'}</button>
      </div>

      <h2>Triggered <span className="count">{alerts.length}</span></h2>
      {!digest && <div className="skeleton" />}
      {digest && alerts.length === 0 && <div className="empty">Nothing crossed your thresholds in this window.</div>}
      {alerts.map((a) => (
        <div className="card" key={a.id}>
          <div className="head">
            <div className="co"><button onClick={() => openResearch(a.symbol)}>{a.name}</button><small>{a.symbol}</small></div>
            <span className="when">{timeAgo(a.time)}</span>
          </div>
          {a.kind === 'filing' ? <Pill cat={a.category} /> : <Pill tone={a.kind === 'price' ? (a.value > 0 ? 'green' : 'red') : 'amber'}>{a.kind === 'price' ? 'Price move' : 'Volume spike'}</Pill>}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
            <div className="headline">{a.title}</div>
            {a.kind !== 'filing' && tape[a.symbol] && <Spark data={tape[a.symbol].spark} />}
          </div>
          {a.detail && <p className="why">{a.detail}</p>}
          <div className="actions">
            <button onClick={() => onAsk(a.symbol, a.kind === 'filing' ? 'Does this change the investment case?' : 'Is there anything in the fundamentals or recent guidance that explains an unusual move?', `${a.name}: ${a.title}. ${a.detail || ''}`)}>Ask FINN</button>
            <button className="ghost" onClick={() => openResearch(a.symbol)}>Research</button>
          </div>
        </div>
      ))}
      {digest?.tape && (
        <>
          <h2>End of day</h2>
          <div className="list">
            {[...digest.tape].sort((a, b) => Math.abs(b.move_pct) - Math.abs(a.move_pct)).map((t) => (
              <div className="row" key={t.symbol} style={{ alignItems: 'center' }}>
                <div className="main"><div className="hl">{t.symbol} <span className="note">₹{fmtNum(t.close)}</span></div><div className="note">vol {t.volume_x}× · 1w {t.ret_1w_pct > 0 ? '+' : ''}{t.ret_1w_pct}% · 1m {t.ret_1m_pct > 0 ? '+' : ''}{t.ret_1m_pct}%</div></div>
                <Spark data={t.spark} />
                <span className={`num ${t.move_pct > 0 ? 'up' : t.move_pct < 0 ? 'down' : ''}`} style={{ width: 56, textAlign: 'right', fontWeight: 600 }}>{t.move_pct > 0 ? '+' : ''}{t.move_pct}%</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
