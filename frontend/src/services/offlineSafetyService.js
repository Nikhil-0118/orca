/**
 * ORCA Client-Side Offline Safety & Geofencing Engine (Phase 7).
 *
 * Runs 100% locally in the browser with ZERO network calls and ZERO external dependencies.
 * Evaluates vessel coordinates against loaded demo boundary line segments.
 */

// ── Thresholds in Kilometers ──────────────────────────────────────────────
export const THRESHOLD_APPROACHING_KM = 15.0;
export const THRESHOLD_WARNING_KM = 5.0;
export const THRESHOLD_BREACH_KM = 0.0;

// Hysteresis buffer gaps to prevent state flapping near borders
export const HYSTERESIS_NORMAL_RECOVERY_KM = 1.0;     // > 16.0 km to return to NORMAL
export const HYSTERESIS_APPROACHING_RECOVERY_KM = 1.0; // > 6.0 km to return to APPROACHING
export const HYSTERESIS_WARNING_RECOVERY_KM = 0.5;     // > 0.5 km to return to WARNING

export const DEMO_DISCLAIMER_WARNING =
  'DEMO ONLY / APPROXIMATE / NOT FOR NAVIGATION — Coordinates in this dataset are sample approximations for demonstration purposes only.';

// ── Canonical Demo Boundary Geometry (matches imbl_boundary_sample.geojson) ──
export const DEMO_BOUNDARIES = [
  {
    id: 'IMBL_DEMO_SEGMENT_01',
    name: 'India-Sri Lanka Maritime Demo Boundary',
    coordinates: [
      [79.04, 9.1],
      [79.22, 9.2167],
      [79.5333, 9.3667],
      [79.8, 9.6667],
      [80.05, 9.9833],
      [80.3333, 10.0833],
      [80.5, 10.5],
    ],
  },
  {
    id: 'EEZ_DEMO_WEST_COAST',
    name: 'India West Coast EEZ Demo Sample',
    coordinates: [
      [68.5, 23.5],
      [68.0, 21.0],
      [69.0, 19.0],
      [70.5, 17.0],
      [72.0, 14.0],
      [73.5, 10.0],
      [75.0, 7.5],
    ],
  },
];

/**
 * Calculates Great-Circle distance between two coordinates in kilometers.
 */
export function haversineDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371.0; // Earth mean radius in km
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const deltaPhi = ((lat2 - lat1) * Math.PI) / 180;
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Calculates minimum distance from a point to a line segment in kilometers.
 * Returns [distanceKm, projLat, projLon].
 */
export function pointToSegmentDistanceKm(plat, plon, lat1, lon1, lat2, lon2) {
  const dx = lon2 - lon1;
  const dy = lat2 - lat1;

  if (dx === 0 && dy === 0) {
    return [haversineDistanceKm(plat, plon, lat1, lon1), lat1, lon1];
  }

  let t = ((plon - lon1) * dx + (plat - lat1) * dy) / (dx * dx + dy * dy);
  t = Math.max(0, Math.min(1, t));

  const projLon = lon1 + t * dx;
  const projLat = lat1 + t * dy;
  const dist = haversineDistanceKm(plat, plon, projLat, projLon);
  return [dist, projLat, projLon];
}

/**
 * Calculates compass bearing from point 1 to point 2 (0 - 360 degrees).
 */
export function calculateBearing(lat1, lon1, lat2, lon2) {
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;

  const y = Math.sin(deltaLambda) * Math.cos(phi2);
  const x =
    Math.cos(phi1) * Math.sin(phi2) -
    Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);
  const bearing = (Math.atan2(y, x) * 180) / Math.PI;
  return Math.round((bearing + 360) % 360);
}

/**
 * Evaluates state transitions with anti-flapping hysteresis gaps.
 */
export function transitionStateWithHysteresis(distanceKm, prevState = null) {
  if (!prevState) {
    if (distanceKm <= THRESHOLD_BREACH_KM) return 'BREACH';
    if (distanceKm <= THRESHOLD_WARNING_KM) return 'WARNING';
    if (distanceKm <= THRESHOLD_APPROACHING_KM) return 'APPROACHING';
    return 'NORMAL';
  }

  if (prevState === 'BREACH') {
    if (distanceKm > THRESHOLD_BREACH_KM + HYSTERESIS_WARNING_RECOVERY_KM) {
      if (distanceKm > THRESHOLD_WARNING_KM + HYSTERESIS_APPROACHING_RECOVERY_KM) {
        if (distanceKm > THRESHOLD_APPROACHING_KM + HYSTERESIS_NORMAL_RECOVERY_KM) {
          return 'NORMAL';
        }
        return 'APPROACHING';
      }
      return 'WARNING';
    }
    return 'BREACH';
  }

  if (prevState === 'WARNING') {
    if (distanceKm <= THRESHOLD_BREACH_KM) return 'BREACH';
    if (distanceKm > THRESHOLD_WARNING_KM + HYSTERESIS_APPROACHING_RECOVERY_KM) {
      if (distanceKm > THRESHOLD_APPROACHING_KM + HYSTERESIS_NORMAL_RECOVERY_KM) {
        return 'NORMAL';
      }
      return 'APPROACHING';
    }
    return 'WARNING';
  }

  if (prevState === 'APPROACHING') {
    if (distanceKm <= THRESHOLD_BREACH_KM) return 'BREACH';
    if (distanceKm <= THRESHOLD_WARNING_KM) return 'WARNING';
    if (distanceKm > THRESHOLD_APPROACHING_KM + HYSTERESIS_NORMAL_RECOVERY_KM) {
      return 'NORMAL';
    }
    return 'APPROACHING';
  }

  // prevState === 'NORMAL'
  if (distanceKm <= THRESHOLD_BREACH_KM) return 'BREACH';
  if (distanceKm <= THRESHOLD_WARNING_KM) return 'WARNING';
  if (distanceKm <= THRESHOLD_APPROACHING_KM) return 'APPROACHING';
  return 'NORMAL';
}

/**
 * Generates deterministic alert metadata without LLMs.
 */
export function generateAlertContent(state, distanceKm, boundaryName) {
  switch (state) {
    case 'BREACH':
      return {
        severity: 'CRITICAL',
        alertRequired: true,
        title: 'CRITICAL: Maritime Boundary Breach Detected',
        message: `Vessel has crossed ${boundaryName}. Return to Indian territorial waters immediately! Offline safety monitoring active.`,
      };
    case 'WARNING':
      return {
        severity: 'WARNING',
        alertRequired: true,
        title: 'WARNING: Immediate Border Proximity',
        message: `Vessel is ${distanceKm.toFixed(2)} km from ${boundaryName}. Immediate course correction recommended.`,
      };
    case 'APPROACHING':
      return {
        severity: 'CAUTION',
        alertRequired: true,
        title: 'CAUTION: Approaching Border Buffer',
        message: `Vessel is approaching ${boundaryName} (${distanceKm.toFixed(2)} km). Monitor heading and radar watch.`,
      };
    default:
      return {
        severity: 'INFO',
        alertRequired: false,
        title: 'NORMAL: Sector Safe',
        message: `Vessel is ${distanceKm.toFixed(2)} km clear of ${boundaryName}. Conditions nominal.`,
      };
  }
}

/**
 * Pure local geofencing evaluation executed entirely in browser memory.
 */
export function evaluateLocalGeofence(
  lat,
  lon,
  prevState = null,
  boundaries = DEMO_BOUNDARIES
) {
  let minDistance = Infinity;
  let closestBearing = 0;
  let closestName = 'Demo Maritime Boundary';
  let closestId = 'IMBL_DEMO_SAMPLE';

  for (const boundary of boundaries) {
    const coords = boundary.coordinates;
    for (let i = 0; i < coords.length - 1; i++) {
      const [lon1, lat1] = coords[i];
      const [lon2, lat2] = coords[i + 1];
      const [dist, projLat, projLon] = pointToSegmentDistanceKm(lat, lon, lat1, lon1, lat2, lon2);
      if (dist < minDistance) {
        minDistance = dist;
        closestBearing = calculateBearing(lat, lon, projLat, projLon);
        closestName = boundary.name;
        closestId = boundary.id;
      }
    }
  }

  if (minDistance === Infinity) {
    minDistance = 45.0;
    closestBearing = 90;
  }

  const roundedDistance = Math.round(minDistance * 100) / 100;
  const state = transitionStateWithHysteresis(roundedDistance, prevState);
  const alert = generateAlertContent(state, roundedDistance, closestName);

  return {
    latitude: Math.round(lat * 10000) / 10000,
    longitude: Math.round(lon * 10000) / 10000,
    nearestBoundaryName: closestName,
    nearestBoundaryId: closestId,
    distanceToBoundaryKm: roundedDistance,
    bearingDegrees: closestBearing,
    state,
    severity: alert.severity,
    alertRequired: alert.alertRequired,
    alertTitle: alert.title,
    alertMessage: alert.message,
    evaluatedAt: new Date().toISOString(),
    demoOnly: true,
    warning: DEMO_DISCLAIMER_WARNING,
  };
}
