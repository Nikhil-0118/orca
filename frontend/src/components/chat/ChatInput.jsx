import React, { useState, useRef, useEffect } from 'react';
import { Mic, ArrowUp } from 'lucide-react';
import { useLanguage } from '../../i18n/LanguageContext';

export const ChatInput = ({ onSend, onVoiceClick, isVoiceActive = false, isLoading }) => {
  const { t } = useLanguage();
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSend(input);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e) => {
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
            placeholder={t('inputPlaceholder', 'Ask ORCA about ocean conditions, navigation safety, or satellite data...')}
            disabled={isLoading}
            rows={1}
            className="chat-input-textarea"
          />
          {onVoiceClick && (
            <button
              type="button"
              onClick={onVoiceClick}
              aria-label={t('voiceSearch', 'Voice Search')}
              title={t('voiceSearch', 'Voice Search')}
              className={`chat-input-btn chat-input-voice ${isVoiceActive ? 'active' : ''}`}
            >
              <Mic className="w-4 h-4" />
            </button>
          )}
          <button
            type="button"
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            aria-label={t('send', 'Send')}
            title={t('send', 'Send')}
            className="chat-input-btn chat-input-send"
          >
            <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
          </button>
        </div>
        <div className="chat-input-hint">
          {t('inputHint', 'ORCA multi-agent marine intelligence · Press Enter to send, Shift+Enter for new line')}
        </div>
      </div>
    </div>
  );
};

export default ChatInput;
