import { Coordinates, DangerZone, DestinationPoint, FishingZone, ActiveRoute, VesselLocationState } from '../types/map.types';

export interface MarineMapState {
  center: Coordinates;
  zoom: number;
  vesselLocation: VesselLocationState | null;
  selectedDestination: DestinationPoint | null;
  activeRoute: ActiveRoute | null;
  availableDestinations: DestinationPoint[];
  fishingZones: FishingZone[];
  dangerZones: DangerZone[];
  showPfzLayer: boolean;
  showDangerLayer: boolean;
  showSstThermalLayer: boolean;
  showRouteLayer: boolean;
}

export const INITIAL_DESTINATIONS: DestinationPoint[] = [
  {
    id: 'pfz-zone-42',
    name: 'INCOIS PFZ Zone #42',
    type: 'pfz',
    coordinates: { latitude: 13.1420, longitude: 80.4520 },
    description: 'High chlorophyll thermal front. Peak catch: Indian Mackerel & Yellowfin Tuna.',
    depthMeters: 45,
    safetyStatus: 'safe',
  },
  {
    id: 'pulicat-lake',
    name: 'Pulicat Lagoon Inlet',
    type: 'harbor',
    coordinates: { latitude: 13.4167, longitude: 80.3167 },
    description: 'Northern calm anchorage. Protected estuary waterway.',
    depthMeters: 14,
    safetyStatus: 'safe',
  },
  {
    id: 'ennore-port',
    name: 'Kamarajar (Ennore) Deep Port',
    type: 'port',
    coordinates: { latitude: 13.2612, longitude: 80.3344 },
    description: 'Deep-draft commercial shipping channel. Navigational clearance active.',
    depthMeters: 32,
    safetyStatus: 'caution',
  },
  {
    id: 'kasimedu-harbor',
    name: 'Kasimedu Fishing Harbor',
    type: 'harbor',
    coordinates: { latitude: 13.1189, longitude: 80.2978 },
    description: 'Main coastal trawler base. High traffic density at dawn.',
    depthMeters: 12,
    safetyStatus: 'safe',
  },
  {
    id: 'mahabalipuram-banks',
    name: 'Mahabalipuram Coral Banks',
    type: 'landmark',
    coordinates: { latitude: 12.6189, longitude: 80.2014 },
    description: 'Southern reef shelf. Caution near sub-surface rock formations.',
    depthMeters: 22,
    safetyStatus: 'safe',
  },
  {
    id: 'nagapattinam-offshore',
    name: 'Nagapattinam Deep Water Basin',
    type: 'pfz',
    coordinates: { latitude: 11.2000, longitude: 80.1500 },
    description: 'Deep oceanic boundary. Rich pelagic biomass.',
    depthMeters: 85,
    safetyStatus: 'safe',
  },
];

export const INITIAL_DANGER_ZONES: DangerZone[] = [
  {
    zone_id: 'cyclonic-surge-alpha',
    severity: 'DANGER',
    title: 'Cyclonic Swell & Wind Shear (3.8m Waves)',
    boundary: {
      type: 'Polygon',
      coordinates: [
        [
          [80.35, 12.95],
          [80.55, 12.95],
          [80.55, 13.15],
          [80.35, 13.15],
          [80.35, 12.95],
        ],
      ],
    },
  },
  {
    zone_id: 'imbl-geofence-warning',
    severity: 'RESTRICTED',
    title: 'IMBL International Border Proximity Geofence',
    boundary: {
      type: 'Polygon',
      coordinates: [
        [
          [80.60, 12.50],
          [80.70, 12.50],
          [80.70, 13.50],
          [80.60, 13.50],
          [80.60, 12.50],
        ],
      ],
    },
  },
];

export const INITIAL_FISHING_ZONES: FishingZone[] = [
  {
    zone_id: 'pfz-incois-42',
    boundary: {
      type: 'Polygon',
      coordinates: [
        [
          [80.38, 13.10],
          [80.48, 13.10],
          [80.48, 13.20],
          [80.38, 13.20],
          [80.38, 13.10],
        ],
      ],
    },
    bearing_degrees: 135,
    distance_km: 18.4,
    depth_meters: 45,
    validity_start: new Date().toISOString(),
    validity_end: new Date(Date.now() + 86400000).toISOString(),
    confidence_score: 0.94,
  },
  {
    zone_id: 'pfz-incois-55',
    boundary: {
      type: 'Polygon',
      coordinates: [
        [
          [80.32, 13.35],
          [80.44, 13.35],
          [80.44, 13.45],
          [80.32, 13.45],
          [80.32, 13.35],
        ],
      ],
    },
    bearing_degrees: 30,
    distance_km: 24.1,
    depth_meters: 38,
    validity_start: new Date().toISOString(),
    validity_end: new Date(Date.now() + 86400000).toISOString(),
    confidence_score: 0.88,
  },
];

export const initialMapState: MarineMapState = {
  center: { latitude: 13.0827, longitude: 80.2707 },
  zoom: 9,
  vesselLocation: {
    coordinates: { latitude: 13.0827, longitude: 80.2707 },
    speed_knots: 6.2,
    heading_degrees: 120,
    accuracy_meters: 5,
    last_updated: new Date().toISOString(),
  },
  selectedDestination: null,
  activeRoute: null,
  availableDestinations: INITIAL_DESTINATIONS,
  fishingZones: INITIAL_FISHING_ZONES,
  dangerZones: INITIAL_DANGER_ZONES,
  showPfzLayer: true,
  showDangerLayer: true,
  showSstThermalLayer: false,
  showRouteLayer: true,
};

/**
 * Calculates Great-Circle distance between two coordinates in kilometers (Haversine formula).
 */
export function calculateDistanceKm(coord1: Coordinates, coord2: Coordinates): number {
  const R = 6371; // Earth radius in km
  const dLat = ((coord2.latitude - coord1.latitude) * Math.PI) / 180;
  const dLon = ((coord2.longitude - coord1.longitude) * Math.PI) / 180;
  const lat1 = (coord1.latitude * Math.PI) / 180;
  const lat2 = (coord2.latitude * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.sin(dLon / 2) * Math.sin(dLon / 2) * Math.cos(lat1) * Math.cos(lat2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Calculates compass bearing from origin to destination (0 - 360 degrees).
 */
export function calculateBearing(coord1: Coordinates, coord2: Coordinates): number {
  const lat1 = (coord1.latitude * Math.PI) / 180;
  const lat2 = (coord2.latitude * Math.PI) / 180;
  const dLon = ((coord2.longitude - coord1.longitude) * Math.PI) / 180;

  const y = Math.sin(dLon) * Math.cos(lat2);
  const x =
    Math.cos(lat1) * Math.sin(lat2) -
    Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
  const brng = (Math.atan2(y, x) * 180) / Math.PI;
  return (brng + 360) % 360;
}

/**
 * Generates an active nautical route from origin to destination with waypoints and clearance assessment.
 */
export function createMarineRoute(
  origin: Coordinates,
  destination: DestinationPoint,
  vesselSpeedKnots = 6.5
): ActiveRoute {
  const distKm = calculateDistanceKm(origin, destination.coordinates);
  const distNm = distKm * 0.539957;
  const bearing = calculateBearing(origin, destination.coordinates);

  // Speed in km/h = knots * 1.852
  const speedKmh = Math.max(1, vesselSpeedKnots * 1.852);
  const etaMinutes = Math.round((distKm / speedKmh) * 60);

  // Generate intermediate navigational waypoints
  const midpoint: Coordinates = {
    latitude: (origin.latitude + destination.coordinates.latitude) / 2 + 0.008, // gentle sea curvature
    longitude: (origin.longitude + destination.coordinates.longitude) / 2 + 0.005,
  };

  const waypoints = [
    { name: 'Departure Sector', coordinates: origin, passed: true },
    { name: 'Channel Checkpoint Bravo', coordinates: midpoint, passed: false },
    { name: destination.name, coordinates: destination.coordinates, passed: false },
  ];

  const safetyClearance = destination.safetyStatus === 'danger' ? 'RESTRICTED' : destination.safetyStatus === 'caution' ? 'CAUTION' : 'SAFE';
  const safetyNote =
    safetyClearance === 'SAFE'
      ? 'Optimal route clear of cyclone swell cells and well within Indian EEZ maritime boundaries.'
      : safetyClearance === 'CAUTION'
      ? 'Caution: Active commercial shipping corridor near route terminus. Maintain radar watch.'
      : 'Restricted: Active cyclonic swell ahead. Reroute advised.';

  return {
    destination,
    origin,
    distanceKm: Math.round(distKm * 10) / 10,
    distanceNauticalMiles: Math.round(distNm * 10) / 10,
    bearingDegrees: Math.round(bearing),
    estimatedTimeMinutes: etaMinutes,
    waypoints,
    safetyClearance,
    safetyNote,
    generatedAt: new Date().toISOString(),
  };
}

/**
 * Searches for a destination matching a user query string.
 */
export function findDestinationByName(query: string, destinations: DestinationPoint[] = INITIAL_DESTINATIONS): DestinationPoint | null {
  const q = query.toLowerCase();
  for (const dest of destinations) {
    if (q.includes(dest.name.toLowerCase()) || q.includes(dest.id.toLowerCase())) {
      return dest;
    }
  }

  if (q.includes('pulicat')) return destinations.find((d) => d.id === 'pulicat-lake') || null;
  if (q.includes('ennore') || q.includes('kamarajar')) return destinations.find((d) => d.id === 'ennore-port') || null;
  if (q.includes('kasimedu') || q.includes('chennai port') || q.includes('harbor')) return destinations.find((d) => d.id === 'kasimedu-harbor') || null;
  if (q.includes('mahabalipuram') || q.includes('mamallapuram') || q.includes('shore')) return destinations.find((d) => d.id === 'mahabalipuram-banks') || null;
  if (q.includes('nagapattinam') || q.includes('deep water')) return destinations.find((d) => d.id === 'nagapattinam-offshore') || null;
  if (q.includes('pfz zone 42') || q.includes('zone 42')) return destinations.find((d) => d.id === 'pfz-zone-42') || null;

  return null;
}

