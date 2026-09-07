/**
 * Safety-Critical SOS Service.
 * Direct dispatch mechanism connecting to Indian Coast Guard MRCC and NavIC satellite beacon hubs.
 */
import { apiRequest } from './apiClient';

export const sosService = {
  async triggerDistress(payload) {
    return apiRequest('/api/v1/sos/trigger', {
      method: 'POST',
      body: JSON.stringify(payload),
      timeoutMs: 8000, // Fast timeout for emergency failover to SMS
    });
  },
};
