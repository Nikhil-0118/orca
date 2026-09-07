import React from 'react';
import { Radio, ShieldAlert } from 'lucide-react';

export const Header = ({ onSosClick, onBackToLanding }) => {
  return (
    <header className="h-16 border-b border-cyan-950/60 bg-navy-950/80 backdrop-blur-md px-6 flex items-center justify-between z-30">
      <div
        className="flex items-center gap-3 cursor-pointer group"
        onClick={onBackToLanding}
        title="Return to Landing Page"
      >
        <img
          src="/orca-emblem.png"
          alt="ORCA Logo"
          className="w-10 h-10 object-contain drop-shadow-[0_0_8px_rgba(56,189,248,0.4)] transition-transform duration-200 group-hover:scale-105"
        />
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-lg tracking-wider text-slate-100 group-hover:text-cyan-300 transition-colors">ORCA</h1>
          </div>
          <p className="text-xs text-slate-400">Multi-Agent Marine Intelligence & Safety Hub</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Navigation to Landing Page */}
        {onBackToLanding && (
          <button
            onClick={onBackToLanding}
            className="text-xs font-mono text-slate-400 hover:text-cyan-300 px-3 py-1.5 rounded-lg border border-slate-800 hover:border-cyan-800/60 transition-colors"
          >
            ← Overview
          </button>
        )}

        {/* Signal & NavIC Telemetry Status */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-navy-900/80 border border-slate-800 text-xs text-slate-300">
          <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
          <span>NavIC: Active</span>
        </div>

        {/* SOS Emergency Trigger Button */}
        <button
          onClick={onSosClick}
          className="flex items-center gap-2 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-semibold text-sm px-4 py-2 rounded-xl shadow-lg shadow-red-600/30 active:scale-95 transition-all duration-150 border border-red-400/30 cursor-pointer"
        >
          <ShieldAlert className="w-4 h-4 animate-bounce" />
          <span>EMERGENCY SOS</span>
        </button>
      </div>
    </header>
  );
};
