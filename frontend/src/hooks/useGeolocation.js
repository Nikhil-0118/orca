import { useState, useEffect, useCallback, useRef } from 'react';

export function useGeolocation() {
  const [locationContext, setLocationContext] = useState(() => {
    try {
      const cached = sessionStorage.getItem('orca_user_gps') || localStorage.getItem('orca_user_gps');
      if (cached) {
        const parsed = JSON.parse(cached);
        if (parsed.latitude && parsed.longitude) {
          return {
            ...parsed,
            source: 'browser_gps',
          };
        }
      }
    } catch {
      // Ignore storage errors
    }
    return {
      latitude: null,
      longitude: null,
      source: 'unavailable',
      accuracy_m: null,
      timestamp: null,
      is_demo: false,
      label: 'Location unavailable',
    };
  });

  const [geoError, setGeoError] = useState(null);
  const [isLocating, setIsLocating] = useState(false);
  const watchIdRef = useRef(null);

  // Function to request live device GPS with high-accuracy + fallback
  const requestLiveGps = useCallback(() => {
    if (typeof window === 'undefined' || !('geolocation' in navigator)) {
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

    const handleSuccess = (pos) => {
      setIsLocating(false);
      setGeoError(null);
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      const acc = pos.coords.accuracy ? Math.round(pos.coords.accuracy) : null;
      const newCtx = {
        latitude: lat,
        longitude: lon,
        source: 'browser_gps',
        accuracy_m: acc,
        timestamp: new Date(pos.timestamp).toISOString(),
        is_demo: false,
        label: `Live GPS (±${acc || 10}m)`,
      };
      setLocationContext(newCtx);
      try {
        sessionStorage.setItem('orca_user_gps', JSON.stringify(newCtx));
        localStorage.setItem('orca_user_gps', JSON.stringify(newCtx));
      } catch {}
    };

    // Primary: High accuracy request
    navigator.geolocation.getCurrentPosition(
      handleSuccess,
      (err) => {
        // Fallback: standard accuracy if high accuracy hardware times out
        navigator.geolocation.getCurrentPosition(
          handleSuccess,
          (fallbackErr) => {
            setIsLocating(false);
            setGeoError(fallbackErr.message);
            setLocationContext((prev) => {
              if (prev.source === 'browser_gps' && prev.latitude) return prev;
              return {
                ...prev,
                latitude: null,
                longitude: null,
                source: 'unavailable',
                is_demo: false,
                label: 'Location unavailable',
              };
            });
          },
          {
            enableHighAccuracy: false,
            timeout: 15000,
            maximumAge: 60000,
          }
        );
      },
      {
        enableHighAccuracy: true,
        timeout: 9000,
        maximumAge: 5000,
      }
    );

    // Also register watchPosition for continuous live GPS tracking if supported
    try {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
      watchIdRef.current = navigator.geolocation.watchPosition(
        handleSuccess,
        () => {},
        { enableHighAccuracy: true, maximumAge: 10000 }
      );
    } catch {}
  }, []);

  // Set demo location explicitly with visible demonstration indicator
  const setDemoLocation = useCallback((lat = 13.0827, lon = 80.2707, label = 'Chennai Coast (Demo)') => {
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

  // Initial GPS acquisition attempt on hook mount + permission check
  useEffect(() => {
    requestLiveGps();

    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions.query({ name: 'geolocation' }).then((status) => {
        if (status.state === 'granted') {
          requestLiveGps();
        }
        status.onchange = () => {
          if (status.state === 'granted') {
            requestLiveGps();
          }
        };
      }).catch(() => {});
    }

    return () => {
      if (watchIdRef.current !== null && typeof navigator !== 'undefined' && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
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
