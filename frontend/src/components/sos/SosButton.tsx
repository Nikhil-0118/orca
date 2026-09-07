/**
 * Safety-Critical SOS Button.
 * Isolated component with minimal dependencies to ensure fault-tolerance.
 */
import React from 'react';
import { AlertOctagon } from 'lucide-react';

interface SosButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

export const SosButton: React.FC<SosButtonProps> = ({ onClick, disabled = false }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-red-600 via-red-700 to-rose-800 text-white font-extrabold text-lg flex items-center justify-center gap-3 shadow-2xl shadow-red-700/50 hover:brightness-110 active:scale-95 transition-all border border-red-400/40 cursor-pointer disabled:opacity-50"
    >
      <AlertOctagon className="w-6 h-6 animate-pulse" />
      <span>ONE-BUTTON SOS (COAST GUARD)</span>
    </button>
  );
};
