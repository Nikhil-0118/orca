import React from 'react';
import { Sparkles, Compass, ArrowDown, Radio, ShieldCheck } from 'lucide-react';
import { OrcaCompanion } from '../orca/OrcaCompanion';

interface HeroSectionProps {
  onExplore: () => void;
  onEnterApp?: () => void;
  scrollProgress?: number;
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onExplore,
  onEnterApp,
  scrollProgress = 0,
}) => {
  // Smoothly fade out and translate upward as the user scrolls into the journey
  const fadeProgress = Math.min(1, Math.max(0, scrollProgress * 5.0));
  const opacity = Math.max(0, 1 - fadeProgress);
  const translateY = -fadeProgress * 35;

  return (
    <section className="relative min-h-screen w-full flex flex-col justify-start px-6 sm:px-10 lg:px-16 xl:px-20 pt-28 sm:pt-32 lg:pt-36 z-10 select-none pointer-events-none">
      {/* ── Two-Sided Editorial Layout Header (Left Text | Open Center Animation Zone | Right Telemetry & ORCA) ── */}
      <div
        className="w-full flex flex-col lg:flex-row justify-between items-start gap-8 transition-all duration-75"
        style={{
          opacity,
          transform: `translate3d(0, ${translateY}px, 0)`,
        }}
      >
        {/* ── LEFT SIDE (Width: 26–30%, Left: 5–8%) ── */}
        <div className="w-full lg:w-[30%] max-w-md flex flex-col items-start text-left space-y-3.5 pointer-events-auto">
          {/* Ambient Satellite Tag */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/80 border border-slate-300/80 text-slate-800 text-[11px] font-mono shadow-xs backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-cyan-600" />
            <span className="font-semibold">ISRO SIH 2026</span>
            <span className="w-1 h-1 rounded-full bg-cyan-600"></span>
            <span className="text-slate-600 font-medium">Marine Intelligence</span>
          </div>

          {/* Main Heading */}
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-slate-950 via-slate-900 to-slate-800 leading-[1.08] font-sans drop-shadow-xs">
            The Ocean Changes. <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-700">
              ORCA Watches.
            </span>
          </h1>

          {/* Concise Supporting Description */}
          <p className="text-xs sm:text-sm text-slate-600 font-normal leading-relaxed">
            Live ocean data, collaborative AI reasoning, and proactive safety guidance for fishermen, disaster agencies, and maritime researchers.
          </p>

          {/* Primary CTA Button & Left-Aligned Scroll Cue */}
          <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <button
              onClick={onEnterApp || onExplore}
              className="group px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs uppercase tracking-wider shadow-md shadow-blue-500/20 hover:shadow-blue-500/35 active:scale-95 transition-all duration-200 cursor-pointer flex items-center gap-2"
            >
              <Compass className="w-4 h-4 text-white stroke-[2.2]" />
              <span>Launch Platform</span>
            </button>

            {/* Subtle Scroll Cue in Left Column */}
            <div
              className="flex items-center gap-1.5 text-slate-500 hover:text-cyan-700 transition-colors cursor-pointer py-1.5 px-2"
              onClick={onExplore}
            >
              <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 font-bold">Scroll to Dive</span>
              <ArrowDown className="w-3.5 h-3.5 animate-bounce text-cyan-600" />
            </div>
          </div>
        </div>

        {/* ── CENTER PROTECTED ANIMATION ZONE (Width: 35–40%) ── */}
        <div className="hidden lg:block lg:w-[35%] pointer-events-none" />

        {/* ── RIGHT SIDE (Width: 25–30%, Right: 5–8%): Telemetry & Animated ORCA Companion ── */}
        <div className="w-full lg:w-[30%] max-w-sm flex flex-col items-start lg:items-end text-left lg:text-right space-y-4 pointer-events-auto">
          {/* Header Label */}
          <div className="inline-flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-slate-500 font-bold bg-white/70 px-3 py-1 rounded-full border border-slate-200/80 shadow-2xs backdrop-blur-sm">
            <Radio className="w-3 h-3 text-cyan-600 animate-pulse" />
            <span>Telemetry Feeds</span>
          </div>

          {/* Telemetry Status Card */}
          <div className="w-full p-3.5 rounded-2xl bg-white/75 border border-slate-200/80 shadow-xs backdrop-blur-md space-y-2 text-left">
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-500">SST Radiometry</span>
              <span className="font-bold text-slate-800 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                28.4°C (MOSDAC)
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-500">PFZ Density</span>
              <span className="font-bold text-cyan-700">Active (INCOIS)</span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-500">IMBL Clearance</span>
              <span className="font-bold text-slate-800">28.5 km</span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono pt-1 border-t border-slate-200/60">
              <span className="text-slate-500">NavIC Satellite</span>
              <span className="font-bold text-emerald-600 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-500" />
                Locked
              </span>
            </div>
          </div>

          {/* ── Living ORCA Companion on the Right Ocean Hero ── */}
          <div className="w-full pt-2 flex flex-col items-center lg:items-end justify-center">
            <OrcaCompanion
              variant="hero"
              onClick={onEnterApp}
              className="hover:scale-105 transition-transform"
            />
          </div>
        </div>
      </div>
    </section>
  );
};

