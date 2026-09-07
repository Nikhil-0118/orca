import React from 'react';
import { Anchor, Waves, Satellite, Navigation, ShieldCheck } from 'lucide-react';

interface ChatEmptyStateProps {
  onSuggestionClick: (text: string) => void;
}

const SUGGESTIONS = [
  {
    text: 'What are the current ocean conditions in this region?',
    icon: Waves,
  },
  {
    text: 'Analyze the marine conditions for this location.',
    icon: Navigation,
  },
  {
    text: 'Is this area safe for navigation?',
    icon: ShieldCheck,
  },
  {
    text: 'Find relevant satellite observations for this region.',
    icon: Satellite,
  },
];

export const ChatEmptyState: React.FC<ChatEmptyStateProps> = ({ onSuggestionClick }) => {
  return (
    <div className="chat-empty-state">
      <div className="chat-empty-icon">
        <Anchor className="w-7 h-7" />
      </div>

      <h2 className="chat-empty-title">Ask ORCA</h2>

      <p className="chat-empty-subtitle">
        ORCA reasons across oceanographic, satellite, and meteorological data
        using specialized agents to deliver marine intelligence and safety assessments.
      </p>

      <div className="chat-suggestions">
        {SUGGESTIONS.map((s, idx) => (
          <button
            key={idx}
            type="button"
            className="chat-suggestion-btn"
            onClick={() => onSuggestionClick(s.text)}
          >
            <span className="chat-suggestion-icon">
              <s.icon className="w-4 h-4" />
            </span>
            {s.text}
          </button>
        ))}
      </div>
    </div>
  );
};
