import { useState, useCallback, useEffect, useRef } from 'react';
import {
  evaluateLocalGeofence,
  GeofenceEvaluation,
  SafetyState,
  SafetyLevel,
  SafetyThresholds,
  THRESHOLD_APPROACHING_KM,
  THRESHOLD_WARNING_KM,
} from '../services/offlineSafetyService';
import { buzzerService } from '../services/buzzerService';

export interface LocationPreset {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  expectedState: SafetyState;
  description: string;
}

export const PRESET_LOCATIONS: LocationPreset[] = [
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
    name: 'Palk Strait (Caution)',
    latitude: 9.38,
    longitude: 79.42,
    expectedState: 'APPROACHING',
    description: '~12 km from IMBL. Caution buffer zone.',
  },
  {
    id: 'palk-bay-warning',
    name: 'Border Corridor (Danger)',
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
  const [latitude, setLatitude] = useState<number>(initialLat);
  const [longitude, setLongitude] = useState<number>(initialLon);
  const [stepSize, setStepSize] = useState<number>(0.01); // in degrees (~1.1 km)
  const [isSimulatedOffline, setIsSimulatedOffline] = useState<boolean>(false);
  const [browserOnline, setBrowserOnline] = useState<boolean>(navigator.onLine);
  
  // Simulator active status & configurable thresholds
  const [isSimulatorRunning, setIsSimulatorRunning] = useState<boolean>(true);
  const [cautionThresholdKm, setCautionThresholdKm] = useState<number>(THRESHOLD_APPROACHING_KM);
  const [dangerThresholdKm, setDangerThresholdKm] = useState<number>(THRESHOLD_WARNING_KM);

  // Track previous state for hysteresis and transitions
  const prevStateRef = useRef<SafetyState | null>(null);
  const prevLevelRef = useRef<SafetyLevel | null>(null);

  // Live evaluation computed synchronously from position
  const [evaluation, setEvaluation] = useState<GeofenceEvaluation>(() => {
    const initialEval = evaluateLocalGeofence(initialLat, initialLon, null, undefined, {
      cautionKm: THRESHOLD_APPROACHING_KM,
      dangerKm: THRESHOLD_WARNING_KM,
    });
    prevStateRef.current = initialEval.state;
    prevLevelRef.current = initialEval.level;
    return initialEval;
  });

  // Track alert history
  const [alertHistory, setAlertHistory] = useState<GeofenceEvaluation[]>([]);

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

  // Re-evaluate geofence and trigger buzzer according to safety level
  const evaluateAndSyncBuzzer = useCallback(
    (lat: number, lon: number, cautionKm: number, dangerKm: number, running: boolean) => {
      const thresholds: SafetyThresholds = { cautionKm, dangerKm };
      const nextEval = evaluateLocalGeofence(lat, lon, prevStateRef.current, undefined, thresholds);

      // Check if alert state changed
      if (nextEval.state !== prevStateRef.current) {
        setAlertHistory((prev) => [nextEval, ...prev.slice(0, 19)]);
      }

      // Sync Audio Buzzer according to 3-tier warning level (SAFE -> CAUTION -> DANGER)
      if (running) {
        if (nextEval.level === 'DANGER') {
          buzzerService.startDangerAlarm();
        } else {
          buzzerService.stopDangerAlarm();
          if (nextEval.level === 'CAUTION' && prevLevelRef.current === 'SAFE') {
            buzzerService.playCautionWarning();
          }
        }
      } else {
        buzzerService.stopDangerAlarm();
      }

      prevStateRef.current = nextEval.state;
      prevLevelRef.current = nextEval.level;
      setEvaluation(nextEval);
    },
    []
  );

  // Current position refs for threshold/running state effect
  const latRef = useRef(latitude);
  const lonRef = useRef(longitude);
  latRef.current = latitude;
  lonRef.current = longitude;

  // Re-evaluate when position changes
  const updatePosition = useCallback(
    (newLat: number, newLon: number) => {
      const clampedLat = Math.max(-90, Math.min(90, newLat));
      const clampedLon = Math.max(-180, Math.min(180, newLon));

      setLatitude(clampedLat);
      setLongitude(clampedLon);
      evaluateAndSyncBuzzer(clampedLat, clampedLon, cautionThresholdKm, dangerThresholdKm, isSimulatorRunning);
    },
    [cautionThresholdKm, dangerThresholdKm, isSimulatorRunning, evaluateAndSyncBuzzer]
  );

  // Re-evaluate only if thresholds or simulator running state change
  useEffect(() => {
    evaluateAndSyncBuzzer(latRef.current, lonRef.current, cautionThresholdKm, dangerThresholdKm, isSimulatorRunning);
  }, [cautionThresholdKm, dangerThresholdKm, isSimulatorRunning, evaluateAndSyncBuzzer]);

  // Clean up buzzer on unmount
  useEffect(() => {
    return () => {
      buzzerService.stopDangerAlarm();
    };
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
  const loadPreset = useCallback(
    (preset: LocationPreset) => {
      updatePosition(preset.latitude, preset.longitude);
    },
    [updatePosition]
  );

  // Reset boat to safe starting position
  const resetBoat = useCallback(() => {
    const safeLat = 9.45;
    const safeLon = 79.2;
    buzzerService.stopDangerAlarm();
    updatePosition(safeLat, safeLon);
  }, [updatePosition]);

  // Toggle offline simulation
  const toggleSimulatedOffline = useCallback((val?: boolean) => {
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
    isSimulatorRunning,
    setIsSimulatorRunning,
    cautionThresholdKm,
    setCautionThresholdKm,
    dangerThresholdKm,
    setDangerThresholdKm,
    evaluation,
    alertHistory,
    moveNorth,
    moveSouth,
    moveEast,
    moveWest,
    updatePosition,
    loadPreset,
    resetBoat,
    toggleSimulatedOffline,
  };
}

