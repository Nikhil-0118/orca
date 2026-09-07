import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Play,
  Square,
  RotateCcw,
  Volume2,
  VolumeX,
  ShieldCheck,
  AlertTriangle,
  Flame,
  Compass,
  Navigation,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Maximize2,
  Minimize2,
  Sliders,
  Radio,
} from 'lucide-react';
import {
  DEMO_BOUNDARIES,
  BoundarySegment,
  SafetyLevel,
} from '../../services/offlineSafetyService';
import { buzzerService, BuzzerState } from '../../services/buzzerService';
import { useOfflineSafety, PRESET_LOCATIONS, LocationPreset } from '../../hooks/useOfflineSafety';

interface OfflineBoatSafetySimulatorProps {
  safetyHook: ReturnType<typeof useOfflineSafety>;
}

// Basemap tile configuration matching ORCA's dark ocean theme
const TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL ||
  'https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png';
const TILE_ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
const TILE_SUBDOMAINS = TILE_URL.includes('cartocdn.com') ? 'abcd' : 'abc';

function getBoatDivIcon(level: SafetyLevel) {
  let pulseClass = 'orca-sim-pulse-safe';
  let boatClass = 'orca-sim-boat-safe';
  let glyph = '⛵';

  if (level === 'DANGER') {
    pulseClass = 'orca-sim-pulse-danger';
    boatClass = 'orca-sim-boat-danger';
    glyph = '🚨';
  } else if (level === 'CAUTION') {
    pulseClass = 'orca-sim-pulse-caution';
    boatClass = 'orca-sim-boat-caution';
    glyph = '⚠️';
  }

  const html = `
    <div class="orca-sim-boat-container">
      <div class="orca-sim-pulse ${pulseClass}"></div>
      <div class="orca-sim-boat-icon ${boatClass}" title="Draggable Boat Marker (Drag me!)">
        <span>${glyph}</span>
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: 'orca-sim-marker',
    iconSize: [44, 44],
    iconAnchor: [22, 22],
    popupAnchor: [0, -22],
  });
}

/**
 * In-place styling update for the boat marker.
 *
 * CRITICAL: Never call marker.setIcon() during continuous marker dragging!
 * setIcon() in Leaflet removes and recreates the marker's DOM element (_icon),
 * which destroys active browser pointer/touch capture and immediately aborts the drag!
 *
 * Modifying existing classNames and glyph text in-place guarantees zero DOM
 * recreation, uninterrupted mouse/touch capture, and continuous 60fps dragging.
 */
function updateMarkerVisual(marker: L.Marker, level: SafetyLevel) {
  const el = marker.getElement();
  if (!el) return;

  const pulseEl = el.querySelector<HTMLDivElement>('.orca-sim-pulse');
  const boatIconEl = el.querySelector<HTMLDivElement>('.orca-sim-boat-icon');
  const spanEl = el.querySelector<HTMLSpanElement>('.orca-sim-boat-icon span');

  let pulseClass = 'orca-sim-pulse orca-sim-pulse-safe';
  let boatClass = 'orca-sim-boat-safe';
  let glyph = '⛵';

  if (level === 'DANGER') {
    pulseClass = 'orca-sim-pulse orca-sim-pulse-danger';
    boatClass = 'orca-sim-boat-danger';
    glyph = '🚨';
  } else if (level === 'CAUTION') {
    pulseClass = 'orca-sim-pulse orca-sim-pulse-caution';
    boatClass = 'orca-sim-boat-caution';
    glyph = '⚠️';
  }

  if (pulseEl && pulseEl.className !== pulseClass) {
    pulseEl.className = pulseClass;
  }
  if (boatIconEl) {
    const expectedClass = `orca-sim-boat-icon ${boatClass}`;
    if (boatIconEl.className !== expectedClass) {
      boatIconEl.className = expectedClass;
    }
  }
  if (spanEl && spanEl.textContent !== glyph) {
    spanEl.textContent = glyph;
  }
}

export const OfflineBoatSafetySimulator: React.FC<OfflineBoatSafetySimulatorProps> = ({
  safetyHook,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const boatMarkerRef = useRef<L.Marker | null>(null);
  const vectorLineRef = useRef<L.Polyline | null>(null);
  const dangerCorridorRef = useRef<L.Polygon | null>(null);
  const isDraggingRef = useRef<boolean>(false);

  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [showConfig, setShowConfig] = useState<boolean>(false);
  const [buzzerState, setBuzzerState] = useState<BuzzerState>(() => buzzerService.getState());

  const {
    latitude,
    longitude,
    stepSize,
    setStepSize,
    isSimulatorRunning,
    setIsSimulatorRunning,
    cautionThresholdKm,
    setCautionThresholdKm,
    dangerThresholdKm,
    setDangerThresholdKm,
    evaluation,
    updatePosition,
    loadPreset,
    resetBoat,
    moveNorth,
    moveSouth,
    moveEast,
    moveWest,
  } = safetyHook;

  // Listen to audio buzzer state changes
  useEffect(() => {
    const unsubscribe = buzzerService.subscribe((state) => {
      setBuzzerState(state);
    });
    return unsubscribe;
  }, []);

  // Handle user enabling audio or toggling mute
  const handleToggleAudio = async () => {
    if (!buzzerState.isAudioUnlocked) {
      await buzzerService.unlockAudio();
    }
    buzzerService.toggleMute();
  };

  const handleUnlockAudio = async () => {
    await buzzerService.unlockAudio();
  };

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const initialCenter: [number, number] = [latitude, longitude];
    const map = L.map(mapContainerRef.current, {
      center: initialCenter,
      zoom: 10,
      minZoom: 4,
      maxZoom: 18,
      zoomControl: false,
      attributionControl: true,
      dragging: true,
      touchZoom: true,
      scrollWheelZoom: true,
    });

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    L.tileLayer(TILE_URL, {
      attribution: TILE_ATTR,
      minZoom: 4,
      maxZoom: 18,
      subdomains: TILE_SUBDOMAINS,
    }).addTo(map);

    // Render Boundary Polylines (India-Sri Lanka IMBL and West Coast EEZ)
    const bounds = L.latLngBounds([]);

    DEMO_BOUNDARIES.forEach((boundary: BoundarySegment) => {
      // Coords are [lon, lat] in GeoJSON -> convert to [lat, lon] for Leaflet
      const latLngs = boundary.coordinates.map(
        (c) => [c[1], c[0]] as [number, number]
      );

      // Outer Danger buffer line
      L.polyline(latLngs, {
        color: '#ef4444',
        weight: 3.5,
        dashArray: '8, 6',
        opacity: 0.9,
      })
        .addTo(map)
        .bindTooltip(`🚨 ${boundary.name} (Restricted Maritime Boundary)`, {
          sticky: true,
          className: 'orca-leaflet-tooltip',
        });

      latLngs.forEach((ll) => bounds.extend(ll));
    });

    // Create semi-transparent danger buffer polygon around IMBL sample
    const imblCoords = DEMO_BOUNDARIES[0].coordinates.map(
      (c) => [c[1], c[0]] as [number, number]
    );
    if (imblCoords.length > 0) {
      // Create offset buffer for visual danger corridor
      const corridorEast = imblCoords.map(
        ([lat, lon]) => [lat + 0.05, lon + 0.08] as [number, number]
      );
      const corridorWest = [...imblCoords]
        .reverse()
        .map(([lat, lon]) => [lat - 0.05, lon - 0.08] as [number, number]);
      const corridorPolygon = [...corridorEast, ...corridorWest];

      dangerCorridorRef.current = L.polygon(corridorPolygon, {
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.08,
        weight: 1,
        dashArray: '4, 8',
      }).addTo(map);
    }

    // Draggable Boat Marker
    const boatMarker = L.marker([latitude, longitude], {
      draggable: true,
      icon: getBoatDivIcon(evaluation.level),
      zIndexOffset: 1000,
      autoPan: true,
    }).addTo(map);

    boatMarker.bindTooltip('<b>Vessel (Draggable)</b><br/>Drag anywhere to test safety engine', {
      permanent: false,
      direction: 'top',
      offset: [0, -22],
    });

    // Handle marker drag in real-time
    boatMarker.on('dragstart', async () => {
      isDraggingRef.current = true;
      boatMarker.closeTooltip();
      // Automatically attempt to unlock audio on first interaction
      if (!buzzerService.getState().isAudioUnlocked) {
        await buzzerService.unlockAudio();
      }
    });

    boatMarker.on('drag', (e: L.LeafletEvent) => {
      const target = e.target as L.Marker;
      const pos = target.getLatLng();
      updatePosition(pos.lat, pos.lng);
    });

    boatMarker.on('dragend', (e: L.LeafletEvent) => {
      isDraggingRef.current = false;
      const target = e.target as L.Marker;
      const pos = target.getLatLng();
      updatePosition(pos.lat, pos.lng);
    });

    boatMarkerRef.current = boatMarker;

    // Vector line connecting boat to closest point on danger boundary
    if (evaluation.nearestPoint) {
      const vectorLine = L.polyline(
        [
          [latitude, longitude],
          [evaluation.nearestPoint[0], evaluation.nearestPoint[1]],
        ],
        {
          color: evaluation.level === 'DANGER' ? '#ef4444' : evaluation.level === 'CAUTION' ? '#f59e0b' : '#10b981',
          weight: 2,
          dashArray: '4, 4',
          opacity: 0.85,
        }
      ).addTo(map);
      vectorLineRef.current = vectorLine;
    }

    // Fit map bounds initially to include boat and nearest boundary
    if (bounds.isValid()) {
      bounds.extend([latitude, longitude]);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 11 });
    }

    mapInstanceRef.current = map;

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []); // Run once on mount

  // Update Boat Marker position, styling, and connecting vector line on coordinate/level changes
  useEffect(() => {
    if (!boatMarkerRef.current || !mapInstanceRef.current) return;

    // Update marker position ONLY if coordinates changed externally (e.g. D-pad or preset),
    // NEVER when the user is actively dragging (Leaflet already moves marker natively during drag)
    if (!isDraggingRef.current) {
      const currentLatLng = boatMarkerRef.current.getLatLng();
      if (
        Math.abs(currentLatLng.lat - latitude) > 0.0001 ||
        Math.abs(currentLatLng.lng - longitude) > 0.0001
      ) {
        boatMarkerRef.current.setLatLng([latitude, longitude]);
      }
    }

    // Update boat marker styling IN-PLACE without recreating the DOM element!
    // Never call setIcon() during drag, as it destroys the DOM node and breaks the active drag event!
    updateMarkerVisual(boatMarkerRef.current, evaluation.level);

    // Update connecting geodesic vector line
    if (evaluation.nearestPoint) {
      const lineColor =
        evaluation.level === 'DANGER'
          ? '#ef4444'
          : evaluation.level === 'CAUTION'
          ? '#f59e0b'
          : '#10b981';

      const linePoints: [number, number][] = [
        [latitude, longitude],
        [evaluation.nearestPoint[0], evaluation.nearestPoint[1]],
      ];

      if (vectorLineRef.current) {
        vectorLineRef.current.setLatLngs(linePoints);
        vectorLineRef.current.setStyle({ color: lineColor });
      } else {
        vectorLineRef.current = L.polyline(linePoints, {
          color: lineColor,
          weight: 2,
          dashArray: '4, 4',
          opacity: 0.85,
        }).addTo(mapInstanceRef.current);
      }
    }
  }, [latitude, longitude, evaluation.level, evaluation.nearestPoint]);

  // Handle map resizing when modal expands/collapses
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const timer = setTimeout(() => {
      mapInstanceRef.current?.invalidateSize();
    }, 200);
    return () => clearTimeout(timer);
  }, [isExpanded]);

  // Recenter map on boat
  const handleRecenter = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([latitude, longitude], 11, { animate: true });
    }
  };

  // Reset boat position and center map
  const handleResetBoat = () => {
    resetBoat();
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([9.45, 79.20], 10, { animate: true });
    }
  };

  // Load preset position and pan map
  const handleLoadPreset = (preset: LocationPreset) => {
    loadPreset(preset);
    if (mapInstanceRef.current) {
      mapInstanceRef.current.panTo([preset.latitude, preset.longitude], { animate: true });
    }
  };

  // Determine Level Card Styles
  const getLevelDisplay = () => {
    switch (evaluation.level) {
      case 'DANGER':
        return {
          title: 'DANGER ZONE BREACH',
          subtitle: '🚨 Immediate Border Proximity — Emergency Alarm Active',
          badgeBg: 'bg-red-950/80',
          badgeBorder: 'border-red-500/70',
          textColor: 'text-red-400',
          icon: Flame,
          pulse: 'animate-pulse',
        };
      case 'CAUTION':
        return {
          title: 'CAUTION: APPROACHING BOUNDARY',
          subtitle: '⚠️ Warning Buffer — Approaching Restricted Maritime Boundary',
          badgeBg: 'bg-amber-950/80',
          badgeBorder: 'border-amber-500/70',
          textColor: 'text-amber-400',
          icon: AlertTriangle,
          pulse: '',
        };
      default:
        return {
          title: 'SAFE NAVIGATIONAL SECTOR',
          subtitle: 'Nominal Indian Waters — Sector Clear',
          badgeBg: 'bg-emerald-950/80',
          badgeBorder: 'border-emerald-500/70',
          textColor: 'text-emerald-400',
          icon: ShieldCheck,
          pulse: '',
        };
    }
  };

  const levelInfo = getLevelDisplay();

  return (
    <div className="flex flex-col space-y-4 text-slate-100">
      {/* Simulator Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-2xl bg-[#070c18] border border-cyan-500/30">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-cyan-300">
            <Radio className="w-4 h-4 animate-pulse text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-300">
                NavIC Offline Safety Simulation
              </span>
              <span className="px-1.5 py-0.2 rounded text-[9px] font-mono uppercase bg-cyan-950 text-cyan-400 border border-cyan-800">
                SIH Demo
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Drag boat marker toward the red maritime boundary line to trigger real-time warning & buzzer.
            </p>
          </div>
        </div>

        {/* Action Controls (Simulator Start/Stop, Reset, Audio, Expand) */}
        <div className="flex items-center gap-2">
          {/* Simulator Start / Stop */}
          <button
            type="button"
            onClick={() => setIsSimulatorRunning(!isSimulatorRunning)}
            className={`px-3 py-1.5 rounded-xl text-xs font-mono font-semibold flex items-center gap-1.5 transition-all ${
              isSimulatorRunning
                ? 'bg-emerald-600/90 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/50'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
            }`}
            title={isSimulatorRunning ? 'Pause Simulator Evaluation' : 'Resume Simulator Evaluation'}
          >
            {isSimulatorRunning ? (
              <>
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>Sim Active</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Sim Paused</span>
              </>
            )}
          </button>

          {/* Reset Boat Position */}
          <button
            type="button"
            onClick={handleResetBoat}
            className="px-3 py-1.5 rounded-xl text-xs font-mono font-semibold bg-slate-800 hover:bg-cyan-600 hover:text-white text-slate-300 border border-slate-700 transition-all flex items-center gap-1.5 shadow-sm"
            title="Reset boat back to Safe Harbor"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Boat</span>
          </button>

          {/* Audio Buzzer Control */}
          <button
            type="button"
            onClick={handleToggleAudio}
            className={`px-3 py-1.5 rounded-xl text-xs font-mono font-semibold flex items-center gap-1.5 transition-all ${
              buzzerState.isAlarmActive && !buzzerState.isMuted
                ? 'bg-red-600 hover:bg-red-500 text-white animate-pulse shadow-lg shadow-red-900/60 orca-sim-alarm-badge-active'
                : buzzerState.isMuted
                ? 'bg-slate-800 text-slate-400 border border-slate-700 hover:text-slate-200'
                : 'bg-cyan-950/80 text-cyan-300 border border-cyan-700 hover:bg-cyan-900'
            }`}
            title={buzzerState.isMuted ? 'Unmute Audio Alarm' : 'Mute Audio Alarm'}
          >
            {buzzerState.isMuted ? (
              <>
                <VolumeX className="w-3.5 h-3.5" />
                <span>Muted</span>
              </>
            ) : (
              <>
                <Volume2 className="w-3.5 h-3.5" />
                <span>{buzzerState.isAlarmActive ? '🚨 BUZZER ON' : 'Audio Ready'}</span>
              </>
            )}
          </button>

          {/* Config thresholds button */}
          <button
            type="button"
            onClick={() => setShowConfig(!showConfig)}
            className={`p-2 rounded-xl transition-colors ${
              showConfig ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title="Configure Thresholds"
          >
            <Sliders className="w-4 h-4" />
          </button>

          {/* Expand / Minimize Map Toggle */}
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            title={isExpanded ? 'Collapse Map' : 'Expand Map'}
          >
            {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Autoplay restriction warning banner if browser blocked audio */}
      {!buzzerState.isAudioUnlocked && (
        <div className="flex items-center justify-between p-2.5 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-200 text-xs font-mono">
          <div className="flex items-center gap-2">
            <Volume2 className="w-4 h-4 text-amber-400 shrink-0" />
            <span>Browser audio is currently suspended. Click to enable sound for the demo buzzer:</span>
          </div>
          <button
            type="button"
            onClick={handleUnlockAudio}
            className="px-2.5 py-1 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-[11px] transition-colors shadow"
          >
            Enable Alarm Sound
          </button>
        </div>
      )}

      {/* Configurable Thresholds Drawer */}
      {showConfig && (
        <div className="p-3.5 rounded-2xl bg-[#070c18] border border-cyan-500/40 flex flex-wrap items-center justify-between gap-4 text-xs font-mono animate-in fade-in">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-amber-400 font-bold">Caution Threshold:</span>
              <input
                type="number"
                min="1"
                max="50"
                step="1"
                value={cautionThresholdKm}
                onChange={(e) => setCautionThresholdKm(Number(e.target.value) || 15)}
                className="w-16 px-2 py-1 bg-slate-900 border border-slate-700 rounded text-slate-100 text-center"
              />
              <span className="text-slate-400">km</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-red-400 font-bold">Danger Threshold:</span>
              <input
                type="number"
                min="0.5"
                max="30"
                step="0.5"
                value={dangerThresholdKm}
                onChange={(e) => setDangerThresholdKm(Number(e.target.value) || 5)}
                className="w-16 px-2 py-1 bg-slate-900 border border-slate-700 rounded text-slate-100 text-center"
              />
              <span className="text-slate-400">km</span>
            </div>
          </div>

          <span className="text-[10px] text-slate-400">
            Current: SAFE (&gt;{cautionThresholdKm}km) &rarr; CAUTION ({dangerThresholdKm}–{cautionThresholdKm}km) &rarr; DANGER (&le;{dangerThresholdKm}km)
          </span>
        </div>
      )}

      {/* Interactive Leaflet Simulator Map */}
      <div
        className={`relative w-full rounded-2xl overflow-hidden border border-slate-800 transition-all duration-300 shadow-2xl ${
          isExpanded ? 'h-[500px]' : 'h-[360px]'
        }`}
      >
        <div ref={mapContainerRef} className="w-full h-full bg-[#050b14]" />

        {/* Live HUD Telemetry Overlay on Map (Top-Left) */}
        <div className="absolute top-3 left-3 z-[400] max-w-[280px] p-3 rounded-xl bg-slate-950/85 backdrop-blur-md border border-cyan-500/30 text-xs font-mono shadow-xl space-y-1.5 pointer-events-auto">
          <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
              Vessel Telemetry
            </span>
            <span
              className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                evaluation.level === 'DANGER'
                  ? 'bg-red-950 text-red-400 border border-red-700'
                  : evaluation.level === 'CAUTION'
                  ? 'bg-amber-950 text-amber-400 border border-amber-700'
                  : 'bg-emerald-950 text-emerald-400 border border-emerald-700'
              }`}
            >
              {evaluation.level}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300 pt-1">
            <div>
              <span className="text-[9px] text-slate-500 block">LAT</span>
              <span className="font-bold text-slate-200">{latitude.toFixed(4)}° N</span>
            </div>
            <div>
              <span className="text-[9px] text-slate-500 block">LON</span>
              <span className="font-bold text-slate-200">{longitude.toFixed(4)}° E</span>
            </div>
            <div>
              <span className="text-[9px] text-slate-500 block">BORDER DISTANCE</span>
              <span
                className={`font-bold ${
                  evaluation.level === 'DANGER'
                    ? 'text-red-400'
                    : evaluation.level === 'CAUTION'
                    ? 'text-amber-400'
                    : 'text-cyan-400'
                }`}
              >
                {evaluation.distanceToBoundaryKm.toFixed(2)} km
              </span>
            </div>
            <div>
              <span className="text-[9px] text-slate-500 block">BEARING</span>
              <span className="font-bold text-slate-200 flex items-center gap-1">
                <Compass className="w-3 h-3 text-cyan-400" />
                {evaluation.bearingDegrees}°
              </span>
            </div>
          </div>
        </div>

        {/* Map Recenter button (Bottom-Left) */}
        <button
          type="button"
          onClick={handleRecenter}
          className="absolute bottom-3 left-3 z-[400] px-2.5 py-1.5 rounded-xl bg-slate-950/85 backdrop-blur-md border border-cyan-500/30 text-[11px] font-mono text-cyan-300 hover:bg-cyan-950 hover:text-white transition-colors flex items-center gap-1.5 shadow-lg"
          title="Recenter map on boat"
        >
          <Navigation className="w-3.5 h-3.5 text-cyan-400" />
          <span>Center Boat</span>
        </button>
      </div>

      {/* Prominent Warning Status Banner */}
      <div
        className={`p-4 rounded-2xl border transition-all ${levelInfo.badgeBg} ${levelInfo.badgeBorder}`}
      >
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            <levelInfo.icon className={`w-5 h-5 ${levelInfo.textColor} ${levelInfo.pulse}`} />
            <span className={`text-sm font-mono font-bold tracking-wide uppercase ${levelInfo.textColor}`}>
              {levelInfo.title}
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            Nearest: {evaluation.nearestBoundaryName}
          </span>
        </div>

        <p className="text-xs text-slate-200 leading-relaxed font-sans">
          {evaluation.alertMessage}
        </p>

        {evaluation.level === 'DANGER' && (
          <div className="mt-2.5 flex items-center justify-between text-xs font-mono font-bold text-red-300 bg-red-900/40 p-2 rounded-xl border border-red-700/50">
            <span className="flex items-center gap-1.5">
              <Volume2 className="w-4 h-4 text-red-400 animate-pulse" />
              BUZZER ALARM ACTIVE — Vessel inside danger perimeter (&le; {dangerThresholdKm} km)
            </span>
            <span>Return to Indian Waters</span>
          </div>
        )}
      </div>

      {/* Control Grid: D-Pad Nudge Controls & Test Location Presets */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Precision D-Pad Arrow Controls */}
        <div className="p-4 rounded-2xl bg-[#070c18] border border-slate-800 flex flex-col items-center">
          <div className="flex items-center justify-between w-full mb-3">
            <span className="text-xs font-bold text-slate-300">Vessel Directional Controls</span>
            {/* Step Size Selector */}
            <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
              {[
                { label: '0.01° (1km)', val: 0.01 },
                { label: '0.05° (5km)', val: 0.05 },
                { label: '0.10° (11km)', val: 0.1 },
              ].map((s) => (
                <button
                  key={s.val}
                  type="button"
                  onClick={() => setStepSize(s.val)}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                    stepSize === s.val
                      ? 'bg-cyan-600 text-white font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* D-Pad Buttons */}
          <div className="grid grid-cols-3 gap-2 w-44 my-1">
            <div />
            <button
              type="button"
              onClick={moveNorth}
              className="p-3 rounded-xl bg-slate-800 hover:bg-cyan-600 text-slate-200 hover:text-white transition-all flex items-center justify-center active:scale-95 shadow-md"
              title="Move North (+Lat)"
            >
              <ArrowUp className="w-5 h-5" />
            </button>
            <div />

            <button
              type="button"
              onClick={moveWest}
              className="p-3 rounded-xl bg-slate-800 hover:bg-cyan-600 text-slate-200 hover:text-white transition-all flex items-center justify-center active:scale-95 shadow-md"
              title="Move West (-Lon)"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-700/50 flex items-center justify-center">
              <Navigation className="w-4 h-4 text-cyan-400" />
            </div>
            <button
              type="button"
              onClick={moveEast}
              className="p-3 rounded-xl bg-slate-800 hover:bg-cyan-600 text-slate-200 hover:text-white transition-all flex items-center justify-center active:scale-95 shadow-md"
              title="Move East (+Lon)"
            >
              <ArrowRight className="w-5 h-5" />
            </button>

            <div />
            <button
              type="button"
              onClick={moveSouth}
              className="p-3 rounded-xl bg-slate-800 hover:bg-cyan-600 text-slate-200 hover:text-white transition-all flex items-center justify-center active:scale-95 shadow-md"
              title="Move South (-Lat)"
            >
              <ArrowDown className="w-5 h-5" />
            </button>
            <div />
          </div>

          <span className="text-[10px] font-mono text-slate-500 mt-2">
            Click arrows to nudge vessel coordinates
          </span>
        </div>

        {/* Quick Location Presets */}
        <div className="p-4 rounded-2xl bg-[#070c18] border border-slate-800 flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-300">Quick Scenario Presets</span>
            <span className="text-[10px] font-mono text-cyan-400">SIH Demo Shortcuts</span>
          </div>
          <div className="space-y-2 flex-1 overflow-y-auto max-h-48 pr-1">
            {PRESET_LOCATIONS.map((preset: LocationPreset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => handleLoadPreset(preset)}
                className="w-full text-left p-2.5 rounded-xl bg-slate-900/80 hover:bg-cyan-950/60 border border-slate-800/80 hover:border-cyan-500/40 transition-all flex items-start justify-between gap-2"
              >
                <div>
                  <div className="text-xs font-semibold text-slate-200">{preset.name}</div>
                  <p className="text-[11px] text-slate-400">{preset.description}</p>
                </div>
                <span
                  className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase font-bold shrink-0 ${
                    preset.expectedState === 'BREACH' || preset.expectedState === 'WARNING'
                      ? 'bg-red-950 text-red-400 border border-red-800'
                      : preset.expectedState === 'APPROACHING'
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  }`}
                >
                  {preset.expectedState}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
