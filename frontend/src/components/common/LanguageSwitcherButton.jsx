import React from 'react';
import { useLanguage } from '../../i18n/LanguageContext';
import { Languages, ChevronDown } from 'lucide-react';

export function LanguageSwitcherButton({ className = '', variant = 'pill' }) {
  const { currentLangObj, openLanguageModal, t } = useLanguage();

  if (variant === 'compact') {
    return (
      <button
        onClick={openLanguageModal}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-800 hover:bg-slate-50 hover:border-blue-400 dark:border-cyan-500/30 dark:bg-[#0a0a0a] dark:hover:bg-cyan-500/10 dark:hover:border-cyan-400 dark:text-slate-200 transition text-xs font-medium shadow-2xs ${className}`}
        title={t('changeLang', 'Language')}
        aria-label={t('changeLang', 'Language')}
      >
        <Languages className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
        <span className="font-semibold text-cyan-700 dark:text-cyan-300">{currentLangObj?.nativeName || 'English'}</span>
      </button>
    );
  }

  return (
    <button
      onClick={openLanguageModal}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full border border-slate-300/90 bg-white/90 text-slate-800 hover:bg-blue-50/60 hover:border-blue-400 dark:border-cyan-500/30 dark:bg-[#0a0a0a] dark:hover:bg-cyan-500/15 dark:hover:border-cyan-400 dark:text-slate-200 transition-all text-xs font-medium shadow-xs hover:shadow-sm dark:hover:shadow-[0_0_12px_rgba(6,182,212,0.2)] ${className}`}
      title={t('changeLang', 'Language')}
      aria-label={t('changeLang', 'Language')}
    >
      <Languages className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 shrink-0" />
      <span className="font-semibold text-slate-900 dark:text-white tracking-wide">
        {currentLangObj?.nativeName || 'English'}
      </span>
      <ChevronDown className="w-3 h-3 text-cyan-600/80 dark:text-cyan-400/80 shrink-0" />
    </button>
  );
}
