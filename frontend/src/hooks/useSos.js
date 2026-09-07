import { useState, useCallback } from 'react';
import { sosService } from '../services/sosService';

export function useSos() {
  const [isTriggering, setIsTriggering] = useState(false);
  const [dispatchResult, setDispatchResult] = useState(null);
  const [error, setError] = useState(null);

  const triggerSos = useCallback(async (payload) => {
    setIsTriggering(true);
    setError(null);
    try {
      const response = await sosService.triggerDistress(payload);
      if (response.success) {
        setDispatchResult(response.data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Emergency SOS dispatch failed');
    } finally {
      setIsTriggering(false);
    }
  }, []);

  return { isTriggering, dispatchResult, error, triggerSos };
}
