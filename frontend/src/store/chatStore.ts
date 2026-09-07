import { ChatMessage, ReasoningStep } from '../types/chat.types';

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  activeReasoningSteps: ReasoningStep[];
  selectedLanguage: string;
}

// Clean initial state — no fake welcome message
export const initialChatState: ChatState = {
  messages: [],
  isLoading: false,
  activeReasoningSteps: [],
  selectedLanguage: 'en',
};
