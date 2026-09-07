import React, { useState } from 'react';
import { Bell, BellRing } from 'lucide-react';

export const PushNotificationToggle: React.FC = () => {
  const [enabled, setEnabled] = useState(false);

  const toggle = () => {
    if (!enabled && 'Notification' in window) {
      Notification.requestPermission().then((permission) => {
        if (permission === 'granted') setEnabled(true);
      });
    } else {
      setEnabled(!enabled);
    }
  };

  return (
    <div className="flex items-center justify-between p-2 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
      <div className="flex items-center gap-2 text-slate-300">
        {enabled ? <BellRing className="w-4 h-4 text-cyan-400" /> : <Bell className="w-4 h-4 text-slate-500" />}
        <span>Live Re-Alerts</span>
      </div>
      <button
        onClick={toggle}
        className={`px-2.5 py-1 rounded text-[11px] font-mono font-medium transition-colors ${
          enabled ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/50' : 'bg-slate-800 text-slate-400'
        }`}
      >
        {enabled ? 'ON' : 'OFF'}
      </button>
    </div>
  );
};
