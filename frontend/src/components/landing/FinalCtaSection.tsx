import React from 'react';
import { Anchor, ArrowRight, Radio } from 'lucide-react';

interface FinalCtaSectionProps {
  onEnterApp: () => void;
}

export const FinalCtaSection: React.FC<FinalCtaSectionProps> = ({ onEnterApp }) => {
  return (
    <section className="relative min-h-[85vh] w-full flex flex-col justify-center items-center px-6 sm:px-12 py-24 text-center z-10 select-none">
      {/* Visual glowing emblem */}
      <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-cyan-400 to-blue-600 p-[1px] shadow-2xl shadow-cyan-500/30 mb-8 animate-pulse-slow">
        <div className="w-full h-full bg-navy-950 rounded-[23px] flex items-center justify-center">
          <Anchor className="w-8 h-8 text-cyan-400 stroke-[2.2]" />
        </div>
      </div>

      <div className="max-w-3xl space-y-6">
        <div className="inline-flex items-center gap-2 text-xs font-mono text-cyan-300 uppercase tracking-widest bg-cyan-950/40 px-3.5 py-1 rounded-full border border-cyan-800/40">
          <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
          <span>Continuous High-Seas Guardian</span>
        </div>

        <h2 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold text-slate-100 tracking-tight leading-tight font-sans">
          ORCA Doesn’t Wait <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-cyan-electric to-blue-500 text-glow-cyan">
            To Be Asked.
          </span>
        </h2>

        <p className="text-xl sm:text-2xl font-light text-slate-300 font-mono tracking-wide">
          Watch. Warn. Guide.
        </p>

        <p className="max-w-xl mx-auto text-sm sm:text-base text-slate-400 font-light">
          Empowering Indian coastal communities and maritime rescue operations with continuous satellite-driven artificial intelligence.
        </p>

        {/* Primary Enter Action */}
        <div className="pt-6">
          <button
            onClick={onEnterApp}
            className="group px-10 py-5 rounded-2xl bg-gradient-to-r from-cyan-500 via-cyan-electric to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-navy-950 font-black text-base uppercase tracking-wider shadow-2xl shadow-cyan-500/40 hover:shadow-cyan-500/60 active:scale-95 transition-all duration-200 cursor-pointer inline-flex items-center gap-3"
          >
            <span>Enter ORCA Platform</span>
            <ArrowRight className="w-5 h-5 text-navy-950 transition-transform group-hover:translate-x-1" />
          </button>
        </div>
      </div>
    </section>
  );
};
