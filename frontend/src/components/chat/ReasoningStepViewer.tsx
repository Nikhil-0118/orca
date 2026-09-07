import React from 'react';
import { Cpu, ChevronRight } from 'lucide-react';
import { ReasoningStep } from '../../types/chat.types';

interface ReasoningStepViewerProps {
  steps: ReasoningStep[];
}

export const ReasoningStepViewer: React.FC<ReasoningStepViewerProps> = ({ steps }) => {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="my-2 p-3 rounded-xl bg-slate-950/80 border border-cyan-900/30 text-xs font-mono">
      <div className="flex items-center gap-2 mb-2 text-cyan-400 font-semibold">
        <Cpu className="w-3.5 h-3.5 animate-spin" />
        <span>Multi-Agent Reasoning Trace</span>
      </div>

      <div className="space-y-1.5">
        {steps.map((step, idx) => (
          <div key={idx} className="flex items-start gap-2 text-slate-300">
            <ChevronRight className="w-3 h-3 text-cyan-500 mt-0.5 shrink-0" />
            <div>
              <span className="text-cyan-300 font-bold uppercase mr-1">[{step.agent}]:</span>
              <span>{step.rationale}</span>
              {step.data_sources_queried.length > 0 && (
                <div className="text-[10px] text-slate-500 mt-0.5">
                  Sources: {step.data_sources_queried.join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
