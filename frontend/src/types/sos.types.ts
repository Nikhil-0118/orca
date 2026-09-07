import { Coordinates } from './map.types';

export type DistressNature =
  | 'ENGINE_FAILURE'
  | 'MEDICAL_EMERGENCY'
  | 'CAPSIZING_SINKING'
  | 'PIRACY_SECURITY'
  | 'BAD_WEATHER_TRAPPED'
  | 'UNKNOWN';

export interface SOSTriggerRequest {
  vessel_id: string;
  vessel_name?: string;
  crew_count: number;
  location: Coordinates;
  distress_nature: DistressNature;
  notes?: string;
  battery_level_percent?: number;
}

export interface SOSDispatchResponse {
  incident_id: string;
  mrcc_acknowledged: boolean;
  dispatched_channels: string[];
  nearest_rescue_centre: string;
  instructions_for_crew: string[];
  dispatched_at: string;
}
