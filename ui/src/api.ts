import { SAMPLES } from './mock'

// Contract with backend POST /ask. Keep in sync with backend.
export type SourceType = 'document' | 'ticket' | 'meeting' | 'slack'
export interface Source { id: string; type: SourceType; title: string; date: string; snippet: string }
export interface Edge { source: string; target: string; label: string }
export interface Conflict { outdated: string; current: string; note: string }
export interface Answer {
  answer: string
  sources: Source[]
  path: Edge[]
  conflicts: Conflict[]
  sample?: boolean // set by the UI when showing a mock answer
}

// Trailing slashes stripped: "https://x.onrender.com/" + "/ask" would hit "//ask", which 404s.
export const API = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '')
export const ID_RE = /\b((?:DOC|RFC|PAY|INC)-\d{3}|(?:MTG|SLACK)-\d{4}-\d{2}-\d{2})\b/

export async function ask(question: string): Promise<Answer> {
  let r: Response
  try {
    r = await fetch(`${API}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal: AbortSignal.timeout(90_000),
    })
  } catch {
    // Only unreachable/timed-out backends fall back; HTTP errors below are real failures and must show.
    const s = SAMPLES[question] // MOCK: offline fallback for the demo questions
    if (s) return { ...s, sample: true }
    throw new Error(`Couldn't reach ${API}. Check that the backend is running, then ask again.`)
  }
  if (!r.ok) {
    const detail = await r.json().then(b => b.detail, () => null)
    throw new Error(typeof detail === 'string' ? detail : `The backend returned an error (${r.status}). Try again.`)
  }
  return r.json()
}

export const health = () =>
  fetch(`${API}/health`, { signal: AbortSignal.timeout(3000) }).then(r => r.ok).catch(() => false)

export function kind(id: string): SourceType | 'entity' {
  const u = id.toUpperCase()
  if (/^(DOC|RFC)-/.test(u)) return 'document'
  if (/^(PAY|INC)-/.test(u)) return 'ticket'
  if (u.startsWith('MTG-')) return 'meeting'
  if (u.startsWith('SLACK-')) return 'slack'
  return 'entity'
}

export function badge(id: string, type: SourceType) {
  if (id.startsWith('RFC')) return 'RFC'
  if (id.startsWith('INC')) return 'Incident'
  return { document: 'Doc', ticket: 'Ticket', meeting: 'Meeting', slack: 'Slack' }[type]
}
