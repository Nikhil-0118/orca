export type AlertSeverity = 'INFO' | 'ADVISORY' | 'WARNING' | 'DANGER' | 'EMERGENCY';

export type AlertType =
  | 'CYCLONE_STORM'
  | 'HIGH_WAVE'
  | 'HEATWAVE_SST'
  | 'IMBL_BOUNDARY'
  | 'PFZ_OPPORTUNITY';

export interface GeoJsonPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface AlertItem {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  description: string;
  affected_polygon?: GeoJsonPolygon;
  issued_at: string;
  expires_at?: string;
  sms_compatible_text: string;
}

export interface AlertSubscriptionRequest {
  phone_number?: string;
  device_token?: string;
  vessel_id: string;
  current_location: { latitude: number; longitude: number };
  alert_types: AlertType[];
  enable_sms_fallback: boolean;
}
