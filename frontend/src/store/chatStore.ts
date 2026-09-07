import { ChatMessage, ReasoningStep } from '../types/chat.types';

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  activeReasoningSteps: ReasoningStep[];
  selectedLanguage: string;
}

// Initial state placeholder
export const initialChatState: ChatState = {
  messages: [
    {
      id: 'welcome-msg',
      role: 'assistant',
      content: 'Namaste. I am ORCA, your marine intelligence assistant. Ask me about weather, potential fishing zones (PFZ), wave heights, or safe navigation windows.',
      timestamp: new Date().toISOString(),
    },
  ],
  isLoading: false,
  activeReasoningSteps: [],
  selectedLanguage: 'en',
};
