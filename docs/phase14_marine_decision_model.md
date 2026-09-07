# ORCA Phase 14: Marine Ecosystem Reasoning & Decision Engine

This document provides a comprehensive developer and operator reference for the ORCA cross-agent marine reasoning architecture introduced in Phase 14.

---

## 1. Contributing Agents

The Marine Decision Engine synthesizes observations across six specialized agents:

1. **Earth Observation (EO) Agent (`eo_agent.py` / `mosdac_service.py`)**:
   - Source: ISRO MOSDAC Satellite NetCDF-4 archives / local storage.
   - Parameter: Chlorophyll-A concentration (`chla`).
   - Units: Truthfully preserved as `None` when absent from NetCDF metadata; never artificially forced to `mg/m³`.
   - Provenance: Grid latitude, grid longitude, observation date, and haversine grid distance (`grid_distance_km`).

2. **Ocean Agent (`ocean_agent.py` / INCOIS Connector)**:
   - Sources: INCOIS ERDDAP / Open-Meteo Marine / OSF models.
   - Parameters: Sea Surface Temperature (SST in °C), significant wave height (m), swell direction/period, surface wind speed (m/s).

3. **Weather Agent (`weather_agent.py` / IMD Connector)**:
   - Sources: IMD coastal bulletins / Open-Meteo Weather models.
   - Parameters: Atmospheric wind speed (knots), wind direction, gust speeds, visibility (km), sea condition description, coastal squall/cyclone warnings.

4. **Safety Agent (`safety_agent.py` / `geofence_service.py`)**:
   - Sources: Geofence polygon databases (IMBL - International Maritime Boundary Line, protected marine sanctuaries, restricted naval zones, port security boundaries).
   - Parameters: Proximity status, distance to nearest border (`distance_km`), risk level (`low`, `moderate`, `high`, `critical`).

5. **Ecosystem Agent (`ecosystem_agent.py`)**:
   - Parameters: Trophic status (Oligotrophic, Mesotrophic, Eutrophic), phytoplankton bloom potential, secondary productivity indicators.

6. **RAG Agent (`rag_agent.py`)**:
   - Sources: Historical maritime advisories, seasonal fishing bans, regional fisheries knowledge.

---

## 2. Evidence Model & Freshness Handling

All raw agent outputs are ingested into a unified schema defined in `app/schemas/evidence.py`:
- `EvidenceItem`: Normalized observation containing source, agent, parameter, value, unit, observation_time, freshness, confidence, distance_km, and notes.

### Freshness Classification:
- **`fresh`**: Observation timestamp within the configured freshness threshold (default: ≤ 24 hours). Full weight in decision scoring.
- **`recent`**: Observation between 24 and 72 hours old. Moderately reduced weight.
- **`stale`**: Observation older than the threshold (e.g., MOSDAC archive NetCDF from past days).
  - Explicitly marked as `stale` in both internal state and user-facing explanations.
  - Weight and confidence are substantially reduced.
  - The system strictly forbids claiming stale data as "real-time" or "current live conditions".
- **`unavailable`**: Service returned null, timed out, or had no coverage for the coordinates.

---

## 3. Spatial Provenance & Grid Relevance

- The user requested coordinates (`requested_latitude`, `requested_longitude`) are strictly differentiated from the observation coordinates (`grid_latitude`, `grid_longitude`).
- The haversine formula calculates `grid_distance_km`.
- Observations located far from the requested area receive lower spatial confidence and an explicit caveat in the supporting evidence.
- The system never silently invents coordinates if a user query omits location; instead it requests clarification or marks location as unavailable.

---

## 4. Conflict Detection & Resolution

Marine datasets frequently originate from differing instruments (e.g., radar satellites, numerical models, coastal weather stations). The reasoning layer actively compares redundant parameters:

- **Wind Discrepancies**: If the Weather Agent reports high winds (e.g., 22 knots) while the Ocean Agent reports gentle breezes (e.g., 6 knots), the discrepancy is flagged as a `SignalConflict`.
- **Resolution Strategy**:
  1. Conservative Safety Principle: Operational decisions prioritize the more hazardous signal to protect lives and vessels.
  2. Transparency Rule: Conflicts are never hidden or silently averaged out. The system explicitly alerts the user: *"Wind conditions differ between available sources (Weather reports 22.0 kt, Ocean reports 5.8 kt); adhering to conservative higher wind estimate for safety."*

---

## 5. Missing Data Handling

- **Zero-Hallucination Policy**: If MOSDAC, Weather, or INCOIS fails, values are recorded as `None` with status `unavailable`.
- **Fault-Tolerant Continuation**: A failure in one sensor (e.g., satellite chlorophyll unavailable due to cloud cover or offline service) does not crash the pipeline. Remaining valid agents (Weather, Ocean, Safety) continue to contribute.
- **Critical Data Gates**: If atmospheric weather or safety boundaries are missing, the operational decision defaults to `INSUFFICIENT_DATA` rather than guessing a `GO` decision.

---

## 6. Safety-First Maritime Decision Hierarchy

Human safety at sea strictly dominates convenience, economic yield, or calm water:

1. **Boundary / Geofence Hazard**: If the vessel is within warning distance or crossing the International Maritime Boundary Line (IMBL), the decision is immediately and unconditionally forced to **`AVOID`** (`HIGH` risk), regardless of mirror-calm seas or high biological productivity.
2. **Severe Atmospheric Alert**: Cyclone warnings, gale alerts, or severe squalls immediately force **`AVOID`**.
3. **Environmental Optimism Overruled**: High chlorophyll concentrations or ideal sea surface temperatures NEVER override a safety hazard.

---

## 7. Biological Indicators vs. Fish Guarantees

Chlorophyll-A measures phytoplankton abundance through optical satellite remote sensing. It is an environmental foundation, NOT an active fish locator:
- **Scientific Honesty**: The system states that chlorophyll concentrations *"suggest biological productivity and primary trophic support, but do not guarantee fish presence or commercial catch."*
- **No Fabricated Fish Forecasts**: Potential Fishing Zones (PFZ) require coordinated thermal fronts and chlorophyll gradients; isolated chlorophyll readings are reported neutrally.

---

## 8. Decision Matrix (`compute_marine_decision`)

The deterministic engine evaluates conditions into four standard operational tiers:

| Recommendation | Risk Level | Primary Criteria |
| :--- | :--- | :--- |
| **`AVOID`** | `HIGH` / `CRITICAL` | Boundary violation / high proximity risk, gale/squall warnings, wind speed > 22 knots, wave height > 2.5 m, or critical conflicting hazard. |
| **`CAUTION`** | `MODERATE` | Moderate winds (15–22 knots), moderate wave heights (1.5–2.5 m), stale/partially missing secondary data, or approaching boundary buffer zone. |
| **`GO`** | `LOW` | All available safety, weather, and ocean signals indicate calm, safe conditions with fresh observations and no boundary alerts. |
| **`INSUFFICIENT_DATA`** | `UNKNOWN` | Missing critical meteorological or navigational safety data preventing a responsible assessment. |

---

## 9. Deterministic Rules vs. LLM Reasoning

To guarantee zero hallucinations and regulatory compliance, responsibilities are strictly decoupled:

### Deterministic Rules Engine:
- **Evidence Extraction**: Parsing and sanitizing raw dictionaries from upstream agents.
- **Freshness & Spatial Math**: Calculating time deltas and haversine distances.
- **Conflict Identification**: Numerical threshold comparisons across overlapping sensors.
- **Decision Calculation**: Evaluating risk boundaries, hard safety overrides, and assigning `GO / CAUTION / AVOID / INSUFFICIENT_DATA`.
- **Fail-Safe Fallbacks**: Formatted textual cards and decision matrices if LLMs are offline or unconfigured.

### LLM Final Reasoning Agent:
- **Conversational Synthesis**: Translating structured evidence and decision matrices into natural, respectful, fisherman-friendly explanations.
- **Direct-Answer-First Communication**: Leading with the operational bottom line before detailing contributing factors.
- **Contextual Adaptation**: Seamlessly switching between operational fishing assessments, factual oceanographic inquiries (SST only), and educational marine biology answers (phytoplankton importance) based on user intent.
