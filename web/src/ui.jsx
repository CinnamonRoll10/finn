import { useState } from 'react'
import { CAT_LABEL, CAT_TONE, pct, sign } from './fmt'

export const Tag = ({ cat, children, tone }) => (
  <span className={`tag ${tone || CAT_TONE[cat] || 'grey'}`}>{children || CAT_LABEL[cat] || cat}</span>
)

export const Delta = ({ v, d = 1 }) => <span className={`d ${sign(v)}`}>{pct(v, d)}</span>

/** Light by default; dark if you tap, and the choice sticks. */
const currentTheme = () => document.documentElement.dataset.theme || 'light'
function ThemeToggle() {
  const [theme, setTheme] = useState(currentTheme)
  const flip = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try { localStorage.setItem('finn.theme', next) } catch { /* private mode */ }
    document.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.setAttribute('content', next === 'dark' ? '#161513' : '#f5f1e8'))
    setTheme(next)
  }
  return (
    <button className="theme" onClick={flip} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        {theme === 'dark'
          ? <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8z" />
          : <path d="M20 14.5A8 8 0 0 1 9.5 4a7 7 0 1 0 10.5 10.5z" />}
      </svg>
    </button>
  )
}

export function Masthead({ right }) {
  const d = new Date()
  const date = d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }).toUpperCase()
  return (
    <div className="mast">
      <span className="brand">Fi<i>nn</i></span>
      <span className="right"><span className="line">{date}<br />{right}</span><ThemeToggle /></span>
    </div>
  )
}

export function Spark({ data, w = 64, h = 22 }) {
  if (!data || data.length < 2) return null
  const min = Math.min(...data), max = Math.max(...data)
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / (max - min || 1)) * (h - 2) - 1}`).join(' ')
  const up = data[data.length - 1] >= data[0]
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} width={w} height={h} aria-hidden>
      <polyline points={pts} fill="none" stroke={up ? 'var(--up)' : 'var(--down)'} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}

export function Bars({ labels, values, title, unit, fmt }) {
  const vals = values.map((v) => (v == null ? 0 : v))
  const max = Math.max(...vals.map(Math.abs), 1)
  const last = vals[vals.length - 1]
  return (
    <div className="chart">
      <div className="chart-title"><span>{title}</span><b className="num">{fmt ? fmt(last) : last}{unit ? ` ${unit}` : ''}</b></div>
      <div className="bars">
        {vals.map((v, i) => (
          <div key={i} className={`b ${v < 0 ? 'neg' : ''} ${i === vals.length - 1 ? 'last' : ''}`} style={{ height: `${(Math.abs(v) / max) * 100}%` }} title={`${labels[i]}: ${v}`} />
        ))}
      </div>
      <div className="axis">{labels.map((l, i) => <span key={i}>{String(l).replace('Mar ', 'FY').slice(-4)}</span>)}</div>
    </div>
  )
}

export const Source = ({ children }) => <span className="src">{children}</span>

/** Render "text [Source]" bullets with the source tag styled. */
export function Bullet({ text }) {
  const parts = String(text).split(/(\[[^\]]{2,40}\])/g)
  return <li>{parts.map((p, i) => (p.startsWith('[') ? <Source key={i}>{p.slice(1, -1)}</Source> : p))}</li>
}

/** Inline text with [Source] tags as chips and **bold** honoured. */
function Inline({ text }) {
  return String(text).split(/(\[[^\]]{2,40}\]|\*\*[^*]+\*\*)/g).map((p, i) => (
    p.startsWith('[') ? <Source key={i}>{p.slice(1, -1)}</Source>
      : p.startsWith('**') ? <b key={i}>{p.slice(2, -2)}</b> : p
  ))
}

/** A model answer laid out to be scanned: the answer first, then points, then what to watch. */
export function Answer({ text }) {
  const blocks = []
  let para = []
  const flush = () => { if (para.length) { blocks.push({ t: 'p', text: para.join(' ') }); para = [] } }
  for (const raw of String(text || '').split('\n')) {
    const line = raw.trim()
    const bullet = line.match(/^(?:[-•*]|\d+[.)])\s+(.*)$/)
    const last = blocks[blocks.length - 1]
    if (!line) flush()
    else if (bullet) { flush(); if (last?.t === 'ul') last.items.push(bullet[1]); else blocks.push({ t: 'ul', items: [bullet[1]] }) }
    else if (!para.length && last?.t === 'ul' && !/[:.]$/.test(last.items[last.items.length - 1]) && !/^[A-Z][a-z]+:/.test(line)) last.items[last.items.length - 1] += ' ' + line
    else if (/^watch\s*:/i.test(line)) { flush(); blocks.push({ t: 'watch', text: line.replace(/^watch\s*:\s*/i, '') }) }
    else if (line.endsWith(':') && line.length <= 70) { flush(); blocks.push({ t: 'label', text: line.slice(0, -1) }) }
    else para.push(line)
  }
  flush()
  const lead = blocks.findIndex((b) => b.t === 'p')
  return (
    <div className="ans">
      {blocks.map((b, i) => (
        b.t === 'ul' ? <ul key={i} className="bullets">{b.items.map((it, j) => <li key={j}><Inline text={it} /></li>)}</ul>
          : b.t === 'label' ? <div key={i} className="kicker">{b.text}</div>
            : b.t === 'watch' ? <div key={i} className="watch"><span className="kicker">Watch</span><Inline text={b.text} /></div>
              : <p key={i} className={i === lead ? 'lead' : ''}><Inline text={b.text} /></p>
      ))}
    </div>
  )
}

export const Stat = ({ k, v, cls }) => <span><span className="k">{k}</span><b className={cls || 'num'}>{v ?? '–'}</b></span>

export const Icon = ({ name }) => {
  const d = {
    today: 'M4 5h16v14H4zM4 9h16M8 3v4M16 3v4',
    alerts: 'M6 17V11a6 6 0 0 1 12 0v6l2 2H4zM10 21h4',
    research: 'M10 4a6 6 0 1 1 0 12 6 6 0 0 1 0-12zM14.5 14.5 20 20',
    ask: 'M4 5h16v11H9l-5 4z',
    network: 'M12 5a2.2 2.2 0 1 1 0 .01M5 18a2.2 2.2 0 1 1 0 .01M19 18a2.2 2.2 0 1 1 0 .01M12 7.4v4.2M12 11.6l-5.4 4.6M12 11.6l5.4 4.6',
  }[name]
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
}
