export default function Sidebar({ conversations, activeId, onSelect, onNew, onDelete }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="logo">🧠 SynapseAI</span>
        <button className="new-chat-btn" onClick={onNew} title="New chat">+</button>
      </div>

      <nav className="conv-list">
        {conversations.map(conv => (
          <div
            key={conv.id}
            className={`conv-item ${conv.id === activeId ? 'active' : ''}`}
            onClick={() => onSelect(conv.id)}
          >
            <span className="conv-title">{conv.title || 'New chat'}</span>
            <button
              className="conv-delete"
              onClick={e => { e.stopPropagation(); onDelete(conv.id) }}
              title="Delete"
            >
              ×
            </button>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="footer-note">Local · Private · Free</span>
      </div>
    </aside>
  )
}
