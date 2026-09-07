import React from 'react';
import { Wifi, WifiOff, Satellite } from 'lucide-react';

interface StatusIndicatorProps {
  isOnline: boolean;
  isSatelliteActive?: boolean;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({ isOnline, isSatelliteActive = true }) => {
  return (
    <div className="flex items-center gap-3 text-xs font-mono">
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900/60 border border-slate-800">
        {isOnline ? (
          <>
            <Wifi className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-emerald-400">4G/5G LIVE</span>
          </>
        ) : (
          <>
            <WifiOff className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-amber-400">SMS FALLBACK</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900/60 border border-slate-800">
        <Satellite className={`w-3.5 h-3.5 ${isSatelliteActive ? 'text-cyan-400' : 'text-slate-500'}`} />
        <span className={isSatelliteActive ? 'text-cyan-400' : 'text-slate-500'}>
          {isSatelliteActive ? 'DAT-SG READY' : 'DAT-SG STANDBY'}
        </span>
      </div>
    </div>
  );
};
