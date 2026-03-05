import { useState, useCallback, useEffect, useRef } from 'react'
import Sidebar from './components/Sidebar.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import InputBar from './components/InputBar.jsx'

const makeConv = () => ({ id: Date.now().toString(), title: 'New chat', messages: [] })

// Parse SSE stream into data objects
async function* parseSSE(response) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try { yield JSON.parse(line.slice(6)) } catch {}
      }
    }
  }
}

export default function App() {
  const [conversations, setConversations] = useState([])
  const [activeId, setActiveId]           = useState(null)
  const [loaded, setLoaded]               = useState(false)
  const [model, setModel]                 = useState('auto')
  const [webSearch, setWebSearch]         = useState(true)
  const [loading, setLoading]             = useState(false)
  const [models, setModels]               = useState(['auto', 'qwen3.5:9b', 'deepseek-r1:8b', 'llama3.2-vision:11b'])
  const abortRef    = useRef(null)
  const saveTimers  = useRef({})

  // ── Load conversations from backend on mount ──────────────────────────────
  useEffect(() => {
    fetch('/api/conversations')
      .then(r => r.json())
      .then(d => {
        const convs = d.conversations ?? []
        if (convs.length === 0) {
          const fresh = makeConv()
          setConversations([fresh])
          setActiveId(fresh.id)
        } else {
          setConversations(convs)
          setActiveId(convs[0].id)
        }
      })
      .catch(() => {
        const fresh = makeConv()
        setConversations([fresh])
        setActiveId(fresh.id)
      })
      .finally(() => setLoaded(true))
  }, [])

  // ── Debounced save to backend whenever conversations change ───────────────
  useEffect(() => {
    if (!loaded) return
    conversations.forEach(conv => {
      if (conv.messages.length === 0) return   // don't save empty chats
      clearTimeout(saveTimers.current[conv.id])
      saveTimers.current[conv.id] = setTimeout(() => {
        fetch(`/api/conversations/${conv.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(conv),
        }).catch(() => {})
      }, 600)
    })
  }, [conversations, loaded])

  // ── Load model list from backend ──────────────────────────────────────────
  useEffect(() => {
    fetch('/api/models')
      .then(r => r.json())
      .then(d => { if (d.models?.length) setModels(d.models) })
      .catch(() => {})
  }, [])

  const activeConv = conversations.find(c => c.id === activeId) ?? conversations[0]

  const updateConv = (id, updater) =>
    setConversations(prev => prev.map(c => c.id === id ? updater(c) : c))

  const newChat = () => {
    const conv = makeConv()
    setConversations(prev => [conv, ...prev])
    setActiveId(conv.id)
  }

  const deleteConv = (id) => {
    // Delete from backend (removes files too)
    fetch(`/api/conversations/${id}`, { method: 'DELETE' }).catch(() => {})
    setConversations(prev => {
      const next = prev.filter(c => c.id !== id)
      if (next.length === 0) {
        const fresh = makeConv()
        setActiveId(fresh.id)
        return [fresh]
      }
      if (activeId === id) setActiveId(next[0].id)
      return next
    })
  }

  const stopGeneration = () => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
  }

  const sendMessage = useCallback(async (content, attachment) => {
    if (!content.trim() || loading) return
    const convId = activeId

    // Build user message — store attachment_meta for display & Ollama calls
    const userMsg = {
      role: 'user',
      content,
      id: `u${Date.now()}`,
      ...(attachment?.type === 'text'  && { file_context: attachment.content }),
      ...(attachment && {
        attachment_meta: {
          name:     attachment.name,
          type:     attachment.type,
          file_url: attachment.file_url,
          mime:     attachment.mime ?? null,
        },
      }),
    }
    const asstId = `a${Date.now() + 1}`

    updateConv(convId, c => ({
      ...c,
      title: c.messages.length === 0 ? content.slice(0, 45) : c.title,
      messages: [...c.messages, userMsg,
        { role: 'assistant', content: '', id: asstId, model: '', search: false }],
    }))
    setLoading(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const history = [...(activeConv?.messages ?? []), userMsg].map(m => ({
        role:    m.role,
        content: m.content,
        ...(m.file_context    && { file_context:    m.file_context }),
        ...(m.attachment_meta && { attachment_meta: m.attachment_meta }),
      }))

      const response = await fetch('/api/chat', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ messages: history, model, web_search: webSearch }),
        signal:  controller.signal,
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      for await (const data of parseSSE(response)) {
        if (data.type === 'meta') {
          updateConv(convId, c => ({
            ...c,
            messages: c.messages.map(m =>
              m.id === asstId ? { ...m, model: data.model, search: data.search } : m
            ),
          }))
        } else if (data.type === 'token') {
          updateConv(convId, c => ({
            ...c,
            messages: c.messages.map(m =>
              m.id === asstId ? { ...m, content: m.content + data.content } : m
            ),
          }))
        } else if (data.type === 'error') {
          throw new Error(data.message)
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        updateConv(convId, c => ({
          ...c,
          messages: c.messages.map(m =>
            m.id === asstId ? { ...m, content: m.content || `Error: ${e.message}` } : m
          ),
        }))
      }
    } finally {
      abortRef.current = null
      setLoading(false)
    }
  }, [activeId, activeConv, loading, model, webSearch])

  if (!loaded) {
    return (
      <div className="app" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Loading…</div>
      </div>
    )
  }

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={newChat}
        onDelete={deleteConv}
      />
      <main className="main">
        <ChatWindow messages={activeConv?.messages ?? []} loading={loading} />
        <InputBar
          onSend={sendMessage}
          onStop={stopGeneration}
          convId={activeId}
          model={model}
          models={models}
          onModelChange={setModel}
          webSearch={webSearch}
          onWebSearchToggle={() => setWebSearch(v => !v)}
          loading={loading}
        />
      </main>
    </div>
  )
}
