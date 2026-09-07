import React from 'react';
import { Anchor, Radio, ChevronRight } from 'lucide-react';

interface LandingNavbarProps {
  onEnterApp: () => void;
}

export const LandingNavbar: React.FC<LandingNavbarProps> = ({ onEnterApp }) => {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-20 px-6 sm:px-12 flex items-center justify-between border-b border-slate-200/60 bg-white/65 backdrop-blur-xl transition-all duration-300 shadow-sm">
      {/* Brand Identity */}
      <div
        className="flex items-center gap-3.5 group cursor-pointer"
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      >
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 p-[1px] shadow-md shadow-blue-500/20 group-hover:shadow-blue-500/40 transition-shadow">
          <div className="w-full h-full bg-slate-900 rounded-[11px] flex items-center justify-center">
            <Anchor className="w-5 h-5 text-cyan-400 stroke-[2.2]" />
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-lg tracking-wider text-slate-900 font-sans">ORCA</span>
            <span className="text-[10px] uppercase font-mono font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
              ISRO / SIH 2026
            </span>
          </div>
          <span className="text-[11px] text-slate-600 font-mono tracking-tight hidden sm:inline">
            Marine Ecosystem Reasoning & Agents
          </span>
        </div>
      </div>

      {/* Nav Actions */}
      <div className="flex items-center gap-4 sm:gap-6">
        <div className="hidden md:flex items-center gap-2 text-xs font-mono text-slate-700 px-3.5 py-1.5 rounded-full bg-white/80 border border-slate-200 shadow-xs">
          <Radio className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
          <span className="font-medium">INCOIS • MOSDAC • NavIC Live</span>
        </div>

        <button
          onClick={onEnterApp}
          className="group flex items-center gap-2 bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs sm:text-sm px-5 py-2.5 rounded-xl shadow-md shadow-blue-500/20 hover:shadow-blue-500/35 active:scale-95 transition-all duration-200 cursor-pointer"
        >
          <span>Launch Platform</span>
          <ChevronRight className="w-4 h-4 text-white transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
    </header>
  );
};
