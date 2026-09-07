import { useState, useCallback } from 'react';
import { SOSDispatchResponse, SOSTriggerRequest } from '../types/sos.types';
import { sosService } from '../services/sosService';

export function useSos() {
  const [isTriggering, setIsTriggering] = useState<boolean>(false);
  const [dispatchResult, setDispatchResult] = useState<SOSDispatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const triggerSos = useCallback(async (payload: SOSTriggerRequest) => {
    setIsTriggering(true);
    setError(null);
    try {
      const response = await sosService.triggerDistress(payload);
      if (response.success) {
        setDispatchResult(response.data);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Emergency SOS dispatch failed');
    } finally {
      setIsTriggering(false);
    }
  }, []);

  return { isTriggering, dispatchResult, error, triggerSos };
}
