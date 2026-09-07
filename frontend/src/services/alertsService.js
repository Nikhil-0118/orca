import { apiRequest } from './apiClient';

export const alertsService = {
  async getActiveAlerts(lat, lon, radiusKm = 50) {
    return apiRequest(`/api/v1/alerts/active?lat=${lat}&lon=${lon}&radius_km=${radiusKm}`, {
      method: 'GET',
    });
  },

  async subscribeToAlerts(payload) {
    return apiRequest('/api/v1/alerts/subscribe', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
