import React from 'react';
import { AgentActivityPanel } from './AgentActivityPanel';
import { ReasoningStep } from '../../types/chat.types';

interface ReasoningStepViewerProps {
  steps: ReasoningStep[];
}

/**
 * ReasoningStepViewer now delegates to the expandable AgentActivityPanel.
 * Kept as a thin wrapper for backwards compatibility.
 */
export const ReasoningStepViewer: React.FC<ReasoningStepViewerProps> = ({ steps }) => {
  return <AgentActivityPanel steps={steps} />;
};
