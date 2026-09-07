import { LocationContext, QueryApiResponse } from '../types/chat.types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export interface SendQueryPayload {
  query: string;
  location?: LocationContext | null;
  lat?: number;
  lon?: number;
  is_demo?: boolean;
  session_id?: string;
  conversation_history?: Array<{ role: string; content: string }>;
}

export const chatService = {
  async sendQuery(payload: SendQueryPayload): Promise<QueryApiResponse> {
    let resolvedLocation: LocationContext | null = null;

    if (payload.location) {
      if (payload.location.latitude === null && payload.location.longitude === null) {
        resolvedLocation = null;
      } else {
        resolvedLocation = payload.location;
      }
    } else if (payload.lat !== undefined && payload.lon !== undefined) {
      resolvedLocation = {
        latitude: payload.lat,
        longitude: payload.lon,
        source: payload.is_demo ? 'demo' : 'browser_gps',
        is_demo: Boolean(payload.is_demo),
      };
    }

    const body = {
      query: payload.query,
      location: resolvedLocation,
      is_demo_mode: resolvedLocation ? resolvedLocation.is_demo : Boolean(payload.is_demo),
      session_id: payload.session_id || `session-${Date.now()}`,
      conversation_history: payload.conversation_history,
    };

    let response: Response;
    try {
      response = await fetch(`${BASE_URL}/api/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
    } catch (networkErr: unknown) {
      const detail = networkErr instanceof Error ? networkErr.message : String(networkErr);
      throw new Error(`Failed to connect to ORCA backend at ${BASE_URL} (${detail}). Ensure the server is running.`);
    }

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || `HTTP error! Status: ${response.status}`);
    }

    const data: QueryApiResponse = await response.json();
    return data;
  },
};
