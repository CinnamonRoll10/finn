const j = async (r) => {
  if (!r.ok) {
    let msg = r.statusText
    try { msg = (await r.json()).detail || msg } catch {}
    throw new Error(msg)
  }
  return r.json()
}
const post = (url, body) => fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body || {}) }).then(j)
export const api = {
  settings: () => fetch('/api/settings').then(j),
  saveSettings: (body) => fetch('/api/settings', { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }).then(j),
  digest: (params) => fetch('/api/digest?' + new URLSearchParams(params)).then(j),
  companies: () => fetch('/api/companies').then(j),
  research: (s) => fetch(`/api/research/${s}`).then(j),
  buildResearch: (s, force = false) => fetch(`/api/research/${s}/build?force=${force}`, { method: 'POST' }).then(j),
  ask: (body) => post('/api/ask', body),
  usage: () => fetch('/api/usage').then(j),
  network: () => fetch('/api/network').then(j),
  networkCompany: (s) => fetch(`/api/network/company/${s}`).then(j),
  person: (id) => fetch(`/api/network/person/${id}`).then(j),
  networkAsk: (question, symbol) => post('/api/network/ask', { question, symbol }),
  logContact: (id) => post(`/api/network/person/${id}/log`),
  forget: (id) => fetch(`/api/network/person/${id}`, { method: 'DELETE' }).then(j),
  restoreNetwork: () => post('/api/network/restore'),
}
