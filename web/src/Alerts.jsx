import { useEffect, useState } from 'react'
import { CAT_LABEL, fmtNum, pct, sign, timeAgo } from './fmt'
import { Masthead, Spark, Tag } from './ui'

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
      <Masthead right={`watching ${settings?.portfolio?.length || 0}`} />
      <h1>Alerts.</h1>
      <p className="deck">You decide what "unusual" means. Finn watches the close and every filing for it.</p>

      <h2>Triggered <span className="count">{alerts.length}</span></h2>
      {!digest && <div className="skeleton" />}
      {digest && alerts.length === 0 && <div className="empty">Nothing crossed your thresholds in this window.</div>}
      {alerts.map((a) => (
        <div className="entry" key={a.id}>
          <div className="head">
            <div className="co"><button onClick={() => openResearch(a.symbol)}>{a.name}</button><small>{a.symbol}</small></div>
            <span className="when">{timeAgo(a.time)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
            <div className="headline">{a.title}</div>
            {a.kind !== 'filing' && tape[a.symbol] && <Spark data={tape[a.symbol].spark} />}
          </div>
          {a.kind === 'filing' ? <Tag cat={a.category} /> : <Tag tone={a.kind === 'price' ? (a.value > 0 ? 'green' : 'red') : 'amber'}>{a.kind === 'price' ? 'Price move' : 'Volume spike'}</Tag>}
          {a.detail && <p className="why" style={{ marginTop: 8 }}>{a.detail}</p>}
          <div className="actions">
            <button onClick={() => onAsk(a.symbol, a.kind === 'filing' ? 'Does this change the investment case?' : 'Is there anything in the fundamentals or recent guidance that explains an unusual move?', `${a.name}: ${a.title}. ${a.detail || ''}`)}>Ask Finn</button>
            <button className="ghost" onClick={() => openResearch(a.symbol)}>Research</button>
          </div>
        </div>
      ))}

      <h2>Thresholds</h2>
      <div className="field" style={{ marginTop: 14 }}><label><span>Price move beyond</span><b>±{Number(th.price_move_pct).toFixed(1)}%</b></label>
        <input type="range" min="1" max="15" step="0.5" value={th.price_move_pct} onChange={(e) => upd('price_move_pct', +e.target.value)} /></div>
      <div className="field"><label><span>Volume above</span><b>{Number(th.volume_multiple).toFixed(1)}× average</b></label>
        <input type="range" min="1.2" max="6" step="0.1" value={th.volume_multiple} onChange={(e) => upd('volume_multiple', +e.target.value)} /></div>
      <div className="field"><label><span>Average measured over</span><b>{th.lookback_days} days</b></label>
        <input type="range" min="5" max="60" step="5" value={th.lookback_days} onChange={(e) => upd('lookback_days', +e.target.value)} /></div>
      <div className="field"><label><span>Filing types that alert at once</span></label>
        <div className="chips wrap">
          {ALERTABLE.map((c) => <button key={c} className={`chip ${cats.has(c) ? 'on' : ''}`} onClick={() => toggle(c)}>{CAT_LABEL[c]}</button>)}
        </div></div>
      <button className="btn wide" disabled={!dirty || saving} onClick={save}>{saving ? 'Saving…' : dirty ? 'Save and re-scan' : 'Saved'}</button>

      {digest?.tape && (
        <>
          <h2>End of day <span className="count">{digest.tape[0]?.date}</span></h2>
          <div className="list">
            {[...digest.tape].sort((a, b) => Math.abs(b.move_pct) - Math.abs(a.move_pct)).map((t) => (
              <div className="row" key={t.symbol} style={{ alignItems: 'center' }}>
                <div className="main">
                  <div className="co"><b>{t.symbol}</b><span className="note" style={{ margin: 0 }}>₹{fmtNum(t.close)}</span></div>
                  <div className="note" style={{ marginTop: 2 }}>vol {t.volume_x}× · 1w {pct(t.ret_1w_pct)} · 1m {pct(t.ret_1m_pct)}</div>
                </div>
                <Spark data={t.spark} />
                <span className={`num ${sign(t.move_pct)}`} style={{ width: 60, textAlign: 'right', fontWeight: 600, fontSize: 14 }}>{pct(t.move_pct)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
