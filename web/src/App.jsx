import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { Icon } from './ui'
import Today from './Today'
import Alerts from './Alerts'
import Research from './Research'
import Ask from './Ask'
import Network from './Network'
import { PersonSheet } from './net'

const TABS = [['today', 'Today'], ['alerts', 'Alerts'], ['research', 'Research'], ['network', 'Network'], ['ask', 'Ask']]

export default function App() {
  const [tab, setTab] = useState(() => localStorage.getItem('finn.tab') || 'today')
  const [settings, setSettings] = useState(null)
  const [win, setWin] = useState({ hours: 24 })
  const [digest, setDigest] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [askPrefill, setAskPrefill] = useState(null)
  const [researchSymbol, setResearchSymbol] = useState(null)
  const [person, setPerson] = useState(null)          // contact whose sheet is open, from any screen
  const [netVersion, setNetVersion] = useState(0)     // bumps when a contact is logged or erased
  const [seenAlerts, setSeenAlerts] = useState(() => new Set(JSON.parse(localStorage.getItem('finn.seen') || '[]')))

  useEffect(() => { localStorage.setItem('finn.tab', tab) }, [tab])
  useEffect(() => { api.settings().then((s) => { setSettings(s); setWin({ hours: s.window_hours || 24 }) }).catch((e) => setError(e.message)) }, [])

  const loadDigest = useCallback((w) => {
    setLoading(true); setError(null)
    const params = w.from ? { from: w.from, to: w.to || w.from } : { hours: w.hours }
    api.digest(params).then(setDigest).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }, [])
  useEffect(() => { if (settings) loadDigest(win) }, [settings, win, loadDigest])
  // the digest returns triage instantly and enriches in the background: poll until complete
  useEffect(() => {
    if (!digest || digest.complete) return
    const params = win.from ? { from: win.from, to: win.to || win.from } : { hours: win.hours }
    const t = setTimeout(() => api.digest(params).then(setDigest).catch(() => {}), 4000)
    return () => clearTimeout(t)
  }, [digest, win])

  const saveSettings = async (patch) => {
    const s = await api.saveSettings(patch)
    setSettings(s)
    if (patch.window_hours) setWin({ hours: patch.window_hours })
  }
  const onAsk = (symbol, question, context) => { setAskPrefill({ symbol, question, context, ts: Date.now() }); setTab('ask') }
  const openResearch = (symbol) => { setResearchSymbol(symbol); setTab('research') }
  const markSeen = () => {
    if (!digest) return
    const s = new Set(digest.alerts.map((a) => a.id)); setSeenAlerts(s)
    localStorage.setItem('finn.seen', JSON.stringify([...s]))
  }
  const networkChanged = () => { setNetVersion((v) => v + 1); loadDigest(win) }
  const unseen = digest ? digest.alerts.filter((a) => !seenAlerts.has(a.id)).length : 0

  return (
    <div className="app">
      {tab === 'today' && <Today digest={digest} loading={loading} error={error} win={win} setWin={setWin} onAsk={onAsk} openResearch={openResearch} openPerson={setPerson} />}
      {tab === 'alerts' && <Alerts digest={digest} settings={settings} saveSettings={saveSettings} reload={() => loadDigest(win)} onAsk={onAsk} openResearch={openResearch} markSeen={markSeen} openPerson={setPerson} />}
      {tab === 'research' && <Research symbol={researchSymbol} setSymbol={setResearchSymbol} onAsk={onAsk} openPerson={setPerson} />}
      {tab === 'network' && <Network openPerson={setPerson} openResearch={openResearch} version={netVersion} />}
      {tab === 'ask' && <Ask prefill={askPrefill} openResearch={openResearch} openPerson={setPerson} />}
      {person && <PersonSheet id={person} onClose={() => setPerson(null)} openResearch={openResearch} onChanged={networkChanged} />}
      <nav className="nav"><div className="inner">
        {TABS.map(([k, label]) => (
          <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>
            <Icon name={k} />{label}
            {k === 'alerts' && unseen > 0 && <span className="badge">{unseen}</span>}
          </button>
        ))}
      </div></nav>
    </div>
  )
}
