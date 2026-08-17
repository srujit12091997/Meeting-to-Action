import { useEffect, useRef, useState } from 'react'
import {
  Mic, Square, Upload, FileText, ListChecks, MessageSquare, Sparkles, Lightbulb,
  CheckCircle2, Calendar, Mail, Download, Clock, LayoutDashboard, Send, Rocket, Loader2, Inbox,
  Moon, Sun,
} from 'lucide-react'
import * as api from './lib/api'
import { SegmentRecorder } from './lib/recorder'

/* --------------------------------- helpers -------------------------------- */
const parseOwners = (s) => s.split(',').map((x) => x.trim()).filter(Boolean)

function summaryMd(ext) {
  const li = (a) => (a?.length ? a.map((x) => '- ' + x).join('\n') : '- (none)')
  const acts =
    (ext.action_items || [])
      .map((it) => `- ${it.task} — ${it.owner || 'Unassigned'} (due ${it.deadline || 'no deadline'})`)
      .join('\n') || '- (none)'
  return `# Meeting Summary\n\n## Overview\n${ext.summary || ''}\n\n## Key Decisions\n${li(
    ext.decisions,
  )}\n\n## Proposed Solutions\n${li(ext.proposed_solutions)}\n\n## Next Action Steps\n${acts}`
}
function summaryHtml(ext) {
  const esc = (s) => String(s ?? '').replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]))
  const ul = (a) => (a?.length ? '<ul>' + a.map((x) => `<li>${esc(x)}</li>`).join('') + '</ul>' : '<p><i>None</i></p>')
  const acts = (ext.action_items || [])
    .map((it) => `<li><b>${esc(it.task)}</b> — ${esc(it.owner || 'Unassigned')} (due ${esc(it.deadline || 'no deadline')})</li>`)
    .join('')
  return `<div style="font-family:'Plus Jakarta Sans',Arial,sans-serif;max-width:640px"><h2 style="color:#0d9488">Meeting Summary</h2>
  <h3>Overview</h3><p>${esc(ext.summary || '')}</p>
  <h3>Key Decisions</h3>${ul(ext.decisions)}
  <h3>Proposed Solutions</h3>${ul(ext.proposed_solutions)}
  <h3>Next Action Steps</h3>${acts ? '<ul>' + acts + '</ul>' : '<p><i>None</i></p>'}</div>`
}
function gcalLink(it, title) {
  const d = (it.deadline || '').replaceAll('-', '')
  if (!d) return '#'
  const end = new Date(it.deadline)
  end.setDate(end.getDate() + 1)
  const e = end.toISOString().slice(0, 10).replaceAll('-', '')
  const p = new URLSearchParams({
    action: 'TEMPLATE',
    text: `${it.task} — ${it.owner || 'Unassigned'}`,
    dates: `${d}/${e}`,
    details: `Action item from: ${title || 'Meeting'}`,
  })
  return 'https://calendar.google.com/calendar/render?' + p.toString()
}
function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

/* --------------------- flat design system (teal + orange) ----------------- */
const btn = 'inline-flex items-center justify-center gap-1.5 rounded-lg font-semibold px-4 py-2 cursor-pointer transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/60 disabled:opacity-40 disabled:cursor-not-allowed'
const primary = `${btn} text-white bg-brand-600 hover:bg-brand-700`
const accentBtn = `${btn} text-white bg-accent-600 hover:bg-accent-700`
const ghost = `${btn} bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:border-brand-400 hover:text-brand-700 dark:hover:text-brand-300`
const danger = `${btn} text-white bg-red-600 hover:bg-red-700`
const input = 'w-full border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 bg-white dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-400 transition'

// Compact variants for the top menu bar (slimmer than page buttons).
const navBtn = 'inline-flex items-center justify-center gap-1.5 rounded-lg font-semibold px-3 py-1.5 text-sm cursor-pointer transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/60 disabled:opacity-40'
const navGhost = `${navBtn} bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:border-brand-400 hover:text-brand-700`
const navAccent = `${navBtn} text-white bg-accent-600 hover:bg-accent-700`
const navDanger = `${navBtn} text-white bg-red-600 hover:bg-red-700`

function Card({ title, children, pad = 'p-5' }) {
  return (
    <div className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl ${pad}`}>
      {title && <h2 className="text-[1.02rem] font-bold flex items-center gap-2 mb-3 text-slate-900 dark:text-slate-100">{title}</h2>}
      {children}
    </div>
  )
}
const Field = ({ label, children }) => (<div><label className="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-1">{label}</label>{children}</div>)
const Stat = ({ b, s }) => (<div className="flex-1 bg-brand-50 dark:bg-slate-700/50 border border-brand-100 dark:border-slate-600 rounded-lg py-2 text-center"><b className="block text-lg text-slate-900 dark:text-slate-100">{b}</b><span className="text-[.66rem] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{s}</span></div>)

/* --------------------------------- Navbar --------------------------------- */
function Navbar({ view, setView, title, setTitle, recording, onToggle, onUpload, dark, onTheme }) {
  const fileRef = useRef()
  return (
    <nav className="sticky top-0 z-20 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
      <div className="max-w-[1080px] mx-auto flex items-center gap-2.5 px-5 py-2 flex-wrap">
        <div className="flex items-center gap-2 font-extrabold text-[1.02rem] text-slate-900 dark:text-slate-100">
          <span className="grid place-items-center w-7 h-7 rounded-lg bg-brand-600 text-white"><Mic size={16} /></span>
          Meeting‑to‑Action
        </div>
        <div className="flex gap-1 ml-1 bg-slate-100 dark:bg-slate-800 p-0.5 rounded-lg">
          <TabBtn active={view === 'dashboard'} onClick={() => setView('dashboard')} icon={<LayoutDashboard size={14} />}>Dashboard</TabBtn>
          <TabBtn active={view === 'history'} onClick={() => setView('history')} icon={<Clock size={14} />}>History</TabBtn>
        </div>
        <div className="flex-1" />
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Team standup"
          className="w-40 text-sm border border-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500/50" />
        <input ref={fileRef} type="file" accept="audio/*" className="hidden" onChange={onUpload} />
        <button className={`${navGhost} !px-2`} onClick={onTheme} title="Toggle theme" aria-label="Toggle dark mode">
          {dark ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button className={navGhost} onClick={() => fileRef.current.click()}><Upload size={15} /> Upload</button>
        <button className={recording ? navDanger : navAccent} onClick={onToggle}>
          {recording ? <><Square size={15} /> Stop</> : <><Mic size={15} /> Start meeting</>}
        </button>
      </div>
    </nav>
  )
}
const TabBtn = ({ active, onClick, icon, children }) => (
  <button onClick={onClick} className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[13px] font-semibold cursor-pointer transition-colors ${active ? 'bg-white dark:bg-slate-700 text-brand-700 dark:text-brand-300 shadow-sm' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}>{icon}{children}</button>
)

/* --------------------------------- App ------------------------------------ */
export default function App() {
  const [view, setView] = useState('dashboard')
  const [title, setTitle] = useState('')
  const [date, setDate] = useState('')
  const [rosterStr, setRosterStr] = useState('')
  const [mics, setMics] = useState([])
  const [micId, setMicId] = useState('')
  const [recording, setRecording] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [stats, setStats] = useState({ seconds: 0, segments: 0 })
  const [extraction, setExtraction] = useState(null)
  const [chat, setChat] = useState([])
  const [emailTo, setEmailTo] = useState('')
  const [toast, setToast] = useState('')
  const [busy, setBusy] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [postErrorMsg, setPostErrorMsg] = useState('')
  const [hist, setHist] = useState([])   // session-only: empty on each new session
  const [dark, setDark] = useState(() => {
    const s = localStorage.getItem('theme')
    return s ? s === 'dark' : window.matchMedia?.('(prefers-color-scheme: dark)').matches || false
  })
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  const recRef = useRef(null)
  const transcriptRef = useRef('')
  const lastExtractRef = useRef(0)
  const extractingRef = useRef(false)
  const rateLimitedUntilRef = useRef(0)   // pause live extraction after a 429
  const metaRef = useRef({})
  metaRef.current = { title, date, owners: parseOwners(rosterStr) }

  const showToast = (m) => { setToast(m); setTimeout(() => setToast(''), 3200) }

  useEffect(() => { refreshMics() }, [])
  async function refreshMics() {
    try {
      const devs = await navigator.mediaDevices.enumerateDevices()
      setMics(devs.filter((d) => d.kind === 'audioinput').map((d, i) => ({ id: d.deviceId, label: d.label || `Microphone ${i + 1}` })))
    } catch {}
  }

  async function doExtract(text) {
    if (!text?.trim()) return null
    const { extraction: ext, error } = await api.extract(text, metaRef.current)
    if (ext) { setExtraction(ext); setPostErrorMsg('') }
    else if (error) {
      setPostErrorMsg(error)
      if (/rate limit|quota|429/i.test(error)) rateLimitedUntilRef.current = Date.now() + 60000
    }
    return ext
  }

  async function start() {
    setTranscript(''); transcriptRef.current = ''; setExtraction(null); setChat([])
    setStats({ seconds: 0, segments: 0 }); lastExtractRef.current = 0
    const r = new SegmentRecorder({
      deviceId: micId,
      segMs: 5000,                     // shorter chunks -> transcript appears faster
      onText: (t) => {
        transcriptRef.current = (transcriptRef.current + ' ' + t).trim()
        setTranscript(transcriptRef.current)
        setStats(r.stats())
        // Re-extract periodically so action items update live. Kept at ~10s to
        // stay well under Gemini's free-tier 20 req/min; paused after a 429.
        const now = Date.now()
        if (now - lastExtractRef.current >= 10000 && now >= rateLimitedUntilRef.current && !extractingRef.current) {
          lastExtractRef.current = now
          extractingRef.current = true
          setAnalyzing(true)
          doExtract(transcriptRef.current).finally(() => { extractingRef.current = false; setAnalyzing(false) })
        }
      },
      onTick: (s) => setStats(s),
    })
    try { await r.start() } catch (e) { showToast('Mic error: ' + e.message); return }
    recRef.current = r
    setRecording(true)
    refreshMics()
  }

  async function stop() {
    setRecording(false); setBusy(true); setPostErrorMsg('')
    // Drain the audio buffer, but never hang forever — cap the wait.
    try {
      await Promise.race([
        recRef.current?.stop() ?? Promise.resolve(),
        new Promise((r) => setTimeout(r, 15000)),
      ])
    } catch {}
    const text = transcriptRef.current
    if (!text.trim()) { setBusy(false); showToast('No speech captured.'); return }
    showToast('Summarizing…')
    await doExtract(text)   // sets extraction, or postErrorMsg on failure
    setBusy(false)
  }

  async function retrySummary() {
    setBusy(true); setPostErrorMsg('')
    await doExtract(transcriptRef.current)
    setBusy(false)
  }

  const toggle = () => (recording ? stop() : start())

  async function onUpload(e) {
    const f = e.target.files[0]
    if (!f) return
    setBusy(true); showToast('Transcribing upload…')
    const fd = new FormData(); fd.append('audio', f, f.name)
    const resp = await fetch('/api/transcribe', { method: 'POST', body: fd })
    const j = await resp.json()
    transcriptRef.current = j.transcript || ''
    setTranscript(transcriptRef.current)
    await doExtract(transcriptRef.current)
    setBusy(false)
  }

  async function askAgent(q) {
    if (!q.trim()) return
    setChat((c) => [...c, { role: 'user', text: q }])
    const a = await api.ask(transcriptRef.current, q)
    setChat((c) => [...c, { role: 'assistant', text: a }])
  }
  async function pushNotion() {
    try {
      const n = await api.confirmToNotion(extraction.action_items || [], title)
      const now = new Date().toISOString()
      const entries = (extraction.action_items || []).map((it, i) => ({
        id: `${Date.now()}-${i}`,
        task: it.task, owner: it.owner, deadline: it.deadline,
        status: 'Not started', meeting: title || extraction.meeting_title || 'meeting',
        created_at: now,
      }))
      setHist((h) => [...entries, ...h])   // record in this session's history
      showToast(`Pushed ${n} tasks to Notion.`)
    } catch { showToast('Push failed.') }
  }
  async function sendEmail() {
    const to = emailTo.split(',').map((s) => s.trim()).filter(Boolean)
    if (!to.length) return showToast('Add at least one recipient.')
    try { const n = await api.emailSummary(to, `Meeting Summary — ${extraction.meeting_title || 'Meeting'}`, summaryHtml(extraction)); showToast(`Sent to ${n} recipient(s).`) }
    catch (e) { showToast(e.message) }
  }
  async function downloadIcs() {
    const j = await api.calendarIcs(extraction.action_items || [], extraction.meeting_title)
    if (!j.events) return showToast('No tasks with deadlines to schedule.')
    download('meeting_tasks.ics', j.ics, 'text/calendar'); showToast(`${j.events} event(s) in .ics`)
  }
  const items = extraction?.action_items || []
  const askEnabled = transcriptRef.current.length > 0 && !recording

  return (
    <div className="min-h-full text-slate-900 dark:text-slate-100">
      <Navbar {...{ view, setView, title, setTitle, recording, onToggle: toggle, onUpload, dark, onTheme: () => setDark((d) => !d) }} />

      <main className="max-w-[1080px] mx-auto px-5 py-5">
        {view === 'history' ? (
          <History hist={hist} />
        ) : (
          <>
            <details className="mb-4">
              <summary className="cursor-pointer text-slate-500 font-semibold select-none">Meeting setup — date, team members, microphone</summary>
              <div className="grid md:grid-cols-3 gap-3 mt-3">
                <Field label="Meeting date (YYYY-MM-DD)"><input className={input} placeholder="2026-08-15" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
                <Field label="Known team members (comma-separated)"><input className={input} placeholder="Sarah, Raj, Priya" value={rosterStr} onChange={(e) => setRosterStr(e.target.value)} /></Field>
                <Field label="Microphone"><select className={input} value={micId} onChange={(e) => setMicId(e.target.value)}><option value="">Default</option>{mics.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}</select></Field>
              </div>
            </details>

            <div className="grid lg:grid-cols-[1.9fr_1fr] gap-4">
              <Card title={<><Mic size={18} className="text-brand-600" /> Live Transcript {recording && <span className="ml-1 inline-flex items-center gap-1 text-xs text-red-600 font-semibold"><span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" /> recording</span>}</>}>
                {recording && (
                  <div className="flex gap-2 mb-3">
                    <Stat b={`${stats.seconds}s`} s="captured" />
                    <Stat b={stats.segments} s="segments" />
                    <Stat b={transcript ? transcript.split(/\s+/).length : 0} s="words" />
                  </div>
                )}
                <div className="min-h-[260px] max-h-[360px] overflow-y-auto leading-relaxed whitespace-pre-wrap bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700 rounded-lg p-4 text-slate-700 dark:text-slate-300">
                  {transcript || <span className="text-slate-400">Press “Start meeting”, or upload audio.</span>}
                </div>
                {recording && <p className="text-slate-400 mt-2 text-sm inline-flex items-center gap-1.5"><Loader2 size={14} className="animate-spin" /> Live transcribing{stats.pending > 0 ? ` · ${stats.pending} segment${stats.pending > 1 ? 's' : ''} buffered` : ''} — capture never blocks.</p>}
                {busy && !recording && <p className="text-slate-400 mt-2 text-sm inline-flex items-center gap-1.5"><Loader2 size={14} className="animate-spin" /> Finishing transcription & summarizing…</p>}
              </Card>

              <Card title={<><ListChecks size={18} className="text-brand-600" /> Action Items <span className="ml-1 bg-brand-50 dark:bg-slate-700 text-brand-700 dark:text-brand-300 rounded-full px-2.5 py-0.5 text-sm font-bold">{items.length}</span>{recording && analyzing && <span className="ml-auto inline-flex items-center gap-1 text-xs text-brand-600 font-medium"><Loader2 size={13} className="animate-spin" /> analyzing</span>}</>}>
                <div className="max-h-[360px] overflow-y-auto space-y-2 pr-1">
                  {items.length ? items.map((it, i) => (
                    <div key={i} className="border border-slate-200 dark:border-slate-700 rounded-lg p-3 hover:border-brand-300 transition-colors animate-fade-up">
                      <b className="block text-slate-900 dark:text-slate-100">{it.task}</b>
                      <span className="text-slate-500 text-sm">{it.owner || 'Unassigned'} · due {it.deadline || 'no deadline'}</span>
                    </div>
                  )) : recording ? (
                    <div className="text-center py-10 px-4">
                      <Loader2 size={26} className="mx-auto text-brand-500 mb-2 animate-spin" />
                      <p className="text-slate-400 text-sm">Listening for tasks… say “<b className="text-slate-500 dark:text-slate-300">Raj will fix the login bug by Monday.</b>”</p>
                    </div>
                  ) : (
                    <div className="text-center py-10 px-4">
                      <ListChecks size={30} className="mx-auto text-slate-300 mb-2" />
                      <p className="text-slate-400 text-sm">No tasks yet. Say “<b className="text-slate-500 dark:text-slate-300">Sarah will finalize the budget by Friday.</b>”</p>
                    </div>
                  )}
                </div>
              </Card>
            </div>

            <div className="mt-4">
              <AskAgent enabled={askEnabled} recording={recording} chat={chat} onAsk={askAgent} />
            </div>

            {!recording && transcript && (
              extraction ? (
                <Results ext={extraction} emailTo={emailTo} setEmailTo={setEmailTo}
                  onEmail={sendEmail} onIcs={downloadIcs} onPush={pushNotion}
                  onDownload={() => download('meeting_summary.md', summaryMd(extraction), 'text/markdown')} />
              ) : busy ? (
                <div className="mt-4 animate-fade-up">
                  <Card>
                    <div className="py-8 text-center text-slate-500 dark:text-slate-400 inline-flex flex-col items-center w-full">
                      <Loader2 size={26} className="animate-spin text-brand-600 mb-2" />
                      Analyzing your meeting and preparing the summary…
                    </div>
                  </Card>
                </div>
              ) : postErrorMsg ? (
                <div className="mt-4 animate-fade-up">
                  <Card>
                    <div className="py-6 text-center">
                      <p className="text-slate-500 dark:text-slate-400 mb-3">{postErrorMsg}</p>
                      <button className={primary} onClick={retrySummary}><Sparkles size={16} /> Retry summary</button>
                    </div>
                  </Card>
                </div>
              ) : null
            )}
          </>
        )}
      </main>

      {toast && <div className="fixed right-5 bottom-5 bg-ink text-white px-4 py-2.5 rounded-lg z-50 animate-fade-up shadow-lg">{toast}</div>}
    </div>
  )
}

function AskAgent({ enabled, recording, chat, onAsk }) {
  const [q, setQ] = useState('')
  const ph = recording ? 'Recording… stop the meeting to ask questions.' : enabled ? 'Ask anything about the meeting…' : 'Start a meeting first to ask questions.'
  const submit = () => { if (enabled && q.trim()) { onAsk(q); setQ('') } }
  return (
    <Card title={<><MessageSquare size={18} className="text-brand-600" /> Ask the agent</>}>
      {chat.length > 0 && (
        <div className="max-h-64 overflow-y-auto mb-3 space-y-2">
          {chat.map((m, i) => (
            <div key={i} className={`px-3.5 py-2 rounded-lg max-w-[85%] text-sm ${m.role === 'user' ? 'bg-brand-50 dark:bg-slate-700 ml-auto text-slate-900 dark:text-slate-100' : 'bg-slate-100 dark:bg-slate-700/60 dark:text-slate-200'}`}>{m.text}</div>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <input className={input} placeholder={ph} disabled={!enabled} value={q}
          onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} />
        <button className={primary} disabled={!enabled} onClick={submit}><Send size={16} /> Ask</button>
      </div>
    </Card>
  )
}

function Results({ ext, emailTo, setEmailTo, onEmail, onIcs, onPush, onDownload }) {
  const dated = (ext.action_items || []).filter((it) => it.deadline)
  const List = ({ arr }) => (<ul className="list-disc pl-5 space-y-1">{arr?.length ? arr.map((x, i) => <li key={i}>{x}</li>) : <li className="text-slate-400">None</li>}</ul>)
  return (
    <div className="mt-4 space-y-4 animate-fade-up">
      <Card title={<><FileText size={18} className="text-brand-600" /> Meeting Summary</>}>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-4">
            <Card title="Overview" pad="p-4"><p className="text-slate-600">{ext.summary || 'No summary.'}</p></Card>
            <Card title={<><CheckCircle2 size={16} className="text-brand-600" /> Key Decisions</>} pad="p-4"><List arr={ext.decisions} /></Card>
          </div>
          <div className="space-y-4">
            <Card title={<><Lightbulb size={16} className="text-brand-600" /> Proposed Solutions</>} pad="p-4"><List arr={ext.proposed_solutions} /></Card>
            <Card title={<><ListChecks size={16} className="text-brand-600" /> Next Action Steps</>} pad="p-4">
              <ul className="list-disc pl-5 space-y-1">
                {(ext.action_items || []).map((it, i) => (<li key={i}><b>{it.task}</b> — {it.owner || 'Unassigned'} · due <i>{it.deadline || 'no deadline'}</i></li>))}
                {!(ext.action_items || []).length && <li className="text-slate-400">None</li>}
              </ul>
            </Card>
          </div>
        </div>
        <button className={`${ghost} mt-4`} onClick={onDownload}><Download size={16} /> Download summary (.md)</button>
      </Card>

      <Card title={<><Rocket size={18} className="text-brand-600" /> Share & schedule</>}>
        <div className="grid md:grid-cols-2 gap-5">
          <div>
            <label className="text-xs font-semibold text-slate-500 block mb-1 inline-flex items-center gap-1"><Mail size={14} /> Email the summary — recipients (comma-separated)</label>
            <div className="flex gap-2"><input className={input} placeholder="alice@team.com, bob@team.com" value={emailTo} onChange={(e) => setEmailTo(e.target.value)} /><button className={primary} onClick={onEmail}><Send size={16} /> Send</button></div>
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-500 block mb-1 inline-flex items-center gap-1"><Calendar size={14} /> Add tasks to calendar</label>
            <button className={ghost} onClick={onIcs}><Download size={16} /> Download .ics (with reminders)</button>
            {dated.length > 0 && (
              <div className="mt-2 text-sm">
                <div className="text-slate-400 mb-1">Or one-click add to Google Calendar:</div>
                {dated.map((it, i) => (<div key={i} className="inline-flex items-center gap-1"><Calendar size={13} className="text-brand-600" /> <a className="text-brand-700 hover:underline" target="_blank" href={gcalLink(it, ext.meeting_title)}>{it.task}</a></div>))}
              </div>
            )}
          </div>
        </div>
      </Card>

      <Card title={<><CheckCircle2 size={18} className="text-brand-600" /> Confirm & push to Notion</>}>
        <p className="text-slate-400 mb-2 text-sm">Ambiguous/unresolved owners are flagged for review.</p>
        <div className="space-y-2">
          {(ext.action_items || []).map((it, i) => {
            const ok = it.owner_status === 'resolved'
            return (
              <div key={i} className="border border-slate-200 dark:border-slate-700 rounded-lg p-3">
                <div className="flex items-center gap-2"><b>{it.task}</b><span className={`text-xs font-bold rounded-full px-2 py-0.5 ${ok ? 'bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-300' : 'bg-orange-100 text-accent-700 dark:bg-orange-500/20 dark:text-orange-300'}`}>{ok ? 'resolved' : 'review'}</span></div>
                <div className="text-slate-500 text-sm">{it.owner || 'Unassigned'} · due {it.deadline || 'no deadline'}</div>
              </div>
            )
          })}
        </div>
        <button className={`${accentBtn} mt-3`} onClick={onPush}><CheckCircle2 size={16} /> Push to Notion</button>
      </Card>
    </div>
  )
}

function History({ hist }) {
  return (
    <Card title={<><Clock size={18} className="text-brand-600" /> Meeting history <span className="ml-1 text-xs font-medium text-slate-400">(this session)</span></>}>
      {!hist.length ? (
        <div className="text-center py-12 px-4">
          <Inbox size={32} className="mx-auto text-slate-300 mb-2" />
          <p className="text-slate-400 text-sm">No meetings yet this session. Tasks you push to Notion will appear here.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">{['Task', 'Owner', 'Deadline', 'Status', 'Meeting', 'Created'].map((h) => <th key={h} className="text-left py-2 px-2 font-semibold">{h}</th>)}</tr></thead>
            <tbody>
              {hist.map((t) => (
                <tr key={t.id} className="border-b border-slate-100 dark:border-slate-700/60 hover:bg-brand-50/40 dark:hover:bg-slate-700/40">
                  <td className="py-2 px-2">{t.task}</td><td className="py-2 px-2">{t.owner || '—'}</td>
                  <td className="py-2 px-2">{t.deadline || '—'}</td><td className="py-2 px-2">{t.status}</td>
                  <td className="py-2 px-2">{t.meeting || '—'}</td><td className="py-2 px-2">{(t.created_at || '').slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
