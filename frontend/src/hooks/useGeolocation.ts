import { useState, useEffect, useCallback } from 'react';
import { LocationContext } from '../types/chat.types';

export function useGeolocation() {
  const [locationContext, setLocationContext] = useState<LocationContext>({
    latitude: null,
    longitude: null,
    source: 'unavailable',
    accuracy_m: null,
    timestamp: null,
    is_demo: false,
    label: 'Location unavailable',
  });
  const [geoError, setGeoError] = useState<string | null>(null);
  const [isLocating, setIsLocating] = useState<boolean>(false);

  // Function to request live device GPS
  const requestLiveGps = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setGeoError('GPS Geolocation is not supported on this device or browser.');
      setLocationContext((prev) => ({
        ...prev,
        source: 'unavailable',
        is_demo: false,
        label: 'GPS not supported',
      }));
      return;
    }

    setIsLocating(true);
    setGeoError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsLocating(false);
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        const acc = pos.coords.accuracy ? Math.round(pos.coords.accuracy) : null;
        setLocationContext({
          latitude: lat,
          longitude: lon,
          source: 'browser_gps',
          accuracy_m: acc,
          timestamp: new Date(pos.timestamp).toISOString(),
          is_demo: false,
          label: `Live GPS (±${acc || 15}m)`,
        });
      },
      (err) => {
        setIsLocating(false);
        setGeoError(err.message);
        // Do NOT silently invent Chennai! Remain honest about unavailable status.
        setLocationContext((prev) => ({
          ...prev,
          latitude: null,
          longitude: null,
          source: 'unavailable',
          is_demo: false,
          label: 'Location unavailable',
        }));
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 5000,
      }
    );
  }, []);

  // Set demo location explicitly with visible demonstration indicator
  const setDemoLocation = useCallback((lat = 13.0827, lon = 80.2707, label = 'Chennai Coast (SIH Demo)') => {
    setLocationContext({
      latitude: lat,
      longitude: lon,
      source: 'demo',
      accuracy_m: null,
      timestamp: new Date().toISOString(),
      is_demo: true,
      label,
    });
    setGeoError(null);
  }, []);

  // Clear demo location and attempt live GPS acquisition
  const clearDemoLocation = useCallback(() => {
    requestLiveGps();
  }, [requestLiveGps]);

  // Initial GPS acquisition attempt on hook mount
  useEffect(() => {
    requestLiveGps();
  }, [requestLiveGps]);

  return {
    locationContext,
    geoError,
    isLocating,
    requestLiveGps,
    setDemoLocation,
    clearDemoLocation,
  };
}
