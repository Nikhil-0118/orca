import React from 'react';
import { AgentActivityPanel } from './AgentActivityPanel';

/**
 * ReasoningStepViewer delegates to the expandable AgentActivityPanel.
 * Kept as a thin wrapper for backwards compatibility.
 */
export const ReasoningStepViewer = ({ steps }) => {
  return <AgentActivityPanel steps={steps} />;
};

export default ReasoningStepViewer;
