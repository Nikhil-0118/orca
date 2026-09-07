import { useState, useCallback, useEffect, useRef } from 'react';
import { evaluateLocalGeofence } from '../services/offlineSafetyService';

export const PRESET_LOCATIONS = [
  {
    id: 'palk-bay-safe',
    name: 'Palk Bay Coastal (Safe)',
    latitude: 9.45,
    longitude: 79.2,
    expectedState: 'NORMAL',
    description: '~23 km from IMBL. Normal safe sector.',
  },
  {
    id: 'palk-bay-approaching',
    name: 'Palk Strait (Approaching)',
    latitude: 9.38,
    longitude: 79.42,
    expectedState: 'APPROACHING',
    description: '~12 km from IMBL. Caution buffer zone.',
  },
  {
    id: 'palk-bay-warning',
    name: 'Border Corridor (Warning)',
    latitude: 9.36,
    longitude: 79.5,
    expectedState: 'WARNING',
    description: '~3.7 km from IMBL. Warning threshold.',
  },
  {
    id: 'palk-bay-breach',
    name: 'International Border (Breach)',
    latitude: 9.3667,
    longitude: 79.535,
    expectedState: 'BREACH',
    description: 'Directly on/across IMBL line. Critical breach.',
  },
  {
    id: 'mumbai-safe',
    name: 'West Coast / Mumbai (Safe)',
    latitude: 19.0,
    longitude: 72.5,
    expectedState: 'NORMAL',
    description: 'Safe coastal water off Mumbai harbor.',
  },
];

export function useOfflineSafety(initialLat = 9.45, initialLon = 79.2) {
  // Vessel state
  const [latitude, setLatitude] = useState(initialLat);
  const [longitude, setLongitude] = useState(initialLon);
  const [stepSize, setStepSize] = useState(0.01); // in degrees (~1.1 km)
  const [isSimulatedOffline, setIsSimulatedOffline] = useState(false);
  const [browserOnline, setBrowserOnline] = useState(navigator.onLine);
  
  // Track previous state for hysteresis
  const prevStateRef = useRef(null);

  // Live evaluation computed synchronously from position
  const [evaluation, setEvaluation] = useState(() => {
    const initialEval = evaluateLocalGeofence(initialLat, initialLon, null);
    prevStateRef.current = initialEval.state;
    return initialEval;
  });

  // Track alert history
  const [alertHistory, setAlertHistory] = useState([]);

  // Monitor real browser online/offline events
  useEffect(() => {
    const handleOnline = () => setBrowserOnline(true);
    const handleOffline = () => setBrowserOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Compute effective offline status
  const isOffline = isSimulatedOffline || !browserOnline;

  // Re-evaluate geofence whenever coordinates change
  const updatePosition = useCallback((newLat, newLon) => {
    const clampedLat = Math.max(-90, Math.min(90, newLat));
    const clampedLon = Math.max(-180, Math.min(180, newLon));
    
    setLatitude(clampedLat);
    setLongitude(clampedLon);

    const nextEval = evaluateLocalGeofence(clampedLat, clampedLon, prevStateRef.current);
    
    // Check if alert severity changed or required
    if (nextEval.state !== prevStateRef.current) {
      setAlertHistory((prev) => [nextEval, ...prev.slice(0, 19)]);
    }
    
    prevStateRef.current = nextEval.state;
    setEvaluation(nextEval);
  }, []);

  // Directional movement handlers (D-Pad)
  const moveNorth = useCallback(() => {
    updatePosition(latitude + stepSize, longitude);
  }, [latitude, longitude, stepSize, updatePosition]);

  const moveSouth = useCallback(() => {
    updatePosition(latitude - stepSize, longitude);
  }, [latitude, longitude, stepSize, updatePosition]);

  const moveEast = useCallback(() => {
    updatePosition(latitude, longitude + stepSize);
  }, [latitude, longitude, stepSize, updatePosition]);

  const moveWest = useCallback(() => {
    updatePosition(latitude, longitude - stepSize);
  }, [latitude, longitude, stepSize, updatePosition]);

  // Preset location loader
  const loadPreset = useCallback((preset) => {
    updatePosition(preset.latitude, preset.longitude);
  }, [updatePosition]);

  // Toggle offline simulation
  const toggleSimulatedOffline = useCallback((val) => {
    setIsSimulatedOffline((prev) => (val !== undefined ? val : !prev));
  }, []);

  return {
    latitude,
    longitude,
    stepSize,
    setStepSize,
    isOffline,
    isSimulatedOffline,
    browserOnline,
    evaluation,
    alertHistory,
    moveNorth,
    moveSouth,
    moveEast,
    moveWest,
    updatePosition,
    loadPreset,
    toggleSimulatedOffline,
  };
}
