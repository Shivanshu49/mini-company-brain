import { useEffect, useRef, useState } from 'react'
import { ask, badge, health, kind, ID_RE, type Answer } from './api'
import Graph from './Graph'

const SUGGESTED = [
  { label: 'Why exponential backoff?', q: 'Why does refund-service retry refunds with exponential backoff, and who should I contact if it breaks?' },
  { label: 'Current max refund retries', q: 'What is the current maximum retry count for refunds?' },
  { label: 'Tier-2 settlement delays', q: 'Why were settlements delayed for Tier-2 merchants in August, and which decision caused it?' },
  { label: 'Root of the ledger duplicates', q: 'Which earlier decision indirectly led to the ledger duplicates?' },
  { label: 'Cloud provider', q: 'Which cloud provider does PayNest host its services on?' },
]

type Turn = { q: string; a?: Answer; error?: string }

const isRefusal = (a: Answer) => /^not found in company knowledge/i.test(a.answer.trim())
const shortDate = (d: string) => new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', timeZone: 'UTC' })

function Cited({ text, onCite }: { text: string; onCite: (id: string) => void }) {
  return text.split(new RegExp(ID_RE, 'g')).map((part, i) =>
    i % 2 ? <button key={i} className={`cite t-${kind(part)}`} onClick={() => onCite(part)}>{part}</button> : part,
  )
}

export default function App() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [sel, setSel] = useState(-1)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [online, setOnline] = useState<boolean | null>(null)
  const [focus, setFocus] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => { health().then(setOnline) }, [])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [turns])

  async function submit(question: string) {
    const q = question.trim()
    if (!q || busy) return
    const i = turns.length
    setTurns(t => [...t, { q }])
    setSel(i)
    setInput('')
    setFocus(null)
    setBusy(true)
    const done = (patch: Partial<Turn>) => setTurns(t => t.map((x, j) => (j === i ? { ...x, ...patch } : x)))
    try {
      done({ a: await ask(q) })
    } catch (e) {
      done({ error: (e as Error).message })
    } finally {
      setBusy(false)
    }
  }

  function cite(id: string) {
    setFocus(id)
    document.getElementById(`src-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }

  const current = turns[sel]?.a
  const outdated = new Map(current?.conflicts.map(c => [c.outdated, c.current]))
  const sources = [...(current?.sources ?? [])].sort((a, b) => a.date.localeCompare(b.date))

  return (
    <div className="app">
      <main className="chat">
        <header className="top">
          <h1>PayNest Brain</h1>
          <span className={`status ${online ? 'on' : 'off'}`}>
            {online === null ? 'Connecting' : online ? 'Knowledge base connected' : 'Backend offline, sample answers only'}
          </span>
        </header>

        <div className="thread">
          {turns.length === 0 && (
            <div className="intro">
              <h2>Ask PayNest anything</h2>
              <p>Answers come from company docs, tickets, meeting notes and Slack threads. Each one shows its sources and how they connect.</p>
              <ul>
                {SUGGESTED.map(s => (
                  <li key={s.q}><button onClick={() => submit(s.q)}>{s.q}</button></li>
                ))}
              </ul>
            </div>
          )}

          {turns.map((t, i) => (
            <section key={i} className={`turn ${i === sel ? 'selected' : ''}`} onClick={() => t.a && setSel(i)}>
              <h3 className="q">{t.q}</h3>
              {!t.a && !t.error && <p className="thinking">Searching docs, tickets, meetings and Slack</p>}
              {t.error && <p className="error">{t.error}</p>}
              {t.a && isRefusal(t.a) && (
                <div className="refused">
                  <strong>Not found in company knowledge.</strong>
                  <p>No doc, ticket, meeting or Slack thread covers this, so the brain didn't guess.</p>
                </div>
              )}
              {t.a && !isRefusal(t.a) && (
                <div className="a">
                  {t.a.answer.split(/\n{2,}/).map((p, j) => <p key={j}><Cited text={p} onCite={cite} /></p>)}
                  {t.a.conflicts.map(c => (
                    <div key={c.outdated} className="conflict">
                      <strong>{c.outdated} is outdated.</strong> <Cited text={c.note} onCite={cite} />
                    </div>
                  ))}
                </div>
              )}
              {t.a?.sample && <p className="sample">Sample answer. The backend is offline.</p>}
            </section>
          ))}
          <div ref={endRef} />
        </div>

        <footer className="composer">
          {turns.length > 0 && (
            <div className="chips">
              {SUGGESTED.map(s => (
                <button key={s.q} title={s.q} disabled={busy} onClick={() => submit(s.q)}>{s.label}</button>
              ))}
            </div>
          )}
          <form onSubmit={e => { e.preventDefault(); submit(input) }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about services, decisions, incidents or owners"
              aria-label="Question"
            />
            <button type="submit" disabled={busy || !input.trim()}>Ask</button>
          </form>
        </footer>
      </main>

      <aside className="evidence">
        {!current || isRefusal(current) ? (
          <p className="empty">
            {current ? 'No sources matched this question.' : 'Ask a question to see the sources behind the answer and how they connect.'}
          </p>
        ) : (
          <>
            <h2>Sources, oldest first</h2>
            <ol className="sources">
              {sources.map(s => (
                <li key={s.id} id={`src-${s.id}`} className={`src t-${s.type} ${focus === s.id ? 'focus' : ''} ${outdated.has(s.id) ? 'stale' : ''}`}>
                  <time dateTime={s.date}>{shortDate(s.date)}</time>
                  <div className="card">
                    <div className="meta">
                      <span className="badge">{badge(s.id, s.type)}</span>
                      <code>{s.id}</code>
                      {outdated.has(s.id) && <span className="flag">Outdated</span>}
                    </div>
                    <h3>{s.title}</h3>
                    <p>{s.snippet}</p>
                    {outdated.has(s.id) && <p className="superseded">Superseded by {outdated.get(s.id)}</p>}
                  </div>
                </li>
              ))}
            </ol>
            <h2>How it connects</h2>
            <Graph edges={current.path} focus={focus} />
          </>
        )}
      </aside>
    </div>
  )
}
