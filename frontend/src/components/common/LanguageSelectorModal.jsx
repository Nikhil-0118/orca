import React, { useState, useMemo } from 'react';
import { useLanguage } from '../../i18n/LanguageContext';
import { Globe, Search, Check, X, Compass, Languages } from 'lucide-react';

export function LanguageSelectorModal() {
  const {
    currentLanguage,
    currentLangObj,
    languages,
    setLanguage,
    t,
    isLanguageModalOpen,
    closeLanguageModal,
  } = useLanguage();

  const [searchQuery, setSearchQuery] = useState('');
  const [tempSelectedCode, setTempSelectedCode] = useState(currentLanguage);

  // Sync temp selection when modal opens or language changes
  React.useEffect(() => {
    setTempSelectedCode(currentLanguage);
  }, [currentLanguage, isLanguageModalOpen]);

  const filteredLanguages = useMemo(() => {
    if (!searchQuery.trim()) return languages;
    const q = searchQuery.toLowerCase();
    return languages.filter(
      (lang) =>
        lang.name.toLowerCase().includes(q) ||
        lang.nativeName.toLowerCase().includes(q) ||
        lang.region.toLowerCase().includes(q)
    );
  }, [languages, searchQuery]);

  if (!isLanguageModalOpen) return null;

  const tempLang = languages.find((l) => l.code === tempSelectedCode) || currentLangObj;

  const handleSelectLanguage = (code) => {
    setTempSelectedCode(code);
    setLanguage(code);
  };

  const handleConfirm = () => {
    setLanguage(tempSelectedCode);
    closeLanguageModal();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 dark:bg-black/80 backdrop-blur-md animate-fade-in">
      <div
        className="relative w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl bg-white dark:bg-[#0a0a0a]/95 border border-slate-200 dark:border-cyan-500/30 shadow-2xl dark:shadow-[0_0_50px_rgba(6,182,212,0.15)] text-slate-900 dark:text-slate-100 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="flex items-start justify-between p-6 border-b border-slate-200 dark:border-cyan-900/40 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 dark:from-[#080808] dark:to-[#050505]">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-cyan-100 dark:bg-cyan-500/10 border border-cyan-300 dark:border-cyan-500/30 text-cyan-700 dark:text-cyan-400">
              <Languages className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-wide">
                  {t('welcomeTitle', 'Choose Your Language / अपनी भाषा चुनें')}
                </h2>
                <span className="px-2 py-0.5 text-[10px] font-mono tracking-widest bg-cyan-100 text-cyan-800 border border-cyan-300 dark:bg-cyan-500/20 dark:text-cyan-300 rounded dark:border-cyan-500/30">
                  INDIA 23
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 max-w-lg">
                {t(
                  'welcomeSubtitle',
                  'Select your preferred Indian language for high-seas marine intelligence, weather updates, and safety navigation.'
                )}
              </p>
            </div>
          </div>

          <button
            onClick={closeLanguageModal}
            className="p-2 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-200/60 dark:text-slate-400 dark:hover:text-white dark:hover:bg-white/10 transition-colors"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Input */}
        <div className="px-6 pt-4 pb-2">
          <div className="relative">
            <Search className="w-4 h-4 text-cyan-600 dark:text-cyan-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('searchLangPlaceholder', 'Search language / भाषा खोजें...')}
              className="w-full bg-slate-100 dark:bg-[#050505] border border-slate-300 dark:border-cyan-900/60 rounded-xl pl-9 pr-4 py-2.5 text-sm text-slate-900 dark:text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition"
              autoFocus
            />
          </div>
        </div>

        {/* Language Grid */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 custom-scrollbar">
          {filteredLanguages.map((lang) => {
            const isSelected = tempSelectedCode === lang.code;
            return (
              <button
                key={lang.code}
                onClick={() => handleSelectLanguage(lang.code)}
                className={`flex items-center justify-between p-3 rounded-xl border text-left transition-all duration-200 group ${
                  isSelected
                    ? 'bg-cyan-50 border-cyan-500 text-cyan-950 dark:bg-cyan-500/15 dark:border-cyan-400 dark:text-white shadow-xs dark:shadow-[0_0_15px_rgba(6,182,212,0.2)] ring-1 ring-cyan-500/40'
                    : 'bg-slate-50/80 border-slate-200 text-slate-700 hover:bg-blue-50/60 hover:border-blue-300 hover:text-slate-900 dark:bg-[#111111]/60 dark:border-neutral-800 dark:text-slate-300 dark:hover:bg-[#1a1a1a] dark:hover:border-neutral-700 dark:hover:text-white'
                }`}
              >
                <div className="flex flex-col min-w-0 pr-2">
                  <span
                    className={`text-base font-semibold leading-snug tracking-wide ${
                      isSelected ? 'text-cyan-700 dark:text-cyan-300' : 'text-slate-900 dark:text-slate-100 group-hover:text-cyan-700 dark:group-hover:text-cyan-200'
                    }`}
                  >
                    {lang.nativeName}
                  </span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                      {lang.name}
                    </span>
                    {lang.dir === 'rtl' && (
                      <span className="text-[9px] uppercase px-1 py-0.2 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400 rounded font-mono">
                        RTL
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-400 dark:text-slate-500 truncate mt-0.5">
                    {lang.region}
                  </span>
                </div>

                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 border transition-colors ${
                    isSelected
                      ? 'bg-cyan-500 border-cyan-400 text-white dark:text-black'
                      : 'border-slate-300 dark:border-slate-700 group-hover:border-slate-400 dark:group-hover:border-slate-500 text-transparent'
                  }`}
                >
                  <Check className="w-3.5 h-3.5 stroke-[3]" />
                </div>
              </button>
            );
          })}

          {filteredLanguages.length === 0 && (
            <div className="col-span-full py-12 text-center text-slate-500 dark:text-slate-400">
              <Compass className="w-8 h-8 text-cyan-600/40 dark:text-cyan-500/40 mx-auto mb-2" />
              <p className="text-sm">No matching Indian language found.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-slate-200 dark:border-cyan-900/40 bg-slate-50 dark:bg-[#080808] flex items-center justify-between">
          <div className="text-xs text-slate-600 dark:text-slate-400 flex items-center gap-2">
            <Globe className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
            <span>
              Active: <strong className="text-cyan-700 dark:text-cyan-300">{tempLang.nativeName}</strong> ({tempLang.name})
            </span>
          </div>

          <button
            onClick={handleConfirm}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm shadow-md shadow-blue-500/25 transition transform active:scale-95 flex items-center gap-2"
          >
            <span>{t('continueBtn', 'Continue in')} {tempLang.nativeName}</span>
            <span className="text-xs">→</span>
          </button>
        </div>
      </div>
    </div>
  );
}
