import { useState, useCallback, useEffect } from 'react'
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
  const [conversations, setConversations] = useState(() => {
    try {
      const saved = localStorage.getItem('synapseai_convs')
      return saved ? JSON.parse(saved) : [makeConv()]
    } catch { return [makeConv()] }
  })
  const [activeId, setActiveId] = useState(() => {
    const saved = localStorage.getItem('synapseai_convs')
    if (saved) {
      const convs = JSON.parse(saved)
      return convs[0]?.id ?? makeConv().id
    }
    return conversations[0]?.id
  })
  const [model, setModel]         = useState('auto')
  const [webSearch, setWebSearch] = useState(true)
  const [loading, setLoading]     = useState(false)
  const [models, setModels]       = useState(['auto', 'qwen3.5:9b', 'deepseek-r1:8b', 'llama3.2-vision:11b'])

  // Persist conversations
  useEffect(() => {
    localStorage.setItem('synapseai_convs', JSON.stringify(conversations))
  }, [conversations])

  // Load model list from backend
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

  const sendMessage = useCallback(async (content) => {
    if (!content.trim() || loading) return
    const convId = activeId
    const userMsg = { role: 'user', content, id: `u${Date.now()}` }
    const asstId  = `a${Date.now() + 1}`

    // Add user message + empty assistant placeholder
    updateConv(convId, c => ({
      ...c,
      title: c.messages.length === 0 ? content.slice(0, 45) : c.title,
      messages: [...c.messages, userMsg, { role: 'assistant', content: '', id: asstId, model: '', search: false }],
    }))
    setLoading(true)

    try {
      const history = [...(activeConv?.messages ?? []), userMsg].map(m => ({
        role: m.role, content: m.content,
      }))
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history, model, web_search: webSearch }),
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
      updateConv(convId, c => ({
        ...c,
        messages: c.messages.map(m =>
          m.id === asstId ? { ...m, content: `Error: ${e.message}` } : m
        ),
      }))
    } finally {
      setLoading(false)
    }
  }, [activeId, activeConv, loading, model, webSearch])

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
