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

export default function InputBar({ onSend, model, models, onModelChange, webSearch, onWebSearchToggle, loading }) {
  const [text, setText] = useState('')
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }, [text])

  const submit = () => {
    const trimmed = text.trim()
    if (!trimmed || loading) return
    onSend(trimmed)
    setText('')
    textareaRef.current.style.height = 'auto'
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
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
        </div>

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
          <button
            className="send-btn"
            onClick={submit}
            disabled={loading || !text.trim()}
            title="Send (Enter)"
          >
            {loading ? (
              <span className="spinner" />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            )}
          </button>
        </div>

        <p className="input-hint">SynapseAI can make mistakes. Verify important info.</p>
      </div>
    </div>
  )
}
