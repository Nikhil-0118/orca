import React, { useEffect, useState } from 'react';
import { ActiveRoute } from '../../types/map.types';
import { Navigation, Compass } from 'lucide-react';

interface RouteLayerProps {
  route: ActiveRoute | null;
  visible: boolean;
}

export const RouteLayer: React.FC<RouteLayerProps> = ({ route, visible }) => {
  const [vesselProgress, setVesselProgress] = useState(0);

  useEffect(() => {
    if (!route) {
      setVesselProgress(0);
      return;
    }

    const interval = setInterval(() => {
      setVesselProgress((prev) => (prev >= 1 ? 0 : prev + 0.015));
    }, 80);

    return () => clearInterval(interval);
  }, [route]);

  if (!visible || !route) return null;

  // Tactical map projected coordinates (Origin at ~40% left, 55% top; Destination relative to bearing)
  const originX = 35; // %
  const originY = 55; // %

  // Map destination coords into screen percentage space
  const rad = (route.bearingDegrees * Math.PI) / 180;
  const distScale = Math.min(38, Math.max(18, route.distanceKm * 1.1));
  const destX = originX + Math.sin(rad) * distScale;
  const destY = originY - Math.cos(rad) * distScale;

  // Bezier control point for slight nautical curvature
  const midX = (originX + destX) / 2 + (destY - originY) * 0.15;
  const midY = (originY + destY) / 2 - (destX - originX) * 0.15;

  // Compute animated vessel position on quadratic bezier curve
  const t = vesselProgress;
  const boatX = (1 - t) * (1 - t) * originX + 2 * (1 - t) * t * midX + t * t * destX;
  const boatY = (1 - t) * (1 - t) * originY + 2 * (1 - t) * t * midY + t * t * destY;

  return (
    <div className="absolute inset-0 pointer-events-none z-20">
      {/* Route SVG Vector Canvas */}
      <svg className="w-full h-full">
        <defs>
          <linearGradient id="routeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00f2fe" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.8" />
          </linearGradient>

          <filter id="routeGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Glow backdrop path */}
        <path
          d={`M ${originX}% ${originY}% Q ${midX}% ${midY}% ${destX}% ${destY}%`}
          fill="none"
          stroke="#00f2fe"
          strokeWidth="6"
          strokeOpacity="0.25"
        />

        {/* Animated Dashed Nautical Route Vector */}
        <path
          d={`M ${originX}% ${originY}% Q ${midX}% ${midY}% ${destX}% ${destY}%`}
          fill="none"
          stroke="url(#routeGradient)"
          strokeWidth="3"
          strokeDasharray="8 6"
          className="animate-[dash_2s_linear_infinite]"
          filter="url(#routeGlow)"
        />
      </svg>

      {/* ── Origin Waypoint (Current Location) ── */}
      <div
        className="absolute transform -translate-x-1/2 -translate-y-1/2 z-30"
        style={{ top: `${originY}%`, left: `${originX}%` }}
      >
        <div className="relative flex items-center justify-center">
          <span className="animate-ping absolute inline-flex h-6 w-6 rounded-full bg-cyan-400 opacity-40"></span>
          <div className="w-4 h-4 rounded-full bg-cyan-400 border-2 border-navy-950 shadow-md shadow-cyan-500/80"></div>
        </div>
        <div className="absolute top-5 left-1/2 -translate-x-1/2 whitespace-nowrap bg-navy-950/90 border border-cyan-700 px-2 py-0.5 rounded text-[9px] font-mono text-cyan-300 shadow-md">
          Current Position
        </div>
      </div>

      {/* ── Destination Waypoint Marker ── */}
      <div
        className="absolute transform -translate-x-1/2 -translate-y-1/2 z-30"
        style={{ top: `${destY}%`, left: `${destX}%` }}
      >
        <div className="relative flex items-center justify-center">
          <span className="animate-ping absolute inline-flex h-8 w-8 rounded-full bg-emerald-400 opacity-50"></span>
          <div className="w-5 h-5 rounded-full bg-emerald-500 border-2 border-white flex items-center justify-center shadow-lg shadow-emerald-500/60 text-navy-950 font-black text-[9px]">
            ★
          </div>
        </div>
        <div className="absolute top-6 left-1/2 -translate-x-1/2 whitespace-nowrap bg-slate-900/95 border border-emerald-500/80 px-2.5 py-1 rounded-lg text-[10px] font-mono text-emerald-300 shadow-xl space-y-0.5 text-center">
          <div className="font-bold text-slate-100">{route.destination.name}</div>
          <div className="text-[9px] text-slate-400">
            {route.distanceKm} km ({route.bearingDegrees}°)
          </div>
        </div>
      </div>

      {/* ── Animated Vessel Marker Traveling along Route ── */}
      <div
        className="absolute transform -translate-x-1/2 -translate-y-1/2 z-30 transition-all duration-75"
        style={{ top: `${boatY}%`, left: `${boatX}%` }}
      >
        <div className="relative flex items-center justify-center">
          <div className="w-7 h-7 rounded-xl bg-navy-950 border border-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-500/50">
            <Navigation
              className="w-4 h-4 text-cyan-300 transform"
              style={{ transform: `rotate(${route.bearingDegrees}deg)` }}
            />
          </div>
        </div>
      </div>

      {/* ── Route Telemetry HUD Card ── */}
      <div className="absolute bottom-12 left-4 z-30 max-w-xs p-3 rounded-2xl bg-navy-950/95 border border-cyan-800/70 shadow-2xl backdrop-blur-md space-y-2 pointer-events-auto">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-cyan-300 font-mono font-bold text-xs">
            <Compass className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
            <span>Active Navigation Trajectory</span>
          </div>
          <span
            className={`px-2 py-0.5 rounded text-[9px] font-bold font-mono ${
              route.safetyClearance === 'SAFE'
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-600/50'
                : 'bg-amber-950 text-amber-300 border border-amber-600/50'
            }`}
          >
            {route.safetyClearance}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-[10px] font-mono text-slate-300 pt-1 border-t border-slate-800">
          <div>
            <span className="text-slate-500 block text-[9px]">Distance</span>
            <span className="font-bold text-slate-100">{route.distanceKm} km</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[9px]">Heading</span>
            <span className="font-bold text-cyan-300">{route.bearingDegrees}°</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[9px]">ETA</span>
            <span className="font-bold text-slate-100">{route.estimatedTimeMinutes} min</span>
          </div>
        </div>

        <p className="text-[10px] text-slate-400 leading-snug font-sans">
          {route.safetyNote}
        </p>
      </div>
    </div>
  );
};
