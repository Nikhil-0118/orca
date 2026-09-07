import { GeoJsonPolygon } from './alert.types';

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface FishingZone {
  zone_id: string;
  boundary: GeoJsonPolygon;
  bearing_degrees: number;
  distance_km: number;
  depth_meters: number;
  validity_start: string;
  validity_end: string;
  confidence_score: number;
}

export interface DangerZone {
  zone_id: string;
  severity: 'WARNING' | 'DANGER' | 'RESTRICTED';
  title: string;
  boundary: GeoJsonPolygon;
}

export interface DestinationPoint {
  id: string;
  name: string;
  type: 'harbor' | 'pfz' | 'port' | 'island' | 'landmark' | 'custom';
  coordinates: Coordinates;
  description?: string;
  depthMeters?: number;
  safetyStatus?: 'safe' | 'caution' | 'danger';
}

export interface RouteWaypoint {
  name: string;
  coordinates: Coordinates;
  passed?: boolean;
}

export interface ActiveRoute {
  destination: DestinationPoint;
  origin: Coordinates;
  distanceKm: number;
  distanceNauticalMiles: number;
  bearingDegrees: number;
  estimatedTimeMinutes: number;
  waypoints: RouteWaypoint[];
  safetyClearance: 'SAFE' | 'CAUTION' | 'RESTRICTED';
  safetyNote: string;
  generatedAt: string;
}

export interface VesselLocationState {
  coordinates: Coordinates;
  speed_knots: number;
  heading_degrees: number;
  accuracy_meters: number;
  last_updated: string;
}

