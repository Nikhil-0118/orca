import React from 'react';
import { Navigation } from 'lucide-react';
import { VesselLocationState } from '../../types/map.types';

interface LiveLocationMarkerProps {
  location: VesselLocationState | null;
}

export const LiveLocationMarker: React.FC<LiveLocationMarkerProps> = ({ location }) => {
  if (!location) return null;

  return (
    <div
      className="absolute transform -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-auto cursor-pointer"
      style={{ top: '50%', left: '50%' }}
    >
      {/* Pulse Beacon */}
      <div className="relative flex items-center justify-center">
        <span className="animate-ping absolute inline-flex h-10 w-10 rounded-full bg-cyan-400 opacity-40"></span>
        <div className="w-8 h-8 rounded-full bg-navy-950 border-2 border-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-500/50">
          <Navigation
            className="w-4 h-4 text-cyan-400 transform"
            style={{ transform: `rotate(${location.heading_degrees}deg)` }}
          />
        </div>
      </div>

      {/* Telemetry pill */}
      <div className="absolute top-10 left-1/2 -translate-x-1/2 whitespace-nowrap bg-navy-950/90 border border-cyan-800/80 px-2 py-0.5 rounded text-[10px] font-mono text-cyan-300 shadow">
        {location.speed_knots.toFixed(1)} kts | {location.coordinates.latitude.toFixed(4)}°N
      </div>
    </div>
  );
};
