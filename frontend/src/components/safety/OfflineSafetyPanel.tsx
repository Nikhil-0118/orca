import React, { useState } from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Radio,
  Wifi,
  WifiOff,
  Compass,
  X,
  Flame,
  Map as MapIcon,
  Activity,
} from 'lucide-react';
import { useOfflineSafety } from '../../hooks/useOfflineSafety';
import { SafetyState } from '../../services/offlineSafetyService';
import { buzzerService } from '../../services/buzzerService';
import { OfflineBoatSafetySimulator } from './OfflineBoatSafetySimulator';

interface OfflineSafetyPanelProps {
  isOpen: boolean;
  onClose: () => void;
  safetyHook: ReturnType<typeof useOfflineSafety>;
}

function getStateBadge(state: SafetyState) {
  switch (state) {
    case 'BREACH':
      return {
        bg: 'rgba(239, 68, 68, 0.15)',
        border: 'rgba(239, 68, 68, 0.4)',
        color: '#ef4444',
        icon: Flame,
        label: 'CRITICAL BREACH',
      };
    case 'WARNING':
      return {
        bg: 'rgba(245, 158, 11, 0.15)',
        border: 'rgba(245, 158, 11, 0.4)',
        color: '#f59e0b',
        icon: AlertTriangle,
        label: 'WARNING ZONE',
      };
    case 'APPROACHING':
      return {
        bg: 'rgba(234, 179, 8, 0.15)',
        border: 'rgba(234, 179, 8, 0.4)',
        color: '#eab308',
        icon: ShieldAlert,
        label: 'APPROACHING',
      };
    default:
      return {
        bg: 'rgba(16, 185, 129, 0.15)',
        border: 'rgba(16, 185, 129, 0.4)',
        color: '#10b981',
        icon: ShieldCheck,
        label: 'NORMAL (SAFE)',
      };
  }
}

export const OfflineSafetyPanel: React.FC<OfflineSafetyPanelProps> = ({
  isOpen,
  onClose,
  safetyHook,
}) => {
  const [activeTab, setActiveTab] = useState<'simulator' | 'diagnostics'>('simulator');

  if (!isOpen) return null;

  const handleClose = () => {
    buzzerService.stopDangerAlarm();
    onClose();
  };

  const {
    latitude,
    longitude,
    isOffline,
    isSimulatedOffline,
    evaluation,
    alertHistory,
    toggleSimulatedOffline,
  } = safetyHook;

  const badge = getStateBadge(evaluation.state);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-navy-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[94vh] overflow-y-auto rounded-3xl bg-[#0b1329] border border-cyan-500/30 p-5 sm:p-6 shadow-2xl shadow-black/80 flex flex-col space-y-4 text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-950/80 border border-cyan-500/40 text-cyan-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100">
                  Offline Boat Safety Simulator
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-cyan-950/80 border border-cyan-700 text-cyan-300">
                  SIH Internal Demo
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Future NavIC Offline Geofence Engine · 100% Local Browser Audio Buzzer · Zero External APIs
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* View Mode Switcher Tabs */}
            <div className="flex items-center bg-slate-900 p-1 rounded-xl border border-slate-800">
              <button
                type="button"
                onClick={() => setActiveTab('simulator')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold flex items-center gap-1.5 transition-all ${
                  activeTab === 'simulator'
                    ? 'bg-cyan-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <MapIcon className="w-3.5 h-3.5" />
                <span>Map Simulator</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('diagnostics')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold flex items-center gap-1.5 transition-all ${
                  activeTab === 'diagnostics'
                    ? 'bg-cyan-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Activity className="w-3.5 h-3.5" />
                <span>Diagnostics & Log</span>
              </button>
            </div>

            <button
              type="button"
              onClick={handleClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors"
              aria-label="Close safety panel"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab 1: Live Interactive Boat Safety Simulator Map */}
        {activeTab === 'simulator' && (
          <OfflineBoatSafetySimulator safetyHook={safetyHook} />
        )}

        {/* Tab 2: Raw Diagnostics, Offline Switcher & Event Log */}
        {activeTab === 'diagnostics' && (
          <div className="space-y-4 animate-in fade-in">
            {/* Connectivity Status Banner & Simulate Internet Toggle */}
            <div className="p-4 rounded-2xl bg-[#070c18] border border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div
                  className={`p-2.5 rounded-xl flex items-center justify-center ${
                    isOffline
                      ? 'bg-red-950/80 border border-red-500/50 text-red-400 animate-pulse'
                      : 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-400'
                  }`}
                >
                  {isOffline ? <WifiOff className="w-5 h-5" /> : <Wifi className="w-5 h-5" />}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs font-mono font-bold uppercase ${
                        isOffline ? 'text-red-400' : 'text-emerald-400'
                      }`}
                    >
                      {isOffline ? '🔴 OFFLINE SAFETY MODE' : '🟢 ONLINE MODE'}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    {isOffline
                      ? 'AI Agents: Disabled · Local Geofence: Active'
                      : 'AI Agents: Available · Geofence: Active'}
                  </p>
                </div>
              </div>

              {/* Dev Switch */}
              <button
                type="button"
                onClick={() => toggleSimulatedOffline()}
                className={`px-3.5 py-2 rounded-xl text-xs font-mono font-semibold transition-all flex items-center gap-2 ${
                  isSimulatedOffline
                    ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/50'
                    : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
                }`}
              >
                <Radio className="w-3.5 h-3.5" />
                <span>
                  {isSimulatedOffline ? 'Simulating Offline (Active)' : 'Simulate Internet OFF'}
                </span>
              </button>
            </div>

            {/* Telemetry Readout Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="text-[10px] font-mono text-slate-400 uppercase">Latitude</div>
                <div className="text-sm font-bold font-mono text-slate-200 mt-1">
                  {latitude.toFixed(4)}° N
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="text-[10px] font-mono text-slate-400 uppercase">Longitude</div>
                <div className="text-sm font-bold font-mono text-slate-200 mt-1">
                  {longitude.toFixed(4)}° E
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="text-[10px] font-mono text-slate-400 uppercase">Border Distance</div>
                <div className="text-sm font-bold font-mono text-cyan-400 mt-1">
                  {evaluation.distanceToBoundaryKm.toFixed(2)} km
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="text-[10px] font-mono text-slate-400 uppercase">Bearing</div>
                <div className="text-sm font-bold font-mono text-slate-200 mt-1 flex items-center gap-1">
                  <Compass className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{evaluation.bearingDegrees}°</span>
                </div>
              </div>
            </div>

            {/* Active Status & Alert Banner */}
            <div
              className="p-4 rounded-2xl border transition-all"
              style={{
                backgroundColor: badge.bg,
                borderColor: badge.border,
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <badge.icon className="w-4 h-4" style={{ color: badge.color }} />
                  <span className="text-xs font-mono font-bold uppercase" style={{ color: badge.color }}>
                    {badge.label}
                  </span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">
                  {new Date(evaluation.evaluatedAt).toLocaleTimeString()}
                </span>
              </div>

              <h4 className="text-sm font-bold text-slate-100">{evaluation.alertTitle}</h4>
              <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                {evaluation.alertMessage}
              </p>

              <div className="mt-2 text-[10px] font-mono text-slate-400">
                Nearest Feature: {evaluation.nearestBoundaryName}
              </div>
            </div>

            {/* Alert History Log */}
            {alertHistory.length > 0 && (
              <div className="p-3 rounded-2xl bg-[#070c18] border border-slate-800">
                <span className="text-xs font-bold text-slate-300 block mb-2">
                  Recent State Transitions ({alertHistory.length})
                </span>
                <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {alertHistory.map((hist, idx) => (
                    <div
                      key={idx}
                      className="text-xs p-2 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between"
                    >
                      <span className="font-mono text-slate-300">
                        {hist.state} · {hist.distanceToBoundaryKm.toFixed(2)} km
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        {new Date(hist.evaluatedAt).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer Conceptual NavIC Architecture & Disclaimer */}
        <div className="border-t border-slate-800/80 pt-3 flex flex-col sm:flex-row items-center justify-between gap-2 text-[10px] font-mono text-slate-500">
          <div className="flex items-center gap-2">
            <span className="text-cyan-400 font-bold">Concept:</span>
            <span>Manual Boat Position &rarr; Offline Safety Engine &rarr; Boundary Distance &rarr; Warning + Buzzer</span>
          </div>
          <div>{evaluation.warning}</div>
        </div>
      </div>
    </div>
  );
};

export default OfflineSafetyPanel;
