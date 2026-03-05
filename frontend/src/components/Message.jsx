import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function CodeBlock({ className, children }) {
  const [copied, setCopied] = useState(false)
  const lang = className?.replace('language-', '') ?? ''
  const code = String(children).replace(/\n$/, '')

  const copy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="code-block">
      <div className="code-header">
        <span className="code-lang">{lang || 'code'}</span>
        <button className="copy-btn" onClick={copy}>{copied ? '✓ Copied' : 'Copy'}</button>
      </div>
      <pre><code>{code}</code></pre>
    </div>
  )
}

const MODEL_LABELS = {
  'qwen3.5:9b':          'Qwen3.5 9B',
  'deepseek-r1:8b':      'DeepSeek R1 8B',
  'llama3.2-vision:11b': 'Llama 3.2 Vision',
  'llama3.2:latest':     'Llama 3.2',
}

export default function Message({ role, content, model, search, isStreaming }) {
  const [showThinking, setShowThinking] = useState(false)

  // Extract <think>...</think> from DeepSeek R1
  const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/)
  const thinking = thinkMatch?.[1]?.trim()
  const display  = content.replace(/<think>[\s\S]*?<\/think>/g, '').trim()

  const label = MODEL_LABELS[model] ?? model

  return (
    <div className={`message message-${role}`}>
      {role === 'assistant' && (
        <div className="message-meta">
          {label && <span className="model-badge">{label}</span>}
          {search && <span className="search-badge">🔍 Web</span>}
        </div>
      )}

      {thinking && (
        <div className="thinking-block">
          <button
            className="thinking-toggle"
            onClick={() => setShowThinking(v => !v)}
          >
            {showThinking ? '▼' : '▶'} Thinking ({thinking.split(' ').length} words)
          </button>
          {showThinking && <div className="thinking-content">{thinking}</div>}
        </div>
      )}

      <div className="message-body">
        {role === 'user' ? (
          <p className="user-text">{content}</p>
        ) : (
          <>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }) {
                  return inline
                    ? <code className="inline-code" {...props}>{children}</code>
                    : <CodeBlock className={className}>{children}</CodeBlock>
                },
                a({ href, children }) {
                  return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
                },
              }}
            >
              {display || (isStreaming ? '' : content)}
            </ReactMarkdown>
            {isStreaming && !display && (
              <span className="cursor-blink">▍</span>
            )}
          </>
        )}
      </div>
    </div>
  )
}
