export const fmtNum = (n, d = 0) => (n == null || isNaN(n) ? '–' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: d, minimumFractionDigits: 0 }))
export const fmtCr = (n) => (n == null ? '–' : `₹${fmtNum(n, Math.abs(n) < 100 ? 1 : 0)} cr`)
export const pct = (n, d = 1) => (n == null || isNaN(n) ? '–' : `${n > 0 ? '+' : ''}${Number(n).toFixed(d)}%`)
export const sign = (n) => (n == null ? '' : n > 0 ? 'up' : n < 0 ? 'down' : '')
export const timeAgo = (iso) => {
  if (!iso) return ''
  const t = new Date(iso.length <= 10 ? iso + 'T15:30:00' : iso)
  const s = (Date.now() - t.getTime()) / 1000
  if (s < 3600) return `${Math.max(1, Math.round(s / 60))}m ago`
  if (s < 86400) return `${Math.round(s / 3600)}h ago`
  if (s < 7 * 86400) return `${Math.round(s / 86400)}d ago`
  return t.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}
export const CAT_LABEL = {
  results: 'Results', 'M&A': 'M&A', fund_raise: 'Fund raise', management_change: 'Management',
  litigation: 'Litigation', insider_trading: 'Insider', earnings_call: 'Concall', investor_meetings: 'Investor meet',
  credit_rating: 'Rating', dividend: 'Dividend', bonus_split: 'Bonus/Split', capex: 'Capex',
  press_release: 'Press release', postal_ballot: 'Postal ballot', agm_egm: 'AGM/EGM', pledging: 'Pledge', unclassified: 'Routine',
}
export const CAT_TONE = {
  results: 'blue', 'M&A': 'purple', management_change: 'amber', litigation: 'red', fund_raise: 'purple',
  credit_rating: 'amber', pledging: 'red', capex: 'green', dividend: 'green', bonus_split: 'green', press_release: 'grey',
}
