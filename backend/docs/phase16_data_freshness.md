# ORCA — Phase 16: Cross-Agent Data Freshness & Source Reliability

## 1. Architecture Overview

Phase 16 equips ORCA with an intelligent, deterministic cross-agent data freshness and source reliability evaluation engine. Prior to Phase 16, individual specialist agents maintained disparate, ad-hoc freshness heuristics or static strings. Phase 16 introduces a centralized provenance evaluation service (`DataFreshnessService`), normalized evidence metadata schemas (`EvidenceMetadata`), deterministic source reliability scoring, cross-agent signal conflict detection, and strict safety supremacy across the multi-agent graph.

```
USER QUERY / CHATBOT
        │
        ▼
   COORDINATOR
        │
   ┌────┴───────────────────────────────┐
   │                                    │
   ▼                                    ▼
EO AGENT                            OCEAN AGENT               WEATHER AGENT
[MOSDAC E06OCM_L4_AC]               [INCOIS ERDDAP]           [IMD Coastal Bulletin]
   │                                    │                          │
   └───────────────────┬────────────────┴──────────────────────────┘
                       ▼
           DATA FRESHNESS SERVICE
       (Calculates observation age &
        parameter-aware freshness tiers)
                       │
                       ▼
          MARINE ANALYSIS AGENT
       (Cross-agent evidence fusion,
        deterministic reliability scoring,
        signal conflict detection,
        safety supremacy decision)
                       │
                       ▼
            FINAL REASONING AGENT
       (Honest uncertainty disclosure,
        stale data acknowledgment,
        ecological indicator context)
                       │
                       ▼
               API / FRONTEND
```

---

## 2. Parameter-Aware Freshness Calculation

A core operational principle established in Phase 16 is that **not all marine parameters have the same acceptable lifespan**. Applying uniform age thresholds across heterogeneous oceanographic phenomena produces dangerous false alarms or hazardous complacency:

| Parameter Category | Parameters | FRESH Window | RECENT Window | STALE Window | VERY_STALE Window | Scientific Justification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Weather** | `wind_speed`, `air_temperature`, `visibility`, `sea_condition` | $\le 3$ hours | $\le 12$ hours | $\le 24$ hours | $> 24$ hours | Atmospheric weather dynamics evolve rapidly in coastal marine environments. Observations $> 12$ hours old cannot guide real-time tactical operations. |
| **Ocean / SST** | `sea_surface_temperature`, `significant_wave_height`, `ocean_surface_wind_speed` | $\le 12$ hours | $\le 24$ hours | $\le 48$ hours | $> 48$ hours | Ocean surface temperatures and wind-waves change on diurnal and synoptic tidal cycles. |
| **Chlorophyll-A** | `chlorophyll_a` | $\le 24$ hours | $\le 72$ hours | $\le 168$ hours | $> 168$ hours | Oceansat-3 (EOS-06) Level-4 composite products (`E06OCM_L4_AC`) incorporate satellite orbital revisit latency and cloud-clearing processing. 24–72 hours is typical for L4 composites. |
| **Geofence / Safety** | `boundary_proximity`, `maritime_boundary` | $\le 720$ hours (30 d) | $\le 2160$ hours (90 d) | $\le 8760$ hours (1 yr) | $> 8760$ hours | Maritime EEZ boundaries, international maritime boundary lines (IMBL), and security perimeters are legally static. |
| **Default / Other** | All unlisted parameters | $\le 24$ hours | $\le 48$ hours | $\le 168$ hours | $> 168$ hours | Conservative marine observation fallback. |

The freshness calculation is implemented in `app/services/data_freshness_service.py` using injectable reference times (`reference_time`) to guarantee deterministic testing without clock dependencies.

---

## 3. Physical Observation Time vs. System Retrieval Time

ORCA strictly decouples sensor observation time from local system ingestion/download time:

* **Observation Time (`observation_time`)**: The exact physical moment when the satellite instrument (e.g., OCM-3 sensor) or marine station recorded the physical state.
* **Retrieval Time (`retrieval_time`)**: The system timestamp when the ORCA backend downloaded or retrieved the dataset.

**Rule**: Data age (`age_hours`) and freshness tier are **strictly calculated from `observation_time`**.
A satellite file downloaded 5 minutes ago containing an observation from 4 days ago is **4 days old (STALE)**, never 5 minutes old. Both timestamps are faithfully preserved in `EvidenceMetadata`.

---

## 4. Deterministic Source Reliability Scoring

Source reliability is computed deterministically rather than through non-deterministic AI heuristics. The scoring matrix evaluates:
1. **Source Provenance / Type**:
   * `remote_authenticated` (e.g. authenticated MOSDAC SSO download): Base reliability `HIGH`.
   * `live` (e.g. live INCOIS ERDDAP API): Base reliability `HIGH`.
   * `archive` (e.g. local verified NetCDF baseline): Base reliability `MEDIUM`.
   * `simulated` / `demo` (e.g. regional fallback model): Base reliability `LOW`.
   * `unavailable`: Reliability `UNKNOWN`.
2. **Freshness Degradation**:
   * `VERY_STALE` observations automatically degrade reliability to `LOW` regardless of source authority.
   * `STALE` observations degrade `HIGH` authority to `MEDIUM`.
3. **Spatial Relevance**:
   * Nearest grid lookups exceeding $50.0\text{ km}$ distance from the requested position flag spatial divergence warnings.

---

## 5. Cross-Agent Signal Conflict Detection

The `MarineAnalysisAgent` and `MarineAnalysisService` continuously audit multi-agent data streams for meaningful domain discrepancies. Configurable physical tolerances prevent false alarms from micro-variations:

1. **Surface Wind Discrepancy**:
   * Trigger: $| \text{Weather Wind} - \text{Ocean Scatterometer Wind} | \ge 8.0\text{ knots}$.
   * Rationale: Atmospheric model vs. ocean surface radar scatterometer discrepancy indicates changing squall conditions.
2. **Ground Swell vs. Calm Local Wind**:
   * Trigger: `significant_wave_height` $\ge 2.0\text{ m}$ while weather wind $< 15.0\text{ knots}$ and reported as "Calm" or "Smooth".
   * Rationale: Distant deep-ocean depressions generate dangerous long-period ground swells that break hazards onto shores even during calm local winds.
3. **Thermal Divergence**:
   * Trigger: Air temperature vs. sea surface temperature divergence $\ge 3.0^\circ\text{C}$ from regional norms.
4. **Calm Conditions vs. Navigational Hazard**:
   * Trigger: Weather and ocean are calm, but safety agent detects boundary breach or security zone proximity.

When a conflict is detected:
* `conflict_detected = True`
* Conflicting sources, parameters, and plain-language explanation are recorded in `MarineAnalysisResult.conflicts`.

---

## 6. Safety Supremacy & Missing-Data Behavior

### Safety Supremacy
Under no circumstances can favorable ecological parameters (e.g. high Chlorophyll-A indicating phytoplankton productivity) override:
* High or critical maritime safety alerts (boundary breach, naval exclusion zones).
* Dangerous marine weather advisories (high wind, storm warnings).
* Rough sea states ($\ge 2.0\text{ m}$ wave heights).

The operational hierarchy strictly enforces:
$$\text{Safety Proximity} \succ \text{Weather / Ocean Hazards} \succ \text{Data Freshness / Reliability} \succ \text{Ecological Context}$$

### Truthful Missing-Data Handling
When a specialist data source is offline or unavailable:
* Missing parameters are explicitly recorded in `missing_parameters`.
* Zero is **never** substituted for missing telemetry.
* Missing live weather or ocean feeds fall back to explicitly labeled simulated/demonstration records (`data_source_type: "simulated"`), never masquerading as live telemetry.

---

## 7. Verification & Test Suite

The Phase 16 implementation was validated with 11 targeted unit and integration tests in `tests/test_phase16_data_freshness.py`:

* `test_01_freshness_tiers_deterministic`: Validates FRESH, RECENT, STALE, VERY_STALE, and UNKNOWN with injectable reference timestamps.
* `test_02_observation_vs_retrieval_time`: Confirms age is calculated from physical satellite acquisition, not download time.
* `test_03_parameter_aware_thresholds`: Validates distinct thresholds across weather, ocean, chlorophyll, and geofence.
* `test_04_source_reliability_scoring`: Tests deterministic reliability scoring.
* `test_05_mosdac_evidence_normalization`: Confirms dataset `E06OCM_L4_AC` and `remote_authenticated` distinction.
* `test_06_missing_weather_handling`: Ensures fallback feeds are strictly labeled `simulated`.
* `test_07_missing_ocean_handling`: Confirms structured unavailable responses without fake numbers.
* `test_08_conflicting_evidence_detection`: Verifies detection of ground swell conflicts.
* `test_09_safety_override_favorable_chlorophyll`: Proves safety risk unconditionally overrides favorable chlorophyll.
* `test_10_parallel_state_preservation`: Verifies LangGraph isolated node state slots.
* `test_11_final_reasoning_stale_data_reduced_confidence`: Validates confidence reduction for stale data.

### Regression Results
* **Focused Phase 16 suite**: 11 / 11 passed (100%).
* **Full backend regression**: 339 / 339 passed (100%).

---

## 8. Real ORCA Integration Verification

Direct end-to-end verification queries were executed against the live ORCA FastAPI backend:

1. **Chlorophyll Query**: `"What is the current chlorophyll concentration near Chennai?"`
   * HTTP 200. Real MOSDAC NetCDF extraction: `0.0885`, observed `2026-09-03` at nearest grid `13.012° N, 80.25° E` (8.18 km). Freshness: `RECENT`.
2. **SST Query**: `"What is the SST near Chennai?"`
   * HTTP 200. Sea surface temperature `~29.99°C`, winds `8.02 m/s`.
3. **Weather Query**: `"What is the weather near Chennai?"`
   * HTTP 200. Explicitly labeled coastal condition with SW winds `12.0 knots`.
4. **Cross-Agent Reasoning Query**: `"Can I go fishing near Chennai today?"`
   * HTTP 200. Fused analysis with clear disclaimer: *"Chlorophyll-A serves as an environmental biological productivity indicator, but this alone does not guarantee fish presence."*

---

## 9. Known Limitations

1. **Satellite Cloud Obscuration**: Oceansat-3 OCM-3 optical sensor cannot penetrate heavy cloud cover during tropical monsoons, necessitating composite L4 products with 1–3 day latency.
2. **Offline Mode**: In offline/airgapped environments, the system utilizes local verified NetCDF archives with transparent `archive` or `simulated` provenance tags.
