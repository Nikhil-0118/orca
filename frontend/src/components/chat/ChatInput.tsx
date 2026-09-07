import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Mic, ArrowUp } from 'lucide-react';

interface ChatInputProps {
  onSend: (text: string) => void;
  onVoiceClick?: () => void;
  isVoiceActive?: boolean;
  isLoading: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  onVoiceClick,
  isVoiceActive = false,
  isLoading,
}) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput('');
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-area">
      <div className="chat-input-inner">
        <div className="chat-input-box">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask ORCA about ocean conditions, navigation safety, or satellite data..."
            disabled={isLoading}
            rows={1}
            className="chat-input-textarea"
          />

          {onVoiceClick && (
            <button
              type="button"
              onClick={onVoiceClick}
              aria-label="Voice input"
              title="Speak to ORCA"
              className={`chat-input-btn chat-input-voice ${isVoiceActive ? 'active' : ''}`}
            >
              <Mic className="w-4 h-4" />
            </button>
          )}

          <button
            type="button"
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            aria-label="Send message"
            className="chat-input-btn chat-input-send"
          >
            <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
          </button>
        </div>

        <div className="chat-input-hint">
          ORCA multi-agent marine intelligence · Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  );
};
