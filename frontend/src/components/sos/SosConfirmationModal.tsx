import React, { useState, useEffect } from 'react';
import { AlertTriangle, Radio, X } from 'lucide-react';
import { DistressNature, SOSTriggerRequest } from '../../types/sos.types';
import { useSos } from '../../hooks/useSos';

interface SosConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  lat: number;
  lon: number;
}

export const SosConfirmationModal: React.FC<SosConfirmationModalProps> = ({
  isOpen,
  onClose,
  lat,
  lon,
}) => {
  const [countdown, setCountdown] = useState(5);
  const [nature, setNature] = useState<DistressNature>('UNKNOWN');
  const { triggerSos, isTriggering, dispatchResult } = useSos();

  useEffect(() => {
    if (!isOpen) {
      setCountdown(5);
      return;
    }

    if (countdown > 0 && !dispatchResult) {
      const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
      return () => clearTimeout(timer);
    } else if (countdown === 0 && !dispatchResult && !isTriggering) {
      // Auto-dispatch on timer expiry
      handleConfirm();
    }
  }, [isOpen, countdown, dispatchResult, isTriggering]);

  const handleConfirm = () => {
    const payload: SOSTriggerRequest = {
      vessel_id: 'IND-TN-02-MM-4412',
      vessel_name: 'Matsya Sagar II',
      crew_count: 4,
      location: { latitude: lat, longitude: lon },
      distress_nature: nature,
    };
    triggerSos(payload);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="w-full max-w-lg rounded-3xl bg-navy-950 border-2 border-red-500/80 p-6 text-slate-100 shadow-2xl shadow-red-950/80 space-y-4">
        <div className="flex items-center justify-between border-b border-red-900/50 pb-3">
          <div className="flex items-center gap-2 text-red-400 font-bold">
            <AlertTriangle className="w-6 h-6 animate-bounce" />
            <h3 className="text-lg">COAST GUARD DISTRESS BROADCAST</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {!dispatchResult ? (
          <>
            <div className="text-center py-4 bg-red-950/30 rounded-2xl border border-red-900/40">
              <div className="text-4xl font-extrabold text-red-500 font-mono">{countdown}s</div>
              <p className="text-xs text-slate-300 mt-1">Broadcasting distress coordinates automatically...</p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">Nature of Distress</label>
              <select
                value={nature}
                onChange={(e) => setNature(e.target.value as DistressNature)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-sm text-slate-200"
              >
                <option value="UNKNOWN">General Distress / Urgent Assistance</option>
                <option value="ENGINE_FAILURE">Engine / Steering Failure</option>
                <option value="CAPSIZING_SINKING">Taking Water / Sinking</option>
                <option value="BAD_WEATHER_TRAPPED">Severe Cyclone / Trapped in High Swell</option>
                <option value="MEDICAL_EMERGENCY">Critical Crew Medical Emergency</option>
              </select>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={onClose}
                className="flex-1 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-sm transition-all"
              >
                CANCEL (FALSE ALARM)
              </button>
              <button
                onClick={handleConfirm}
                disabled={isTriggering}
                className="flex-1 py-3 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-sm shadow-lg shadow-red-600/40 transition-all"
              >
                {isTriggering ? 'DISPATCHING...' : 'DISPATCH NOW'}
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-3">
            <div className="p-4 rounded-2xl bg-emerald-950/60 border border-emerald-700/80 text-xs text-emerald-200 font-mono space-y-1">
              <div className="flex items-center gap-2 font-bold text-emerald-400">
                <Radio className="w-4 h-4" />
                <span>DISTRESS SIGNAL CONFIRMED (MRCC ACKNOWLEDGED)</span>
              </div>
              <div>Incident ID: {dispatchResult.incident_id}</div>
              <div>Rescue Hub: {dispatchResult.nearest_rescue_centre}</div>
              <div>Uplinks: {dispatchResult.dispatched_channels.join(', ')}</div>
            </div>

            <div className="p-3 bg-slate-900 rounded-xl text-xs space-y-1 text-slate-300">
              <div className="font-semibold text-slate-100">Survival Protocols:</div>
              {dispatchResult.instructions_for_crew.map((inst, idx) => (
                <div key={idx}>• {inst}</div>
              ))}
            </div>

            <button
              onClick={onClose}
              className="w-full py-3 rounded-xl bg-slate-800 text-slate-200 font-bold text-sm"
            >
              CLOSE
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
