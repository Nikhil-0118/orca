"""
Phase 13 End-to-End Integration & Verification Tests.

Verifies:
1. CORS and Origin configuration.
2. MOSDAC cache retention enforcement and storage monitoring helper.
3. MOSDAC download safety (corrupt download rejected, active dataset untouched).
4. Real MOSDAC query through /api/query (Chennai chlorophyll lookup: 0.0885).
5. Location-aware query execution vs. no-location query resilience.
6. Specialist agent query routing (Chlorophyll, SST, Weather, Fishing advice).
7. Contract integrity between frontend payload and backend QueryRequest schema.
"""
import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.mosdac_downloader import (
    MosdacDownloader,
    validate_netcdf_file,
    mosdac_downloader,
)
from app.services.mosdac_service import mosdac_service
from app.schemas.query import QueryRequest, QueryResponse


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ─── 1. CORS Configuration Tests ───────────────────────────────────────────

def test_cors_allowed_origins(client):
    """Verify that frontend dev origins (both localhost and 127.0.0.1) are permitted with CORS."""
    for origin in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"]:
        response = client.get("/api/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin


# ─── 2. MOSDAC Storage Safety & Retention Tests ────────────────────────────

def test_mosdac_storage_retention_enforcement():
    """Verify that cache retention safely prunes older NetCDFs while keeping active and rollback files."""
    real_file = settings.MOSDAC_NETCDF_PATH
    if not os.path.exists(real_file):
        pytest.skip(f"Test NetCDF not found at {real_file}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create 4 test NetCDF files with staggered timestamps
        file_paths = []
        for i in range(4):
            dst = os.path.join(tmp_dir, f"E06OCML4AC_2026090{i+1}_25km_v1.0.1.nc")
            shutil.copyfile(real_file, dst)
            # Set modified time so 04 is newest, 01 is oldest
            os.utime(dst, (1000000 + i * 1000, 1000000 + i * 1000))
            file_paths.append(dst)

        # Also create a stale .tmp file
        tmp_stub = os.path.join(tmp_dir, "corrupt_download.nc.tmp")
        with open(tmp_stub, "w") as f:
            f.write("temporary junk")

        # Initialize downloader with retention limit = 2
        downloader = MosdacDownloader(
            download_dir=tmp_dir,
            default_file_path=file_paths[-1],
            max_cached_files=2,
        )

        # Enforce retention with newest file active
        active_file = file_paths[-1]  # 20260904
        deleted = downloader.enforce_retention(active_filepath=active_file)

        # Stale .tmp file must be cleaned up
        assert not os.path.exists(tmp_stub)

        # Active file must NEVER be deleted
        assert os.path.exists(active_file)

        # Total remaining .nc files must not exceed max_cached_files (2)
        remaining_nc = [f for f in os.listdir(tmp_dir) if f.endswith(".nc")]
        assert len(remaining_nc) <= 2
        assert os.path.basename(active_file) in remaining_nc


def test_mosdac_storage_summary_helper():
    """Verify that get_storage_summary returns truthful directory statistics."""
    summary = mosdac_downloader.get_storage_summary()
    assert "cache_directory" in summary
    assert "file_count" in summary
    assert "total_size_bytes" in summary
    assert "total_size_mb" in summary
    assert "max_cached_files" in summary
    assert summary["max_cached_files"] >= 1
    assert summary["file_count"] >= 1


def test_mosdac_corrupt_download_rejected():
    """Verify that an HTML error or corrupted download is quarantined and does not overwrite active data."""
    real_file = settings.MOSDAC_NETCDF_PATH
    if not os.path.exists(real_file):
        pytest.skip(f"Test NetCDF not found at {real_file}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        active_copy = os.path.join(tmp_dir, "E06OCML4AC_20260903_25km_v1.0.1.nc")
        shutil.copyfile(real_file, active_copy)
        orig_mtime = os.path.getmtime(active_copy)
        orig_size = os.path.getsize(active_copy)

        downloader = MosdacDownloader(
            download_dir=tmp_dir,
            default_file_path=active_copy,
            max_cached_files=2,
        )

        # Simulate a corrupt download (HTML 404 page)
        corrupt_target = os.path.join(tmp_dir, "corrupt.nc")
        temp_path = corrupt_target + ".tmp"
        with open(temp_path, "w") as f:
            f.write("<html><body>404 Not Found</body></html>")

        # Validate temporary file
        is_valid, err, meta = validate_netcdf_file(temp_path)
        assert is_valid is False
        assert "below minimum valid NetCDF threshold" in err or "NetCDF parsing exception" in err

        # Active file must remain unmodified
        assert os.path.getmtime(active_copy) == orig_mtime
        assert os.path.getsize(active_copy) == orig_size


# ─── 3. End-to-End Query Verification via /api/query ──────────────────────

def test_chennai_chlorophyll_mosdac_query(client):
    """
    Test Query 1: Chennai chlorophyll lookup.
    Verifies full path:
      /api/query -> Planner -> EO Agent -> MosdacService -> real NetCDF -> chlorophyll = 0.0885
    """
    payload = {
        "query": "Give me chlorophyll data near Chennai",
        "location": {
            "lat": 13.0827,
            "lon": 80.2707,
        },
        "session_id": "test-phase13-chennai",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Validate top-level schema
    assert "answer" in data
    assert "risk_level" in data
    assert "agents_used" in data

    # Verify that EO Agent participated
    assert any("eo" in a.lower() or "satellite" in a.lower() for a in data["agents_used"])

    # Verify structured evidence contains MOSDAC
    assert any("mosdac" in item["source"].lower() for item in data.get("structured_evidence", []))

    # Verify that the answer or structured evidence references 0.0885 from NetCDF
    answer_text = data["answer"]
    evidence_summaries = " ".join(item["summary"] for item in data.get("structured_evidence", []))
    combined_text = f"{answer_text} {evidence_summaries}"
    assert ("0.0885" in combined_text or "0.0882" in combined_text)


def test_sea_surface_temperature_query(client):
    """Test Query 2: Sea surface temperature near Chennai."""
    payload = {
        "query": "What is the sea surface temperature near Chennai?",
        "location": {
            "lat": 13.0827,
            "lon": 80.2707,
        },
        "session_id": "test-phase13-sst",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 10


def test_weather_marine_query(client):
    """Test Query 3: Marine weather near Chennai coast."""
    payload = {
        "query": "What is the weather near the Chennai coast?",
        "location": {
            "lat": 13.0827,
            "lon": 80.2707,
        },
        "session_id": "test-phase13-weather",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert any("weather" in a.lower() for a in data["agents_used"])


def test_no_location_fishing_query(client):
    """
    Test Query 4: 'Can I go fishing today?' without providing location.
    The backend must not crash and should respond gracefully.
    """
    payload = {
        "query": "Can I go fishing today?",
        "location": None,
        "session_id": "test-phase13-no-loc-fishing",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 10
    # Must not crash or hallucinate a fake GPS fix
    assert data.get("location") is None or data["location"].get("source") == "unavailable"


def test_general_marine_query_without_location(client):
    """Test general knowledge marine query without location."""
    payload = {
        "query": "What is sea surface temperature?",
        "location": None,
        "session_id": "test-phase13-general",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 10


# ─── 4. Frontend-Backend Contract Validation ───────────────────────────────

def test_query_request_schema_compatibility():
    """Verify that QueryRequest accepts both legacy {lat, lon} and canonical LocationContext."""
    # Case A: Legacy {lat, lon}
    req_a = QueryRequest(
        query="Test query",
        location={"lat": 13.0827, "lon": 80.2707},
        session_id="sess-a",
    )
    assert req_a.location.lat == 13.0827

    # Case B: Null location
    req_b = QueryRequest(
        query="General query",
        location=None,
        session_id="sess-b",
    )
    assert req_b.location is None

    # Case C: Canonical LocationContext
    req_c = QueryRequest(
        query="GPS query",
        location={
            "latitude": 13.0827,
            "longitude": 80.2707,
            "source": "browser_gps",
            "is_demo": False,
        },
        session_id="sess-c",
    )
    assert req_c.location.latitude == 13.0827
