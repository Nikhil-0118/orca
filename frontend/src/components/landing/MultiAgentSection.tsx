import React, { useState, useEffect } from 'react';
import { Wind, Fish, Thermometer, ShieldCheck, Cpu, CheckCircle2 } from 'lucide-react';

export const MultiAgentSection: React.FC = () => {
  const [activeAgentIndex, setActiveAgentIndex] = useState(0);

  const agents = [
    {
      id: 'weather',
      name: 'Weather & Storm Agent',
      icon: Wind,
      color: 'text-amber-400',
      border: 'border-amber-500/40',
      bgGlow: 'shadow-amber-500/20 bg-amber-950/30',
      role: 'Cyclone tracks, gale force winds, and wave threshold analytics',
      action: 'Computing 36h storm surge cone and wave height models',
    },
    {
      id: 'fishing',
      name: 'Fishing Zone Agent',
      icon: Fish,
      color: 'text-emerald-400',
      border: 'border-emerald-500/40',
      bgGlow: 'shadow-emerald-500/20 bg-emerald-950/30',
      role: 'Potential Fishing Zones (PFZ) and chlorophyll thermal front mapping',
      action: 'Correlating OCM chlorophyll gradient edges with pelagic schools',
    },
    {
      id: 'ocean_temp',
      name: 'Ocean Temperature Agent',
      icon: Thermometer,
      color: 'text-cyan-400',
      border: 'border-cyan-500/40',
      bgGlow: 'shadow-cyan-500/20 bg-cyan-950/30',
      role: 'Sea Surface Temperature (SST) trends & marine heatwave alerts',
      action: 'Detecting thermal anomalies across 0.25° MOSDAC raster grids',
    },
    {
      id: 'safety',
      name: 'Safety & Boundary Agent',
      icon: ShieldCheck,
      color: 'text-blue-400',
      border: 'border-blue-500/40',
      bgGlow: 'shadow-blue-500/20 bg-blue-950/30',
      role: 'IMBL proximity, EEZ limits, and prohibited maritime geofences',
      action: 'Calculating geodesic distance to international boundary line',
    },
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveAgentIndex((prev) => (prev + 1) % agents.length);
    }, 2800);
    return () => clearInterval(timer);
  }, [agents.length]);

  return (
    <section className="relative min-h-screen w-full flex flex-col justify-center items-center px-6 sm:px-12 py-20 z-10">
      <div className="max-w-4xl text-center space-y-4 mb-16">
        <div className="inline-flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-widest bg-cyan-950/40 px-3 py-1 rounded-full border border-cyan-800/40 backdrop-blur-sm">
          <Cpu className="w-3.5 h-3.5" />
          <span>Layer 03 — Multi-Agent Reasoning Architecture</span>
        </div>
        <h2 className="text-4xl sm:text-6xl font-extrabold text-slate-100 tracking-tight">
          Specialist AI Agents <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-emerald-400 to-blue-500">
            Collaborating in Parallel
          </span>
        </h2>
        <p className="text-sm sm:text-base text-slate-300 font-light max-w-2xl mx-auto">
          Instead of a generic black-box model, ORCA deploys four dedicated domain agents that independently verify conditions and cross-check safety parameters before synthesizing a single reasoned decision.
        </p>
      </div>

      {/* Interactive Agent Network Grid */}
      <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        {/* Left: Agent Cards (7 cols) */}
        <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {agents.map((agent, index) => {
            const isCurrent = activeAgentIndex === index;
            return (
              <div
                key={agent.id}
                onClick={() => setActiveAgentIndex(index)}
                className={`p-5 rounded-2xl border transition-all duration-300 cursor-pointer backdrop-blur-xl ${
                  isCurrent
                    ? `${agent.border} ${agent.bgGlow} shadow-xl scale-[1.02]`
                    : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className={`p-2.5 rounded-xl bg-slate-900 border border-slate-800 ${agent.color}`}>
                    <agent.icon className="w-5 h-5" />
                  </div>
                  {isCurrent && (
                    <span className="text-[10px] font-mono font-bold text-cyan-400 px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 animate-pulse">
                      ACTIVE REASONING
                    </span>
                  )}
                </div>

                <h3 className="font-bold text-slate-100 text-sm sm:text-base mb-1">{agent.name}</h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-3">{agent.role}</p>

                <div className="text-[11px] font-mono text-slate-300 bg-slate-900/90 p-2.5 rounded-xl border border-slate-800/80">
                  <span className="text-cyan-400 block text-[10px] font-semibold mb-0.5">CURRENT TASK:</span>
                  <span className="leading-tight block">{agent.action}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: Master Orchestrator Synthesizer (5 cols) */}
        <div className="lg:col-span-5 h-full flex flex-col justify-between p-8 rounded-3xl glass-panel relative overflow-hidden">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-400 to-blue-600 p-[1px]">
                <div className="w-full h-full bg-navy-950 rounded-[15px] flex items-center justify-center">
                  <Cpu className="w-6 h-6 text-cyan-400" />
                </div>
              </div>
              <div>
                <h4 className="text-lg font-bold text-slate-100">Master Orchestrator</h4>
                <p className="text-xs text-slate-400 font-mono">Consensus & Reasoning Engine</p>
              </div>
            </div>

            <div className="space-y-2 pt-2 text-xs font-mono">
              <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-slate-300 space-y-1.5">
                <div className="text-cyan-400 font-bold flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Cross-Agent Verification Matrix</span>
                </div>
                <div className="text-slate-400 text-[11px]">
                  • Weather & Storm: Wave height safe (&lt;2.0m)<br />
                  • Fishing Zone: PFZ active bearing 135°<br />
                  • Ocean Temp: No thermal heatwave<br />
                  • Safety Boundary: 28.5 km IMBL clearance
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800/80">
            <div className="text-[11px] font-mono text-emerald-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              <span>SYNTHESIS: Unanimous Safety Consensus (98.4%)</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
