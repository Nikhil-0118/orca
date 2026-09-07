import { useState, useEffect } from 'react';
import { VesselLocationState } from '../types/map.types';

export function useGeolocation() {
  const [location, setLocation] = useState<VesselLocationState>({
    coordinates: { latitude: 13.0827, longitude: 80.2707 },
    speed_knots: 6.2,
    heading_degrees: 135,
    accuracy_meters: 8,
    last_updated: new Date().toISOString(),
  });
  const [geoError, setGeoError] = useState<string | null>(null);

  useEffect(() => {
    if (!('geolocation' in navigator)) {
      setGeoError('GPS Geolocation is not supported on this browser.');
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setLocation({
          coordinates: {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
          },
          speed_knots: pos.coords.speed ? pos.coords.speed * 1.94384 : 0,
          heading_degrees: pos.coords.heading || 0,
          accuracy_meters: pos.coords.accuracy,
          last_updated: new Date(pos.timestamp).toISOString(),
        });
      },
      (err) => {
        setGeoError(err.message);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 5000,
      }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, []);

  return { location, geoError };
}
