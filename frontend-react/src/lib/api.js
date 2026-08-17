// Same-origin in production (/api). Vite proxies /api to :8000 in dev.
const base = '/api'

async function post(path, body) {
  const r = await fetch(base + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return r
}

export async function extract(transcript, meta) {
  const r = await post('/extract', {
    transcript,
    meeting_title: meta.title || null,
    meeting_date: meta.date || null,
    known_owners: meta.owners || [],
  })
  if (!r.ok) {
    let error = 'Extraction failed.'
    try { error = (await r.json()).detail || error } catch {}
    return { extraction: null, error }
  }
  return { extraction: (await r.json()).extraction, error: null }
}

export async function transcribeBlob(blob) {
  const ext = blob.type.includes('ogg') ? 'ogg' : 'webm'
  const fd = new FormData()
  fd.append('audio', blob, 'seg.' + ext)
  try {
    const r = await fetch(base + '/transcribe', { method: 'POST', body: fd })
    return (await r.json()).transcript?.trim() || ''
  } catch {
    return ''
  }
}

export async function ask(transcript, question) {
  try {
    const r = await post('/ask', { transcript, question })
    return (await r.json()).answer || '(no answer)'
  } catch {
    return '⚠️ Model busy — please ask again.'
  }
}

export async function confirmToNotion(items, label) {
  const r = await post('/confirm', { items, meeting_label: label || 'meeting' })
  if (!r.ok) throw new Error('push failed')
  return (await r.json()).pushed
}

export async function emailSummary(recipients, subject, html) {
  const r = await post('/email-summary', { recipients, subject, html })
  if (r.status === 400) throw new Error((await r.json()).detail)
  if (!r.ok) throw new Error('email failed')
  return (await r.json()).sent
}

export async function calendarIcs(action_items, meeting_title) {
  const r = await post('/calendar-ics', { action_items, meeting_title })
  return await r.json()
}

export async function history() {
  const r = await fetch(base + '/history')
  return (await r.json()).tasks
}
