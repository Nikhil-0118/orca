import React from 'react';
import { Anchor } from 'lucide-react';
import { useLanguage } from '../../i18n/LanguageContext';

export const LandingFooter = () => {
  const { t } = useLanguage();

  return (
    <footer className="relative z-10 border-t border-slate-200/80 dark:border-slate-800/80 bg-white/90 dark:bg-navy-950/90 backdrop-blur-md px-6 sm:px-12 py-10 text-xs text-slate-600 dark:text-slate-400">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-50 dark:bg-cyan-950 border border-cyan-200 dark:border-cyan-800/40 flex items-center justify-center">
            <Anchor className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div>
            <div className="font-bold text-slate-800 dark:text-slate-200">ORCA — {t('marineIntelligence', 'Marine Intelligence')}</div>
            <div className="text-[11px] text-slate-500">{t('appSub', 'Autonomous Marine Intelligence Hub')}</div>
          </div>
        </div>

        <div className="flex items-center gap-6 text-slate-600 dark:text-slate-400 font-mono text-[11px]">
          <span className="hover:text-cyan-600 dark:hover:text-cyan-400 cursor-pointer transition-colors">MOSDAC Data</span>
          <span className="hover:text-cyan-600 dark:hover:text-cyan-400 cursor-pointer transition-colors">INCOIS ERDDAP</span>
          <span className="hover:text-cyan-600 dark:hover:text-cyan-400 cursor-pointer transition-colors">NavIC DAT-SG</span>
        </div>

        <div className="text-[11px] font-mono text-slate-500 text-center sm:text-right">
          © 2026 ORCA Marine Initiative. {t('highSeasSafety', 'High-seas safety first.')}
        </div>
      </div>
    </footer>
  );
};
