"""
Unit tests for MosdacService (Phase 10 — Step 10).
Tests coordinate validation, nearest grid extraction, longitude conversion,
fill value handling, and structured output.
"""
import pytest
from app.services.mosdac_service import MosdacService, haversine_distance_km


@pytest.fixture(scope="module")
def mosdac_svc():
    svc = MosdacService()
    yield svc
    svc.close()


def test_mosdac_service_mumbai(mosdac_svc):
    """Test 1: Mumbai (19.0760, 72.8777)."""
    res = mosdac_svc.get_chlorophyll(19.0760, 72.8777)
    assert res["status"] == "success"
    assert res["source"] == "MOSDAC"
    assert res["parameter"] == "chlorophyll_a"
    assert res["requested_latitude"] == 19.0760
    assert res["requested_longitude"] == 72.8777
    assert res["normalized_longitude"] == 72.8777
    assert res["grid_latitude"] == 19.016
    assert res["grid_longitude"] == 73.0
    assert res["value"] == 0.0000  # Land mask
    assert res["unit"] is None
    assert "Unit metadata not explicitly provided" in res["unit_notes"]
    assert res["observation_date"] in ("2026-09-03", "2026-09-04", "2026-09-05")
    assert res["grid_distance_km"] < 25.0


def test_mosdac_service_chennai(mosdac_svc):
    """Test 2: Chennai (13.0827, 80.2707)."""
    res = mosdac_svc.get_chlorophyll(13.0827, 80.2707)
    assert res["status"] == "success"
    assert res["source"] == "MOSDAC"
    assert res["parameter"] == "chlorophyll_a"
    assert res["requested_latitude"] == 13.0827
    assert res["requested_longitude"] == 80.2707
    assert res["grid_latitude"] == 13.012
    assert res["grid_longitude"] == 80.25
    assert res["value"] in (0.0885, 0.0882, 0.0909)
    assert res["observation_date"] in ("2026-09-03", "2026-09-04", "2026-09-05")
    assert res["grid_distance_km"] < 15.0


def test_mosdac_service_kolkata(mosdac_svc):
    """Test 3: Kolkata (22.5726, 88.3639)."""
    res = mosdac_svc.get_chlorophyll(22.5726, 88.3639)
    assert res["status"] == "success"
    assert res["grid_latitude"] == 22.522
    assert res["grid_longitude"] == 88.25
    assert res["value"] == 0.0000  # Inland land mask
    assert res["observation_date"] in ("2026-09-03", "2026-09-04", "2026-09-05")
    assert res["grid_distance_km"] < 20.0


def test_mosdac_service_negative_longitude(mosdac_svc):
    """Test 4: Negative longitude (25.0, -70.0 -> 290.0)."""
    res = mosdac_svc.get_chlorophyll(25.0000, -70.0000)
    assert res["status"] == "success"
    assert res["requested_latitude"] == 25.0
    assert res["requested_longitude"] == -70.0
    assert res["normalized_longitude"] == 290.0
    assert res["grid_latitude"] == 25.038
    assert res["grid_longitude"] == 290.0
    assert res["value"] in (0.0343, 0.0355)
    assert res["observation_date"] in ("2026-09-03", "2026-09-04", "2026-09-05")
    assert res["grid_distance_km"] < 10.0


def test_mosdac_service_invalid_coordinates(mosdac_svc):
    """Out-of-bounds latitude should return invalid_coordinates status."""
    res = mosdac_svc.get_chlorophyll(95.0, 72.0)
    assert res["status"] == "invalid_coordinates"
    assert res["value"] is None

    res2 = mosdac_svc.get_chlorophyll(19.0, 400.0)
    assert res2["status"] == "invalid_coordinates"
    assert res2["value"] is None


def test_mosdac_service_unavailable_file():
    """Service with non-existent file path should return status unavailable."""
    svc = MosdacService(filepath=r"C:\nonexistent_path\nonexistent_file.nc")
    res = svc.get_chlorophyll(19.0, 72.0)
    assert res["status"] == "unavailable"
    assert res["value"] is None
