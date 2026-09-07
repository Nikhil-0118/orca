import React from 'react';
import { Satellite, Activity, Wind, Waves, Thermometer } from 'lucide-react';

export const OceanToDataTransition: React.FC = () => {
  return (
    <section className="relative min-h-[60vh] w-full flex flex-col justify-center px-6 sm:px-10 lg:px-16 xl:px-20 py-16 z-10 select-none pointer-events-none">
      {/* Two-Sided Content Composition: Left Intro | Open Center Animation Safe Zone | Right Sensor Grid */}
      <div className="w-full flex flex-col lg:flex-row justify-between items-start gap-8">
        {/* ── LEFT SIDE (Width: ~32%) ── */}
        <div className="w-full lg:w-[32%] max-w-md text-left space-y-3.5 pointer-events-auto">
          <div className="inline-flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-widest bg-cyan-950/50 px-3 py-1 rounded-full border border-cyan-800/50 backdrop-blur-sm">
            <Satellite className="w-3.5 h-3.5 text-cyan-400" />
            <span>Layer 01 — Satellite Ingestion</span>
          </div>

          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-slate-100 tracking-tight leading-[1.15]">
            Converting Raw Ocean Swells Into <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
              Real-Time Intelligence
            </span>
          </h2>

          <p className="text-xs sm:text-sm text-slate-300 font-light leading-relaxed">
            Every second, ISRO satellites and coastal ocean buoys capture terabytes of thermal, optical, and gravitational data across the Indian Ocean Basin.
          </p>
        </div>

        {/* ── CENTER SAFE ZONE (~36% Width) — PROTECTED FOR SATELLITE BEAM & SHIP ── */}
        <div className="hidden lg:block lg:w-[36%] pointer-events-none" />

        {/* ── RIGHT SIDE SENSOR NODES (Width: ~32%) ── */}
        <div className="w-full lg:w-[32%] max-w-md grid grid-cols-2 gap-3 pointer-events-auto">
          {[
            { icon: Thermometer, label: 'SST Radiometry', val: '28.4°C', tag: 'INSAT-3D / 3DR' },
            { icon: Activity, label: 'Chlorophyll OCM', val: '0.85 mg/m³', tag: 'Oceansat-3' },
            { icon: Wind, label: 'Wind Vector Grids', val: '14.5 kts SW', tag: 'SCATSAT' },
            { icon: Waves, label: 'Significant Waves', val: '1.8 m', tag: 'INCOIS Buoys' },
          ].map((item, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-2xl glass-panel-subtle hover:glass-panel border border-slate-800/80 hover:border-cyan-500/40 transition-all duration-300 group text-left"
            >
              <div className="flex items-center justify-between mb-1.5">
                <item.icon className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                <span className="text-[9px] font-mono text-slate-500 uppercase">{item.tag}</span>
              </div>
              <div className="text-base sm:text-lg font-bold text-slate-100 font-mono group-hover:text-cyan-300 transition-colors">
                {item.val}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">{item.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
