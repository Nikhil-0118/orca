import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

export const ThemeToggle = ({ className = '', variant = 'pill' }) => {
  const { theme, toggleTheme, isDark } = useTheme();

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleTheme();
    }
  };

  if (variant === 'compact') {
    return (
      <button
        type="button"
        onClick={toggleTheme}
        onKeyDown={handleKeyDown}
        className={`flex items-center justify-center w-8 h-8 rounded-lg border transition-all duration-200 cursor-pointer ${
          isDark
            ? 'border-slate-800 bg-[#0d0d0d] text-cyan-400 hover:border-cyan-400 hover:bg-cyan-500/10 hover:text-cyan-300'
            : 'border-slate-300 bg-white text-amber-500 hover:border-amber-400 hover:bg-amber-50/80 hover:text-amber-600 shadow-xs'
        } ${className}`}
        aria-label={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        aria-pressed={isDark}
      >
        {isDark ? (
          <Moon className="w-4 h-4 transition-transform duration-200 hover:rotate-12" />
        ) : (
          <Sun className="w-4 h-4 transition-transform duration-200 hover:rotate-45" />
        )}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      onKeyDown={handleKeyDown}
      className={`group flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold font-mono tracking-wide transition-all duration-200 cursor-pointer shadow-xs active:scale-95 ${
        isDark
          ? 'border-cyan-500/30 bg-[#0a0a0a] text-slate-200 hover:border-cyan-400 hover:bg-cyan-500/15 hover:shadow-[0_0_12px_rgba(6,182,212,0.25)]'
          : 'border-slate-300/80 bg-white/90 text-slate-800 hover:border-amber-400 hover:bg-amber-50/80 hover:shadow-sm'
      } ${className}`}
      aria-label={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      aria-pressed={isDark}
    >
      <div className="relative flex items-center justify-center">
        {isDark ? (
          <Moon className="w-3.5 h-3.5 text-cyan-400 transition-transform duration-300 group-hover:rotate-12" />
        ) : (
          <Sun className="w-3.5 h-3.5 text-amber-500 transition-transform duration-300 group-hover:rotate-45" />
        )}
      </div>
      <span className="text-[11px] font-medium hidden xs:inline">
        {isDark ? 'Dark' : 'Light'}
      </span>
    </button>
  );
};

export default ThemeToggle;
