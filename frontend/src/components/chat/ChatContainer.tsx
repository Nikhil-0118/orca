import React, { useState } from 'react';
import { useChat } from '../../hooks/useChat';
import { useVoiceRecognition } from '../../hooks/useVoiceRecognition';
import { ChatInput } from './ChatInput';
import { ChatMessageList } from './ChatMessageList';
import { ChatEmptyState } from './ChatEmptyState';
import { OrcaVoiceOverlay } from '../orca/OrcaVoiceOverlay';
import { DestinationPoint } from '../../types/map.types';
import { LocationContext, OrcaCompanionState } from '../../types/chat.types';
import { GeofenceEvaluation } from '../../services/offlineSafetyService';

interface ChatContainerProps {
  locationContext?: LocationContext;
  isOffline?: boolean;
  offlineSafetyEval?: GeofenceEvaluation;
  onDestinationSelect?: (destination: DestinationPoint) => void;
  onCompanionStateChange?: (state: OrcaCompanionState) => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  locationContext,
  isOffline = false,
  offlineSafetyEval,
  onDestinationSelect,
  onCompanionStateChange,
}) => {
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);

  const {
    messages,
    isLoading,
    companionState,
    setCompanionState,
    sendMessage,
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
      sendMessage(text);
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

  const handleVoiceSend = (spokenText: string) => {
    sendMessage(spokenText);
    handleCloseVoice();
  };

  const handleSuggestionClick = (text: string) => {
    sendMessage(text);
  };

  const hasMessages = messages.length > 0;

  return (
    <>
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
              <strong>OFFLINE SAFETY MODE ACTIVE</strong> — AI queries disabled · Local geofencing active
            </span>
          </div>
          {offlineSafetyEval && (
            <span style={{ fontSize: 11, color: '#fca5a5' }}>
              {offlineSafetyEval.distanceToBoundaryKm.toFixed(1)} km · {offlineSafetyEval.state}
            </span>
          )}
        </div>
      )}

      {/* Empty state OR message list */}
      {!hasMessages && !isLoading ? (
        <ChatEmptyState onSuggestionClick={handleSuggestionClick} />
      ) : (
        <ChatMessageList messages={messages} isLoading={isLoading} />
      )}

      {/* Input */}
      <ChatInput
        onSend={(text) => sendMessage(text)}
        onVoiceClick={handleOpenVoice}
        isVoiceActive={isListening}
        isLoading={isLoading}
      />

      {/* Voice Recognition Modal */}
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
    </>
  );
};
