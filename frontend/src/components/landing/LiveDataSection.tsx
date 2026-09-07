import React, { useState, useEffect } from 'react';
import { Satellite, Radio, ShieldAlert, Cpu, Zap } from 'lucide-react';

export const LiveDataSection: React.FC = () => {
  const [pulseActive, setPulseActive] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPulseActive((prev) => (prev + 1) % 3);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  const sources = [
    {
      id: 'mosdac',
      agency: 'ISRO MOSDAC',
      subtitle: 'Space Applications Centre (SAC)',
      icon: Satellite,
      color: 'text-cyan-400',
      borderColor: 'border-cyan-500/30',
      activeColor: 'border-cyan-400 bg-cyan-950/40 shadow-cyan-500/20',
      feeds: ['Sea Surface Temp (SST)', 'Chlorophyll-a Grids', 'Geostrophic Ocean Currents'],
      telemetry: 'INSAT-3D / Oceansat OCM-3 Live Link',
    },
    {
      id: 'incois',
      agency: 'INCOIS ERDDAP',
      subtitle: 'Ministry of Earth Sciences',
      icon: Radio,
      color: 'text-emerald-400',
      borderColor: 'border-emerald-500/30',
      activeColor: 'border-emerald-400 bg-emerald-950/40 shadow-emerald-500/20',
      feeds: ['Potential Fishing Zones (PFZ)', 'High Swell & Wave Forecast', 'Severe Cyclone Warnings'],
      telemetry: 'Coastal Wave Rider Buoy Network',
    },
    {
      id: 'navic',
      agency: 'NavIC / DAT-SG',
      subtitle: 'ISRO Satellite Messaging Bridge',
      icon: ShieldAlert,
      color: 'text-blue-400',
      borderColor: 'border-blue-500/30',
      activeColor: 'border-blue-400 bg-blue-950/40 shadow-blue-500/20',
      feeds: ['International Boundary (IMBL)', 'Distress Beacon Reception', 'Sub-GHz Broadcast Channels'],
      telemetry: 'GSAT-N2 Marine Transponder Active',
    },
  ];

  return (
    <section className="relative min-h-screen w-full flex flex-col justify-center items-center px-6 sm:px-12 py-20 z-10">
      <div className="max-w-4xl text-center space-y-4 mb-16">
        <div className="inline-flex items-center gap-2 text-xs font-mono text-emerald-400 uppercase tracking-widest bg-emerald-950/40 px-3 py-1 rounded-full border border-emerald-800/40 backdrop-blur-sm">
          <Zap className="w-3.5 h-3.5" />
          <span>Layer 02 — Multi-Source Ingestion Engine</span>
        </div>
        <h2 className="text-4xl sm:text-6xl font-extrabold text-slate-100 tracking-tight">
          Live Data Streams <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-500">
            Fusing Satellite & Oceanographic Signals
          </span>
        </h2>
        <p className="text-sm sm:text-base text-slate-300 font-light max-w-2xl mx-auto">
          Isolated data connectors pull live feeds without coupling, feeding normalized telemetry into ORCA's neural reasoning core.
        </p>
      </div>

      {/* Interactive Data Ingestion Flow: Sources -> Transmission Beams -> Central Node */}
      <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        {/* Left 3 Source Cards (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {sources.map((src, idx) => {
            const isActive = pulseActive === idx;
            return (
              <div
                key={src.id}
                className={`p-6 rounded-2xl border transition-all duration-500 backdrop-blur-xl shadow-xl ${
                  isActive ? src.activeColor : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl bg-slate-900 border border-slate-800 ${src.color}`}>
                      <src.icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-100 text-base sm:text-lg">{src.agency}</h3>
                      <p className="text-xs text-slate-400">{src.subtitle}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded-full border border-emerald-800/50">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                    <span>LIVE FEED</span>
                  </div>
                </div>

                {/* Feed Tags */}
                <div className="mt-4 flex flex-wrap gap-2">
                  {src.feeds.map((feed, fIdx) => (
                    <span
                      key={fIdx}
                      className="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-900/80 text-slate-300 border border-slate-800 flex items-center gap-1"
                    >
                      <span className="text-cyan-400">•</span>
                      {feed}
                    </span>
                  ))}
                </div>

                <div className="mt-3 text-[11px] font-mono text-slate-500 flex items-center gap-1">
                  <span>Sensor Link:</span>
                  <span className="text-slate-400">{src.telemetry}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Flow Visualization: Animated Beams into ORCA (5 cols) */}
        <div className="lg:col-span-5 h-full flex flex-col justify-center items-center p-8 rounded-3xl glass-panel relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(#00f2fe_1px,transparent_1px)] [background-size:16px_16px] opacity-10"></div>

          {/* Central Target Core */}
          <div className="relative z-10 flex flex-col items-center text-center space-y-4">
            <div className="relative">
              <div className="w-24 h-24 rounded-3xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-700 p-1 shadow-2xl shadow-cyan-500/40 animate-pulse-slow">
                <div className="w-full h-full bg-navy-950 rounded-[22px] flex items-center justify-center">
                  <Cpu className="w-10 h-10 text-cyan-400" />
                </div>
              </div>
              <span className="absolute -top-2 -right-2 px-2 py-0.5 rounded-full bg-cyan-500 text-navy-950 font-mono font-bold text-[10px]">
                INGESTING
              </span>
            </div>

            <div>
              <h4 className="text-lg font-bold text-slate-100">ORCA Normalization Bus</h4>
              <p className="text-xs text-slate-400 max-w-xs mt-1">
                Standardizes ERDDAP NetCDF, HDF5, and NavIC binary streams into Pydantic models in &lt;12ms.
              </p>
            </div>

            {/* Live Throughput Metrics */}
            <div className="w-full grid grid-cols-2 gap-2 pt-2 text-left font-mono text-[11px]">
              <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800">
                <span className="text-slate-500 block text-[10px]">THROUGHPUT</span>
                <span className="text-cyan-300 font-bold">14,200 pts/sec</span>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800">
                <span className="text-slate-500 block text-[10px]">LATENCY</span>
                <span className="text-emerald-400 font-bold">8.4 ms</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
