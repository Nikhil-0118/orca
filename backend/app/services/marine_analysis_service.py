"""
Cross-Agent Marine Analysis & Decision Service (Phase 14).

Performs:
1. Normalization of multi-agent observations into a Common Evidence Model.
2. Cross-agent environmental condition correlation (Chlorophyll, SST, Wind, Weather, Safety).
3. Data freshness and spatial relevance evaluation.
4. Signal conflict detection between divergent agent sources.
5. Safety-first marine decision reasoning (GO | CAUTION | AVOID | INSUFFICIENT_DATA).
6. Separation of analytical reasoning from natural language generation.
"""
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.state import OrcaState
from app.schemas.evidence import (
    EvidenceItem,
    EvidenceMetadata,
    FreshnessLevel,
    ReliabilityLevel,
    SignalConflict,
    MarineDecision,
    MarineAnalysisResult,
)
from app.services.data_freshness_service import data_freshness_service

logger = logging.getLogger("orca.services.marine_analysis")


def classify_query_intent(query: str) -> str:
    """
    Classify query intent to ensure decision engine activates only for decision-oriented queries.
    Returns: 'fishing' | 'safety' | 'weather' | 'ocean' | 'chlorophyll' | 'general'
    """
    q = (query or "").lower().strip()

    # Fishing decision intent
    fishing_patterns = [
        r"\bfish(?:es|ing)?\b",
        r"\bcatch\b",
        r"\bpfz\b",
        r"\bangling\b",
        r"\btrawler\b",
        r"where.*(?:find|are|get).*fish",
        r"best.*fish",
        r"which.*area.*fish",
        r"where.*should.*i.*fish",
        r"can i go",
        r"should i sail",
        r"safe to fish",
        r"good to fish",
        r"favorable.*fishing",
        r"fishing.*conditions",
    ]
    if any(re.search(pat, q) for pat in fishing_patterns):
        return "fishing"

    # Safety decision intent
    safety_patterns = [
        r"is it safe",
        r"is this safe",
        r"am i safe",
        r"danger",
        r"hazard",
        r"boundary",
        r"imbl",
        r"restricted",
        r"cyclone warning",
        r"rough sea",
    ]
    if any(re.search(pat, q) for pat in safety_patterns):
        return "safety"

    # Chlorophyll / Ocean color intent
    chla_patterns = [
        r"chlorophyll",
        r"chla",
        r"ocean color",
        r"phytoplankton",
        r"productivity",
        r"algae",
    ]
    if any(re.search(pat, q) for pat in chla_patterns):
        return "chlorophyll"

    # Weather intent
    weather_patterns = [
        r"\bweather\b",
        r"\brain\b",
        r"\bwind\b",
        r"\bgale\b",
        r"\bforecast\b",
        r"\bvisibility\b",
        r"atmospheric",
    ]
    if any(re.search(pat, q) for pat in weather_patterns):
        return "weather"

    # Ocean intent
    ocean_patterns = [
        r"\bsst\b",
        r"sea surface temp",
        r"water temp",
        r"wave",
        r"swell",
        r"sea state",
        r"current",
    ]
    if any(re.search(pat, q) for pat in ocean_patterns):
        return "ocean"

    return "general"


class MarineAnalysisService:
    """
    Cross-Agent Marine Reasoner and Decision Engine.
    Combines observations from Satellite EO, Ocean, Weather, and Safety agents
    into a structured, evidence-based marine analysis.
    """

    def extract_evidence_items(self, state: OrcaState) -> List[EvidenceItem]:
        """
        Extract normalized, truthfully-typed EvidenceItem objects across all agent outputs.
        Guarantees that unobserved/missing parameters are not fabricated and unit=None is preserved.
        """
        evidence: List[EvidenceItem] = []
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        eo = state.get("eo_result") or {}
        ocean = state.get("ocean_result") or {}
        weather = state.get("weather_result") or {}
        safety = state.get("safety_result") or {}
        ecosystem = state.get("ecosystem_result") or {}

        # ── 1. Satellite EO / MOSDAC Evidence ─────────────────────────────────
        is_mosdac = eo.get("source") in ("MOSDAC", "ISRO-MOSDAC") or eo.get("parameter") == "chlorophyll_a"
        if is_mosdac:
            val = eo.get("value")
            st = eo.get("status", "unavailable")
            src_name = eo.get("source") or "MOSDAC"
            src_type = eo.get("data_source_type", "archive")
            dataset_id = eo.get("dataset") or "E06OCM_L4_AC"
            obs_time = eo.get("observation_date") or eo.get("observation_time") or (eo.get("data_time") or "")[:10] or None
            ret_time = eo.get("retrieved_at") or now_iso

            if st == "success" and val is not None:
                meta = data_freshness_service.build_evidence_metadata(
                    source=src_name,
                    source_type=src_type,
                    dataset=dataset_id,
                    parameter="chlorophyll_a",
                    observation_time=obs_time,
                    retrieval_time=ret_time,
                    status="available",
                    is_spatial_match=bool((eo.get("grid_distance_km") or 0.0) <= 50.0),
                )
                if eo.get("freshness"):
                    try:
                        meta.freshness = FreshnessLevel(eo["freshness"])
                    except Exception:
                        pass
                is_stale = meta.freshness in (FreshnessLevel.STALE, FreshnessLevel.VERY_STALE, "stale", "very_stale")
                evidence.append(
                    EvidenceItem(
                        source=src_name,
                        agent="eo",
                        parameter="chlorophyll_a",
                        value=float(val),
                        unit=eo.get("unit"),  # None for current verified MOSDAC NetCDF
                        observation_time=obs_time,
                        retrieval_time=ret_time,
                        latitude=eo.get("grid_latitude"),
                        longitude=eo.get("grid_longitude"),
                        distance_km=eo.get("grid_distance_km"),
                        freshness=meta.freshness,
                        data_source_type=src_type if src_type in ("archive", "live", "simulated", "remote_authenticated") else "archive",
                        confidence="medium" if is_stale else "high",
                        status="available",
                        notes=(
                            f"Chlorophyll-A concentration from verified EOS-06 OCM NetCDF archive ({dataset_id}). "
                            "Unit metadata is not explicitly provided in the NetCDF variable attributes. "
                            f"{'Archival' if is_stale else 'Recent'} observation."
                        ),
                        metadata=meta,
                    )
                )
            else:
                meta = data_freshness_service.build_evidence_metadata(
                    source=src_name,
                    source_type="unavailable",
                    dataset=dataset_id,
                    parameter="chlorophyll_a",
                    observation_time=None,
                    retrieval_time=now_iso,
                    status="unavailable",
                    is_spatial_match=False,
                )
                evidence.append(
                    EvidenceItem(
                        source=src_name,
                        agent="eo",
                        parameter="chlorophyll_a",
                        value=None,
                        unit=None,
                        observation_time=None,
                        retrieval_time=now_iso,
                        latitude=None,
                        longitude=None,
                        distance_km=None,
                        freshness=FreshnessLevel.UNKNOWN,
                        data_source_type="unavailable",
                        confidence="low",
                        status="unavailable",
                        notes=eo.get("notes") or eo.get("error") or "MOSDAC Chlorophyll-A data is currently unavailable.",
                        metadata=meta,
                    )
                )
        elif eo:
            obs = eo.get("observations") or []
            first = obs[0] if obs else {}
            cloud = first.get("cloud_cover")
            meta_stac = data_freshness_service.build_evidence_metadata(
                source=eo.get("source") or "Satellite EO",
                source_type=eo.get("data_source_type") or "archive",
                dataset=first.get("collection") or "Bhoonidhi-STAC",
                parameter="cloud_cover",
                observation_time=first.get("acquisition_time") or first.get("observation_time"),
                retrieval_time=now_iso,
                status="available" if cloud is not None else "unavailable",
            )
            evidence.append(
                EvidenceItem(
                    source=eo.get("source") or "Satellite EO",
                    agent="eo",
                    parameter="cloud_cover",
                    value=cloud,
                    unit="%",
                    observation_time=first.get("observation_time"),
                    retrieval_time=now_iso,
                    latitude=None,
                    longitude=None,
                    distance_km=None,
                    freshness=meta_stac.freshness,
                    data_source_type=eo.get("data_source_type") or "archive",
                    confidence="medium",
                    status="available" if cloud is not None else "unavailable",
                    notes="Regional cloud cover envelope observation.",
                    metadata=meta_stac,
                )
            )

        # ── 1b. Marine Ecosystem Agent Evidence ────────────────────────────────
        chla_already_present = any(i.parameter == "chlorophyll_a" and i.status == "available" for i in evidence)
        if not chla_already_present and ecosystem:
            chl = (ecosystem.get("chlorophyll_a") or {}).get("value") or (ecosystem.get("measured_chlorophyll") or {}).get("value")
            if chl is not None:
                meta_eco = data_freshness_service.build_evidence_metadata(
                    source=ecosystem.get("source") or "ISRO-MOSDAC OCM-3",
                    source_type=ecosystem.get("data_source_type") or "archive",
                    dataset="Level-2 Chlorophyll-a",
                    parameter="chlorophyll_a",
                    observation_time=ecosystem.get("observation_time") or ecosystem.get("data_time"),
                    retrieval_time=now_iso,
                    status="available",
                )
                evidence.append(
                    EvidenceItem(
                        source=ecosystem.get("source") or "ISRO-MOSDAC OCM-3",
                        agent="ecosystem",
                        parameter="chlorophyll_a",
                        value=float(chl),
                        unit=(ecosystem.get("chlorophyll_a") or {}).get("unit"),
                        observation_time=ecosystem.get("observation_time") or ecosystem.get("data_time"),
                        retrieval_time=now_iso,
                        latitude=ecosystem.get("latitude"),
                        longitude=ecosystem.get("longitude"),
                        distance_km=None,
                        freshness=meta_eco.freshness,
                        data_source_type=ecosystem.get("data_source_type") or "archive",
                        confidence="medium",
                        status="available",
                        notes=ecosystem.get("notes") or "Chlorophyll-A concentration from marine ecosystem data.",
                        metadata=meta_eco,
                    )
                )

        # ── 2. Ocean Agent Evidence ───────────────────────────────────────────
        if ocean:
            o_live = ocean.get("status") == "live" or ocean.get("data_source_type") == "live"
            o_time = ocean.get("observation_time") or ocean.get("data_time")
            o_src = ocean.get("source") or ("INCOIS-ERDDAP" if o_live else "INCOIS-mock")
            o_type = ocean.get("data_source_type") or ("live" if o_live else "simulated")
            sst = ocean.get("sea_surface_temperature_c") or (ocean.get("sea_surface_temperature") or {}).get("value")
            wave_h = ocean.get("significant_wave_height_m")
            w_spd_m_s = ((ocean.get("wind") or {}).get("speed") or {}).get("value")

            if sst is not None:
                meta_sst = data_freshness_service.build_evidence_metadata(
                    source=o_src,
                    source_type=o_type,
                    dataset="NOAA_AVHRR_AMSR_datasets",
                    parameter="sea_surface_temperature",
                    observation_time=o_time,
                    retrieval_time=now_iso,
                    status="available",
                )
                if ocean.get("freshness"):
                    try:
                        meta_sst.freshness = FreshnessLevel(ocean["freshness"])
                    except Exception:
                        pass
                evidence.append(
                    EvidenceItem(
                        source=o_src,
                        agent="ocean",
                        parameter="sea_surface_temperature",
                        value=round(float(sst), 2),
                        unit="°C",
                        observation_time=o_time,
                        retrieval_time=now_iso,
                        latitude=ocean.get("latitude"),
                        longitude=ocean.get("longitude"),
                        distance_km=ocean.get("distance_km"),
                        freshness=meta_sst.freshness,
                        data_source_type=o_type,
                        confidence="high" if o_live and meta_sst.freshness == FreshnessLevel.FRESH else "medium",
                        status="available",
                        notes="Sea surface temperature observation from INCOIS ocean telemetry.",
                        metadata=meta_sst,
                    )
                )

            if wave_h is not None:
                meta_wave = data_freshness_service.build_evidence_metadata(
                    source=o_src,
                    source_type=o_type,
                    dataset="ascat_daily_datasets",
                    parameter="significant_wave_height",
                    observation_time=o_time,
                    retrieval_time=now_iso,
                    status="available",
                )
                if ocean.get("freshness"):
                    try:
                        meta_wave.freshness = FreshnessLevel(ocean["freshness"])
                    except Exception:
                        pass
                evidence.append(
                    EvidenceItem(
                        source=o_src,
                        agent="ocean",
                        parameter="significant_wave_height",
                        value=round(float(wave_h), 2),
                        unit="m",
                        observation_time=o_time,
                        retrieval_time=now_iso,
                        latitude=ocean.get("latitude"),
                        longitude=ocean.get("longitude"),
                        distance_km=ocean.get("distance_km"),
                        freshness=meta_wave.freshness,
                        data_source_type=o_type,
                        confidence="high" if o_live and meta_wave.freshness == FreshnessLevel.FRESH else "medium",
                        status="available",
                        notes="Significant wave height from coastal hydrodynamic models.",
                        metadata=meta_wave,
                    )
                )

            if w_spd_m_s is not None:
                w_kts = round(float(w_spd_m_s) * 1.94384, 1)
                meta_owind = data_freshness_service.build_evidence_metadata(
                    source=o_src,
                    source_type=o_type,
                    dataset="ascat_daily_datasets",
                    parameter="ocean_surface_wind_speed",
                    observation_time=o_time,
                    retrieval_time=now_iso,
                    status="available",
                )
                evidence.append(
                    EvidenceItem(
                        source=o_src,
                        agent="ocean",
                        parameter="ocean_surface_wind_speed",
                        value=round(float(w_spd_m_s), 2),
                        unit="m/s",
                        observation_time=o_time,
                        retrieval_time=now_iso,
                        latitude=ocean.get("latitude"),
                        longitude=ocean.get("longitude"),
                        distance_km=ocean.get("distance_km"),
                        freshness=meta_owind.freshness,
                        data_source_type=o_type,
                        confidence="high" if o_live and meta_owind.freshness == FreshnessLevel.FRESH else "medium",
                        status="available",
                        notes=f"Ocean surface wind velocity (~{w_kts} knots).",
                        metadata=meta_owind,
                    )
                )

        # ── 3. Weather Agent Evidence ─────────────────────────────────────────
        if weather:
            w_live = weather.get("status") == "live" or weather.get("data_source_type") == "live"
            w_src = weather.get("source") or ("IMD" if w_live else "IMD-mock")
            w_type = weather.get("data_source_type") or ("live" if w_live else "simulated")
            w_time = weather.get("observation_time") or weather.get("data_time")
            w_spd = (weather.get("wind") or {}).get("speed")
            w_dir = (weather.get("wind") or {}).get("direction", "Variable")
            sea_cond = weather.get("sea_condition")
            vis = (weather.get("visibility") or {}).get("value")
            warns = weather.get("warnings") or []

            if w_spd is not None:
                meta_wwind = data_freshness_service.build_evidence_metadata(
                    source=w_src,
                    source_type=w_type,
                    parameter="wind_speed",
                    observation_time=w_time,
                    retrieval_time=now_iso,
                    status="available",
                )
                if weather.get("freshness"):
                    try:
                        meta_wwind.freshness = FreshnessLevel(weather["freshness"])
                    except Exception:
                        pass
                evidence.append(
                    EvidenceItem(
                        source=w_src,
                        agent="weather",
                        parameter="wind_speed",
                        value=float(w_spd),
                        unit="knots",
                        observation_time=w_time,
                        retrieval_time=now_iso,
                        latitude=weather.get("latitude"),
                        longitude=weather.get("longitude"),
                        distance_km=None,
                        freshness=meta_wwind.freshness,
                        data_source_type=w_type,
                        confidence="high" if w_live and meta_wwind.freshness == FreshnessLevel.FRESH else "medium",
                        status="available",
                        notes=f"Coastal wind speed with direction {w_dir}.",
                        metadata=meta_wwind,
                    )
                )

            if sea_cond:
                meta_wsea = data_freshness_service.build_evidence_metadata(
                    source=w_src,
                    source_type=w_type,
                    parameter="sea_condition",
                    observation_time=w_time,
                    retrieval_time=now_iso,
                    status="available",
                )
                evidence.append(
                    EvidenceItem(
                        source=w_src,
                        agent="weather",
                        parameter="sea_condition",
                        value=str(sea_cond),
                        unit=None,
                        observation_time=w_time,
                        retrieval_time=now_iso,
                        latitude=weather.get("latitude"),
                        longitude=weather.get("longitude"),
                        distance_km=None,
                        freshness=meta_wsea.freshness,
                        data_source_type=w_type,
                        confidence="high" if w_live and meta_wsea.freshness == FreshnessLevel.FRESH else "medium",
                        status="available",
                        notes="Qualitative coastal sea state bulletin.",
                        metadata=meta_wsea,
                    )
                )

            if warns:
                meta_warns = data_freshness_service.build_evidence_metadata(
                    source=w_src,
                    source_type=w_type,
                    parameter="weather_warnings",
                    observation_time=w_time,
                    retrieval_time=now_iso,
                    status="available",
                )
                evidence.append(
                    EvidenceItem(
                        source=w_src,
                        agent="weather",
                        parameter="weather_warnings",
                        value=warns,
                        unit=None,
                        observation_time=w_time,
                        retrieval_time=now_iso,
                        latitude=weather.get("latitude"),
                        longitude=weather.get("longitude"),
                        distance_km=None,
                        freshness=meta_warns.freshness,
                        data_source_type=w_type,
                        confidence="high" if w_live else "medium",
                        status="available",
                        notes=f"Active weather warnings: {', '.join(warns)}",
                        metadata=meta_warns,
                    )
                )

        # ── 4. Safety Agent Evidence ──────────────────────────────────────────
        if safety:
            prox = safety.get("proximity") or {}
            dist_km = prox.get("distance_km")
            prox_status = prox.get("status")
            risk_lvl = safety.get("risk_level", "low")
            risk_sc = safety.get("risk_score", 10)
            factors = safety.get("contributing_factors") or []

            meta_safety = data_freshness_service.build_evidence_metadata(
                source="Local-Geofence-Engine",
                source_type="demo",
                parameter="boundary_proximity",
                observation_time=None,
                retrieval_time=now_iso,
                status="available" if dist_km is not None else "unavailable",
            )
            evidence.append(
                EvidenceItem(
                    source="Local-Geofence-Engine",
                    agent="safety",
                    parameter="boundary_proximity",
                    value=dist_km,
                    unit="km" if dist_km is not None else None,
                    observation_time=None,
                    retrieval_time=now_iso,
                    latitude=None,
                    longitude=None,
                    distance_km=dist_km,
                    freshness=FreshnessLevel.FRESH,
                    data_source_type="demo",
                    confidence="high",
                    status="available" if dist_km is not None else "unavailable",
                    notes=f"Status: {prox_status or 'clear'}. Alert: {prox.get('alert_message', 'No active boundary restriction')}",
                    metadata=meta_safety,
                )
            )

            meta_risk = data_freshness_service.build_evidence_metadata(
                source="Safety-Reasoning-Engine",
                source_type="demo",
                parameter="overall_safety_risk",
                observation_time=None,
                retrieval_time=now_iso,
                status="available",
            )
            evidence.append(
                EvidenceItem(
                    source="Safety-Reasoning-Engine",
                    agent="safety",
                    parameter="overall_safety_risk",
                    value=risk_lvl,
                    unit=None,
                    observation_time=None,
                    retrieval_time=now_iso,
                    latitude=None,
                    longitude=None,
                    distance_km=None,
                    freshness=FreshnessLevel.FRESH,
                    data_source_type="demo",
                    confidence="high",
                    status="available",
                    notes=f"Combined safety score: {risk_sc}/100. Factors: {', '.join(factors) if factors else 'Routine operations'}",
                    metadata=meta_risk,
                )
            )

        # ── 5. Marine Ecosystem Evidence ──────────────────────────────────────
        if ecosystem:
            trophic = ecosystem.get("trophic_status")
            if trophic:
                meta_eco = data_freshness_service.build_evidence_metadata(
                    source="Ecosystem-Model",
                    source_type="simulated",
                    parameter="trophic_status",
                    observation_time=None,
                    retrieval_time=now_iso,
                    status="available",
                )
                evidence.append(
                    EvidenceItem(
                        source="Ecosystem-Model",
                        agent="ecosystem",
                        parameter="trophic_status",
                        value=trophic,
                        unit=None,
                        observation_time=None,
                        retrieval_time=now_iso,
                        latitude=None,
                        longitude=None,
                        distance_km=None,
                        freshness=FreshnessLevel.RECENT,
                        data_source_type="simulated",
                        confidence="medium",
                        status="available",
                        notes=f"Trophic state: {trophic}.",
                        metadata=meta_eco,
                    )
                )

        return evidence

    def detect_conflicts(self, evidence_items: List[EvidenceItem]) -> List[SignalConflict]:
        """
        Cross-correlate agent observations and detect genuine disagreements.
        Never hides divergent signals; records conservative safety resolution.
        Populates conflicting_sources, conflicting_parameters, and reason.
        """
        conflicts: List[SignalConflict] = []

        # 1. Compare Wind Speed between Weather and Ocean
        weather_wind: Optional[float] = None
        ocean_wind_kts: Optional[float] = None

        for item in evidence_items:
            if item.agent == "weather" and item.parameter == "wind_speed" and isinstance(item.value, (int, float)):
                weather_wind = float(item.value)
            elif item.agent == "ocean" and item.parameter == "ocean_surface_wind_speed" and isinstance(item.value, (int, float)):
                # Ocean wind is in m/s; convert to knots
                ocean_wind_kts = round(float(item.value) * 1.94384, 1)

        if weather_wind is not None and ocean_wind_kts is not None:
            diff = abs(weather_wind - ocean_wind_kts)
            if diff >= 8.0:
                higher_wind = max(weather_wind, ocean_wind_kts)
                conflicts.append(
                    SignalConflict(
                        parameter="wind_speed",
                        sources_involved=["IMD Weather Agent", "INCOIS Ocean Agent"],
                        conflicting_sources=["IMD", "INCOIS-ERDDAP"],
                        conflicting_parameters=["wind_speed", "ocean_surface_wind_speed"],
                        reason=f"Surface wind estimate discrepancy: IMD reports {weather_wind} kt while INCOIS reports {ocean_wind_kts} kt (Δ {round(diff, 1)} kt).",
                        description=(
                            f"Discrepancy in surface wind estimates: IMD Weather reports {weather_wind} knots, "
                            f"while INCOIS Ocean telemetry indicates {ocean_wind_kts} knots (Δ {round(diff, 1)} kt)."
                        ),
                        resolution=(
                            f"Conservative maritime safety principle applied: Higher wind speed (~{higher_wind} kt) "
                            f"is retained for operational hazard assessment."
                        ),
                    )
                )

        # 2. Compare Weather vs Dangerous Ocean Swell (Waves)
        # Weather reports calm conditions, but Ocean indicates dangerous wave swell (>= 2.0m)
        wave_item = next((i for i in evidence_items if i.parameter == "significant_wave_height" and i.value is not None), None)
        if wave_item and float(wave_item.value) >= 2.0:
            w_speed_val = weather_wind if weather_wind is not None else 10.0
            if w_speed_val < 15.0:
                conflicts.append(
                    SignalConflict(
                        parameter="wave_swell_vs_local_wind",
                        sources_involved=["IMD Weather Agent", "INCOIS Ocean Agent"],
                        conflicting_sources=["IMD", wave_item.source],
                        conflicting_parameters=["wind_speed", "significant_wave_height"],
                        reason=(
                            f"Local atmospheric winds are relatively light ({w_speed_val} kt), "
                            f"but ocean telemetry detects dangerous wave swell ({wave_item.value} m) "
                            "likely generated by distant oceanic weather systems."
                        ),
                        description=(
                            f"Weather indicates calm/moderate local wind ({w_speed_val} kt), "
                            f"but ocean telemetry records hazardous significant wave swell of {wave_item.value} m."
                        ),
                        resolution=(
                            "Safety override: High wave swell poses severe capsize and surfing risks for small vessels. "
                            "Hazardous ocean swell conditions take precedence over calm local winds."
                        ),
                    )
                )

        # 3. Compare Sea Surface Temperature (SST) Discrepancies if multiple sources exist
        sst_items = [i for i in evidence_items if i.parameter == "sea_surface_temperature" and i.value is not None]
        if len(sst_items) >= 2:
            sst_vals = [float(i.value) for i in sst_items]
            diff_sst = max(sst_vals) - min(sst_vals)
            if diff_sst >= 3.0:
                conflicts.append(
                    SignalConflict(
                        parameter="sea_surface_temperature",
                        sources_involved=[i.source for i in sst_items],
                        conflicting_sources=[i.source for i in sst_items],
                        conflicting_parameters=["sea_surface_temperature"],
                        reason=f"Significant SST divergence between sources: {min(sst_vals)}°C vs {max(sst_vals)}°C (Δ {round(diff_sst, 1)}°C).",
                        description=f"Material disagreement between SST reporting sources ({min(sst_vals)}°C vs {max(sst_vals)}°C).",
                        resolution="Retaining regional baseline and flagging thermal gradient uncertainty.",
                    )
                )

        # 4. Compare Weather vs Safety Hazard Divergence
        weather_wind_val = weather_wind or 12.0
        safety_risk_item = next((i for i in evidence_items if i.parameter == "overall_safety_risk"), None)
        safety_risk = str(safety_risk_item.value).lower() if safety_risk_item and safety_risk_item.value else "low"

        if safety_risk in ("high", "critical") and weather_wind_val < 15.0:
            conflicts.append(
                SignalConflict(
                    parameter="navigational_safety_vs_weather",
                    sources_involved=["Safety Geofence Agent", "IMD Weather Agent"],
                    conflicting_sources=["Safety-Reasoning-Engine", "IMD"],
                    conflicting_parameters=["overall_safety_risk", "wind_speed"],
                    reason=f"Weather conditions appear calm (wind ~{weather_wind_val} kt), but jurisdictional or navigational boundary assessment enforces {safety_risk.upper()} risk.",
                    description=(
                        f"Weather conditions are relatively calm (wind ~{weather_wind_val} kt), "
                        f"but safety assessment identifies elevated hazard/boundary risk ({safety_risk.upper()})."
                    ),
                    resolution=(
                        "Safety and boundary restrictions strictly supersede favorable weather. "
                        "Operators must not navigate into restricted or hazardous sectors regardless of calm seas."
                    ),
                )
            )

        return conflicts

    def analyze_conditions(
        self,
        evidence_items: List[EvidenceItem],
        location: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Analyze current marine conditions using cautious, scientifically truthful language.
        Does NOT make unsupported catch guarantees.
        """
        conditions: Dict[str, Any] = {
            "chlorophyll": {"status": "unavailable", "summary": "Chlorophyll data not available."},
            "thermal": {"status": "unavailable", "summary": "Sea temperature data not available."},
            "surface_wind_wave": {"status": "unavailable", "summary": "Wind and wave data not available."},
            "atmospheric": {"status": "unavailable", "summary": "Atmospheric weather data not available."},
            "safety": {"status": "clear", "summary": "No active boundary restrictions detected."},
        }

        # 1. Chlorophyll
        chla_item = next((i for i in evidence_items if i.parameter == "chlorophyll_a"), None)
        if chla_item and chla_item.status == "available" and chla_item.value is not None:
            val = chla_item.value
            age_desc = "archival" if chla_item.freshness == "stale" else "recent"
            dist_str = f" (~{chla_item.distance_km} km away)" if chla_item.distance_km else ""
            conditions["chlorophyll"] = {
                "status": "available",
                "value": val,
                "unit": chla_item.unit,
                "freshness": chla_item.freshness,
                "observation_date": chla_item.observation_time,
                "distance_km": chla_item.distance_km,
                "summary": (
                    f"Chlorophyll-A concentration is {val} from MOSDAC {age_desc} observation{dist_str}. "
                    "Chlorophyll-A serves as an environmental biological productivity indicator, but this alone "
                    "does not guarantee fish presence or aggregation."
                ),
            }
        elif chla_item and chla_item.status == "unavailable":
            conditions["chlorophyll"] = {
                "status": "unavailable",
                "summary": "Satellite chlorophyll observation is currently unavailable in this sector.",
            }

        # 2. Thermal / SST
        sst_item = next((i for i in evidence_items if i.parameter == "sea_surface_temperature"), None)
        if sst_item and sst_item.status == "available" and sst_item.value is not None:
            sst_val = sst_item.value
            conditions["thermal"] = {
                "status": "available",
                "value": sst_val,
                "unit": "°C",
                "summary": f"Sea surface temperature is approximately {sst_val}°C, typical of warm coastal waters.",
            }

        # 3. Surface Wind & Wave
        wave_item = next((i for i in evidence_items if i.parameter == "significant_wave_height"), None)
        wind_item = next((i for i in evidence_items if i.parameter == "wind_speed"), None)
        ocean_wind_item = next((i for i in evidence_items if i.parameter == "ocean_surface_wind_speed"), None)

        w_spd = wind_item.value if wind_item and wind_item.value is not None else None
        if w_spd is None and ocean_wind_item and ocean_wind_item.value is not None:
            w_spd = round(float(ocean_wind_item.value) * 1.94384, 1)

        wave_val = wave_item.value if wave_item and wave_item.value is not None else None

        wind_desc = "light"
        if w_spd is not None:
            if w_spd >= 22.0:
                wind_desc = "strong/hazardous"
            elif w_spd >= 15.0:
                wind_desc = "moderate with chop"
            else:
                wind_desc = "manageable"

        conditions["surface_wind_wave"] = {
            "status": "available" if (w_spd is not None or wave_val is not None) else "unavailable",
            "wind_speed_knots": w_spd,
            "wave_height_meters": wave_val,
            "summary": (
                f"Surface winds are ~{w_spd or 'N/A'} knots ({wind_desc})"
                + (f" with significant wave height of ~{wave_val}m." if wave_val is not None else ".")
            ),
        }

        # 4. Atmospheric / Weather
        sea_item = next((i for i in evidence_items if i.parameter == "sea_condition"), None)
        warn_item = next((i for i in evidence_items if i.parameter == "weather_warnings"), None)
        warns = warn_item.value if warn_item and warn_item.value else []

        conditions["atmospheric"] = {
            "status": "available",
            "sea_condition": sea_item.value if sea_item else "Moderate",
            "warnings": warns,
            "summary": (
                f"Coastal sea state is evaluated as {sea_item.value if sea_item else 'Moderate'}."
                + (f" Active warnings: {', '.join(warns)}." if warns else " No active weather bulletins.")
            ),
        }

        # 5. Safety & Boundary
        safety_item = next((i for i in evidence_items if i.parameter == "boundary_proximity"), None)
        overall_risk_item = next((i for i in evidence_items if i.parameter == "overall_safety_risk"), None)

        risk_val = overall_risk_item.value if overall_risk_item else "low"
        conditions["safety"] = {
            "status": "restricted" if risk_val in ("high", "critical") else "clear",
            "risk_level": risk_val,
            "boundary_distance_km": safety_item.distance_km if safety_item else None,
            "summary": (
                f"Navigational risk is assessed as {str(risk_val).upper()}."
                + (f" Nearest boundary is ~{safety_item.distance_km} km away." if safety_item and safety_item.distance_km else "")
            ),
        }

        return conditions

    def evaluate_data_quality(
        self,
        evidence_items: List[EvidenceItem],
        location: Optional[dict],
    ) -> Dict[str, Any]:
        """
        Audit freshness, missing data, and spatial relevance.
        """
        freshness_map: Dict[str, str] = {}
        stale_parameters: List[str] = []
        missing_parameters: List[str] = []

        expected = ["chlorophyll_a", "sea_surface_temperature", "wind_speed", "significant_wave_height", "boundary_proximity"]
        found = {i.parameter: i for i in evidence_items}

        for p in expected:
            if p not in found or found[p].status == "unavailable" or found[p].value is None:
                missing_parameters.append(p)
            else:
                item = found[p]
                freshness_map[p] = item.freshness
                if item.freshness in (FreshnessLevel.STALE, FreshnessLevel.VERY_STALE, "stale", "very_stale"):
                    stale_parameters.append(p)

        # Audit overall source reliability across active items
        reliabilities = [
            item.metadata.reliability.value
            for item in evidence_items
            if item.metadata and item.metadata.reliability
        ]
        if any(r == "LOW" for r in reliabilities) or len(missing_parameters) >= 3:
            overall_reliability = "LOW"
        elif any(r == "MEDIUM" for r in reliabilities) or stale_parameters:
            overall_reliability = "MEDIUM"
        elif all(r == "HIGH" for r in reliabilities) and reliabilities:
            overall_reliability = "HIGH"
        else:
            overall_reliability = "MEDIUM"

        # Spatial relevance audit
        spatial_notes: List[str] = []
        for item in evidence_items:
            if item.distance_km is not None and item.distance_km > 40.0:
                spatial_notes.append(f"{item.parameter} grid observation is ~{item.distance_km} km from requested coordinates.")

        return {
            "freshness_breakdown": freshness_map,
            "stale_parameters": stale_parameters,
            "missing_parameters": missing_parameters,
            "overall_reliability": overall_reliability,
            "spatial_distance_notes": spatial_notes,
            "location_provided": bool(location and location.get("lat") is not None and location.get("lon") is not None),
        }

    def compute_marine_decision(
        self,
        query: str,
        category: str,
        conditions: Dict[str, Any],
        data_quality: Dict[str, Any],
        conflicts: List[SignalConflict],
        safety_result: Dict[str, Any],
    ) -> Optional[MarineDecision]:
        """
        Synthesize evidence into an actionable marine decision (GO | CAUTION | AVOID | INSUFFICIENT_DATA).
        Strictly prioritizes safety over operational convenience.
        """
        # Only decision-oriented queries generate a formal MarineDecision
        if category not in ("fishing", "safety"):
            return None

        safety_risk = (safety_result.get("risk_level") or "low").lower()
        warnings: List[str] = []
        reasoning: List[str] = []
        conditions_summary: List[str] = []
        missing_info: List[str] = []

        # Surface any active signal conflicts in decision notes
        for conf in conflicts:
            warnings.append(f"Evidence discrepancy: {conf.description} — {conf.resolution}")

        # ── 1. Safety Supremacy Check ─────────────────────────────────────────
        if safety_risk in ("high", "critical"):
            rec: str = "AVOID"
            risk_lvl: str = "CRITICAL" if safety_risk == "critical" else "HIGH"
            conf: str = "HIGH"

            prox = safety_result.get("proximity") or {}
            dist_km = prox.get("distance_km")
            alert_msg = prox.get("alert_message") or "Demarcation limit proximity"

            decision_summary = (
                "⚠️ Sailing and fishing are strictly NOT RECOMMENDED in this sector. "
                f"Elevated navigational risk ({safety_risk.upper()}) detected: {alert_msg}."
            )
            warnings.append(f"Safety restriction: {alert_msg}" + (f" ({dist_km} km to boundary)" if dist_km else ""))
            reasoning.append("Maritime boundary proximity and navigational safety supersede all other favorable conditions.")
            conditions_summary.append(f"Navigational risk: {safety_risk.upper()}")
            conditions_summary.append("Maritime boundary constraint active")

            return MarineDecision(
                recommendation=rec,
                risk_level=risk_lvl,
                confidence=conf,
                decision_summary=decision_summary,
                conditions_summary=conditions_summary,
                reasoning=reasoning,
                supporting_evidence=[],
                warnings=warnings,
                missing_information=[],
                conflicts=conflicts,
                freshness_assessment=data_quality.get("freshness_breakdown", {}),
            )

        # ── 2. Weather & Wind Assessment ──────────────────────────────────────
        surf = conditions.get("surface_wind_wave") or {}
        w_spd = surf.get("wind_speed_knots")
        w_warns = (conditions.get("atmospheric") or {}).get("warnings") or []
        wave_h = surf.get("wave_height_meters")

        has_severe_weather = bool(w_warns) or (w_spd is not None and w_spd >= 22.0) or (wave_h is not None and wave_h >= 2.5)
        has_moderate_weather = (w_spd is not None and w_spd >= 15.0) or (wave_h is not None and wave_h >= 1.8)

        # ── 3. Missing Data & Freshness Check ─────────────────────────────────
        is_loc_provided = data_quality.get("location_provided", True)
        if not is_loc_provided:
            missing_info.append("Specific operational coordinates not provided in query context.")

        stale_params = data_quality.get("stale_parameters") or []
        chla_cond = conditions.get("chlorophyll") or {}
        chla_val = chla_cond.get("value")
        chla_stale = "chlorophyll_a" in stale_params

        # ── 4. Decision Synthesis ─────────────────────────────────────────────
        if has_severe_weather:
            rec = "AVOID"
            risk_lvl = "HIGH"
            conf = "HIGH"
            decision_summary = (
                "Fishing is NOT RECOMMENDED due to adverse meteorological or sea conditions. "
                f"Surface winds (~{w_spd or 22} knots) or elevated wave swell presents operational hazards."
            )
            reasoning.append(f"Adverse winds ({w_spd or 'strong'} kt) or wave swell ({wave_h or 'high'} m) exceed safe operating thresholds.")
            if w_warns:
                warnings.extend(w_warns)
            conditions_summary.append(f"Surface wind: ~{w_spd or 'elevated'} knots")
            conditions_summary.append("Severe sea state / weather warning active")

        elif not is_loc_provided and category == "fishing":
            # Missing location
            rec = "CAUTION"
            risk_lvl = "MODERATE"
            conf = "LOW"
            decision_summary = (
                "Operational assessment is available with CAUTION. "
                "Because your exact vessel coordinates were not provided, regional baseline conditions are shown. "
                "Specify your coastal sector (e.g. Chennai, Gujarat, Mumbai) for precise guidance."
            )
            reasoning.append("Vessel coordinates were not specified; localized navigational hazards cannot be ruled out.")
            conditions_summary.append("Location: Regional coastal baseline (unlocalized)")
            if w_spd is not None:
                conditions_summary.append(f"Regional winds: ~{w_spd} knots")

        elif has_moderate_weather or chla_stale or len(conflicts) > 0:
            # Favorable or moderate sea state, but caution warranted due to weather, stale data, or conflict
            rec = "CAUTION"
            risk_lvl = "MODERATE"
            conf = "MEDIUM" if (chla_stale or len(conflicts) > 0) else "HIGH"

            reasons = []
            if has_moderate_weather:
                reasons.append(f"Surface winds (~{w_spd} kts) or wave heights produce moderate sea chop requiring nautical vigilance.")
                conditions_summary.append(f"Surface winds: ~{w_spd} knots (moderate chop)")
            else:
                conditions_summary.append(f"Surface winds: ~{w_spd or 12} knots (moderate)")

            sst_cond = conditions.get("thermal") or {}
            sst_val = sst_cond.get("value")
            if sst_val is not None:
                conditions_summary.append(f"Sea surface temperature: ~{sst_val}°C")

            if chla_val is not None:
                conditions_summary.append(f"Chlorophyll-A (MOSDAC): {chla_val} (observed {chla_cond.get('observation_date')})")
                reasons.append(
                    f"Chlorophyll-A concentration ({chla_val}) indicates primary biological productivity and phytoplankton activity, "
                    "serving as an ecological indicator for potential fishing areas without guaranteeing fish presence."
                )
                if chla_stale:
                    reasons.append(
                        f"Chlorophyll-A observation ({chla_val}) is from an archival observation ({chla_cond.get('observation_date')}); "
                        "biological features may have evolved, so treat as environmental background rather than real-time conditions."
                    )
            else:
                missing_info.append("Satellite chlorophyll observation unavailable in immediate grid.")

            if conflicts:
                reasons.append(f"Operational caution: {len(conflicts)} signal discrepancy detected between monitoring feeds.")

            conditions_summary.append("Navigational safety: Clear of active boundary demarcation")
            reasons.append("No active boundary violations or storm advisories detected.")

            decision_summary = (
                "Fishing is RECOMMENDED WITH CAUTION. "
                + " ".join(reasons[:2])
            )
            reasoning.extend(reasons)

        else:
            # Clean GO recommendation
            rec = "GO"
            risk_lvl = "LOW"
            conf = "HIGH"
            decision_summary = (
                "Conditions are FAVORABLE for coastal fishing and marine operations. "
                "Surface winds, wave swell, and navigational safety are all within clear operational limits."
            )
            if w_spd is not None:
                conditions_summary.append(f"Surface winds: ~{w_spd} knots (calm to moderate)")
            sst_cond = conditions.get("thermal") or {}
            sst_val = sst_cond.get("value")
            if sst_val is not None:
                conditions_summary.append(f"Sea surface temperature: ~{sst_val}°C")
            if chla_val is not None:
                conditions_summary.append(f"Chlorophyll-A (MOSDAC): {chla_val}")
                reasoning.append(
                    f"Chlorophyll-A ({chla_val}) indicates active biological productivity supporting coastal pelagic activity."
                )
            conditions_summary.append("Navigational safety: Clear of restrictions")
            reasoning.append("Marine weather, sea state, and boundary proximity are all within safe operational thresholds.")

        # Always add truthful disclaimer
        reasoning.append("Chlorophyll-A indicates environmental primary productivity but does not guarantee fish presence.")
        warnings.append("Operational assessment based on available evidence. Always confirm local port/IMD bulletins prior to casting off.")

        return MarineDecision(
            recommendation=rec,
            risk_level=risk_lvl,
            confidence=conf,
            decision_summary=decision_summary,
            conditions_summary=conditions_summary[:6],
            reasoning=reasoning,
            supporting_evidence=[],
            warnings=warnings,
            missing_information=missing_info,
            conflicts=conflicts,
            freshness_assessment=data_quality.get("freshness_breakdown", {}),
        )

    def run_analysis(self, state: OrcaState) -> MarineAnalysisResult:
        """
        Execute full cross-agent analysis:
        Extract evidence -> correlate conditions -> detect conflicts -> evaluate quality -> compute decision.
        """
        query = state.get("query") or ""
        location = state.get("location")
        safety_res = state.get("safety_result") or {}

        category = classify_query_intent(query)
        evidence_items = self.extract_evidence_items(state)
        conflicts = self.detect_conflicts(evidence_items)
        conditions = self.analyze_conditions(evidence_items, location)
        data_quality = self.evaluate_data_quality(evidence_items, location)

        decision = self.compute_marine_decision(
            query=query,
            category=category,
            conditions=conditions,
            data_quality=data_quality,
            conflicts=conflicts,
            safety_result=safety_res,
        )

        logger.info(
            "marine_analysis_completed",
            extra={
                "category": category,
                "evidence_count": len(evidence_items),
                "conflicts_count": len(conflicts),
                "has_decision": decision is not None,
                "recommendation": decision.recommendation if decision else None,
            },
        )

        return MarineAnalysisResult(
            query_category=category,
            target_location=location,
            evidence_items=evidence_items,
            conditions=conditions,
            conflicts=conflicts,
            conflict_detected=bool(conflicts),
            data_quality=data_quality,
            decision=decision,
        )


# Singleton analysis service
marine_analysis_service = MarineAnalysisService()
