import React, { useState, useEffect } from 'react';
import { MessageSquare, Bot, CheckCircle2, Clock, Sparkles } from 'lucide-react';

export const ReasoningFlowSection: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 6);
    }, 2200);
    return () => clearInterval(timer);
  }, []);

  const steps = [
    { label: 'USER QUESTION', text: '“Is it safe to go fishing tomorrow morning near Chennai coast?”' },
    { label: 'ORCA ORCHESTRATION', text: 'Intent classified: Fishing safety & wave forecast assessment.' },
    { label: 'CONCURRENT AGENTS', text: 'Weather, PFZ, Ocean Temp & Boundary agents query MOSDAC & INCOIS simultaneously.' },
    { label: 'LIVE DATA VERIFICATION', text: 'Waves: 1.4m | Wind: 11 kts | PFZ: Active 18km SE | IMBL: Clear.' },
    { label: 'CROSS-CHECK & SYNTHESIS', text: 'Cross-verified morning wave window vs midday squall forecast.' },
    { label: 'FINAL REASONED ANSWER', text: 'Optimal fishing window identified with full safety clearance.' },
  ];

  return (
    <section className="relative min-h-screen w-full flex flex-col justify-center items-center px-6 sm:px-12 py-20 z-10">
      <div className="max-w-4xl text-center space-y-4 mb-16">
        <div className="inline-flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-widest bg-cyan-950/40 px-3 py-1 rounded-full border border-cyan-800/40 backdrop-blur-sm">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Layer 04 — Product in Action</span>
        </div>
        <h2 className="text-4xl sm:text-6xl font-extrabold text-slate-100 tracking-tight">
          Plain Language In. <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-emerald-400 to-blue-400">
            Explainable Decision Out.
          </span>
        </h2>
        <p className="text-sm sm:text-base text-slate-300 font-light max-w-2xl mx-auto">
          Watch how ORCA transforms a single natural question from a fisherman into verifiable ocean intelligence in seconds.
        </p>
      </div>

      {/* Interactive Chat Reasoning Pipeline Visualizer */}
      <div className="w-full max-w-4xl glass-panel p-6 sm:p-10 rounded-3xl relative overflow-hidden space-y-8 shadow-2xl">
        {/* User Question Box */}
        <div className="flex items-start gap-3.5 bg-slate-900/90 p-4 sm:p-5 rounded-2xl border border-cyan-900/40 shadow-lg">
          <div className="w-9 h-9 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0 border border-cyan-500/30">
            <MessageSquare className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider block font-bold">
              Fisherman Query (Tamil / Telugu / Hindi / English)
            </span>
            <p className="text-base sm:text-lg font-medium text-slate-100 mt-1">
              "Is it safe to go fishing tomorrow morning near Chennai coast?"
            </p>
          </div>
        </div>

        {/* Step Progression Ribbon */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {steps.map((s, idx) => {
            const isPassed = activeStep >= idx;
            const isCurrent = activeStep === idx;
            return (
              <div
                key={idx}
                onClick={() => setActiveStep(idx)}
                className={`p-2.5 rounded-xl border text-center transition-all duration-300 cursor-pointer ${
                  isCurrent
                    ? 'border-cyan-400 bg-cyan-950/60 shadow-md shadow-cyan-500/30 text-cyan-300 scale-105'
                    : isPassed
                    ? 'border-slate-700 bg-slate-900/70 text-slate-300'
                    : 'border-slate-800/60 bg-slate-950/40 text-slate-600'
                }`}
              >
                <div className="text-[9px] font-mono font-bold uppercase truncate">{s.label}</div>
                <div className="w-1.5 h-1.5 rounded-full mx-auto mt-1.5 bg-current"></div>
              </div>
            );
          })}
        </div>

        {/* Reasoning Status Trace */}
        <div className="p-4 rounded-2xl bg-slate-950/90 border border-slate-800 text-xs font-mono text-slate-300 space-y-1.5">
          <div className="text-cyan-400 font-bold flex items-center gap-2">
            <Bot className="w-4 h-4 text-cyan-400 animate-spin" />
            <span>Execution Trace: {steps[activeStep].label}</span>
          </div>
          <p className="text-slate-400 leading-relaxed pl-6">{steps[activeStep].text}</p>
        </div>

        {/* Synthesized Output Result (Progressive Reveal) */}
        <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950/50 via-slate-900 to-cyan-950/50 border border-emerald-500/40 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold font-mono">
              <CheckCircle2 className="w-4 h-4" />
              <span>ORCA REASONED VERDICT</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">Confidence: 98.6%</span>
          </div>

          <p className="text-base sm:text-lg font-medium text-slate-100 leading-snug">
            "Conditions are safe during the morning window. Wave height remains under 1.4m with calm swell. High-catch PFZ zone active 18.4 km South-East."
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3 text-xs font-mono">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950 text-emerald-300 border border-emerald-700/60 font-bold">
              <Clock className="w-4 h-4" />
              <span>Best Safe Window: 06:20 – 10:45 AM</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 border border-slate-800">
              Bearing: 135° SE | Depth: 45m
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 border border-slate-800">
              IMBL Clearance: 28.5 km (Safe)
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
