import { transcribeBlob } from './api'

/**
 * Producer/consumer pipeline for live transcription.
 *
 * CAPTURE (producer) runs back-to-back audio segments and hands each blob off
 * to a processing chain WITHOUT waiting — so the mic never stalls on Whisper.
 * TRANSCRIPTION (consumer) drains the queue in order in the background. If the
 * backend is slow, blobs buffer instead of being dropped, so no speech is lost.
 */
export class SegmentRecorder {
  constructor({ deviceId, segMs = 5000, onText, onTick } = {}) {
    this.deviceId = deviceId
    this.segMs = segMs
    this.onText = onText
    this.onTick = onTick
    this.recording = false
    this.stream = null
    this.rec = null
    this.timer = null
    this.captured = 0    // segments recorded (producer)
    this.processed = 0   // segments transcribed (consumer)
    this.pending = 0     // segments waiting in the buffer
    this._chain = Promise.resolve()  // ordered processing pipeline
    this._cleanedUp = false
  }

  _mime() {
    for (const m of ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus']) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return m
    }
    return ''
  }

  async start() {
    const mime = this._mime()
    if (!mime) throw new Error('Audio recording not supported in this browser.')
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: this.deviceId ? { deviceId: { exact: this.deviceId } } : true,
    })
    this.recording = true
    this.mime = mime
    this._captureLoop()
  }

  // PRODUCER: record a segment, hand it off, immediately start the next one.
  _captureLoop() {
    const rec = new MediaRecorder(this.stream, { mimeType: this.mime })
    const chunks = []
    rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data) }
    rec.onstop = () => {
      const blob = new Blob(chunks, { type: rec.mimeType })
      this.captured++
      this._enqueue(blob)               // non-blocking hand-off
      if (this.recording) this._captureLoop()   // gapless: next segment starts now
      else this._cleanup()
    }
    rec.start()
    this.rec = rec
    this.timer = setTimeout(() => { if (rec.state === 'recording') rec.stop() }, this.segMs)
  }

  // CONSUMER: append this blob to the ordered transcription pipeline.
  _enqueue(blob) {
    this.pending++
    this.onTick?.(this.stats())
    this._chain = this._chain.then(async () => {
      try {
        if (blob.size >= 1200) {
          const text = await transcribeBlob(blob)
          if (text) this.onText?.(text)
        }
      } finally {
        this.processed++
        this.pending--
        this.onTick?.(this.stats())
      }
    })
  }

  stats() {
    return {
      seconds: Math.round((this.captured * this.segMs) / 1000),
      segments: this.processed,
      pending: this.pending,
    }
  }

  _cleanup() {
    if (this._cleanedUp) return
    this._cleanedUp = true
    this.stream?.getTracks().forEach((t) => t.stop())
    this._doneResolve?.()
  }

  // Stop capture, then wait for the buffer to fully drain (no lost audio).
  async stop() {
    this.recording = false
    clearTimeout(this.timer)
    if (this.rec && this.rec.state !== 'inactive') this.rec.stop()
    else this._cleanup()
    await new Promise((res) => { this._doneResolve = res; if (this._cleanedUp) res() })
    await this._chain   // finish transcribing everything still queued
  }
}
