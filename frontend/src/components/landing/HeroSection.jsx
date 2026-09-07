import React from 'react';
import { Sparkles, Compass, ArrowDown, Radio, ShieldCheck } from 'lucide-react';
import { useLanguage } from '../../i18n/LanguageContext';

const HeroSectionComponent = ({
  onExplore,
  onEnterApp,
  scrollProgress = 0,
}) => {
  const { t } = useLanguage();

  // Smoothly fade out and translate upward as the user scrolls into the journey
  const fadeProgress = Math.min(1, Math.max(0, scrollProgress * 5.0));
  const opacity = Math.max(0, 1 - fadeProgress);
  const translateY = -fadeProgress * 35;

  return (
    <section className="relative min-h-screen w-full flex flex-col justify-start px-6 sm:px-10 lg:px-16 xl:px-20 pt-28 sm:pt-32 lg:pt-36 z-10 select-none pointer-events-none">
      {/* ── Two-Sided Editorial Layout Header (Left Text | Open Center Animation Zone | Right Telemetry & ORCA) ── */}
      <div
        className="w-full flex flex-col lg:flex-row justify-between items-start gap-8"
        style={{
          opacity,
          visibility: opacity > 0.001 ? 'visible' : 'hidden',
          transform: `translate3d(0, ${translateY}px, 0)`,
          willChange: 'transform, opacity',
        }}
      >
        {/* ── LEFT SIDE (Width: 26–30%, Left: 5–8%) ── */}
        <div className="w-full lg:w-[30%] max-w-md flex flex-col items-start text-left space-y-3.5 pointer-events-auto">
          {/* Ambient Satellite Tag */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/80 dark:bg-slate-900/80 border border-slate-300/80 dark:border-slate-700/80 text-slate-800 dark:text-slate-200 text-[11px] font-mono shadow-xs backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
            <span className="text-slate-900 dark:text-white font-medium">{t('marineIntelligence', 'Marine Intelligence')}</span>
          </div>

          {/* Main Heading */}
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-slate-950 via-slate-900 to-slate-800 dark:from-white dark:via-slate-100 dark:to-slate-200 leading-[1.08] font-sans drop-shadow-xs">
            {t('oceanChanges', 'The Ocean Changes.')} <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-700 dark:from-cyan-400 dark:via-cyan-electric dark:to-blue-400">
              {t('orcaWatches', 'ORCA Watches.')}
            </span>
          </h1>

          {/* Concise Supporting Description */}
          <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-normal leading-relaxed">
            {t('heroSubtitleEditorial', 'Live ocean data, collaborative AI reasoning, and proactive safety guidance for fishermen, disaster agencies, and maritime researchers.')}
          </p>

          {/* Primary CTA Button & Left-Aligned Scroll Cue */}
          <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <button
              onClick={onEnterApp || onExplore}
              className="group px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs uppercase tracking-wider shadow-md shadow-blue-500/20 hover:shadow-blue-500/35 active:scale-95 transition-all duration-200 cursor-pointer flex items-center gap-2"
            >
              <Compass className="w-4 h-4 text-white stroke-[2.2]" />
              <span>{t('launchPlatform', 'Launch Platform')}</span>
            </button>

            {/* Subtle Scroll Cue in Left Column */}
            <div
              className="flex items-center gap-1.5 text-slate-700 hover:text-cyan-700 dark:text-slate-300 dark:hover:text-cyan-400 transition-colors cursor-pointer py-1.5 px-2"
              onClick={onExplore}
            >
              <span className="text-[10px] font-mono uppercase tracking-widest text-slate-800 dark:text-slate-200 font-bold">{t('scrollToDive', 'Scroll to Dive')}</span>
              <ArrowDown className="w-3.5 h-3.5 animate-bounce text-cyan-600 dark:text-cyan-400" />
            </div>
          </div>
        </div>

        {/* ── CENTER PROTECTED ANIMATION ZONE (Width: 35–40%) ── */}
        <div className="hidden lg:block lg:w-[35%] pointer-events-none" />

        {/* ── RIGHT SIDE (Width: 25–30%, Right: 5–8%): Telemetry & Animated ORCA Companion ── */}
        <div className="w-full lg:w-[30%] max-w-sm flex flex-col items-start lg:items-end text-left lg:text-right space-y-4 pointer-events-auto">
          {/* Header Label */}
          <div className="inline-flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-slate-800 dark:text-slate-200 font-bold bg-white/80 dark:bg-slate-900/80 px-3 py-1 rounded-full border border-slate-200/90 dark:border-slate-700/80 shadow-2xs backdrop-blur-sm">
            <Radio className="w-3 h-3 text-cyan-600 dark:text-cyan-400 animate-pulse" />
            <span>{t('telemetryFeeds', 'Telemetry Feeds')}</span>
          </div>

          {/* Telemetry Status Card */}
          <div className="w-full p-3.5 rounded-2xl bg-white/85 dark:bg-slate-900/85 border border-slate-200/90 dark:border-slate-800 shadow-xs backdrop-blur-md space-y-2 text-left">
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-600 dark:text-slate-400 font-medium">{t('sstRadiometry', 'SST Radiometry')}</span>
              <span className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                28.4°C (MOSDAC)
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-600 dark:text-slate-400 font-medium">{t('pfzDensity', 'PFZ Density')}</span>
              <span className="font-bold text-cyan-700 dark:text-cyan-400">{t('activeIncois', 'Active (INCOIS)')}</span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-600 dark:text-slate-400 font-medium">{t('imblClearance', 'IMBL Clearance')}</span>
              <span className="font-bold text-slate-900 dark:text-white">28.5 km</span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono pt-1 border-t border-slate-200/60 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400 font-medium">{t('navicSatellite', 'NavIC Satellite')}</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-500" />
                {t('lockedStatus', 'Locked')}
              </span>
            </div>
          </div>

          {/* ── Living Ocean Pod Status Indicator ── */}
          <div className="w-full pt-1 flex flex-col items-start lg:items-end justify-center">
            <button
              onClick={onEnterApp}
              className="group inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white/85 dark:bg-slate-900/85 border border-slate-200/90 dark:border-slate-800 hover:border-cyan-400 text-slate-800 dark:text-slate-200 hover:text-cyan-700 dark:hover:text-cyan-300 text-[11px] font-mono shadow-xs backdrop-blur-md transition-all cursor-pointer"
            >
              <span className="w-2 h-2 rounded-full bg-cyan-500 animate-ping"></span>
              <span className="font-semibold tracking-wide">{t('orcaPodLive', 'ORCA POD TELEMETRY // LIVE')}</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export const HeroSection = React.memo(HeroSectionComponent);
