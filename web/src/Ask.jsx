import { useEffect, useRef, useState } from 'react'
import { api } from './api'

export default function Ask({ prefill, openResearch }) {
  const [companies, setCompanies] = useState([])
  const [symbol, setSymbol] = useState(prefill?.symbol || null)
  const [threads, setThreads] = useState({})
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [questions, setQuestions] = useState([])
  const [ready, setReady] = useState(null)
  const ctx = useRef(null)
  const bottom = useRef(null)

  useEffect(() => { api.companies().then(setCompanies).catch(() => {}) }, [])
  useEffect(() => {
    if (!prefill) return
    setSymbol(prefill.symbol); ctx.current = prefill.context || null
    if (prefill.question) send(prefill.question, prefill.symbol, prefill.context)
  }, [prefill?.ts]) // eslint-disable-line
  useEffect(() => {
    if (!symbol) return
    api.research(symbol).then((r) => { setReady(r.status === 'ready'); setQuestions(r.data?.sections?.questions || []) }).catch(() => setReady(false))
  }, [symbol])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [threads, busy])

  const thread = threads[symbol] || []
  const send = async (q, sym = symbol, context = ctx.current) => {
    if (!q?.trim() || !sym) return
    const t = threads[sym] || []
    setThreads({ ...threads, [sym]: [...t, { role: 'user', text: q }] })
    setInput(''); setBusy(true)
    try {
      const r = await api.ask({ symbol: sym, question: q, history: t.slice(-4), context })
      setThreads((cur) => ({ ...cur, [sym]: [...(cur[sym] || []), { role: 'finn', text: r.answer, model: r.model }] }))
    } catch (e) {
      setThreads((cur) => ({ ...cur, [sym]: [...(cur[sym] || []), { role: 'finn', text: e.message.includes('Build research') ? 'I have not read this company yet. Open Research and build it first, then ask.' : `Error: ${e.message}` }] }))
    } finally { setBusy(false); ctx.current = null }
  }

  return (
    <div className="screen">
      <div className="topbar"><span className="wordmark">FI<span>NN</span></span><span className="date">answers cite the source</span></div>
      <h1>Ask</h1>
      <div className="chips">
        {companies.map((c) => <button key={c.symbol} className={`chip small ${c.symbol === symbol ? 'on' : ''}`} onClick={() => setSymbol(c.symbol)}>{c.research_ready && <span className="dot" />}{c.symbol}</button>)}
      </div>
      {!symbol && <div className="empty">Pick a company. Answers come only from its annual report, concall transcripts and reported numbers.</div>}
      {symbol && ready === false && (
        <div className="card"><p className="sub" style={{ margin: 0 }}>Research for {symbol} is not built yet.</p><button className="btn" style={{ marginTop: 10 }} onClick={() => openResearch(symbol)}>Build it in Research</button></div>
      )}
      {symbol && ready && thread.length === 0 && (
        <div className="suggest">
          {['What did management promise last quarter, and did they deliver?', 'Where do the story and the numbers disagree?', 'Is profit turning into cash?', ...questions].slice(0, 6).map((q, i) => <button key={i} onClick={() => send(q)}>{q}</button>)}
        </div>
      )}
      <div className="chat">
        {thread.map((m, i) => <div key={i} className={`msg ${m.role}`}>{m.text}{m.model && <div className="m">{m.model} · primary sources only</div>}</div>)}
        {busy && <div className="msg finn"><div className="skeleton" style={{ width: 160, margin: 0 }} /></div>}
        <div ref={bottom} />
      </div>
      {symbol && (
        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input) }}>
          <div className="inner">
            <input type="text" placeholder={`Ask about ${symbol}…`} value={input} onChange={(e) => setInput(e.target.value)} disabled={busy || !ready} />
            <button className="btn" disabled={busy || !ready || !input.trim()}>Send</button>
          </div>
        </form>
      )}
    </div>
  )
}
