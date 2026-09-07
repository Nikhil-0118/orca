import React from 'react';
import { Anchor } from 'lucide-react';

export const LandingFooter: React.FC = () => {
  return (
    <footer className="relative z-10 border-t border-slate-800/80 bg-navy-950/90 backdrop-blur-md px-6 sm:px-12 py-10 text-xs text-slate-400">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-800/40 flex items-center justify-center">
            <Anchor className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <div className="font-bold text-slate-200">ORCA — Marine Intelligence</div>
            <div className="text-[11px] text-slate-500">Built for Smart India Hackathon 2026 • Under ISRO</div>
          </div>
        </div>

        <div className="flex items-center gap-6 text-slate-400 font-mono text-[11px]">
          <span className="hover:text-cyan-400 cursor-pointer">MOSDAC Data</span>
          <span className="hover:text-cyan-400 cursor-pointer">INCOIS ERDDAP</span>
          <span className="hover:text-cyan-400 cursor-pointer">NavIC DAT-SG</span>
        </div>

        <div className="text-[11px] font-mono text-slate-500 text-center sm:text-right">
          © 2026 ORCA Marine Initiative. High-seas safety first.
        </div>
      </div>
    </footer>
  );
};
