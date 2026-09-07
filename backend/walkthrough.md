# ORCA Phase 14: Marine Ecosystem Reasoning with Collaborative Agents

## 1. Overview & Objective
Phase 14 upgraded ORCA from a system that merely retrieves isolated specialist agent observations into a unified, evidence-based marine decision and cross-agent reasoning engine.

The orchestration pipeline now enforces:
```
User Query
   ↓
Chatbot / API (/api/query)
   ↓
Query Planner
   ↓
LangGraph Coordinator
   ↓
Parallel Specialist Agents (EO / MOSDAC, Ocean / INCOIS, Weather / IMD, Ecosystem)
   ↓
Safety Agent (Geofence, IMBL, restricted marine areas)
   ↓
Cross-Agent Marine Analysis Node (evidence normalization, conflict detection, condition synthesis, marine decision)
   ↓
RAG Agent (domain advisories)
   ↓
Final Reasoning Agent (synthesizes structured decision & evidence into fisherman-friendly answers)
   ↓
FastAPI Response
```

---

## 2. Key Modules Added & Modified

### New Modules
1. **`app/schemas/evidence.py`**:
   - `EvidenceItem`: Normalized data model supporting `source`, `agent`, `parameter`, `value`, `unit` (`None` permitted for unit-less NetCDF), `observation_time`, `retrieval_time`, `latitude`, `longitude`, `distance_km`, `freshness` (`fresh`, `recent`, `stale`, `unavailable`), `data_source_type`, `confidence`, `status`, `notes`.
   - `SignalConflict`: Records discrepancies (e.g. Weather 22 kt vs Ocean 5.8 kt) with conservative resolution.
   - `MarineDecision`: Structured recommendation (`GO`, `CAUTION`, `AVOID`, `INSUFFICIENT_DATA`), `risk_level`, `confidence`, `reasoning`, `supporting_evidence`, `warnings`, `missing_information`.
   - `MarineAnalysisResult`: Composite artifact containing all evidence items, condition interpretations, quality audit, conflicts, and the decision.

2. **`app/services/marine_analysis_service.py`**:
   - `extract_evidence_items`: Ingests and normalizes upstream observations from `eo_result`, `ocean_result`, `weather_result`, `safety_result`, `ecosystem_result`.
   - `detect_conflicts`: Analyzes cross-agent discrepancies (wind speed differences, boundary vs calm sea discrepancies) and records conservative safety resolutions without concealing conflicts.
   - `analyze_conditions`: Generates cautious scientific domain interpretations without unsupported guarantees of fish catch.
   - `compute_marine_decision`: Implements the safety-first decision hierarchy where navigational boundary hazards strictly override calm weather and favorable chlorophyll.
   - `run_analysis`: Orchestrates the complete pipeline.

3. **`app/agents/marine_analysis_agent.py`**:
   - LangGraph node `marine_analysis_node(state: OrcaState) -> dict`, producing `marine_analysis_result` and `marine_decision`.

4. **`docs/phase14_marine_decision_model.md`**:
   - Complete 9-part developer and operator specification detailing agent contributions, freshness tiers, spatial math, conflict handling, safety supremacy, and deterministic vs LLM boundaries.

### Modified Modules
1. **`app/core/state.py`**:
   - Extended `OrcaState` with `marine_analysis_result: Optional[dict]` and `marine_decision: Optional[dict]`.
2. **`app/core/graph.py`**:
   - Wired `analysis_node` into the workflow between `safety_node` and `rag_node`, preserving parallel fan-out of specialist agents.
3. **`app/agents/final_reasoning_agent.py`**:
   - Updated system prompts and LLM prompt builder to consume `cross_agent_marine_analysis` and `marine_decision`.
   - Enhanced deterministic fallback handler to format decision recommendations (`Recommendation: GO / CAUTION / AVOID / INSUFFICIENT DATA`), supporting reasons, and chlorophyll-A primary productivity caveats.
4. **`app/services/planner.py`**:
   - Handled general `"marine conditions"` queries by routing to both Ocean and Weather specialists.

---

## 3. Test Suite Verification

### Phase 14 Test Suite (`tests/test_phase14_cross_agent_reasoning.py`)
All 10 Phase 14 tests pass:
- **Test 1**: Multi-agent fishing query near Chennai (`GO`/`CAUTION`, multiple evidence items, no fabricated values) -> **PASS**
- **Test 2**: Factual SST query near Chennai (factual SST response, no forced fishing decision) -> **PASS**
- **Test 3**: Weather suitability query (considers both weather and ocean) -> **PASS**
- **Test 4**: Safety hazard prioritization (safety hazard forces `AVOID` despite calm weather) -> **PASS**
- **Test 5**: MOSDAC unavailable handling (marked unavailable truthfully, no fabricated chlorophyll) -> **PASS**
- **Test 6**: Weather unavailable handling (reduced confidence, `INSUFFICIENT_DATA` if critical) -> **PASS**
- **Test 7**: Stale MOSDAC NetCDF data (freshness marked `stale`, weight reduced, never claimed real-time) -> **PASS**
- **Test 8**: Signal conflict detection (wind discrepancy detected, higher wind retained conservatively) -> **PASS**
- **Test 9**: No location query (graceful handling, no invented coordinates) -> **PASS**
- **Test 10**: General educational marine question (informative answer on phytoplankton/chlorophyll, no forced operational decision) -> **PASS**

### Core Regression Suite
- 114 passed, 0 failed in 92 seconds.
- Full system audit (all 312 unit/integration tests) passed with 100% success rate.

---

## 4. Live API Verification (Step 21)

Executed against live FastAPI server at `http://127.0.0.1:8000/api/query`:

| Query | HTTP Status | Evidence & Synthesis Summary | Status |
| :--- | :--- | :--- | :--- |
| 1. *"Give me chlorophyll data near Chennai"* | 200 | MOSDAC Chlorophyll-A `0.0885`, NetCDF observation date `2026-09-03`, grid `13.012° N, 80.25° E`, unit metadata preserved as `None`. | **VERIFIED** |
| 2. *"What is the sea surface temperature near Chennai?"* | 200 | INCOIS ERDDAP SST `~29.99°C`, moderate sea state. Pure factual response without forced fishing decision. | **VERIFIED** |
| 3. *"What is the weather near the Chennai coast?"* | 200 | IMD coastal report (SW moderate winds 12 kt, visibility 8 km, smooth to slight). | **VERIFIED** |
| 4. *"Can I go fishing near Chennai today?"* | 200 | Combines Ocean, Weather, Safety, and EO. `Recommendation: GO (Favorable conditions)`. Explicitly notes chlorophyll is an ecological indicator, not a guarantee of fish catch. | **VERIFIED** |
| 5. *"Is this location safe for fishing?"* | 200 | Evaluates geodesic boundaries and maritime risks. Low assessed risk (0/100) with clear operational limits. | **VERIFIED** |
