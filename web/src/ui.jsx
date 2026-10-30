import { CAT_LABEL, CAT_TONE, pct, sign } from './fmt'

export const Pill = ({ cat, children, tone }) => (
  <span className={`pill ${tone || CAT_TONE[cat] || 'grey'}`}>{children || CAT_LABEL[cat] || cat}</span>
)

export const Delta = ({ v, d = 1 }) => <span className={`d num ${sign(v)}`}>{pct(v, d)}</span>

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
    <div>
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

export const Icon = ({ name }) => {
  const d = {
    today: 'M4 5h16v14H4zM4 9h16M8 3v4M16 3v4',
    alerts: 'M6 17V11a6 6 0 0 1 12 0v6l2 2H4zM10 21h4',
    research: 'M10 4a6 6 0 1 1 0 12 6 6 0 0 1 0-12zM14.5 14.5 20 20',
    ask: 'M4 5h16v11H9l-5 4z',
  }[name]
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
}
