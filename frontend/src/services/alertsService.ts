import { AlertItem, AlertSubscriptionRequest } from '../types/alert.types';
import { apiRequest, ApiResponse } from './apiClient';

export const alertsService = {
  async getActiveAlerts(lat: number, lon: number, radiusKm: number = 50): Promise<ApiResponse<AlertItem[]>> {
    return apiRequest<AlertItem[]>(`/api/v1/alerts/active?lat=${lat}&lon=${lon}&radius_km=${radiusKm}`, {
      method: 'GET',
    });
  },

  async subscribeToAlerts(payload: AlertSubscriptionRequest): Promise<ApiResponse<boolean>> {
    return apiRequest<boolean>('/api/v1/alerts/subscribe', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
