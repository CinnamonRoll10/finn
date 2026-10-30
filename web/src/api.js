const j = async (r) => {
  if (!r.ok) {
    let msg = r.statusText
    try { msg = (await r.json()).detail || msg } catch {}
    throw new Error(msg)
  }
  return r.json()
}
export const api = {
  settings: () => fetch('/api/settings').then(j),
  saveSettings: (body) => fetch('/api/settings', { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }).then(j),
  digest: (params) => fetch('/api/digest?' + new URLSearchParams(params)).then(j),
  companies: () => fetch('/api/companies').then(j),
  research: (s) => fetch(`/api/research/${s}`).then(j),
  buildResearch: (s, force = false) => fetch(`/api/research/${s}/build?force=${force}`, { method: 'POST' }).then(j),
  ask: (body) => fetch('/api/ask', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }).then(j),
  usage: () => fetch('/api/usage').then(j),
}
