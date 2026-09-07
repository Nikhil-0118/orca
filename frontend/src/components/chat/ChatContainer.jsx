import React, { useState } from 'react';
import { MessageSquare, RefreshCw, Radio } from 'lucide-react';
import { useChat } from '../../hooks/useChat';
import { useVoiceRecognition } from '../../hooks/useVoiceRecognition';
import { ChatInput } from './ChatInput';
import { ChatMessageList } from './ChatMessageList';
import { ChatEmptyState } from './ChatEmptyState';
import { OrcaVoiceOverlay } from '../orca/OrcaVoiceOverlay';
import { useLanguage } from '../../i18n/LanguageContext';

export const ChatContainer = ({
  currentLat = 13.0827,
  currentLon = 80.2707,
  locationContext,
  onRequestGps,
  isOffline = false,
  offlineSafetyEval,
  onDestinationSelect,
  onCompanionStateChange,
  showHeader = !locationContext,
}) => {
  const { t } = useLanguage();
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);

  const {
    messages,
    isLoading,
    companionState,
    setCompanionState,
    sendMessage,
    clearChat,
  } = useChat({
    onRouteGenerated: (dest) => {
      if (onDestinationSelect) {
        onDestinationSelect(dest);
      }
    },
    isOffline,
    offlineSafetyEval,
    locationContext,
  });

  // Keep parent companion state in sync if prop provided
  React.useEffect(() => {
    if (onCompanionStateChange) {
      onCompanionStateChange(companionState);
    }
  }, [companionState, onCompanionStateChange]);

  const {
    isListening,
    transcript,
    audioLevel,
    error: voiceError,
    startListening,
    stopListening,
    clearError: clearVoiceError,
  } = useVoiceRecognition({
    onResult: (text) => {
      sendMessage(text, currentLat, currentLon);
    },
  });

  const handleOpenVoice = () => {
    setIsVoiceModalOpen(true);
    setCompanionState('listening');
    startListening();
  };

  const handleCloseVoice = () => {
    stopListening();
    clearVoiceError();
    setIsVoiceModalOpen(false);
    setCompanionState('idle');
  };

  const handleVoiceSend = (spokenText) => {
    sendMessage(spokenText, currentLat, currentLon);
    handleCloseVoice();
  };

  const handleSuggestionClick = (text) => {
    sendMessage(text, currentLat, currentLon);
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="flex-1 min-h-0 flex flex-col relative overflow-hidden">
      {/* Chat Header (shown in standalone / dashboard view without external topbar) */}
      {showHeader && (
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-navy-950/80 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-cyan-950 border border-cyan-500/50 flex items-center justify-center">
              <MessageSquare className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-200">ORCA Marine Intelligence</h2>
              <p className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                <Radio className="w-2.5 h-2.5 text-emerald-400 animate-pulse" />
                <span>Multi-Agent Synthesizer Active</span>
              </p>
            </div>
          </div>

          {clearChat && (
            <button
              type="button"
              onClick={clearChat}
              aria-label="Clear chat"
              title="Reset conversation"
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800/80 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {/* Offline Status Warning Bar if disconnected */}
      {isOffline && (
        <div
          style={{
            maxWidth: 768,
            margin: '0 auto 12px',
            padding: '8px 16px',
            borderRadius: 10,
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#f87171',
            fontSize: 12,
            fontFamily: 'JetBrains Mono, monospace',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 8,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: '#ef4444',
                boxShadow: '0 0 6px #ef4444',
              }}
            />
            <span>
              <strong>{t('offlineModeActive', 'OFFLINE SAFETY MODE ACTIVE')}</strong> — {t('offlineDisclaimer', 'AI queries disabled · Local geofencing active')}
            </span>
          </div>
          {offlineSafetyEval && (
            <span style={{ fontSize: 11, color: '#fca5a5' }}>
              {offlineSafetyEval.distanceToBoundaryKm?.toFixed(1) || '0.0'} km · {offlineSafetyEval.state}
            </span>
          )}
        </div>
      )}

      {/* Empty state OR message list */}
      {!hasMessages && !isLoading ? (
        <ChatEmptyState onSuggestionClick={handleSuggestionClick} />
      ) : (
        <ChatMessageList
          messages={messages}
          isLoading={isLoading}
          locationContext={locationContext}
          onRequestGps={onRequestGps}
        />
      )}

      {/* Input Box */}
      <ChatInput
        onSend={(text) => sendMessage(text, currentLat, currentLon)}
        onVoiceClick={handleOpenVoice}
        isVoiceActive={isListening}
        isLoading={isLoading}
      />

      {/* Voice Recognition Modal / Overlay */}
      <OrcaVoiceOverlay
        isOpen={isVoiceModalOpen}
        isListening={isListening}
        transcript={transcript}
        audioLevel={audioLevel}
        error={voiceError}
        onClose={handleCloseVoice}
        onSend={handleVoiceSend}
        onRetry={() => {
          clearVoiceError();
          startListening();
        }}
      />
    </div>
  );
};

export default ChatContainer;
