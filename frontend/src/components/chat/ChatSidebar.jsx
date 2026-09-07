import React from 'react';
import { Plus, MessageSquare, Shield, Anchor } from 'lucide-react';
import { useLanguage } from '../../i18n/LanguageContext';

export const ChatSidebar = ({ isOpen, onClose, onNewChat, onOpenSafety, isOffline = false }) => {
  const { t } = useLanguage();

  return (
    <>
      {isOpen && <div className="chat-sidebar-backdrop hidden max-md:block" onClick={onClose} />}
      <aside className={`chat-sidebar ${!isOpen ? 'collapsed' : ''}`}>
        <div className="chat-sidebar-header">
          <div className="chat-sidebar-brand">
            <div className="chat-sidebar-logo">
              <img src="/orca-emblem.png" alt="ORCA Logo" className="w-5 h-5 object-contain" />
            </div>
            <span className="chat-sidebar-title">ORCA</span>
          </div>
        </div>
        <button type="button" className="chat-new-btn" onClick={() => { onNewChat(); if (window.innerWidth < 768) onClose(); }}>
          <Plus className="w-4 h-4" /><span>{t('newChat', 'New Chat')}</span>
        </button>
        {onOpenSafety && (
          <button type="button" className="chat-new-btn"
            style={{ marginTop: 8, borderColor: isOffline ? 'rgba(239, 68, 68, 0.4)' : 'rgba(6, 182, 212, 0.3)', background: isOffline ? 'rgba(239, 68, 68, 0.08)' : 'rgba(6, 182, 212, 0.05)', color: isOffline ? '#f87171' : '#06b6d4' }}
            onClick={() => { onOpenSafety(); if (window.innerWidth < 768) onClose(); }}>
            <Shield className="w-4 h-4" /><span>{t('safetySimulator', 'Safety Simulator')} {isOffline ? '(Offline)' : ''}</span>
          </button>
        )}
        <div className="chat-sidebar-history">
          <div className="chat-sidebar-empty">
            <div className="chat-sidebar-empty-icon"><MessageSquare className="w-5 h-5" /></div>
            <p>{t('noConversations', 'No conversations yet.')}</p>
            <p style={{ marginTop: 4, fontSize: 12 }}>{t('startChatPrompt', 'Start a new chat to begin.')}</p>
          </div>
        </div>
        <div className="chat-sidebar-footer">
          <div style={{ padding: '8px 12px', borderRadius: 8, fontSize: 11, fontFamily: 'JetBrains Mono, monospace', display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', background: 'var(--chat-input-box-bg, #0d0d0d)', border: '1px solid var(--chat-sidebar-border, rgba(255, 255, 255, 0.08))', color: isOffline ? '#f87171' : '#94a3b8' }}>
            <span>{t('safetyEngineActive', 'Safety Engine: ACTIVE')}</span>
          </div>
        </div>
      </aside>
    </>
  );
};
