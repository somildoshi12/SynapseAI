import { useState, useRef, useEffect } from 'react'

const MODEL_LABELS = {
  auto:                  '⚡ Auto',
  'qwen3.5:9b':          'Qwen3.5 9B',
  'deepseek-r1:8b':      'DeepSeek R1 8B',
  'llama3.2-vision:11b': 'Llama 3.2 Vision',
  'llama3.2:latest':     'Llama 3.2',
  'mxbai-embed-large:latest': 'mxbai (embed)',
  'nomic-embed-text:latest':  'nomic (embed)',
}

export default function InputBar({
  onSend, onStop, convId,
  model, models, onModelChange,
  webSearch, onWebSearchToggle,
  loading,
}) {
  const [text, setText]             = useState('')
  const [attachment, setAttachment] = useState(null)
  const [uploading, setUploading]   = useState(false)
  const textareaRef  = useRef(null)
  const fileInputRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }, [text])

  const submit = () => {
    const trimmed = text.trim()
    if ((!trimmed && !attachment) || loading) return
    onSend(trimmed || ' ', attachment)
    setText('')
    setAttachment(null)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const url = `/api/upload?conv_id=${encodeURIComponent(convId ?? 'default')}`
      const res = await fetch(url, { method: 'POST', body: fd })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail ?? `Upload failed (${res.status})`)
      }
      const data = await res.json()
      setAttachment({
        name:     data.name,
        type:     data.type,
        file_url: data.file_url,
        mime:     data.mime ?? null,
        base64:   data.base64 ?? null,   // kept for small images
        content:  data.content ?? null,  // text files
      })
    } catch (err) {
      alert(`File upload error: ${err.message}`)
    } finally {
      setUploading(false)
    }
  }

  // Filter out embedding models from selector
  const chatModels = models.filter(m =>
    !m.includes('embed') && !m.includes('nomic')
  )

  return (
    <div className="input-bar-wrap">
      <div className="input-bar">
        <div className="input-controls-top">
          {/* Model selector */}
          <select
            className="model-select"
            value={model}
            onChange={e => onModelChange(e.target.value)}
            disabled={loading}
          >
            {chatModels.map(m => (
              <option key={m} value={m}>{MODEL_LABELS[m] ?? m}</option>
            ))}
          </select>

          {/* Web search toggle */}
          <button
            className={`search-toggle ${webSearch ? 'active' : ''}`}
            onClick={onWebSearchToggle}
            disabled={loading}
            title={webSearch ? 'Web search ON — click to disable' : 'Web search OFF — click to enable'}
          >
            🔍 {webSearch ? 'Search ON' : 'Search OFF'}
          </button>

          {/* File upload */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf,.txt,.md,.py,.js,.ts,.jsx,.tsx,.json,.csv,.html,.css,.yaml,.yml,.sh,.sql,.xml"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <button
            className="attach-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading || uploading}
            title="Attach file (image, PDF, or text)"
          >
            {uploading ? <span className="spinner-sm" /> : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
              </svg>
            )}
          </button>
        </div>

        {/* Attachment preview chip */}
        {attachment && (
          <div className="attachment-preview">
            {attachment.type === 'image' ? (
              <img
                src={attachment.file_url ?? `data:image/jpeg;base64,${attachment.base64}`}
                alt={attachment.name}
                className="attachment-thumb"
              />
            ) : (
              <span className="attachment-icon">📄</span>
            )}
            <span className="attachment-name">{attachment.name}</span>
            <button
              className="attachment-remove"
              onClick={() => setAttachment(null)}
              title="Remove attachment"
            >×</button>
          </div>
        )}

        <div className="input-row">
          <textarea
            ref={textareaRef}
            className="chat-input"
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={onKey}
            placeholder="Message SynapseAI…  (Shift+Enter for new line)"
            rows={1}
            disabled={loading}
          />
          {loading ? (
            <button
              className="stop-btn"
              onClick={onStop}
              title="Stop generation"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <rect x="4" y="4" width="16" height="16" rx="2"/>
              </svg>
            </button>
          ) : (
            <button
              className="send-btn"
              onClick={submit}
              disabled={!text.trim() && !attachment}
              title="Send (Enter)"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          )}
        </div>

        <p className="input-hint">
          SynapseAI can make mistakes. Verify important info. &nbsp;·&nbsp; Made by Somil Doshi
        </p>
      </div>
    </div>
  )
}
