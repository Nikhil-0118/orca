import React from 'react';
import { Plus, MessageSquare, Shield, Anchor } from 'lucide-react';

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onOpenSafety?: () => void;
  isOffline?: boolean;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  isOpen,
  onClose,
  onNewChat,
  onOpenSafety,
  isOffline = false,
}) => {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="chat-sidebar-backdrop hidden max-md:block"
          onClick={onClose}
        />
      )}

      <aside className={`chat-sidebar ${!isOpen ? 'collapsed' : ''}`}>
        {/* Header with branding */}
        <div className="chat-sidebar-header">
          <div className="chat-sidebar-brand">
            <div className="chat-sidebar-logo">
              <Anchor className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <span className="chat-sidebar-title">ORCA</span>
          </div>
        </div>

        {/* New Chat Button */}
        <button
          type="button"
          className="chat-new-btn"
          onClick={() => {
            onNewChat();
            if (window.innerWidth < 768) {
              onClose();
            }
          }}
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>

        {/* Safety Simulator Launch Button */}
        {onOpenSafety && (
          <button
            type="button"
            className="chat-new-btn"
            style={{
              marginTop: 8,
              borderColor: isOffline ? 'rgba(239, 68, 68, 0.4)' : 'rgba(6, 182, 212, 0.3)',
              background: isOffline ? 'rgba(239, 68, 68, 0.08)' : 'rgba(6, 182, 212, 0.05)',
              color: isOffline ? '#f87171' : '#06b6d4',
            }}
            onClick={() => {
              onOpenSafety();
              if (window.innerWidth < 768) {
                onClose();
              }
            }}
          >
            <Shield className="w-4 h-4" />
            <span>Safety Simulator {isOffline ? '(Offline)' : ''}</span>
          </button>
        )}

        {/* Conversation History */}
        <div className="chat-sidebar-history">
          <div className="chat-sidebar-empty">
            <div className="chat-sidebar-empty-icon">
              <MessageSquare className="w-5 h-5" />
            </div>
            <p>No conversations yet.</p>
            <p style={{ marginTop: 4, fontSize: 12 }}>
              Start a new chat to begin.
            </p>
          </div>
        </div>

        {/* Footer with Mode Indicator */}
        <div className="chat-sidebar-footer">
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 8,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: '100%',
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(100, 116, 139, 0.15)',
              color: isOffline ? '#f87171' : '#94a3b8',
            }}
          >
            <span>Safety Engine:</span>
            <span style={{ color: '#10b981', fontWeight: 'bold' }}>ACTIVE</span>
          </div>
        </div>
      </aside>
    </>
  );
};
