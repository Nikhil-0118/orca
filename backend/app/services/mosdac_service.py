"""
MOSDAC Data Access Service.
Provides high-performance, validated spatial extraction of Chlorophyll-A from local NetCDF archives.
"""
from datetime import datetime, timezone
import logging
import math
import os
from typing import Any, Dict, Optional, Tuple
import numpy as np
import xarray as xr

from app.config import settings
from app.services.mosdac_downloader import mosdac_downloader

logger = logging.getLogger("orca.services.mosdac")

FILL_VALUE_THRESHOLD = -900000000.0  # NetCDF fill value is -999000000.0


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two decimal coordinates in kilometers.
    Correctly accounts for antimeridian and 0-360 longitude wrapping.
    """
    r_lat1 = math.radians(lat1)
    r_lat2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon_deg = ((lon2 - lon1 + 180.0) % 360.0) - 180.0
    dlon = math.radians(dlon_deg)

    a = math.sin(dlat / 2.0) ** 2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return round(6371.0 * c, 2)


class MosdacService:
    """
    Data-access service for ISRO MOSDAC oceanographic NetCDF products.
    Coordinates with MosdacDownloader for active dataset resolution and freshness tracking.
    """

    def __init__(self, filepath: Optional[str] = None):
        self._custom_filepath: Optional[str] = filepath
        self.filepath: str = filepath or getattr(settings, "MOSDAC_NETCDF_PATH", "")
        self._ds: Optional[xr.Dataset] = None
        self._lats: Optional[np.ndarray] = None
        self._lons: Optional[np.ndarray] = None
        self._chla: Optional[np.ndarray] = None
        self._chla_attrs: Dict[str, Any] = {}
        self._chla_encoding: Dict[str, Any] = {}
        self._obs_date: str = "unknown"
        self._active_metadata: Dict[str, Any] = {}
        self._is_loaded: bool = False

    def load_dataset(self) -> bool:
        """Load NetCDF dataset and cache coordinate and data arrays in memory."""
        # 1. Determine target file path
        if self._custom_filepath:
            target_path = self._custom_filepath
            active_meta: Dict[str, Any] = {}
        else:
            active_meta = mosdac_downloader.get_active_dataset()
            target_path = active_meta.get("filepath") or self.filepath
            self._active_metadata = active_meta

        if self._is_loaded and (self._chla is not None or self._ds is not None) and self.filepath == target_path:
            return True

        if not target_path or not os.path.exists(target_path):
            logger.warning("mosdac_netcdf_file_not_found", extra={"filepath": target_path})
            return False

        try:
            if self._ds is not None:
                try:
                    self._ds.close()
                except Exception:
                    pass
                self._ds = None

            # Open with context manager to guarantee immediate release of file handles on Windows
            with xr.open_dataset(target_path) as ds:
                self._lats = ds["lat"].values.copy()
                self._lons = ds["lon"].values.copy()
                self._chla = ds["chla"].isel(time=0, lev=0).values.copy()
                self._chla_attrs = dict(ds["chla"].attrs)
                self._chla_encoding = dict(ds["chla"].encoding)

                # Determine observation date from coordinate or metadata
                if "time" in ds.coords and ds["time"].size > 0:
                    time_val = str(ds["time"].values[0])
                    self._obs_date = time_val.split("T")[0]
                elif active_meta.get("observation_date"):
                    self._obs_date = active_meta["observation_date"]
                else:
                    self._obs_date = "2026-09-03"

            self.filepath = target_path
            self._is_loaded = True
            logger.info("mosdac_netcdf_loaded", extra={"filepath": self.filepath, "date": self._obs_date})
            return True
        except Exception as exc:
            logger.error("mosdac_netcdf_load_failed", extra={"error": str(exc), "filepath": target_path})
            self._is_loaded = False
            self._ds = None
            self._chla = None
            return False

    def get_chlorophyll(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Extract Chlorophyll-A at the nearest MOSDAC grid cell for a given coordinate.

        Args:
            latitude: Decimal latitude (-90 to +90)
            longitude: Decimal longitude (-180 to +180 or 0 to 360)

        Returns:
            Structured dictionary with coordinate metadata, chlorophyll value, distance, and status.
        """
        # 1. Validate coordinates
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 360.0):
            return {
                "source": "MOSDAC",
                "parameter": "chlorophyll_a",
                "requested_latitude": latitude,
                "requested_longitude": longitude,
                "normalized_longitude": None,
                "grid_latitude": None,
                "grid_longitude": None,
                "value": None,
                "unit": None,
                "unit_notes": "Unit metadata not explicitly provided by this NetCDF variable.",
                "observation_date": None,
                "grid_distance_km": None,
                "status": "invalid_coordinates",
                "error": f"Coordinates out of bounds: lat={latitude}, lon={longitude}",
            }

        # 2. Ensure dataset is loaded
        if not self.load_dataset() or (self._chla is None and self._ds is None) or self._lats is None or self._lons is None:
            return {
                "source": "MOSDAC",
                "parameter": "chlorophyll_a",
                "requested_latitude": latitude,
                "requested_longitude": longitude,
                "normalized_longitude": None,
                "grid_latitude": None,
                "grid_longitude": None,
                "value": None,
                "unit": None,
                "unit_notes": "Unit metadata not explicitly provided by this NetCDF variable.",
                "observation_date": None,
                "grid_distance_km": None,
                "status": "unavailable",
                "error": f"MOSDAC NetCDF file unavailable at {self.filepath}",
            }

        # Validate latitude within dataset spatial coverage
        lat_min = float(self._lats.min())
        lat_max = float(self._lats.max())
        if not (lat_min <= latitude <= lat_max):
            return {
                "source": "MOSDAC",
                "parameter": "chlorophyll_a",
                "requested_latitude": latitude,
                "requested_longitude": longitude,
                "normalized_longitude": None,
                "grid_latitude": None,
                "grid_longitude": None,
                "value": None,
                "unit": None,
                "unit_notes": "Unit metadata not explicitly provided by this NetCDF variable.",
                "observation_date": self._obs_date,
                "grid_distance_km": None,
                "status": "invalid_coordinates",
                "error": f"Latitude {latitude} outside dataset bounds [{lat_min:.2f}, {lat_max:.2f}]",
            }

        # 3. Normalize longitude: convert negative to [0, 360) without modifying positive
        is_negative = longitude < 0.0
        normalized_lon = (longitude % 360.0) if is_negative else longitude
        normalized_lon = round(normalized_lon, 4)

        # 4. Find nearest grid cell indices
        lat_idx = int(np.abs(self._lats - latitude).argmin())
        lon_idx = int(np.abs(self._lons - normalized_lon).argmin())

        grid_lat = float(self._lats[lat_idx])
        grid_lon = float(self._lons[lon_idx])

        # 5. Extract chla accounting for dimensions: ('time', 'lev', 'lat', 'lon')
        if hasattr(self, "_chla") and self._chla is not None:
            raw_val = float(self._chla[lat_idx, lon_idx])
            unit_attr = self._chla_attrs.get("units") if hasattr(self, "_chla_attrs") else None
            fill_attr = (
                self._chla_attrs.get("_FillValue") if hasattr(self, "_chla_attrs") else None
            ) or (
                self._chla_encoding.get("_FillValue") if hasattr(self, "_chla_encoding") else None
            )
        elif self._ds is not None:
            raw_val = float(self._ds["chla"].isel(time=0, lev=0, lat=lat_idx, lon=lon_idx).values)
            unit_attr = self._ds["chla"].attrs.get("units")
            fill_attr = self._ds["chla"].attrs.get("_FillValue") or self._ds["chla"].encoding.get("_FillValue")
        else:
            return {
                "source": "MOSDAC",
                "parameter": "chlorophyll_a",
                "requested_latitude": latitude,
                "requested_longitude": longitude,
                "status": "unavailable",
                "error": "Dataset is not loaded in memory",
            }

        # 6. Calculate great-circle distance
        dist_km = haversine_distance_km(latitude, longitude, grid_lat, grid_lon)

        # 7. Check unit metadata truthfulness (do not fabricate units)
        unit_str = str(unit_attr).strip() if unit_attr and str(unit_attr).strip() else None
        unit_notes = "Unit metadata not explicitly provided by this NetCDF variable." if unit_str is None else ""

        # 8. Detect fill / missing values
        is_fill = (
            np.isnan(raw_val)
            or np.isinf(raw_val)
            or raw_val <= FILL_VALUE_THRESHOLD
            or (fill_attr is not None and abs(raw_val - float(fill_attr)) < 1e-3)
        )

        if is_fill:
            logger.info("mosdac_grid_fill_value_detected", extra={"lat": latitude, "lon": longitude, "raw": raw_val})
            return {
                "source": "MOSDAC",
                "parameter": "chlorophyll_a",
                "requested_latitude": latitude,
                "requested_longitude": longitude,
                "normalized_longitude": normalized_lon,
                "grid_latitude": round(grid_lat, 4),
                "grid_longitude": round(grid_lon, 4),
                "value": None,
                "raw_value": raw_val,
                "unit": unit_str,
                "unit_notes": unit_notes,
                "observation_date": self._obs_date,
                "grid_distance_km": dist_km,
                "status": "no_data",
                "error": "Selected grid point contains fill/missing value (-999000000.0).",
            }

        retrieved_at = self._active_metadata.get("retrieved_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        data_age_hours = self._active_metadata.get("data_age_hours")
        freshness = self._active_metadata.get("freshness", "stale")

        return {
            "source": "MOSDAC",
            "parameter": "chlorophyll_a",
            "requested_latitude": latitude,
            "requested_longitude": longitude,
            "normalized_longitude": normalized_lon,
            "grid_latitude": round(grid_lat, 4),
            "grid_longitude": round(grid_lon, 4),
            "value": round(raw_val, 4),
            "unit": unit_str,
            "unit_notes": unit_notes,
            "observation_date": self._obs_date,
            "grid_distance_km": dist_km,
            "data_age_hours": data_age_hours,
            "freshness": freshness,
            "data_source_type": self._active_metadata.get("data_source_type", "archive"),
            "file_path": self.filepath,
            "retrieved_at": retrieved_at,
            "status": "success",
        }

    def close(self):
        """Close dataset file handle and release memory."""
        if self._ds is not None:
            try:
                self._ds.close()
            except Exception:
                pass
            self._ds = None
        self._lats = None
        self._lons = None
        self._chla = None
        self._chla_attrs = {}
        self._chla_encoding = {}
        self._is_loaded = False
        import gc
        gc.collect()


# Singleton service instance
mosdac_service = MosdacService()
