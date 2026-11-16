import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import { Answer, Masthead } from './ui'
import { PersonRow, Routes } from './net'

const NET = '__network'
const NET_ASKS = ['Who should I reconnect with?', 'How do I reach Anup Bagchi?', 'Who are my go-to people for rural lending?', 'Who do I know at Swiggy?', 'Anyone I know in specialty chemicals?']
const CO_ASKS = ['What did management promise last quarter, and did they deliver?', 'Who should I call about this company?', 'Where do the story and the numbers disagree?', 'Is profit turning into cash?']
const Speech = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)

export default function Ask({ prefill, openResearch, openPerson }) {
  const [companies, setCompanies] = useState([])
  const [symbol, setSymbol] = useState(prefill?.symbol || NET)
  const [threads, setThreads] = useState({})
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [questions, setQuestions] = useState([])
  const [ready, setReady] = useState(null)
  const [listening, setListening] = useState(false)
  const ctx = useRef(null)
  const bottom = useRef(null)
  const isNet = symbol === NET

  useEffect(() => { api.companies().then(setCompanies).catch(() => {}) }, [])
  useEffect(() => {
    if (!prefill) return
    setSymbol(prefill.symbol); ctx.current = prefill.context || null
    if (prefill.question) send(prefill.question, prefill.symbol, prefill.context)
  }, [prefill?.ts]) // eslint-disable-line
  useEffect(() => {
    if (isNet) { setReady(true); return }
    api.research(symbol).then((r) => { setReady(r.status === 'ready'); setQuestions(r.data?.sections?.questions || []) }).catch(() => setReady(false))
  }, [symbol, isNet])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [threads, busy])

  const thread = threads[symbol] || []
  const send = async (q, sym = symbol, context = ctx.current) => {
    if (!q?.trim() || !sym) return
    const t = threads[sym] || []
    setThreads((cur) => ({ ...cur, [sym]: [...(cur[sym] || []), { role: 'user', text: q }] }))
    setInput(''); setBusy(true)
    try {
      const r = await api.ask({ symbol: sym === NET ? null : sym, question: q, history: t.slice(-4).map(({ role, text }) => ({ role, text })), context })
      setThreads((cur) => ({ ...cur, [sym]: [...(cur[sym] || []), { role: 'finn', text: r.answer, model: r.model, people: r.people, link: r.link, network: r.kind === 'network' }] }))
    } catch (e) {
      setThreads((cur) => ({ ...cur, [sym]: [...(cur[sym] || []), { role: 'finn', text: e.message.includes('Build research') ? 'I have not read this company yet. Build it in Research first.' : `Error: ${e.message}` }] }))
    } finally { setBusy(false); ctx.current = null }
  }
  // speak the question: on a phone, between meetings, typing is the slow part
  const listen = () => {
    if (!Speech || listening) return
    const rec = new Speech()
    rec.lang = 'en-IN'; rec.interimResults = false
    rec.onresult = (e) => { const said = e.results[0][0].transcript; setInput(said); send(said) }
    rec.onend = () => setListening(false); rec.onerror = () => setListening(false)
    setListening(true); rec.start()
  }
  const canAsk = isNet || ready || /who|network|know|call|reconnect/i.test(input)

  return (
    <div className="screen">
      <Masthead right={isNet ? 'your network' : 'answers cite sources'} />
      <h1>Ask.</h1>
      <div className="chips">
        <button className={`chip ${isNet ? 'on' : ''}`} onClick={() => setSymbol(NET)}>MY NETWORK</button>
        {companies.map((c) => <button key={c.symbol} className={`chip ${c.symbol === symbol ? 'on' : ''}`} onClick={() => setSymbol(c.symbol)}>{c.research_ready && <span className="dot" />}{c.symbol}</button>)}
      </div>
      {isNet && thread.length === 0 && <p className="deck">Ask who you know, or pick a company to ask about its business.</p>}
      {!isNet && ready === false && (
        <div><p className="deck">Finn has not read {symbol} yet.</p><button className="btn" onClick={() => openResearch(symbol)}>Build it in Research</button></div>
      )}
      {(isNet || ready) && thread.length === 0 && (
        <div className="suggest">
          {(isNet ? NET_ASKS : [...CO_ASKS, ...questions].slice(0, 6)).map((q, i) => <button key={i} onClick={() => send(q)}>{q}</button>)}
        </div>
      )}
      <div className="chat">
        {thread.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.role === 'finn' ? <Answer text={m.text} /> : m.text}
            {m.link && <Routes link={m.link} onOpen={openPerson} />}
            {m.people?.length > 0 && <div className="plist">{m.people.map((p) => <PersonRow key={p.id} p={p} onOpen={openPerson} compact />)}</div>}
            {m.network && <div className="m">from your network</div>}
            {m.model && <div className="m">{m.model} · primary sources only</div>}
          </div>
        ))}
        {busy && <div className="msg finn"><div className="skeleton" style={{ width: 180, margin: 0 }} /><div className="skeleton" style={{ width: 240 }} /></div>}
        <div ref={bottom} />
      </div>
      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input) }}>
        <div className="inner">
          <input type="text" placeholder={listening ? 'Listening…' : isNet ? 'Who do I know at…' : `Ask about ${symbol}`} value={input} onChange={(e) => setInput(e.target.value)} disabled={busy} />
          {Speech && <button type="button" className={`mic ${listening ? 'on' : ''}`} onClick={listen} aria-label="Speak your question" disabled={busy}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M12 4a2.5 2.5 0 0 1 2.5 2.5v5a2.5 2.5 0 0 1-5 0v-5A2.5 2.5 0 0 1 12 4zM6.5 11.5a5.5 5.5 0 0 0 11 0M12 17v3" /></svg>
          </button>}
          <button className="btn" disabled={busy || !canAsk || !input.trim()}>Send</button>
        </div>
      </form>
    </div>
  )
}
