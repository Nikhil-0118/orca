# ORCA Phase 15 — Authenticated MOSDAC Automatic Data Ingestion

## 1. MOSDAC Official Download API Overview

ISRO Space Applications Centre (SAC) provides an official Python Data Download API client for MOSDAC:
- **Client Package**: `mdapi.zip` downloaded directly from the official MOSDAC portal (`https://www.mosdac.gov.in/software/mdapi.zip`).
- **Core Components**:
  - `mdapi.py`: Official command-line and API client script implementing the SSO authentication, catalog search, file download with progress streaming, and session logout.
  - `config.json`: Configuration template defining user credentials, catalog query parameters, bounding box filtering, and download destination.
- **Protocol & Transport**: Communicates over HTTPS using Python's `requests` library. MOSDAC enforces SSO session authentication, rate-limits downloads (documented maximum 5,000 files per user per day), and validates user dataset permissions.

---

## 2. Authentication Model

MOSDAC utilizes SSO (Single Sign-On) credentials:
- **Authentication Handshake**: `mdapi.py` sends user credentials (`username` and `password`) to the MOSDAC SSO authentication endpoint.
- **Session Tokens**: Upon successful authentication, a session cookie / token is issued and reused for subsequent authenticated download requests.
- **Session Termination**: At the conclusion of catalog interactions, `mdapi.py` dispatches a logout request to cleanly release backend server sessions.
- **Process Isolation**: To prevent any possibility of official client errors (such as unexpected `sys.exit(1)`) crashing the ORCA FastAPI web process, ORCA executes `mdapi.py` in an isolated temporary subprocess using an ephemeral configuration file that is wiped immediately upon completion.

---

## 3. Verified Dataset ID

Through verification against the live MOSDAC Open Catalog API (`https://mosdac.gov.in/apios/datasets.json`), the exact operational dataset identifier for the Level-4 Analyzed Chlorophyll product was confirmed:

- **Product Name**: Oceansat-2 / EOS-06 Level-4 Analyzed Chlorophyll-A Concentration (25 km Global Grid)
- **Dataset ID (`datasetId`)**: `E06OCM_L4_AC`
- **Sample Verified NetCDF**: `E06OCML4AC_20260903_25km_v1.0.1.nc`
- **Variable Structure**:
  - Spatial Coordinates: `lat` (1080 points, -81.08° to 89.95°), `lon` (1440 points, 0.0° to 359.75°)
  - Temporal Dimension: `time` (daily composite)
  - Target Variable: `chla` (float32 array, fill value `-999000000.0`)
  - Explicit Units: None (preserved faithfully as `unit = None`)

---

## 4. Environment Variables

All MOSDAC ingestion configurations are managed strictly via backend environment variables. **No credentials or secrets are ever exposed to the frontend or stored in code.**

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `MOSDAC_USERNAME` | `str` | `""` | MOSDAC registered SSO username (backend only). |
| `MOSDAC_PASSWORD` | `str` | `""` | MOSDAC registered SSO password (backend only). |
| `MOSDAC_DATASET_ID` | `str` | `"E06OCM_L4_AC"` | Official MOSDAC dataset ID for Level-4 Chlorophyll. |
| `MOSDAC_AUTO_DOWNLOAD_ENABLED` | `bool` | `false` | Master toggle for automated remote acquisition. |
| `MOSDAC_DOWNLOAD_DIR` | `str` | `C:\home\sys_oper\MOSDAC_Downloads` | Destination directory for downloaded NetCDF files. |
| `MOSDAC_LOOKBACK_DAYS` | `int` | `3` | Query window lookback in days to account for processing latency. |
| `MOSDAC_DOWNLOAD_COUNT` | `int` | `1` | Maximum number of files to ingest per download batch. |
| `MOSDAC_REFRESH_INTERVAL_HOURS` | `float` | `24.0` | Minimum duration between remote download attempts. |
| `MOSDAC_BOUNDING_BOX` | `str` | `"60,5,95,25"` | Bounding box (`minLon,minLat,maxLon,maxLat`) covering Indian maritime zones. |
| `MOSDAC_MAX_CACHED_FILES` | `int` | `2` | Maximum number of NetCDF files retained in the local cache. |

---

## 5. Download Flow

```text
User / Orchestrator Query
           │
           ▼
  app/services/mosdac_service.py
           │
           ▼
  app/services/mosdac_downloader.py (get_active_dataset)
           │
           ├─► [Recent Valid Local File Exists & Fresh?] ──► Use Local Cache
           │
           └─► [Refresh Required & MOSDAC_AUTO_DOWNLOAD_ENABLED = true]
                     │
                     ▼
            app/services/mosdac_api_service.py
                     │
                     ▼
           [Account Lockout Check & Rate Limit Check]
                     │
                     ▼
          Create Staging Temp Directory
                     │
                     ▼
          Spawn official mdapi.py subprocess
          (with ephemeral config.json & auto-shred)
                     │
            ┌────────┴────────┐
            ▼                 ▼
         Success           Failure
            │                 │
            ▼                 ▼
     Validate NetCDF    Log Redacted Error
     (xarray, chla)     Fall back to latest valid local .nc
            │
            ├─► Invalid ──► Prune Staging ──► Use Local Fallback
            │
            └─► Valid
                  │
                  ▼
          Windows-Safe Atomic Promotion (promote_downloaded_file)
          - Closes all file handles across services & runs gc.collect()
          - Copies staging file to <filename>.tmp in cache dir
          - Performs atomic os.replace() with bounded exponential retries
          - If locked by OS: preserves existing valid dataset as fallback
                  │
                  ▼
          Apply Cache Retention (enforce_retention)
          (prune older .nc > MOSDAC_MAX_CACHED_FILES)
                  │
                  ▼
          Activate New Dataset (data_source_type: "remote_authenticated")
```

---

## 5.1 Windows File Locking & Promotion Safety

On Windows operating systems, attempting to replace a file via `os.replace()` while any process (such as a web server or concurrent thread) holds an open file handle results in `PermissionError: [WinError 5] Access is denied` or `[WinError 32] Sharing violation`.

ORCA overcomes this with a robust two-layer solution:
1. **Immediate Handle Closure & Memory Caching**:
   `MosdacService.load_dataset()` opens the NetCDF dataset using a context manager (`with xr.open_dataset(...) as ds:`) and copies the coordinate arrays (`lat`, `lon`) and the 2D Chlorophyll-A slice into memory. The underlying NetCDF file handle is closed immediately upon load. Subsequent coordinate lookups operate purely in RAM at sub-millisecond speeds without locking the underlying file on disk.
2. **Bounded Retry Promotion (`promote_downloaded_file`)**:
   During dataset updates, `promote_downloaded_file()` invokes `mosdac_service.close()` and triggers garbage collection before attempting `os.replace()`. If a temporary filesystem lock is encountered, it retries up to 5 times with bounded backoff. If promotion cannot proceed, the existing validated dataset is preserved unharmed, temporary staging artifacts are scrubbed, and ORCA gracefully falls back without crashing.

---

---

## 6. Fallback Behavior

The local NetCDF archive system remains fully operational as a resilient, self-healing fallback layer:
1. **Prioritized Ingestion**: If `MOSDAC_AUTO_DOWNLOAD_ENABLED=true` and valid credentials exist, remote acquisition is attempted.
2. **Graceful Fallback**: If the remote download fails (network timeout, invalid credentials, service downtime, or dataset not yet compiled for today), ORCA automatically logs the sanitized reason and falls back to the newest valid local dataset (`E06OCML4AC_20260903_25km_v1.0.1.nc`).
3. **Transparent Reporting**: The metadata accurately reports `is_fallback: true` and `data_source_type: "archive"` so downstream reasoning agents (and the user) know the age and provenance of the data.
4. **No Fabricated Data**: If no valid local file is present and remote download fails, ORCA returns a structured `unavailable` status. Chlorophyll values are never invented.

---

## 7. Storage Retention Policy

To prevent storage exhaustion in persistent production environments, ORCA enforces an automated retention policy (`enforce_retention`):
- **Active & Rollback**: Retains the currently active dataset and the immediate predecessor as rollback (`MOSDAC_MAX_CACHED_FILES=2`).
- **Pruning**: Automatically deletes any older `.nc` files exceeding the retention limit.
- **Orphan Cleanup**: Deletes any orphaned `.tmp` staging artifacts left over from interrupted processes.
- **Safety**: Never deletes an active file before a replacement file has been fully downloaded and validated via `xarray`.

---

## 8. Data Freshness & Latency Classification

ORCA continuously tracks the observation timestamp against the current UTC clock:
- **Data Age Calculation**: Computed as `(now_utc - observation_time).total_seconds() / 3600.0`.
- **Classification**:
  - `fresh`: Data age is within `MOSDAC_MAX_FILE_AGE_HOURS` (default: 24.0 hours).
  - `stale`: Data age exceeds threshold due to satellite compilation cycles or archive replay.
  - `unavailable`: Observation time cannot be verified.
- **Honest Labeling**: Level-4 analyzed satellite products inherently involve multi-sensor compositing latency (~24 hours). ORCA never misrepresents delayed satellite analyses as instantaneous real-time observations.

---

## 9. Error Handling & Account Lockout Prevention

MOSDAC security policies enforce temporary account locks if multiple failed authentication attempts occur in succession. ORCA protects user accounts with robust guardrails:
- **Consecutive Failure Tracking**: Tracks consecutive authentication errors (`401 Unauthorized` / invalid credentials).
- **Lockout Cooldown**: Upon 3 consecutive authentication failures (`MAX_CONSECUTIVE_AUTH_FAILURES = 3`), ORCA triggers an automatic lockout cooldown (15 minutes), preventing any further login attempts until the cooldown expires.
- **Rate-Limiting Cooldown**: The `MOSDAC_REFRESH_INTERVAL_HOURS` (24h) guarantees that repeated queries from chatbot users do not flood MOSDAC with download calls.
- **Sanitized Logging**: All exceptions, standard error streams, and process outputs are filtered through `_sanitize_text` to guarantee passwords never enter application logs.

---

## 10. Security Audit & Confidentiality

- **Strict Git Exclusion**: `.env` and `.env.local` are explicitly ignored by Git (`orca/.gitignore`).
- **Zero Credentials in Version Control**: No passwords or auth tokens exist in codebase source files, unit tests, or documentation.
- **Ephemeral Config Files**: The configuration file generated for `mdapi.py` exists only during the subprocess execution and is shredded immediately in a `finally:` block.
- **Redacted Payloads**: The `/api/query` response payload, LangGraph state, and agent reasoning traces exclude any authentication parameters.

---

## 11. How to Enable Automatic Download Locally

To configure and enable automatic authenticated MOSDAC ingestion on your local machine:

1. Copy `.env.example` to `.env` in `orca/backend/`:
   ```bash
   cp .env.example .env
   ```
2. Open `orca/backend/.env` in your local editor and populate your MOSDAC SSO credentials:
   ```env
   MOSDAC_USERNAME=your_mosdac_username
   MOSDAC_PASSWORD=your_mosdac_password
   MOSDAC_DATASET_ID=E06OCM_L4_AC
   MOSDAC_AUTO_DOWNLOAD_ENABLED=true
   MOSDAC_LOOKBACK_DAYS=3
   MOSDAC_DOWNLOAD_COUNT=1
   MOSDAC_REFRESH_INTERVAL_HOURS=24.0
   MOSDAC_BOUNDING_BOX=60,5,95,25
   ```
3. Restart the ORCA backend service:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
4. Perform a query (e.g., via the ORCA chatbot or `curl`):
   ```bash
   curl -X POST http://127.0.0.1:8000/api/query \
     -H "Content-Type: application/json" \
     -d '{"query": "Give me chlorophyll data near Chennai", "session_id": "manual-test", "location": {"lat": 13.0827, "lon": 80.2707}}'
   ```

---

## 12. MOSDAC Account & Data-Access Policy Limitations

- **Account Approval**: General user accounts on MOSDAC may have restricted access to certain near-real-time (NRT) satellite streams until approved by SAC.
- **Product Latency**: Level-4 analyzed chlorophyll products (`E06OCM_L4_AC`) are compiled after orbit aggregation and typically lag real-time by 24 to 72 hours.
- **Daily Quota**: MOSDAC limits bulk downloads to 5,000 files per user per day. ORCA's search query sets `count = 1` and bounding box filtering to minimize bandwidth consumption.
- **Maintenance Windows**: MOSDAC services occasionally undergo scheduled maintenance; ORCA's local archive fallback ensures uninterrupted operation during outages.
