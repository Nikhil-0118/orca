import React from 'react';
import { Radio, ChevronRight } from 'lucide-react';
import { useLanguage } from '../../i18n/LanguageContext';
import { LanguageSwitcherButton } from '../common/LanguageSwitcherButton';
import { ThemeToggle } from '../common/ThemeToggle';

export const LandingNavbar = React.memo(({ onEnterApp }) => {
  const { t } = useLanguage();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-20 px-6 sm:px-12 flex items-center justify-between border-b border-slate-200/80 dark:border-slate-800/80 bg-white/80 dark:bg-navy-950/80 backdrop-blur-xl transition-all duration-250 shadow-xs">
      {/* Brand Identity */}
      <div
        className="flex items-center gap-3.5 group cursor-pointer"
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      >
        <img
          src="/orca-emblem.png"
          alt="ORCA Logo"
          className="w-10 h-10 object-contain drop-shadow-sm transition-transform duration-200 group-hover:scale-105"
        />
        <div>
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-lg tracking-wider text-slate-900 dark:text-white font-sans">ORCA</span>
            <span className="text-[10px] uppercase font-mono font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 dark:bg-cyan-950/60 dark:text-cyan-300 dark:border-cyan-800/60">
              ISRO / SIH 2026
            </span>
          </div>
          <span className="text-[11px] text-slate-600 dark:text-slate-400 font-mono tracking-tight hidden sm:inline">
            {t('appSub', 'Marine Ecosystem Reasoning & Agents')}
          </span>
        </div>
      </div>

      {/* Nav Actions */}
      <div className="flex items-center gap-2 sm:gap-3.5">
        <div className="hidden lg:flex items-center gap-2 text-xs font-mono text-slate-700 dark:text-slate-300 px-3.5 py-1.5 rounded-full bg-white/90 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 shadow-xs">
          <Radio className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 animate-pulse" />
          <span className="font-medium">{t('liveTelemetry', 'INCOIS • MOSDAC • NavIC Live')}</span>
        </div>

        {/* Multilingual Selector Button */}
        <LanguageSwitcherButton />

        {/* Theme Switcher Toggle (🌙 Dark / ☀ Light) */}
        <ThemeToggle />

        <button
          onClick={onEnterApp}
          className="group flex items-center gap-2 bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs sm:text-sm px-4 sm:px-5 py-2 sm:py-2.5 rounded-xl shadow-md shadow-blue-500/20 hover:shadow-blue-500/35 active:scale-95 transition-all duration-200 cursor-pointer"
        >
          <span>{t('launchPlatform', 'Launch Platform')}</span>
          <ChevronRight className="w-4 h-4 text-white transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
    </header>
  );
});
