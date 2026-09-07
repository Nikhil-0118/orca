import { useState, useEffect, useCallback } from 'react';
import { alertsService } from '../services/alertsService';

export function useAlerts(lat = 13.0827, lon = 80.2707) {
  const [alerts, setAlerts] = useState([]);
  const [isSmsFallbackActive, setIsSmsFallbackActive] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const response = await alertsService.getActiveAlerts(lat, lon);
      if (response.success) {
        setAlerts(response.data);
      }
    } catch {
      // In case of poor connectivity, flag SMS fallback status
      setIsSmsFallbackActive(true);
    } finally {
      setLoading(false);
    }
  }, [lat, lon]);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000); // 1-minute live poll
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  return { alerts, isSmsFallbackActive, loading, refetch: fetchAlerts };
}
