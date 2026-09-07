/**
 * ORCA Chat API Service (Phase 18 — JSX conversion).
 * Communicates with FastAPI /api/query endpoint.
 * Passes spatial payload through from backend response.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const chatService = {
  async sendQuery(payload) {
    let resolvedLocation = null;

    if (payload.location) {
      resolvedLocation = payload.location;
    } else if (payload.lat !== undefined && payload.lon !== undefined) {
      resolvedLocation = {
        latitude: payload.lat,
        longitude: payload.lon,
        source: payload.is_demo ? 'demo' : 'browser_gps',
        is_demo: Boolean(payload.is_demo),
      };
    } else if (payload.vessel_location) {
      resolvedLocation = {
        latitude: payload.vessel_location.latitude,
        longitude: payload.vessel_location.longitude,
        source: 'browser_gps',
        is_demo: false,
      };
    }

    const body = {
      query: payload.query,
      location: resolvedLocation,
      is_demo_mode: resolvedLocation ? resolvedLocation.is_demo : Boolean(payload.is_demo),
      session_id: payload.session_id || `session-${Date.now()}`,
      conversation_history: payload.conversation_history,
    };

    const response = await fetch(`${BASE_URL}/api/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || `HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  },
};

export default chatService;
