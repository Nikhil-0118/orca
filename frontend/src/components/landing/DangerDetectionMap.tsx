import React, { useState, useEffect } from 'react';
import { AlertTriangle, Navigation, ShieldCheck, Radio } from 'lucide-react';

export const DangerDetectionMap: React.FC = () => {
  const [boatProgress, setBoatProgress] = useState(0);
  const isDangerApproaching = boatProgress > 0.45;
  const isRerouted = boatProgress > 0.7;

  useEffect(() => {
    const interval = setInterval(() => {
      setBoatProgress((prev) => (prev >= 1 ? 0 : prev + 0.05));
    }, 450);
    return () => clearInterval(interval);
  }, []);

  // Compute boat simulation coordinates along flight path
  const boatX = isRerouted ? 30 + (boatProgress - 0.7) * 90 : 25 + boatProgress * 45;
  const boatY = isRerouted ? 70 - (boatProgress - 0.7) * 40 : 45 + boatProgress * 25;

  return (
    <section className="relative min-h-screen w-full flex flex-col justify-center items-center px-6 sm:px-12 py-20 z-10">
      <div className="max-w-4xl text-center space-y-4 mb-12">
        <div className="inline-flex items-center gap-2 text-xs font-mono text-red-400 uppercase tracking-widest bg-red-950/40 px-3 py-1 rounded-full border border-red-800/40 backdrop-blur-sm">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>Layer 05 — Proactive Geofencing & Danger Avoidance</span>
        </div>
        <h2 className="text-4xl sm:text-6xl font-extrabold text-slate-100 tracking-tight">
          Live Danger Detection <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-400 via-amber-400 to-cyan-400 text-glow-red">
            Before Accidents Happen
          </span>
        </h2>
        <p className="text-sm sm:text-base text-slate-300 font-light max-w-2xl mx-auto">
          ORCA runs continuous geospatial tracking on moving vessels, projecting collision courses with high-swell storm cells, coral reefs, and international maritime boundaries.
        </p>
      </div>

      {/* High-Seas Tactical Map Simulation Canvas Container */}
      <div className="w-full max-w-5xl h-[520px] rounded-3xl glass-panel relative overflow-hidden border border-slate-700/80 shadow-2xl flex flex-col">
        {/* Top HUD Status Banner */}
        <div className="absolute top-4 left-4 right-4 z-20 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
          <div className="flex items-center gap-2 bg-navy-950/90 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 shadow-lg">
            <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span>Vessel: Matsya Sagar II (IND-TN-02)</span>
          </div>

          {/* Dynamic Warning Banner */}
          <div
            className={`px-4 py-1.5 rounded-xl text-xs font-mono font-bold flex items-center gap-2 transition-all duration-300 shadow-xl backdrop-blur-md ${
              isDangerApproaching
                ? 'bg-red-950/90 border border-red-500 text-red-200 animate-pulse'
                : 'bg-emerald-950/80 border border-emerald-500/60 text-emerald-300'
            }`}
          >
            {isDangerApproaching ? (
              <>
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <span>⚠ DANGER DETECTED: Storm Surge Cell Ahead — Auto-Reroute Active</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Course Nominal — Clear of Maritime Geofences</span>
              </>
            )}
          </div>
        </div>

        {/* Map Grid & Nautical Vectors Background */}
        <div className="relative flex-1 w-full h-full bg-[#020b18] overflow-hidden">
          {/* Subtle Radar Sweep */}
          <div className="absolute inset-0 bg-[radial-gradient(#082044_1px,transparent_1px)] [background-size:28px_28px] opacity-40"></div>

          {/* Maritime Boundary (IMBL) Line */}
          <div className="absolute top-0 bottom-0 left-[78%] w-0.5 border-r-2 border-dashed border-amber-500/50 z-10">
            <span className="absolute top-16 -left-32 text-[10px] font-mono text-amber-400 bg-navy-950/90 px-2 py-0.5 rounded border border-amber-800/60">
              IMBL Border Line (Prohibited)
            </span>
          </div>

          {/* High-Yield Potential Fishing Zone (PFZ) Overlay */}
          <div className="absolute top-[20%] left-[15%] w-48 h-36 rounded-3xl border-2 border-dashed border-emerald-400/60 bg-emerald-500/10 flex flex-col justify-between p-3 pointer-events-none">
            <span className="text-[10px] font-mono font-bold text-emerald-300 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              INCOIS PFZ Zone #42
            </span>
            <span className="text-[9px] font-mono text-slate-400">Chlorophyll: 0.92 mg/m³</span>
          </div>

          {/* Active Storm Surge Danger Zone */}
          <div
            className={`absolute top-[48%] left-[42%] w-60 h-44 rounded-full border-2 transition-all duration-500 flex flex-col items-center justify-center p-4 pointer-events-none ${
              isDangerApproaching
                ? 'border-red-500 bg-red-600/25 shadow-2xl shadow-red-600/40 animate-pulse'
                : 'border-red-800/40 bg-red-950/15'
            }`}
          >
            <AlertTriangle className={`w-7 h-7 mb-1 ${isDangerApproaching ? 'text-red-400' : 'text-red-800'}`} />
            <span className="text-xs font-mono font-bold text-red-200">CYCLONIC SWELL (3.8m Waves)</span>
            <span className="text-[10px] font-mono text-red-400">MOSDAC Wind Shear: 38 kts</span>
          </div>

          {/* Planned Danger Route (Dashed Red Line) */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
            {/* Danger Heading Path */}
            <line
              x1="25%"
              y1="45%"
              x2="55%"
              y2="65%"
              stroke="rgba(239, 68, 68, 0.4)"
              strokeWidth="2"
              strokeDasharray="6,6"
            />
            {/* Generated Safe Alternate Reroute (Green Curved Path) */}
            {isDangerApproaching && (
              <path
                d="M 180 200 Q 240 380 480 340"
                fill="none"
                stroke="#10b981"
                strokeWidth="3"
                strokeDasharray="4,4"
                className="animate-pulse"
              />
            )}
          </svg>

          {/* Animated Vessel Marker */}
          <div
            className="absolute z-30 transform -translate-x-1/2 -translate-y-1/2 transition-all duration-300 pointer-events-none"
            style={{ top: `${boatY}%`, left: `${boatX}%` }}
          >
            <div className="relative flex items-center justify-center">
              <span
                className={`animate-ping absolute inline-flex h-8 w-8 rounded-full opacity-60 ${
                  isDangerApproaching ? 'bg-red-500' : 'bg-cyan-400'
                }`}
              ></span>
              <div
                className={`w-8 h-8 rounded-full border-2 flex items-center justify-center shadow-lg transition-colors ${
                  isDangerApproaching
                    ? 'bg-red-950 border-red-400 text-red-300 shadow-red-500/50'
                    : 'bg-navy-950 border-cyan-400 text-cyan-300 shadow-cyan-500/50'
                }`}
              >
                <Navigation
                  className="w-4 h-4 transform"
                  style={{ transform: isRerouted ? 'rotate(45deg)' : 'rotate(110deg)' }}
                />
              </div>
            </div>

            {/* Telemetry Tag */}
            <div className="absolute top-9 left-1/2 -translate-x-1/2 whitespace-nowrap bg-navy-950/95 border border-slate-700 px-2 py-0.5 rounded text-[9px] font-mono text-slate-300 shadow-md">
              Heading: {isRerouted ? '045° (Safe Divert)' : '110° (Collision Vector)'}
            </div>
          </div>
        </div>

        {/* Bottom Recommendation HUD */}
        <div className="h-14 bg-navy-950/95 border-t border-slate-800 px-6 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-3">
            <span className="text-slate-400 hidden sm:inline">SAFETY RECOMMENDATION:</span>
            <span className="text-cyan-300 font-semibold">
              {isDangerApproaching
                ? 'Alternate route generated: Steer 045° to avoid storm cell and stay within Indian EEZ.'
                : 'Maintain current heading toward PFZ Zone #42. Distance: 12.4 km.'}
            </span>
          </div>

          <div className="text-emerald-400 font-bold hidden md:block">
            {isDangerApproaching ? 'RE-ROUTING (SAFETY FIRST)' : 'ALL CLEAR'}
          </div>
        </div>
      </div>
    </section>
  );
};
