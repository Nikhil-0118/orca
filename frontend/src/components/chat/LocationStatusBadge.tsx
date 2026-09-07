import React from 'react';
import { Navigation, Compass, AlertCircle, RefreshCw } from 'lucide-react';
import { LocationContext } from '../../types/chat.types';

interface LocationStatusBadgeProps {
  locationContext: LocationContext;
  isLocating?: boolean;
  onRequestGps: () => void;
  onSetDemo: (lat?: number, lon?: number, label?: string) => void;
  onClearDemo: () => void;
}

export const LocationStatusBadge: React.FC<LocationStatusBadgeProps> = ({
  locationContext,
  isLocating = false,
  onRequestGps,
  onSetDemo,
  onClearDemo,
}) => {
  const isDemo = locationContext.is_demo || locationContext.source === 'demo';
  const isLive = locationContext.source === 'browser_gps' && locationContext.latitude !== null;
  const isUnavailable = !isDemo && !isLive;

  return (
    <div className="orca-location-badge-container">
      {isLive && (
        <div className="orca-loc-badge orca-loc-live" title="Active live device GPS coordinate fix">
          <span className="orca-loc-dot orca-loc-dot-live" />
          <Navigation className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
          <span className="orca-loc-label">
            <strong>Live GPS:</strong> {locationContext.latitude?.toFixed(2)}°N, {locationContext.longitude?.toFixed(2)}°E
            {locationContext.accuracy_m ? ` (±${locationContext.accuracy_m}m)` : ''}
          </span>
          <button
            type="button"
            className="orca-loc-switch-btn"
            onClick={() => onSetDemo(13.0827, 80.2707, 'Chennai Coast (SIH Demo)')}
            title="Switch to SIH Demonstration Coordinates"
          >
            Switch to Demo
          </button>
        </div>
      )}

      {isDemo && (
        <div className="orca-loc-badge orca-loc-demo" title="SIH demonstration coordinates (Approximate position)">
          <span className="orca-loc-dot orca-loc-dot-demo" />
          <Compass className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
          <span className="orca-loc-label">
            <strong>Demo Mode:</strong> {locationContext.label || 'Chennai (SIH Demo)'} ({locationContext.latitude?.toFixed(2)}°, {locationContext.longitude?.toFixed(2)}°)
          </span>
          <button
            type="button"
            className="orca-loc-switch-btn"
            onClick={onClearDemo}
            title="Detect device GPS coordinates"
          >
            {isLocating ? (
              <RefreshCw className="w-3 h-3 animate-spin" aria-hidden="true" />
            ) : (
              'Use Live GPS'
            )}
          </button>
        </div>
      )}

      {isUnavailable && (
        <div className="orca-loc-badge orca-loc-unavailable" title="Live location access is unavailable">
          <span className="orca-loc-dot orca-loc-dot-unavailable" />
          <AlertCircle className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />
          <span className="orca-loc-label">
            <strong>Location Unavailable:</strong> GPS permissions not granted
          </span>
          <div className="flex items-center gap-1.5 ml-1">
            <button
              type="button"
              className="orca-loc-switch-btn"
              onClick={onRequestGps}
              title="Request browser GPS access"
            >
              {isLocating ? (
                <RefreshCw className="w-3 h-3 animate-spin" aria-hidden="true" />
              ) : (
                'Enable GPS'
              )}
            </button>
            <button
              type="button"
              className="orca-loc-switch-btn orca-loc-demo-btn"
              onClick={() => onSetDemo(13.0827, 80.2707, 'Chennai Coast (SIH Demo)')}
              title="Use SIH Chennai demo location"
            >
              Use Demo
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
