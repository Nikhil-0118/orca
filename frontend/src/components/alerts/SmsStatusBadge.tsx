import React from 'react';
import { MessageSquareText } from 'lucide-react';

interface SmsStatusBadgeProps {
  isActive: boolean;
}

export const SmsStatusBadge: React.FC<SmsStatusBadgeProps> = ({ isActive }) => {
  return (
    <div className={`p-2.5 rounded-xl border text-xs ${
      isActive
        ? 'bg-amber-950/50 border-amber-600/60 text-amber-300'
        : 'bg-slate-900/40 border-slate-800 text-slate-400'
    }`}>
      <div className="flex items-center gap-2 font-semibold">
        <MessageSquareText className="w-4 h-4 text-amber-400" />
        <span>SMS Fallback Service</span>
      </div>
      <p className="text-[10px] mt-1 text-slate-300">
        {isActive
          ? 'Weak signal detected. Critical alerts transmitting via 160-char SMS.'
          : 'Ready on Standby (Auto-activates when 4G/5G drops below 1-bar).'}
      </p>
    </div>
  );
};
