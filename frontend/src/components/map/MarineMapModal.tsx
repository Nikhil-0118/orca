import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import L from 'leaflet';
import {
  X,
  Layers,
  Navigation,
  Compass,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  MapPin,
  Anchor,
} from 'lucide-react';
import { SpatialPayload } from '../../types/chat.types';

interface MarineMapModalProps {
  spatial: SpatialPayload;
  onClose: () => void;
}

const TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL ||
  'https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png';
const TILE_ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
const TILE_SUBDOMAINS = TILE_URL.includes('cartocdn.com') ? 'abcd' : 'abc';

function createModalCustomIcon(type: string, status?: string) {
  let html = '';
  let className = 'orca-map-marker';

  if (type === 'vessel') {
    html = `
      <div class="orca-vessel-marker orca-modal-vessel">
        <div class="orca-vessel-pulse"></div>
        <div class="orca-vessel-core"></div>
      </div>
    `;
    className += ' orca-marker-vessel';
  } else if (type === 'fishing') {
    html = `
      <div class="orca-fishing-marker orca-modal-fishing" title="Recommended Fishing Spot">
        <div class="orca-fishing-pulse"></div>
        <div class="orca-fishing-icon">🎣</div>
      </div>
    `;
    className += ' orca-marker-fishing';
  } else if (type === 'waypoint') {
    html = `
      <div class="orca-waypoint-marker">
        <div class="orca-waypoint-dot"></div>
      </div>
    `;
    className += ' orca-marker-waypoint';
  } else {
    const isDanger = status === 'danger' || status === 'warning';
    const color = isDanger ? '#ef4444' : '#06b6d4';
    html = `
      <div class="orca-pin-marker" style="color: ${color};">
        <svg width="26" height="32" viewBox="0 0 24 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 0C5.37258 0 0 5.37258 0 12C0 19.5 12 30 12 30C12 30 24 19.5 24 12C24 5.37258 18.6274 0 12 0Z" fill="${color}" fill-opacity="0.95"/>
          <circle cx="12" cy="11" r="4.5" fill="#070c18"/>
        </svg>
      </div>
    `;
    className += ' orca-marker-pin';
  }

  const isVessel = type === 'vessel';
  const isFishing = type === 'fishing';
  const isWaypoint = type === 'waypoint';

  return L.divIcon({
    html,
    className,
    iconSize: isVessel ? [32, 32] : isFishing ? [36, 36] : isWaypoint ? [18, 18] : [26, 32],
    iconAnchor: isVessel ? [16, 16] : isFishing ? [18, 18] : isWaypoint ? [9, 9] : [13, 32],
    popupAnchor: [0, -30],
  });
}

export const MarineMapModal: React.FC<MarineMapModalProps> = ({ spatial, onClose }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Layer toggles
  const [showVessel, setShowVessel] = useState(true);
  const [showFishing, setShowFishing] = useState(true);
  const [showBoundaries, setShowBoundaries] = useState(true);
  const [showRoutes, setShowRoutes] = useState(true);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Leaflet map setup
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const initialCenter: [number, number] = [
      spatial.center?.latitude ?? 13.0827,
      spatial.center?.longitude ?? 80.2707,
    ];
    const initialZoom = (spatial.zoom ?? 9) + 1;

    const map = L.map(mapContainerRef.current, {
      center: initialCenter,
      zoom: initialZoom,
      minZoom: 3,
      maxZoom: 20,
      zoomControl: true,
      attributionControl: true,
    });

    L.tileLayer(TILE_URL, {
      attribution: TILE_ATTR,
      minZoom: 3,
      maxZoom: 20,
      maxNativeZoom: 19,
      subdomains: TILE_SUBDOMAINS,
    }).addTo(map);

    const bounds = L.latLngBounds([]);

    // Zones / Boundary Polylines
    if (showBoundaries && spatial.zones && spatial.zones.length > 0) {
      spatial.zones.forEach((zone) => {
        if (zone.geometry_type === 'LineString' && Array.isArray(zone.coordinates)) {
          const latLngs = zone.coordinates.map((coord: any) => [coord[1], coord[0]] as [number, number]);
          const polyline = L.polyline(latLngs, {
            color: zone.stroke_color || '#f59e0b',
            weight: 3.5,
            dashArray: '6, 10',
            opacity: zone.opacity || 0.9,
          }).addTo(map);

          polyline.bindPopup(`
            <div style="font-family: sans-serif; font-size: 12px; color: #0f172a; line-height: 1.4;">
              <strong style="color: #0284c7;">${zone.title}</strong><br/>
              <span style="color: #64748b;">${zone.description || 'Maritime Boundary Demarcation (Demo)'}</span>
            </div>
          `);
          latLngs.forEach((ll) => bounds.extend(ll));
        }
      });
    }

    // Routes
    if (showRoutes && spatial.routes && spatial.routes.length > 0) {
      spatial.routes.forEach((route) => {
        const routeLatLngs: [number, number][] = [];

        if (route.waypoints && route.waypoints.length > 0) {
          route.waypoints.forEach((wp) => {
            routeLatLngs.push([wp.latitude, wp.longitude]);
          });
        } else {
          routeLatLngs.push([route.origin.latitude, route.origin.longitude]);
          routeLatLngs.push([route.destination.latitude, route.destination.longitude]);
        }

        const isApprox = route.is_approximate || route.is_inland_warning;
        const strokeColor = isApprox ? '#f59e0b' : '#38bdf8';
        const glowColor = isApprox ? '#fbbf24' : '#00f2fe';

        // Glow
        L.polyline(routeLatLngs, {
          color: glowColor,
          weight: 8,
          opacity: 0.3,
        }).addTo(map);

        // Path
        const line = L.polyline(routeLatLngs, {
          color: strokeColor,
          weight: 3.5,
          dashArray: isApprox ? '5, 9' : '8, 8',
          opacity: 0.95,
        }).addTo(map);

        const routeTitle = isApprox ? 'Approximate Route (Overland / Reference)' : 'Marine Route';
        const etaText = route.estimated_time_minutes
          ? `~${Math.floor(route.estimated_time_minutes / 60) > 0 ? `${Math.floor(route.estimated_time_minutes / 60)}h ` : ''}${Math.round(route.estimated_time_minutes % 60)}m`
          : 'Unavailable — vessel speed not provided';

        line.bindPopup(`
          <div style="font-family: sans-serif; font-size: 12px; color: #0f172a; line-height: 1.4;">
            <strong style="color: ${isApprox ? '#d97706' : '#0284c7'};">${routeTitle}</strong><br/>
            <span>Distance: <strong>${route.distance_km} km</strong> (${route.distance_nm} NM)</span><br/>
            <span>Initial Bearing: <strong>${route.bearing_degrees}°</strong></span><br/>
            <span>ETA: <strong>${etaText}</strong></span><br/>
            <span>Destination: <strong>${route.destination.latitude.toFixed(4)}°N, ${route.destination.longitude.toFixed(4)}°E</strong></span><br/>
            <span style="font-size: 11px; color: #64748b;">${route.safety_note || ''}</span>
          </div>
        `);

        routeLatLngs.forEach((ll) => bounds.extend(ll));
      });
    }

    // Markers
    if (spatial.markers && spatial.markers.length > 0) {
      spatial.markers.forEach((marker) => {
        if (marker.marker_type === 'vessel' && !showVessel) return;
        if (marker.marker_type === 'fishing' && !showFishing) return;

        const icon = createModalCustomIcon(marker.marker_type, marker.status);
        const m = L.marker([marker.latitude, marker.longitude], { icon }).addTo(map);

        m.bindPopup(`
          <div style="font-family: sans-serif; font-size: 12px; color: #0f172a; line-height: 1.4;">
            <strong style="color: #0284c7;">${marker.label}</strong><br/>
            <span>Coordinates: ${marker.latitude.toFixed(4)}°N, ${marker.longitude.toFixed(4)}°E</span><br/>
            ${marker.description ? `<span style="color: #64748b;">${marker.description}</span>` : ''}
          </div>
        `);

        bounds.extend([marker.latitude, marker.longitude]);
      });
    }

    if (bounds.isValid() && (spatial.markers.length > 1 || (spatial.routes && spatial.routes.length > 0))) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 13 });
    }

    mapInstanceRef.current = map;

    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 60);

    const resizeObserver = new ResizeObserver(() => {
      map.invalidateSize();
    });
    if (mapContainerRef.current) {
      resizeObserver.observe(mapContainerRef.current);
    }

    return () => {
      clearTimeout(timer);
      resizeObserver.disconnect();
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [spatial, showVessel, showFishing, showBoundaries, showRoutes]);

  const safetyState = spatial.safety_state;
  const isCaution = safetyState === 'APPROACHING' || safetyState === 'WARNING';
  const isBreach = safetyState === 'BREACH';
  const primaryRoute = spatial.routes && spatial.routes.length > 0 ? spatial.routes[0] : null;

  return createPortal(
    <div
      className="orca-map-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Expanded Marine Map"
    >
      <div className="orca-map-modal-container">
        {/* Top Control Bar */}
        <div className="orca-map-modal-topbar">
          <div className="flex items-center gap-3">
            <div className="orca-topbar-logo">
              <Anchor className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="orca-modal-title">{spatial.title}</h2>
                {safetyState && (
                  <span
                    className={`orca-spatial-badge ${
                      isBreach
                        ? 'badge-breach'
                        : isCaution
                        ? 'badge-caution'
                        : 'badge-normal'
                    }`}
                  >
                    {isBreach ? (
                      <ShieldAlert className="w-3 h-3" />
                    ) : isCaution ? (
                      <AlertTriangle className="w-3 h-3" />
                    ) : (
                      <ShieldCheck className="w-3 h-3" />
                    )}
                    <span>{safetyState}</span>
                  </span>
                )}
              </div>
              <p className="orca-modal-subtitle">
                Interactive Geodesic Nautical Map · Real-time Proximity Tracking
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Layer Toggles */}
            <div className="orca-layer-toggles">
              <button
                type="button"
                className={`orca-layer-chip ${showVessel ? 'active' : ''}`}
                onClick={() => setShowVessel(!showVessel)}
                title="Toggle Vessel Marker"
              >
                <MapPin className="w-3 h-3" />
                <span>Vessel</span>
              </button>

              {spatial.markers.some((m) => m.marker_type === 'fishing') && (
                <button
                  type="button"
                  className={`orca-layer-chip ${showFishing ? 'active' : ''}`}
                  onClick={() => setShowFishing(!showFishing)}
                  title="Toggle Fishing Destination"
                >
                  <span>🎣 Fishing Spot</span>
                </button>
              )}

              <button
                type="button"
                className={`orca-layer-chip ${showBoundaries ? 'active' : ''}`}
                onClick={() => setShowBoundaries(!showBoundaries)}
                title="Toggle Maritime Boundaries"
              >
                <Layers className="w-3 h-3" />
                <span>Boundaries</span>
              </button>

              {spatial.routes && spatial.routes.length > 0 && (
                <button
                  type="button"
                  className={`orca-layer-chip ${showRoutes ? 'active' : ''}`}
                  onClick={() => setShowRoutes(!showRoutes)}
                  title="Toggle Marine Route"
                >
                  <Navigation className="w-3 h-3" />
                  <span>Route</span>
                </button>
              )}
            </div>

            {/* Close Button */}
            <button
              type="button"
              className="orca-modal-close-btn"
              onClick={onClose}
              aria-label="Close interactive map"
              title="Close map (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Inland Navigation Warning Banner */}
        {spatial.navigation_warning && (
          <div className="orca-spatial-inland-warning orca-modal-inland-warning" role="alert">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
            <div className="orca-inland-warning-content">
              {spatial.navigation_warning.split('\n\n').map((para, idx) => (
                <p key={idx} className={idx === 0 ? 'font-semibold text-amber-300' : 'mt-1 text-slate-300'}>
                  {para}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Full-Screen Map Canvas */}
        <div ref={mapContainerRef} className="orca-map-modal-canvas" />

        {/* Bottom Navigational Telemetry HUD */}
        <div className="orca-map-modal-hud">
          <div className="orca-hud-left truncate">
            <span className="orca-hud-item">
              <MapPin className="w-3.5 h-3.5 text-cyan-400" />
              <span>
                Center: {spatial.center.latitude.toFixed(4)}°N, {spatial.center.longitude.toFixed(4)}°E
              </span>
            </span>
          </div>

          <div className="orca-hud-right shrink-0">
            {spatial.boundary_distance_km !== null && spatial.boundary_distance_km !== undefined && (
              <span className="orca-hud-item">
                <Navigation className="w-3.5 h-3.5 text-cyan-400" />
                <span>Distance to Boundary: {spatial.boundary_distance_km} km</span>
              </span>
            )}
            {spatial.boundary_bearing_deg !== null && spatial.boundary_bearing_deg !== undefined && (
              <span className="orca-hud-item">
                <Compass className="w-3.5 h-3.5 text-cyan-400" />
                <span>Bearing: {spatial.boundary_bearing_deg}°</span>
              </span>
            )}
            {primaryRoute && (
              <span className="orca-hud-item text-cyan-300">
                <Navigation className="w-3.5 h-3.5 text-cyan-400" />
                <span>
                  Route: {primaryRoute.distance_km} km ({primaryRoute.distance_nm} NM) · {primaryRoute.bearing_degrees}°
                  {primaryRoute.estimated_time_minutes
                    ? ` · ETA ~${Math.floor(primaryRoute.estimated_time_minutes / 60) > 0 ? `${Math.floor(primaryRoute.estimated_time_minutes / 60)}h ` : ''}${Math.round(primaryRoute.estimated_time_minutes % 60)}m`
                    : ' · ETA: Unavailable (vessel speed not provided)'}
                </span>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};
