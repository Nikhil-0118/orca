export type AgentType =
  | 'orchestrator'
  | 'weather_storm_agent'
  | 'fishing_zone_agent'
  | 'ocean_temp_agent'
  | 'safety_boundary_agent';

export interface ReasoningStep {
  agent: AgentType | string;
  action: string;
  rationale: string;
  data_sources_queried: string[];
  timestamp: string;
}

export type OrcaCompanionState = 'idle' | 'listening' | 'thinking' | 'answering' | 'error';

export interface StructuredEvidenceItem {
  source: string;
  summary: string;
}

export interface DecisionInfo {
  label: string;
  summary?: string;
  confidence?: 'high' | 'moderate' | 'low' | string;
}

export interface BestTimeInfo {
  available: boolean;
  window?: string | null;
  basis?: string | null;
}

export interface HumanConditions {
  wind?: string | null;
  sea_state?: string | null;
  water_temperature?: string | null;
  visibility?: string | null;
  safety?: string | null;
}

export interface HumanFriendlyResponse {
  direct_answer: string;
  decision_code?: 'YES' | 'GO' | 'CAUTION' | 'NO' | 'AVOID' | 'UNCERTAIN' | 'INSUFFICIENT_DATA' | null;
  explanation: string;
  best_time?: string | null;
  conditions?: HumanConditions | null;
  safety_notice?: string | null;
  data_quality_note?: string | null;
  sources?: string[];
}

export interface LocationContext {
  latitude: number | null;
  longitude: number | null;
  source: 'browser_gps' | 'user_input' | 'manual_map' | 'user_override' | 'map_selection' | 'demo' | 'simulator' | 'named_region' | 'unavailable';
  accuracy_m?: number | null;
  speed_knots?: number | null;
  timestamp?: string | null;
  is_demo: boolean;
  is_approximate?: boolean;
  label?: string | null;
  geographic_type?: 'inland' | 'coastal' | 'marine' | 'unknown' | null;
  resolved_place?: string | null;
}

export type SpatialQueryType =
  | 'user_location'
  | 'target_location'
  | 'boundary_safety'
  | 'marine_route'
  | 'danger_areas'
  | 'fishing_destination';

export interface MapMarker {
  id: string;
  latitude: number;
  longitude: number;
  label: string;
  marker_type: 'vessel' | 'target' | 'boundary' | 'hazard' | 'waypoint' | 'fishing';
  status?: 'safe' | 'caution' | 'warning' | 'danger' | 'info';
  description?: string;
}

export interface MapZone {
  id: string;
  title: string;
  zone_type: 'boundary_line' | 'restricted' | 'warning' | 'caution';
  geometry_type: 'LineString' | 'Polygon';
  coordinates: any[];
  stroke_color?: string;
  fill_color?: string;
  opacity?: number;
  description?: string;
}

export interface MapRoute {
  origin: { latitude: number; longitude: number; label: string };
  destination: { latitude: number; longitude: number; label: string };
  waypoints?: Array<{ latitude: number; longitude: number; name: string }>;
  distance_km: number;
  distance_nm: number;
  bearing_degrees: number;
  estimated_time_minutes?: number | null;
  safety_clearance: 'SAFE' | 'CAUTION' | 'RESTRICTED';
  safety_note?: string;
  is_approximate?: boolean;
  is_inland_warning?: boolean;
}

export interface SpatialPayload {
  enabled: boolean;
  type: SpatialQueryType;
  title: string;
  summary: string;
  center: { latitude: number; longitude: number };
  zoom: number;
  markers: MapMarker[];
  zones?: MapZone[];
  routes?: MapRoute[];
  boundary_distance_km?: number | null;
  boundary_bearing_deg?: number | null;
  safety_state?: 'NORMAL' | 'APPROACHING' | 'WARNING' | 'BREACH' | null;
  navigation_warning?: string | null;
  is_marine_navigable?: boolean;
  target_location?: { latitude: number; longitude: number; name?: string } | null;
  vessel_location?: { latitude: number; longitude: number; name?: string } | null;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  location?: LocationContext;
  user_location?: LocationContext;
  query_location?: Record<string, any>;
  mode?: 'conversation' | 'utility' | 'marine' | 'safety' | 'location';
  decision?: DecisionInfo;
  risk_level?: string;
  risk_summary?: string;
  key_conditions?: string[];
  recommendations?: string[];
  best_time?: BestTimeInfo;
  reasoning_summary?: string;
  evidence?: string[];
  structured_evidence?: StructuredEvidenceItem[];
  data_limitations?: string[];
  agents_used?: string[];
  reasoning_steps?: ReasoningStep[];
  involved_agents?: (AgentType | string)[];
  suggested_actions?: string[];
  next_safe_window?: string;
  human_response?: HumanFriendlyResponse;
  spatial?: SpatialPayload | null;
}

export interface QueryApiRequest {
  query: string;
  location?: LocationContext | { lat: number; lon: number } | null;
  session_id: string;
  conversation_history?: Array<{ role: string; content: string }>;
  is_demo_mode?: boolean;
}

export interface QueryApiResponse {
  mode?: 'conversation' | 'utility' | 'marine' | 'safety' | 'location';
  answer: string;
  location?: LocationContext;
  user_location?: LocationContext;
  query_location?: Record<string, any>;
  decision?: DecisionInfo;
  risk_level: string;
  risk_summary?: string;
  key_conditions?: string[];
  recommendations: string[];
  best_time?: BestTimeInfo;
  reasoning_summary?: string;
  evidence: string[];
  structured_evidence?: StructuredEvidenceItem[];
  data_limitations?: string[];
  agents_used?: string[];
  human_response?: HumanFriendlyResponse;
  spatial?: SpatialPayload | null;
}
