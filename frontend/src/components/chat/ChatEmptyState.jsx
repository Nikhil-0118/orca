import React from 'react';
import { Waves, Satellite, Navigation, ShieldCheck, Anchor } from 'lucide-react';
import { useLanguage } from '../../i18n/LanguageContext';

export const ChatEmptyState = ({ onSuggestionClick }) => {
  const { t } = useLanguage();

  const suggestions = [
    { key: 'sugg1', fallback: 'What are the current ocean conditions in this region?', icon: Waves },
    { key: 'suggFishing', fallback: 'Find high-yield fishing spots and navigation routes.', icon: Anchor },
    { key: 'sugg3', fallback: 'Is this area safe for navigation?', icon: ShieldCheck },
    { key: 'sugg4', fallback: 'Find relevant satellite observations for this region.', icon: Satellite },
  ];

  return (
    <div className="chat-empty-state">
      <div className="chat-empty-icon">
        <img src="/orca-emblem.png" alt="ORCA Logo" style={{ width: 36, height: 36, objectFit: 'contain' }} />
      </div>
      <h2 className="chat-empty-title">{t('askOrcaTitle', 'Ask ORCA')}</h2>
      <p className="chat-empty-subtitle">
        {t('askOrcaSubtitle', 'ORCA reasons across oceanographic, satellite, and meteorological data using specialized agents to deliver marine intelligence and safety assessments.')}
      </p>
      <div className="chat-suggestions">
        {suggestions.map((s, idx) => {
          const text = t(s.key, s.fallback);
          return (
            <button key={idx} type="button" className="chat-suggestion-btn" onClick={() => onSuggestionClick(text)}>
              <span className="chat-suggestion-icon"><s.icon className="w-4 h-4" /></span>
              {text}
            </button>
          );
        })}
      </div>
    </div>
  );
};
