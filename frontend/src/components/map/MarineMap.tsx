import React, { useState } from 'react';
import { Layers, MapPin, Navigation, Crosshair } from 'lucide-react';
import { ActiveRoute, DangerZone, DestinationPoint, FishingZone, VesselLocationState } from '../../types/map.types';
import { DangerZoneLayer } from './DangerZoneLayer';
import { FishingZoneLayer } from './FishingZoneLayer';
import { LiveLocationMarker } from './LiveLocationMarker';
import { RouteLayer } from './RouteLayer';
import { INITIAL_DESTINATIONS, createMarineRoute } from '../../store/marineMapStore';

interface MarineMapProps {
  vesselLocation: VesselLocationState | null;
  selectedDestination?: DestinationPoint | null;
  activeRoute?: ActiveRoute | null;
  fishingZones?: FishingZone[];
  dangerZones?: DangerZone[];
  onDestinationSelect?: (destination: DestinationPoint) => void;
}

export const MarineMap: React.FC<MarineMapProps> = ({
  vesselLocation,
  selectedDestination,
  activeRoute: initialActiveRoute,
  fishingZones = [],
  dangerZones = [],
  onDestinationSelect,
}) => {
  const [showPfz, setShowPfz] = useState(true);
  const [showDanger, setShowDanger] = useState(true);
  const [showRoute, setShowRoute] = useState(true);

  // Compute active route if selected destination exists and no external route provided
  const currentCoords = vesselLocation?.coordinates || { latitude: 13.0827, longitude: 80.2707 };
  const currentRoute =
    initialActiveRoute ||
    (selectedDestination ? createMarineRoute(currentCoords, selectedDestination, vesselLocation?.speed_knots || 6.5) : null);

  const handleSelectDest = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const destId = e.target.value;
    if (!destId) return;
    const found = INITIAL_DESTINATIONS.find((d) => d.id === destId);
    if (found && onDestinationSelect) {
      onDestinationSelect(found);
    }
  };

  return (
    <div className="relative w-full h-full bg-[#020a17] overflow-hidden flex flex-col select-none">
      {/* Top Location & Destination Controls Toolbar */}
      <div className="absolute top-3 left-3 right-3 z-30 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        {/* Left: Destination Selector */}
        <div className="flex items-center gap-2 bg-navy-950/90 backdrop-blur-md p-1.5 rounded-2xl border border-slate-800 shadow-2xl pointer-events-auto">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono text-cyan-300">
            <Crosshair className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span className="hidden sm:inline">Nav Destination:</span>
          </div>

          <select
            value={selectedDestination?.id || ''}
            onChange={handleSelectDest}
            aria-label="Select marine destination"
            className="bg-navy-900/90 text-slate-100 text-xs font-mono px-3 py-1.5 rounded-xl border border-cyan-800/60 focus:border-cyan-400 focus:outline-none cursor-pointer"
          >
            <option value="">-- Choose Marine Destination --</option>
            {INITIAL_DESTINATIONS.map((dest) => (
              <option key={dest.id} value={dest.id}>
                {dest.name} ({dest.type.toUpperCase()})
              </option>
            ))}
          </select>
        </div>

        {/* Right: Layer Toggles */}
        <div className="flex items-center gap-1.5 bg-navy-950/90 backdrop-blur-md p-1.5 rounded-2xl border border-slate-800 shadow-2xl pointer-events-auto">
          <button
            onClick={() => setShowRoute(!showRoute)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-mono transition-all ${
              showRoute ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 shadow-xs' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            <Navigation className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Route Line</span>
          </button>

          <button
            onClick={() => setShowPfz(!showPfz)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-mono transition-all ${
              showPfz ? 'bg-emerald-950 text-emerald-300 border border-emerald-700/50 shadow-xs' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">PFZ Zones</span>
          </button>

          <button
            onClick={() => setShowDanger(!showDanger)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-mono transition-all ${
              showDanger ? 'bg-red-950 text-red-300 border border-red-700/50 shadow-xs' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Danger Zones</span>
          </button>
        </div>
      </div>

      {/* Geospatial Map Canvas / Tile Grid Simulation */}
      <div className="relative flex-1 w-full h-full bg-[radial-gradient(#0c2344_1px,transparent_1px)] [background-size:28px_28px] overflow-hidden">
        {/* Subtle Map Bathymetric Swell Rings */}
        <div className="absolute inset-0 opacity-15 pointer-events-none">
          <svg className="w-full h-full">
            <circle cx="45%" cy="50%" r="280" fill="none" stroke="#00f2fe" strokeWidth="1" strokeDasharray="4 8" />
            <circle cx="45%" cy="50%" r="420" fill="none" stroke="#00f2fe" strokeWidth="1" strokeDasharray="6 12" />
          </svg>
        </div>

        {/* Overlays */}
        <FishingZoneLayer zones={fishingZones} visible={showPfz} />
        <DangerZoneLayer zones={dangerZones} visible={showDanger} />
        <RouteLayer route={currentRoute} visible={showRoute} />
        <LiveLocationMarker location={vesselLocation} />

        {/* IMBL Prohibited Border Visual Demarcation */}
        <div className="absolute top-0 bottom-0 left-[82%] w-0.5 border-r-2 border-dashed border-amber-500/50 pointer-events-none z-10">
          <span className="absolute top-12 -left-28 text-[9px] font-mono text-amber-400 bg-navy-950/90 px-2 py-0.5 rounded border border-amber-800/60 shadow">
            IMBL Maritime Border
          </span>
        </div>
      </div>

      {/* Bottom Map Status Bar */}
      <div className="h-9 bg-navy-950/95 border-t border-slate-800/90 px-4 flex items-center justify-between text-[11px] font-mono text-slate-400">
        <div className="flex items-center gap-2 truncate">
          <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span className="truncate">
            Vessel: {currentCoords.latitude.toFixed(4)}°N, {currentCoords.longitude.toFixed(4)}°E (Speed: {vesselLocation?.speed_knots?.toFixed(1) || '6.2'} kts)
          </span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-emerald-400 font-semibold hidden md:inline">IMBL: 28.5 km Clear</span>
          <span className="text-slate-500 hidden sm:inline">|</span>
          <span className="text-slate-400">ISRO MOSDAC & INCOIS Active</span>
        </div>
      </div>
    </div>
  );
};

