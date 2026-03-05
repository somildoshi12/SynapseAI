import { useEffect, useRef } from 'react'
import Message from './Message.jsx'

export default function ChatWindow({ messages, loading }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="chat-window empty">
        <div className="empty-state">
          <div className="empty-icon">🧠</div>
          <h2>SynapseAI</h2>
          <p>Your local AI — powered by Ollama.<br />Private, fast, and free.</p>
          <div className="model-hints">
            <span>⚡ Auto routes to the best model</span>
            <span>🔍 Web search built in</span>
            <span>💻 Code · Math · Vision</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-window">
      <div className="messages">
        {messages.map(msg => (
          <Message key={msg.id} {...msg} isStreaming={loading && msg === messages[messages.length - 1] && msg.role === 'assistant'} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
