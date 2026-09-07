import React from 'react';
import { ShieldAlert, Radio, RefreshCw } from 'lucide-react';
import { useAlerts } from '../../hooks/useAlerts';
import { PushNotificationToggle } from './PushNotificationToggle';
import { SmsStatusBadge } from './SmsStatusBadge';

export const AlertFeed: React.FC = () => {
  const { alerts, isSmsFallbackActive, loading, refetch } = useAlerts();

  return (
    <div className="h-full flex flex-col p-3 space-y-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-slate-200">Alert Center</h2>
        </div>
        <button
          onClick={() => refetch()}
          className="text-slate-500 hover:text-slate-300 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <PushNotificationToggle />
      <SmsStatusBadge isActive={isSmsFallbackActive} />

      {/* Alert Feed List */}
      <div className="flex-1 overflow-y-auto space-y-2.5">
        {alerts.length === 0 ? (
          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80 text-center text-xs text-slate-500 font-mono">
            <Radio className="w-5 h-5 mx-auto mb-2 text-emerald-500/60 animate-pulse" />
            No active emergency alerts in this maritime sector. Conditions nominal.
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className="p-3 rounded-xl bg-red-950/40 border border-red-800/60 text-xs text-slate-200 space-y-1 shadow-md"
            >
              <div className="flex items-center justify-between text-[11px] font-bold text-red-400">
                <span>{alert.severity}</span>
                <span className="font-mono text-slate-500">
                  {new Date(alert.issued_at).toLocaleTimeString()}
                </span>
              </div>
              <h4 className="font-semibold text-slate-100">{alert.title}</h4>
              <p className="text-slate-400 leading-snug">{alert.description}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
