import React, { useEffect, useRef } from 'react';
import {
  ArrowDown,
  Sparkles,
  Compass,
  Satellite,
  Radio,
  ShieldAlert,
  Anchor,
  Zap,
} from 'lucide-react';

interface ScrollJourneyProps {
  onExplore: () => void;
  journeyProgressRef: React.MutableRefObject<number>;
}

/**
 * Compute opacity for a layer that fades in then fades out at scroll-driven breakpoints.
 * Returns 0 outside the active range, 1 at full visibility, and a linear ramp between.
 */
function layerOpacity(
  jp: number,
  inStart: number,
  inEnd: number,
  outStart: number,
  outEnd: number,
): number {
  if (jp <= inStart) return 0;
  if (jp <= inEnd) return (jp - inStart) / (inEnd - inStart);
  if (jp <= outStart) return 1;
  if (jp >= outEnd) return 0;
  return 1 - (jp - outStart) / (outEnd - outStart);
}

/* ── Static data for satellite observation dots ── */
const OBS_POINTS = [
  { x: '22%', y: '38%' },
  { x: '48%', y: '28%' },
  { x: '72%', y: '42%' },
  { x: '35%', y: '58%' },
  { x: '80%', y: '55%' },
  { x: '15%', y: '62%' },
  { x: '58%', y: '68%' },
  { x: '85%', y: '32%' },
];

const COORD_LABELS = [
  { x: '23%', y: '36%', text: '12.8°N, 80.2°E' },
  { x: '49%', y: '26%', text: '8.7°N, 76.9°E' },
  { x: '73%', y: '40%', text: '15.4°N, 73.8°E' },
];

const SENSOR_STRIPS = [
  { color: 'bg-cyan-400', label: 'SST: 28.4°C' },
  { color: 'bg-emerald-400', label: 'CHL: 0.85 mg/m³' },
  { color: 'bg-blue-400', label: 'Wind: 14.5 kts SW' },
  { color: 'bg-amber-400', label: 'Waves: 1.8 m' },
];

export const ScrollJourney: React.FC<ScrollJourneyProps> = ({
  onExplore,
  journeyProgressRef,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const heroRef = useRef<HTMLDivElement>(null);
  const satRef = useRef<HTMLDivElement>(null);
  const dataRef = useRef<HTMLDivElement>(null);
  const orcaRef = useRef<HTMLDivElement>(null);
  const hintRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const update = () => {
      const rect = container.getBoundingClientRect();
      const scrollInto = Math.max(0, -rect.top);
      const scrollRange = container.offsetHeight - window.innerHeight;
      if (scrollRange <= 0) return;
      const jp = Math.min(1, scrollInto / scrollRange);

      // Share with OceanCanvas via ref (no React render)
      journeyProgressRef.current = jp;

      /* ── Layer visibility computations ── */

      // Hero: fully visible at 0 %, fades out 0.05 → 0.22
      const heroO = jp <= 0.05 ? 1 : jp >= 0.22 ? 0 : 1 - (jp - 0.05) / 0.17;
      const heroTY = -jp * 180;

      // Satellite: in 0.10→0.25, hold, out 0.40→0.52
      const satO = layerOpacity(jp, 0.10, 0.25, 0.40, 0.52);

      // Data convergence: in 0.38→0.52, hold, out 0.65→0.76
      const dataO = layerOpacity(jp, 0.38, 0.52, 0.65, 0.76);

      // ORCA activation: in 0.60→0.75, hold, out 0.90→1.0
      const orcaO = layerOpacity(jp, 0.60, 0.75, 0.90, 1.0);

      // Scroll hint: disappears immediately
      const hintO = jp <= 0.01 ? 1 : jp >= 0.08 ? 0 : 1 - (jp - 0.01) / 0.07;

      /* ── Apply via refs — zero React renders ── */

      if (heroRef.current) {
        heroRef.current.style.opacity = String(heroO);
        heroRef.current.style.transform = `translate3d(0,${heroTY}px,0)`;
      }
      if (satRef.current) {
        satRef.current.style.opacity = String(satO);
        satRef.current.style.transform = `translate3d(0,${(1 - satO) * 30}px,0)`;
      }
      if (dataRef.current) {
        dataRef.current.style.opacity = String(dataO);
        dataRef.current.style.transform = `translate3d(0,${(1 - dataO) * 25}px,0)`;
      }
      if (orcaRef.current) {
        orcaRef.current.style.opacity = String(orcaO);
        orcaRef.current.style.transform = `translate3d(0,${(1 - orcaO) * 20}px,0) scale(${0.92 + orcaO * 0.08})`;
      }
      if (hintRef.current) {
        hintRef.current.style.opacity = String(hintO);
      }
    };

    const onScroll = () => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(update);
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    update(); // set initial state

    return () => {
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(rafRef.current);
    };
  }, [journeyProgressRef]);

  return (
    <div ref={containerRef} className="relative w-full" style={{ height: '500vh' }}>
      <div className="sticky top-0 h-screen w-full overflow-hidden">

        {/* ═══════════════════════════════════════════════════════
            LAYER 1 — Hero Content (visible 0 %→22 %)
        ═══════════════════════════════════════════════════════ */}
        <div
          ref={heroRef}
          className="absolute inset-0 z-10 flex flex-col justify-center items-center px-6 sm:px-12 pt-20 text-center select-none"
          style={{ willChange: 'transform, opacity' }}
        >
          {/* SIH badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/20 text-cyan-300 text-xs font-mono mb-8 backdrop-blur-md shadow-lg shadow-cyan-950/50">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>ISRO Smart India Hackathon 2026</span>
            <span className="w-1 h-1 rounded-full bg-cyan-400" />
            <span className="text-slate-400">Marine Ecosystem Intelligence</span>
          </div>

          <div className="max-w-4xl space-y-6">
            <h1 className="text-5xl sm:text-7xl lg:text-8xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-white via-slate-100 to-slate-400 leading-[1.08] font-sans">
              The Ocean Changes. <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-cyan-electric to-blue-500 text-glow-cyan">
                ORCA Watches.
              </span>
            </h1>
            <p className="max-w-2xl mx-auto text-base sm:text-xl text-slate-300 font-light leading-relaxed">
              Live ocean data, collaborative AI reasoning, and proactive safety
              guidance for fishermen, disaster agencies, and maritime researchers.
            </p>
            <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
              <button
                onClick={onExplore}
                className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-gradient-to-r from-cyan-500 via-cyan-electric to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-navy-950 font-black text-sm uppercase tracking-wider shadow-2xl shadow-cyan-500/30 hover:shadow-cyan-500/50 active:scale-95 transition-all duration-200 cursor-pointer flex items-center justify-center gap-2"
              >
                <Compass className="w-4 h-4 text-navy-950 stroke-[2.5]" />
                <span>Explore ORCA</span>
              </button>
            </div>
          </div>

          {/* Ambient telemetry ticker */}
          <div className="absolute bottom-16 left-6 right-6 hidden md:flex items-center justify-center gap-8 text-[11px] font-mono text-slate-400 pointer-events-none">
            <div className="flex items-center gap-2 bg-slate-900/40 px-3 py-1 rounded-lg border border-slate-800/60 backdrop-blur-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              <span>SST Grid: 28.4°C (MOSDAC)</span>
            </div>
            <div className="flex items-center gap-2 bg-slate-900/40 px-3 py-1 rounded-lg border border-slate-800/60 backdrop-blur-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>PFZ Density: Active (INCOIS)</span>
            </div>
            <div className="flex items-center gap-2 bg-slate-900/40 px-3 py-1 rounded-lg border border-slate-800/60 backdrop-blur-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              <span>IMBL Clearance: 28.5 km</span>
            </div>
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════
            LAYER 2 — Satellite Telemetry (visible 10 %→52 %)
        ═══════════════════════════════════════════════════════ */}
        <div
          ref={satRef}
          className="absolute inset-0 z-20 flex flex-col justify-center items-center pointer-events-none"
          style={{ willChange: 'transform, opacity', opacity: 0 }}
        >
          {/* Header */}
          <div className="relative z-10 text-center mb-4 px-4">
            <div className="inline-flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-widest bg-cyan-950/50 px-3 py-1.5 rounded-full border border-cyan-700/30 backdrop-blur-sm">
              <Satellite className="w-3.5 h-3.5" />
              <span>Satellite Telemetry Active</span>
            </div>
            <h2 className="text-3xl sm:text-5xl font-bold text-slate-100 mt-4 tracking-tight">
              Observing the{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
                Indian Ocean Basin
              </span>
            </h2>
            <p className="text-sm text-slate-400 mt-2 max-w-lg mx-auto">
              ISRO satellites and coastal sensors scan terabytes of thermal,
              optical, and gravitational data every second.
            </p>
          </div>

          {/* Orbital arc SVG */}
          <svg
            className="absolute inset-0 w-full h-full"
            viewBox="0 0 1000 600"
            preserveAspectRatio="xMidYMid slice"
            fill="none"
          >
            <path
              d="M 0,340 Q 300,60 600,220 T 1000,160"
              stroke="rgba(0,242,254,0.15)"
              strokeWidth="1"
              strokeDasharray="6 10"
              className="journey-orbit-line"
            />
            <path
              d="M 0,480 Q 350,180 700,380 T 1000,280"
              stroke="rgba(0,242,254,0.10)"
              strokeWidth="0.8"
              strokeDasharray="4 12"
              className="journey-orbit-line"
              style={{ animationDuration: '12s' }}
            />
            <path
              d="M 200,20 Q 500,380 800,120"
              stroke="rgba(0,210,255,0.08)"
              strokeWidth="0.6"
              strokeDasharray="3 14"
              className="journey-orbit-line"
              style={{ animationDuration: '10s' }}
            />
          </svg>

          {/* Observation dots */}
          {OBS_POINTS.map((pos, i) => (
            <div
              key={`obs-${i}`}
              className="absolute w-1.5 h-1.5 rounded-full bg-cyan-400"
              style={{
                left: pos.x,
                top: pos.y,
                boxShadow: '0 0 6px rgba(0,242,254,0.5)',
                animation: `journey-obs-pulse 3s ease-in-out ${i * 0.4}s infinite`,
              }}
            />
          ))}

          {/* Coordinate labels */}
          {COORD_LABELS.map((c, i) => (
            <span
              key={`coord-${i}`}
              className="absolute text-[9px] font-mono text-cyan-400/40 hidden sm:block"
              style={{ left: c.x, top: c.y, transform: 'translate(12px, -4px)' }}
            >
              {c.text}
            </span>
          ))}

          {/* Bottom sensor strip */}
          <div className="absolute bottom-10 left-6 right-6 hidden sm:flex items-center justify-center gap-4 text-[11px] font-mono text-slate-400 z-10">
            {SENSOR_STRIPS.map((s, i) => (
              <div
                key={`sensor-${i}`}
                className="flex items-center gap-2 bg-slate-900/50 px-3 py-1.5 rounded-lg border border-cyan-900/30 backdrop-blur-sm"
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${s.color} animate-pulse`}
                />
                <span>{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════
            LAYER 3 — Live Data Convergence (visible 38 %→76 %)
        ═══════════════════════════════════════════════════════ */}
        <div
          ref={dataRef}
          className="absolute inset-0 z-30"
          style={{ willChange: 'transform, opacity', opacity: 0 }}
        >
          {/* Section header */}
          <div className="absolute top-[10%] left-1/2 -translate-x-1/2 text-center z-10 w-full max-w-lg px-4">
            <div className="inline-flex items-center gap-2 text-xs font-mono text-emerald-400 uppercase tracking-widest bg-emerald-950/50 px-3 py-1.5 rounded-full border border-emerald-700/30 backdrop-blur-sm">
              <Zap className="w-3.5 h-3.5" />
              <span>Live Data Streams</span>
            </div>
            <h3 className="text-2xl sm:text-3xl font-bold text-slate-100 mt-3">
              Multi-Source{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">
                Intelligence Feeds
              </span>
            </h3>
          </div>

          {/* Connection lines SVG */}
          <svg
            className="absolute inset-0 w-full h-full"
            viewBox="0 0 1000 1000"
            preserveAspectRatio="none"
            fill="none"
          >
            {/* MOSDAC → Centre */}
            <path
              d="M 160,320 C 280,380 400,460 500,500"
              stroke="rgba(0,242,254,0.25)"
              strokeWidth="1.2"
              strokeDasharray="8 12"
              className="journey-data-line"
            />
            {/* INCOIS → Centre */}
            <path
              d="M 840,320 C 720,380 600,460 500,500"
              stroke="rgba(16,185,129,0.25)"
              strokeWidth="1.2"
              strokeDasharray="8 12"
              className="journey-data-line"
              style={{ animationDelay: '0.5s' }}
            />
            {/* NavIC → Centre */}
            <path
              d="M 500,780 C 500,680 500,580 500,500"
              stroke="rgba(59,130,246,0.25)"
              strokeWidth="1.2"
              strokeDasharray="8 12"
              className="journey-data-line"
              style={{ animationDelay: '1s' }}
            />
          </svg>

          {/* MOSDAC label */}
          <div className="absolute top-[26%] left-[6%] sm:left-[10%] max-w-[180px] sm:max-w-[200px] pointer-events-none">
            <div className="glass-panel-subtle p-3 sm:p-4 rounded-2xl border border-cyan-500/20 space-y-1.5">
              <div className="flex items-center gap-2">
                <Satellite className="w-4 h-4 text-cyan-400 shrink-0" />
                <span className="text-sm font-bold text-slate-100">MOSDAC</span>
              </div>
              <div className="text-[10px] sm:text-[11px] font-mono text-slate-400 leading-snug">
                SST • Chlorophyll • Currents
              </div>
              <div className="text-[9px] font-mono text-cyan-400/50">
                ISRO Space Applications Centre
              </div>
            </div>
          </div>

          {/* INCOIS label */}
          <div className="absolute top-[26%] right-[6%] sm:right-[10%] max-w-[180px] sm:max-w-[200px] pointer-events-none">
            <div className="glass-panel-subtle p-3 sm:p-4 rounded-2xl border border-emerald-500/20 space-y-1.5">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-sm font-bold text-slate-100">INCOIS</span>
              </div>
              <div className="text-[10px] sm:text-[11px] font-mono text-slate-400 leading-snug">
                Fishing Zones • Storm Alerts
              </div>
              <div className="text-[9px] font-mono text-emerald-400/50">
                Ministry of Earth Sciences
              </div>
            </div>
          </div>

          {/* NavIC label */}
          <div className="absolute bottom-[16%] left-1/2 -translate-x-1/2 max-w-[180px] sm:max-w-[200px] pointer-events-none">
            <div className="glass-panel-subtle p-3 sm:p-4 rounded-2xl border border-blue-500/20 space-y-1.5">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-blue-400 shrink-0" />
                <span className="text-sm font-bold text-slate-100">NavIC / DAT-SG</span>
              </div>
              <div className="text-[10px] sm:text-[11px] font-mono text-slate-400 leading-snug">
                Boundary • Distress Data
              </div>
              <div className="text-[9px] font-mono text-blue-400/50">
                ISRO Satellite Messaging
              </div>
            </div>
          </div>

          {/* Central convergence point */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
            <div className="w-3 h-3 rounded-full bg-cyan-400 shadow-lg shadow-cyan-400/50 animate-pulse" />
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════
            LAYER 4 — ORCA Activation (visible 60 %→100 %)
        ═══════════════════════════════════════════════════════ */}
        <div
          ref={orcaRef}
          className="absolute inset-0 z-40 flex flex-col justify-center items-center pointer-events-none"
          style={{ willChange: 'transform, opacity', opacity: 0 }}
        >
          <div className="text-center">
            {/* Status badge */}
            <div className="inline-flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-widest bg-cyan-950/50 px-3 py-1.5 rounded-full border border-cyan-700/30 backdrop-blur-sm mb-8">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>System Online</span>
            </div>

            {/* ORCA core node */}
            <div className="relative mx-auto" style={{ width: '6rem', height: '6rem' }}>
              {/* Expanding pulse rings */}
              <div className="orca-pulse-ring" style={{ animationDelay: '0s' }} />
              <div className="orca-pulse-ring" style={{ animationDelay: '1s' }} />
              <div className="orca-pulse-ring" style={{ animationDelay: '2s' }} />

              {/* Core */}
              <div className="relative z-10 w-24 h-24 rounded-full bg-gradient-to-tr from-cyan-500/10 to-blue-500/10 border border-cyan-400/30 flex items-center justify-center backdrop-blur-sm">
                <div className="w-14 h-14 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-2xl shadow-cyan-500/40">
                  <Anchor className="w-7 h-7 text-white stroke-[2]" />
                </div>
              </div>
            </div>

            {/* Label */}
            <h3 className="text-3xl sm:text-5xl font-black text-slate-100 mt-8 tracking-tight">
              ORCA{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500 text-glow-cyan">
                Intelligence
              </span>
            </h3>
            <p className="text-sm sm:text-base text-slate-400 font-mono mt-2 tracking-wide">
              Multi-Agent Marine Reasoning Core
            </p>

            {/* Incoming feed indicators */}
            <div className="flex items-center justify-center gap-6 mt-6">
              <div className="flex items-center gap-1.5 text-[10px] font-mono text-cyan-400/70">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                <span>MOSDAC</span>
              </div>
              <div className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400/70">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>INCOIS</span>
              </div>
              <div className="flex items-center gap-1.5 text-[10px] font-mono text-blue-400/70">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                <span>NavIC</span>
              </div>
            </div>

            {/* Readout */}
            <div className="mt-8 inline-flex items-center gap-4 text-[11px] font-mono text-slate-500">
              <span>3 AGENTS ACTIVE</span>
              <span className="w-px h-3 bg-slate-700" />
              <span>LATENCY 8.4 ms</span>
              <span className="w-px h-3 bg-slate-700" />
              <span>14,200 pts/sec</span>
            </div>
          </div>
        </div>

        {/* ═══════ Scroll-to-Explore Indicator ═══════ */}
        <div
          ref={hintRef}
          className="absolute bottom-6 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center gap-2 text-slate-500 cursor-pointer select-none"
          style={{ willChange: 'opacity' }}
          onClick={onExplore}
        >
          <span className="text-[10px] font-mono uppercase tracking-widest text-slate-400">
            Scroll to Explore
          </span>
          <ArrowDown className="w-4 h-4 animate-bounce text-cyan-400" />
        </div>
      </div>
    </div>
  );
};
