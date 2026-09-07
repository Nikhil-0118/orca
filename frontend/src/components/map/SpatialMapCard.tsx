import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Maximize2,
  Navigation,
  Compass,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  MapPin,
} from 'lucide-react';
import { SpatialPayload } from '../../types/chat.types';
import { MarineMapModal } from './MarineMapModal';

interface SpatialMapCardProps {
  spatial: SpatialPayload;
}

// Configurable basemap tile URL with clean fallback
const TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL ||
  'https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png';
const TILE_ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
const TILE_SUBDOMAINS = TILE_URL.includes('cartocdn.com') ? 'abcd' : 'abc';

function formatEta(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) {
    return 'Unavailable — vessel speed not provided';
  }
  const hrs = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  if (hrs > 0) {
    return `${hrs}h ${mins}m`;
  }
  return `${mins}m`;
}

/**
 * Creates custom HTML/SVG icons for Leaflet without relying on external image files.
 */
function createCustomIcon(type: string, status?: string) {
  let html = '';
  let className = 'orca-map-marker';

  if (type === 'vessel') {
    html = `
      <div class="orca-vessel-marker">
        <div class="orca-vessel-pulse"></div>
        <div class="orca-vessel-core"></div>
      </div>
    `;
    className += ' orca-marker-vessel';
  } else if (type === 'fishing') {
    html = `
      <div class="orca-fishing-marker" title="Recommended Fishing Spot">
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
        <svg width="22" height="28" viewBox="0 0 24 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 0C5.37258 0 0 5.37258 0 12C0 19.5 12 30 12 30C12 30 24 19.5 24 12C24 5.37258 18.6274 0 12 0Z" fill="${color}" fill-opacity="0.9"/>
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
    iconSize: isVessel ? [28, 28] : isFishing ? [32, 32] : isWaypoint ? [16, 16] : [24, 30],
    iconAnchor: isVessel ? [14, 14] : isFishing ? [16, 16] : isWaypoint ? [8, 8] : [12, 30],
    popupAnchor: [0, -28],
  });
}

export const SpatialMapCard: React.FC<SpatialMapCardProps> = ({ spatial }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Destroy any existing map instance on re-render
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const initialCenter: [number, number] = [
      spatial.center?.latitude ?? 13.0827,
      spatial.center?.longitude ?? 80.2707,
    ];
    const initialZoom = spatial.zoom ?? 9;

    const map = L.map(mapContainerRef.current, {
      center: initialCenter,
      zoom: initialZoom,
      minZoom: 3,
      maxZoom: 20,
      zoomControl: false,
      attributionControl: true,
      scrollWheelZoom: false, // Prevent page scroll interference in chat
      dragging: true,
      touchZoom: true,
    });

    // Add minimal zoom control to bottom right
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Add dark basemap raster tiles
    L.tileLayer(TILE_URL, {
      attribution: TILE_ATTR,
      minZoom: 3,
      maxZoom: 20,
      maxNativeZoom: 19,
      subdomains: TILE_SUBDOMAINS,
    }).addTo(map);

    const bounds = L.latLngBounds([]);

    // Render Zones / Boundary Line Strings
    if (spatial.zones && spatial.zones.length > 0) {
      spatial.zones.forEach((zone) => {
        if (zone.geometry_type === 'LineString' && Array.isArray(zone.coordinates)) {
          // GeoJSON coordinates are [lon, lat], Leaflet polyline requires [lat, lon]
          const latLngs = zone.coordinates.map((coord: any) => [coord[1], coord[0]] as [number, number]);
          const polyline = L.polyline(latLngs, {
            color: zone.stroke_color || '#f59e0b',
            weight: 2.5,
            dashArray: '5, 8',
            opacity: zone.opacity || 0.85,
          }).addTo(map);

          if (zone.title) {
            polyline.bindTooltip(zone.title, { sticky: true, className: 'orca-leaflet-tooltip' });
          }
          latLngs.forEach((ll) => bounds.extend(ll));
        }
      });
    }

    // Render Routes
    if (spatial.routes && spatial.routes.length > 0) {
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

        // Glow backdrop
        L.polyline(routeLatLngs, {
          color: glowColor,
          weight: 6,
          opacity: 0.25,
        }).addTo(map);

        // Main line
        const routeLine = L.polyline(routeLatLngs, {
          color: strokeColor,
          weight: 2.5,
          dashArray: isApprox ? '4, 8' : '6, 6',
          opacity: 0.9,
        }).addTo(map);

        const routeLabel = isApprox
          ? `Approximate Route (${route.distance_km} km / ${route.distance_nm} NM — Reference / Overland)`
          : `Marine Route (${route.distance_km} km / ${route.distance_nm} NM)`;

        routeLine.bindTooltip(routeLabel, {
          sticky: true,
          className: 'orca-leaflet-tooltip',
        });

        routeLatLngs.forEach((ll) => bounds.extend(ll));
      });
    }

    // Render Markers
    if (spatial.markers && spatial.markers.length > 0) {
      spatial.markers.forEach((marker) => {
        const icon = createCustomIcon(marker.marker_type, marker.status);
        const leafletMarker = L.marker([marker.latitude, marker.longitude], { icon }).addTo(map);

        const tooltipContent = marker.description
          ? `<strong>${marker.label}</strong><br/><span style="font-size: 10px; color: #94a3b8;">${marker.description}</span>`
          : `<strong>${marker.label}</strong>`;

        leafletMarker.bindTooltip(tooltipContent, {
          direction: 'top',
          offset: [0, -10],
          className: 'orca-leaflet-tooltip',
        });

        bounds.extend([marker.latitude, marker.longitude]);
      });
    }

    // Fit map view to bounds if multiple features exist
    if (bounds.isValid() && (spatial.markers.length > 1 || (spatial.routes && spatial.routes.length > 0))) {
      map.fitBounds(bounds, { padding: [35, 35], maxZoom: 12 });
    }

    mapInstanceRef.current = map;

    // Small delay to ensure container dimension calculation is accurate
    const resizeTimer = setTimeout(() => {
      map.invalidateSize();
    }, 60);

    const resizeObserver = new ResizeObserver(() => {
      map.invalidateSize();
    });
    if (mapContainerRef.current) {
      resizeObserver.observe(mapContainerRef.current);
    }

    return () => {
      clearTimeout(resizeTimer);
      resizeObserver.disconnect();
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [spatial]);

  const safetyState = spatial.safety_state;
  const isCaution = safetyState === 'APPROACHING' || safetyState === 'WARNING';
  const isBreach = safetyState === 'BREACH';
  const primaryRoute = spatial.routes && spatial.routes.length > 0 ? spatial.routes[0] : null;

  return (
    <>
      <div className="orca-spatial-card" aria-label="Marine Spatial Card">
        {/* Card Header */}
        <div className="orca-spatial-header">
          <div className="orca-spatial-header-left">
            <MapPin className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
            <span className="orca-spatial-title">{spatial.title}</span>
            {spatial.safety_state && (
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
                  <ShieldAlert className="w-2.5 h-2.5" />
                ) : isCaution ? (
                  <AlertTriangle className="w-2.5 h-2.5" />
                ) : (
                  <ShieldCheck className="w-2.5 h-2.5" />
                )}
                <span>{spatial.safety_state}</span>
              </span>
            )}
          </div>

          <button
            type="button"
            className="orca-spatial-expand-btn"
            onClick={() => setIsModalOpen(true)}
            aria-label="Expand interactive map"
            title="Expand into full-screen interactive marine map"
          >
            <Maximize2 className="w-3.5 h-3.5" />
            <span>Expand Map</span>
          </button>
        </div>

        {/* Inland Navigation Warning Banner */}
        {spatial.navigation_warning && (
          <div className="orca-spatial-inland-warning" role="alert">
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

        {/* Embedded Map Container */}
        <div
          ref={mapContainerRef}
          className="orca-spatial-canvas"
          role="region"
          aria-label="Interactive leaflet map preview"
        />

        {/* Route Details Box (When destination route exists) */}
        {primaryRoute && (
          <div className="orca-spatial-route-box">
            <div className="orca-route-box-header">
              <span className="font-semibold text-slate-200">🎣 Fishing Destination</span>
              {primaryRoute.is_approximate && (
                <span className="orca-route-approx-tag">Approximate Route</span>
              )}
            </div>
            <div className="orca-route-box-grid">
              <div>
                <span className="text-slate-400 text-[10px] block uppercase">Distance</span>
                <span className="text-cyan-300 font-mono font-medium text-xs">
                  {primaryRoute.distance_km} km ({primaryRoute.distance_nm} NM)
                </span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] block uppercase">Bearing</span>
                <span className="text-cyan-300 font-mono font-medium text-xs">
                  {primaryRoute.bearing_degrees}°
                </span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] block uppercase">ETA</span>
                <span className={`font-mono text-xs ${primaryRoute.estimated_time_minutes ? 'text-cyan-300 font-medium' : 'text-slate-400'}`}>
                  {formatEta(primaryRoute.estimated_time_minutes)}
                </span>
              </div>
              <div>
                <span className="text-slate-400 text-[10px] block uppercase">Coordinates</span>
                <span className="text-slate-300 font-mono text-xs">
                  {primaryRoute.destination.latitude.toFixed(4)}°N, {primaryRoute.destination.longitude.toFixed(4)}°E
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Telemetry Footer Bar */}
        <div className="orca-spatial-footer">
          <div className="orca-spatial-summary truncate">{spatial.summary}</div>
          <div className="orca-spatial-stats shrink-0">
            {spatial.boundary_distance_km !== null && spatial.boundary_distance_km !== undefined && (
              <span className="orca-stat-pill">
                <Navigation className="w-3 h-3 text-cyan-400" />
                <span>{spatial.boundary_distance_km} km to Boundary</span>
              </span>
            )}
            {spatial.boundary_bearing_deg !== null && spatial.boundary_bearing_deg !== undefined && (
              <span className="orca-stat-pill">
                <Compass className="w-3 h-3 text-cyan-400" />
                <span>{spatial.boundary_bearing_deg}°</span>
              </span>
            )}
            {primaryRoute && !spatial.boundary_distance_km && (
              <span className="orca-stat-pill orca-route-pill">
                <Navigation className="w-3 h-3 text-cyan-400" />
                <span>
                  {primaryRoute.distance_km} km ({primaryRoute.distance_nm} NM)
                </span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Full-Screen Interactive Map Modal */}
      {isModalOpen && (
        <MarineMapModal
          spatial={spatial}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </>
  );
};
