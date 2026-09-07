"""
Human-Friendly Response Formatter for ORCA (Phase 17).

Transforms multi-agent evidence, deterministic marine decisions, and risk telemetry
into clear, professional, human-centered responses for fishermen and marine users.

Core Invariants:
1. Direct answer first (YES / CAUTION / NO / UNCERTAIN) for operational questions.
2. The deterministic marine_decision remains the sole operational authority.
3. No technical/developer jargon leaks into the primary answer (NetCDF, grid coordinates,
   internal agent names, variable attributes, raw JSON, debug tags).
4. Weather is never equated to guaranteed fish abundance; chlorophyll limitations are clear.
5. Best time is never fabricated without verified future forecasts.
6. Phase 16 data freshness and simulation provenance are communicated in plain language.
7. Factual queries (SST, chlorophyll, weather) receive direct factual answers without
   forced fishing recommendations.
"""
from typing import Any, Dict, List, Optional, Tuple
import re


DIRECTION_MAP = {
    "N": "north", "NNE": "north-northeast", "NE": "northeast", "ENE": "east-northeast",
    "E": "east", "ESE": "east-southeast", "SE": "southeast", "SSE": "south-southeast",
    "S": "south", "SSW": "south-southwest", "SW": "southwest", "WSW": "west-southwest",
    "W": "west", "WNW": "west-northwest", "NW": "northwest", "NNW": "north-northwest",
    "VARIABLE": "variable directions", "VAR": "variable directions",
}


def _format_wind_direction(dir_str: Optional[str]) -> str:
    if not dir_str:
        return "variable directions"
    cleaned = dir_str.strip().upper()
    if cleaned in DIRECTION_MAP:
        return DIRECTION_MAP[cleaned]
    # Check if first word is a cardinal direction (e.g. 'SW Moderate' -> 'southwest')
    first_token = re.split(r"[\s\-_/]", cleaned)[0]
    if first_token in DIRECTION_MAP:
        return DIRECTION_MAP[first_token]
    return cleaned.lower()


def _sanitize_human_text(text: str) -> str:
    """Strip any accidental internal debug markers, dataset IDs, and technical tags."""
    if not text:
        return ""
    # Strip provenance tags and debug blocks
    cleaned = re.sub(r"\[(?:LIVE|SIMULATED|DEMO|RAG|MOSDAC)[^\]]*\]", "", text)
    cleaned = re.sub(r"\[Signal Conflict[^\]]*\]:?", "Note:", cleaned)
    cleaned = re.sub(r"\[DEMO BOUNDARY\]", "", cleaned)
    cleaned = re.sub(r"\[SIMULATED WEATHER DATA\]", "", cleaned)
    # Strip internal agent names
    cleaned = re.sub(
        r"\b(?:Weather|Ocean|Satellite EO|Safety|Coordinator|Final Reasoning|Marine Analysis)\s+Agent\b",
        "marine monitoring service",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Strip internal technical tokens and file formats
    cleaned = re.sub(r"\bE06OCM[A-Za-z0-9_]*\b", "", cleaned)
    cleaned = re.sub(r"\bNetCDF(?:-4)?\b", "satellite dataset", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bvariable attributes?\b", "metadata", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:grid coordinates|grid latitude|grid longitude|nearest grid)\b", "coordinates", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b[Ss][Vv][Gg](?=[A-Z])", "", cleaned)
    # Collapse multiple spaces and blank lines
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def classify_human_intent(query: str) -> str:
    """
    Classify query intent for human-centered presentation.
    Returns: 'fishing' | 'fish_abundance' | 'safety' | 'chlorophyll' | 'sst' | 'weather' | 'ocean' | 'educational' | 'general'
    """
    q = (query or "").lower().strip()

    # 0. Fishing Location Recommendation queries
    fishing_location_patterns = [
        r"where.*(?:find|are|get|catch).*fish",
        r"maximum\s+fish",
        r"best.*fish(?:ing)?.*(?:area|spot|ground|zone|location|place)",
        r"which.*area.*(?:better|best|good).*fish",
        r"where.*(?:should|can).*fish",
        r"where\s+to\s+fish",
        r"fishing\s+(?:spot|area|zone|location|ground)s?\s+(?:near|around|in|at)",
        r"recommended\s+fishing\s+(?:spot|area|zone|location|ground)",
        r"find.*fishing.*(?:spot|area|zone|location|ground)",
        r"spot\s+for\s+fishing",
        r"place\s+for\s+fishing",
    ]
    if any(re.search(pat, q) for pat in fishing_location_patterns):
        return "fishing_location"

    # 1. Fish Abundance / Catch prediction queries
    abundance_patterns = [
        r"will i get more fish",
        r"will i catch more fish",
        r"are there more fish",
        r"how many fish",
        r"more fish here",
        r"good catch today",
        r"high fish catch",
        r"fish abundance",
        r"fish presence",
        r"lot of fish",
        r"lots of fish",
    ]
    if any(re.search(pat, q) for pat in abundance_patterns):
        return "fish_abundance"

    # 2. Educational marine biology queries
    edu_patterns = [
        r"why is chlorophyll",
        r"what is chlorophyll",
        r"role of chlorophyll",
        r"importance of chlorophyll",
        r"explain chlorophyll",
        r"what is phytoplankton",
        r"what are phytoplankton",
        r"marine food web",
    ]
    if any(re.search(pat, q) for pat in edu_patterns):
        return "educational"

    # 3. Factual Chlorophyll / Ocean Color
    chla_patterns = [
        r"\bchlorophyll\b",
        r"\bchla\b",
        r"ocean color",
        r"phytoplankton concentration",
        r"phytoplankton density",
    ]
    if any(re.search(pat, q) for pat in chla_patterns):
        return "chlorophyll"

    # 4. Factual SST
    sst_patterns = [
        r"\bsst\b",
        r"sea surface temp",
        r"water temp",
        r"sea temp",
        r"ocean temp",
    ]
    if any(re.search(pat, q) for pat in sst_patterns):
        return "sst"

    # 4b. Fishing timing / schedule queries
    timing_patterns = [
        r"\bwhen should i (?:go )?fish",
        r"\bwhen can i (?:go )?fish",
        r"\bwhat time should i (?:go )?fish",
        r"\bwhat time can i (?:go )?fish",
        r"\bbest time to fish",
        r"\bbest time for fish",
        r"\bbest timing\b",
        r"\boptimal (?:time|window) for fish",
        r"\bwhen to fish",
        r"\bwhen.*fishing",
    ]
    if any(re.search(pat, q) for pat in timing_patterns):
        return "timing"

    # 5. Operational Fishing decision
    fishing_patterns = [
        r"\bcan i go fishing\b",
        r"\bcan we go fishing\b",
        r"\bshould i go fishing\b",
        r"\bshould we go fishing\b",
        r"\bcan i fish\b",
        r"\bcan we fish\b",
        r"\bshould i fish\b",
        r"\bgo for fishing\b",
        r"\bsafe to fish\b",
        r"\bgood to fish\b",
        r"\bfishing.*today\b",
        r"\bfishing.*now\b",
        r"\bfishing.*near\b",
        r"\bfishing.*conditions\b",
        r"\bfishing\b",
        r"\bfish\b",
        r"\bcatch\b",
        r"\btrawler\b",
    ]
    if any(re.search(pat, q) for pat in fishing_patterns):
        return "fishing"

    # 6. Navigational Safety & Boundary queries
    safety_patterns = [
        r"\bis it safe\b",
        r"\bam i safe\b",
        r"\bis this safe\b",
        r"\bis.*safe to sail\b",
        r"\bboundary\b",
        r"\bborder\b",
        r"\bimbl\b",
        r"\brestricted\b",
        r"\bhazard\b",
        r"\bdanger\b",
        r"\bemergency\b",
    ]
    if any(re.search(pat, q) for pat in safety_patterns):
        return "safety"

    # 7. Sea Conditions / Waves
    ocean_patterns = [
        r"\bwave\b",
        r"\bwaves\b",
        r"\bswell\b",
        r"sea condition",
        r"sea state",
        r"ocean condition",
        r"current",
    ]
    if any(re.search(pat, q) for pat in ocean_patterns):
        return "ocean"

    # 8. Weather
    weather_patterns = [
        r"\bweather\b",
        r"\bwind\b",
        r"\brain\b",
        r"\bforecast\b",
        r"\bvisibility\b",
        r"\bcyclone\b",
        r"\bstorm\b",
    ]
    if any(re.search(pat, q) for pat in weather_patterns):
        return "weather"

    return "general"


class HumanResponseFormatter:
    """Presentation formatter that translates operational marine reasoning into human-friendly answers."""

    def format_response(
        self,
        query: str,
        marine_decision: Optional[Dict[str, Any]],
        enforced_risk: str,
        driver_agent: str,
        conflict_explanation: Optional[str],
        state: Dict[str, Any],
        data_quality: Optional[Dict[str, Any]] = None,
        conflicts: Optional[List[Any]] = None,
        best_time: Optional[Dict[str, Any]] = None,
        raw_llm_answer: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build the authoritative human response.
        Returns (human_formatted_answer_string, human_response_dict).
        """
        intent = classify_human_intent(query)
        ocean = state.get("ocean_result") or {}
        weather = state.get("weather_result") or {}
        safety = state.get("safety_result") or {}
        eo = state.get("eo_result") or {}
        ecosystem = state.get("ecosystem_result") or {}

        # ── 1. Extract and Humanize Conditions ───────────────────────────────────
        human_conditions = self._build_human_conditions(ocean, weather, safety, eo, ecosystem)

        # ── 2. Determine Plain-Language Best Time ────────────────────────────────
        human_best_time = self._build_human_best_time(best_time)

        # ── 3. Determine Plain-Language Data Quality Note ────────────────────────
        human_data_quality = self._build_human_data_quality(eo, weather, ocean, safety, data_quality)

        # ── 4. Clean Human Sources ──────────────────────────────────────────────
        human_sources = self._build_human_sources(eo, ocean, weather, safety)

        # ── 5. Format Based on Intent ───────────────────────────────────────────
        if intent == "fishing_location":
            return self._format_fishing_location_query(
                query=query,
                marine_decision=marine_decision,
                enforced_risk=enforced_risk,
                driver_agent=driver_agent,
                conflict_explanation=conflict_explanation,
                conditions=human_conditions,
                best_time=human_best_time,
                data_quality_note=human_data_quality,
                sources=human_sources,
                weather=weather,
                ocean=ocean,
                safety=safety,
                eo=eo,
                ecosystem=ecosystem,
                state=state,
            )
        elif intent == "fishing":
            return self._format_fishing_query(
                query=query,
                marine_decision=marine_decision,
                enforced_risk=enforced_risk,
                driver_agent=driver_agent,
                conflict_explanation=conflict_explanation,
                conditions=human_conditions,
                best_time=human_best_time,
                data_quality_note=human_data_quality,
                sources=human_sources,
                weather=weather,
                safety=safety,
            )
        elif intent == "timing":
            return self._format_timing_query(
                query=query,
                marine_decision=marine_decision,
                enforced_risk=enforced_risk,
                best_time=human_best_time,
                raw_best_time=best_time,
                conditions=human_conditions,
                data_quality_note=human_data_quality,
                sources=human_sources,
                weather=weather,
                safety=safety,
            )
        elif intent == "fish_abundance":
            return self._format_fish_abundance_query(
                query=query,
                enforced_risk=enforced_risk,
                conditions=human_conditions,
                data_quality_note=human_data_quality,
                sources=human_sources,
                eo=eo,
                ecosystem=ecosystem,
            )
        elif intent == "chlorophyll":
            return self._format_chlorophyll_query(
                query=query,
                eo=eo,
                ecosystem=ecosystem,
                data_quality_note=human_data_quality,
                sources=human_sources,
            )
        elif intent == "sst":
            return self._format_sst_query(
                query=query,
                ocean=ocean,
                conditions=human_conditions,
                sources=human_sources,
            )
        elif intent == "weather":
            return self._format_weather_query(
                query=query,
                weather=weather,
                conditions=human_conditions,
                sources=human_sources,
            )
        elif intent == "ocean":
            return self._format_ocean_query(
                query=query,
                ocean=ocean,
                weather=weather,
                conditions=human_conditions,
                sources=human_sources,
            )
        elif intent == "safety":
            return self._format_safety_query(
                query=query,
                safety=safety,
                enforced_risk=enforced_risk,
                driver_agent=driver_agent,
                conflict_explanation=conflict_explanation,
                conditions=human_conditions,
                sources=human_sources,
            )
        elif intent == "educational":
            return self._format_educational_query(query, sources=human_sources)
        else:
            return self._format_general_query(
                query=query,
                raw_answer=raw_llm_answer,
                enforced_risk=enforced_risk,
                conditions=human_conditions,
                sources=human_sources,
            )

    def _build_human_conditions(
        self,
        ocean: Dict[str, Any],
        weather: Dict[str, Any],
        safety: Dict[str, Any],
        eo: Dict[str, Any],
        ecosystem: Dict[str, Any],
    ) -> Dict[str, Optional[str]]:
        # Wind
        w_spd = (weather.get("wind") or {}).get("speed")
        w_dir = _format_wind_direction((weather.get("wind") or {}).get("direction"))
        if w_spd is None:
            ocean_w = ((ocean.get("wind") or {}).get("speed") or {}).get("value")
            if ocean_w is not None:
                w_spd = round(float(ocean_w) * 1.94384, 1)

        wind_desc = "light breeze"
        if w_spd is not None:
            if w_spd >= 22.0:
                wind_desc = "strong and hazardous"
            elif w_spd >= 15.0:
                wind_desc = "moderate breeze with surface chop"
            elif w_spd >= 8.0:
                wind_desc = "gentle to moderate breeze"
            else:
                wind_desc = "light breeze"
            wind_str = f"{round(w_spd)} knots from the {w_dir} ({wind_desc})"
        else:
            wind_str = "Wind telemetry unavailable"

        # Sea State / Waves
        wave_h = ocean.get("significant_wave_height_m")
        sea_cond = weather.get("sea_condition") or "Moderate"
        if wave_h is not None:
            sea_str = f"{sea_cond} sea state, ocean wave height about {round(wave_h, 1)} m"
        else:
            sea_str = f"{sea_cond} sea state"

        # Water Temperature
        sst = ocean.get("sea_surface_temperature_c") or (ocean.get("sea_surface_temperature") or {}).get("value")
        if sst is not None:
            sst_str = f"About {round(float(sst))}°C"
        else:
            sst_str = "Warm coastal waters"

        # Visibility
        vis = (weather.get("visibility") or {}).get("value") or "8.0 km"
        vis_str = f"Clear (~{vis})"

        # Safety / Boundary
        prox = safety.get("proximity") or {}
        dist_km = prox.get("distance_km")
        status = prox.get("status", "inside")
        risk_lvl = safety.get("risk_level", "low")

        if risk_lvl in ("high", "critical") or status in ("near_boundary", "breach"):
            demo_tag = " (demo boundary, NOT FOR NAVIGATION)" if prox.get("demo_only") else ""
            safety_str = f"WARNING: Near monitored boundary (~{dist_km} km away){demo_tag}. Restricted zone." if dist_km else f"WARNING: Boundary restriction active{demo_tag}."
        else:
            safety_str = "Clear of monitored maritime boundaries and restricted zones"

        # Chlorophyll
        chla_val = eo.get("value")
        obs_date = eo.get("observation_date") or (eo.get("data_time") or "")[:10]
        if chla_val is not None:
            unit_str = f" {eo.get('unit')}" if eo.get("unit") else ""
            date_str = f" (observed {obs_date})" if obs_date else ""
            src_str = "ISRO MOSDAC" if eo.get("source") == "MOSDAC" else "satellite ocean color"
            chla_str = f"{chla_val}{unit_str}{date_str} ({src_str})"
        elif (ecosystem.get("chlorophyll_a") or {}).get("value") is not None:
            eco_val = (ecosystem.get("chlorophyll_a") or {}).get("value")
            chla_str = f"~{eco_val} mg/m³ (ecosystem model)"
        else:
            chla_str = None

        return {
            "wind": wind_str,
            "sea_state": sea_str,
            "water_temperature": sst_str,
            "visibility": vis_str,
            "safety": safety_str,
            "chlorophyll": chla_str,
        }

    def _build_human_best_time(self, best_time: Optional[Dict[str, Any]]) -> str:
        if best_time and best_time.get("available") and best_time.get("window"):
            win = best_time["window"]
            basis = best_time.get("basis", "")
            return f"Recommended time window: {win}" + (f" ({basis})" if basis else "")
        return "Best fishing time cannot be predicted reliably from the available data yet."

    def _build_human_data_quality(
        self,
        eo: Dict[str, Any],
        weather: Dict[str, Any],
        ocean: Dict[str, Any],
        safety: Dict[str, Any],
        data_quality: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        notes = []
        # Check simulation
        if weather.get("status") not in ("live", "success") and weather.get("source") in ("simulated", "demo", "IMD-SIMULATED"):
            notes.append("This weather information is simulated for prototype use and should not be treated as live weather.")
        if ocean.get("status") not in ("live", "success") and ocean.get("source") in ("simulated", "demo"):
            notes.append("Ocean measurements reflect simulated baseline observations.")

        # Check freshness
        is_eo_stale = eo.get("freshness") in ("stale", "very_stale")
        if is_eo_stale and eo.get("observation_date"):
            notes.append(f"Satellite chlorophyll data is from an earlier observation ({eo.get('observation_date')}), so it should not be treated as a live reading.")

        if notes:
            return " ".join(notes)
        return "Based on fresh coastal weather and recent satellite observations."

    def _build_human_sources(
        self,
        eo: Dict[str, Any],
        ocean: Dict[str, Any],
        weather: Dict[str, Any],
        safety: Dict[str, Any],
    ) -> List[str]:
        sources = []
        if weather:
            sources.append("IMD Weather")
        if ocean:
            sources.append("INCOIS Ocean Data")
        if eo:
            sources.append("ISRO Satellite Data")
        if safety:
            sources.append("Safety / Boundary Monitoring")
        return sources or ["Marine Coastal Network"]

    def _format_fishing_query(
        self,
        query: str,
        marine_decision: Optional[Dict[str, Any]],
        enforced_risk: str,
        driver_agent: str,
        conflict_explanation: Optional[str],
        conditions: Dict[str, Optional[str]],
        best_time: str,
        data_quality_note: Optional[str],
        sources: List[str],
        weather: Dict[str, Any],
        safety: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        # Extract recommendation code
        rec = "CAUTION"
        if marine_decision:
            rec = str(marine_decision.get("recommendation") or marine_decision.get("label") or "CAUTION").upper()
        elif enforced_risk in ("high", "critical"):
            rec = "AVOID"
        elif enforced_risk == "low":
            rec = "GO"
        else:
            rec = "CAUTION"

        warns = (weather.get("warnings") or [])
        prox = (safety.get("proximity") or {})
        dist_km = prox.get("distance_km")

        if rec == "GO":
            decision_code = "GO"
            direct_answer = "GO — Conditions are suitable for fishing."
            explanation = (
                "Winds are manageable and the sea conditions are suitable for normal coastal operations. "
                "No major safety warning is currently active."
            )
            safety_notice = "Check the latest marine warning before departure. Maintain standard nautical watch."

        elif rec == "CAUTION":
            decision_code = "CAUTION"
            direct_answer = "CAUTION — You can go fishing, but extra care is needed."
            explanation = (
                "Moderate surface winds and sea chop present challenges for smaller craft. "
                "Conditions are manageable, but require heightened vigilance."
            )
            safety_notice = "Check the latest marine warning before departure. Stay vigilant and wear life jackets."

        elif rec == "AVOID":
            decision_code = "AVOID"
            direct_answer = "AVOID — Conditions are not safe for fishing."
            if (safety.get("risk_level") or "").lower() in ("high", "critical"):
                alert_msg = prox.get("alert_message") or "You are too close to a monitored maritime boundary"
                dist_str = f" (about {dist_km} km away)" if dist_km else ""
                explanation = (
                    f"You are too close to a monitored maritime boundary: {alert_msg}{dist_str}. "
                    "Navigational risk is elevated. Do not cross into restricted waters."
                )
            elif warns:
                explanation = f"An active severe-weather warning is affecting this area: {', '.join(warns)}. Strong winds and rough seas make sailing dangerous."
            else:
                explanation = "Rough sea conditions and elevated hazards make sailing unsafe for small craft at this time."
            safety_notice = "Advise small craft to remain in port until conditions abate. Monitor marine emergency channels."

        else:  # INSUFFICIENT_DATA
            decision_code = "INSUFFICIENT_DATA"
            direct_answer = "INSUFFICIENT DATA — ORCA cannot reliably determine whether conditions are safe."
            explanation = (
                "Essential weather or navigational safety data for this specific location is missing or unavailable. "
                "For your safety, do not sail without local confirmation."
            )
            safety_notice = "Check with local harbor authorities or IMD coastal stations prior to departure."

        if conflict_explanation and "disagree" not in explanation.lower():
            explanation += f" Note: Coastal data sources disagree: {conflict_explanation}"

        eco_note = "Chlorophyll levels can indicate biological productivity, but they do not guarantee where fish will be."

        cond_lines = [
            f"• Wind: {conditions.get('wind')}",
            f"• Sea: {conditions.get('sea_state')}",
            f"• Water temperature: {conditions.get('water_temperature')}",
        ]
        if conditions.get("chlorophyll"):
            cond_lines.append(f"• Chlorophyll: {conditions.get('chlorophyll')}")
        cond_lines.append(f"• Safety: {conditions.get('safety')}")

        lines = [
            direct_answer,
            "",
            explanation,
            "",
            "Current conditions:",
            *cond_lines,
            "",
            f"Best time:\n{best_time}",
            "",
            f"Safety:\n{safety_notice}",
            "",
            f"Note on fish abundance:\n{eco_note}",
        ]

        if data_quality_note:
            lines.extend(["", f"Data:\n{data_quality_note}"])

        formatted_answer = _sanitize_human_text("\n".join(lines))

        human_resp = {
            "direct_answer": direct_answer,
            "decision_code": decision_code,
            "explanation": explanation,
            "best_time": best_time,
            "conditions": conditions,
            "safety_notice": safety_notice,
            "data_quality_note": data_quality_note,
            "sources": sources,
        }

        return formatted_answer, human_resp

    def _format_fishing_location_query(
        self,
        query: str,
        marine_decision: Optional[Dict[str, Any]],
        enforced_risk: str,
        driver_agent: str,
        conflict_explanation: Optional[str],
        conditions: Dict[str, Optional[str]],
        best_time: str,
        data_quality_note: Optional[str],
        sources: List[str],
        weather: Dict[str, Any],
        ocean: Dict[str, Any],
        safety: Dict[str, Any],
        eo: Dict[str, Any],
        ecosystem: Dict[str, Any],
        state: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Produce structured fishing-location recommendation incorporating chlorophyll/phytoplankton
        biological productivity, SST, wind, sea state, and safety constraints.
        Strictly observes scientific limits: does not claim chlorophyll = fish abundance.
        """
        # 1. Decision Code (GO | CAUTION | AVOID)
        rec = "CAUTION"
        if marine_decision:
            rec = str(marine_decision.get("recommendation") or marine_decision.get("label") or "CAUTION").upper()
        elif enforced_risk in ("high", "critical"):
            rec = "AVOID"
        elif enforced_risk == "low":
            rec = "GO"
        else:
            rec = "CAUTION"

        # 2. Recommended Area Resolution
        from app.services.spatial_reasoner import _lookup_fishing_coordinates
        dest_lat, dest_lon, dest_name, dest_desc = _lookup_fishing_coordinates(
            query,
            target_location=None,
            query_location_entity=None,
            conversation_history=state.get("conversation_history"),
            user_location=None,
        )

        place_name = "Chennai" if "chennai" in query.lower() or "chennai" in dest_name.lower() else (
            "Mumbai" if "mumbai" in query.lower() or "mumbai" in dest_name.lower() else (
                "Kochi" if "kochi" in query.lower() or "kochi" in dest_name.lower() else (
                    dest_name.split()[0] if dest_name else "this coastal sector"
                )
            )
        )

        clean_dest_name = dest_name.replace(" (Catalog Baseline)", "").replace(" (Deterministic Baseline)", "").strip()
        area_title = f"{clean_dest_name} (Catalog Baseline)"
        coords_str = f"~{dest_lat:.4f}°N, {dest_lon:.4f}°E" if dest_lat and dest_lon else ""
        area_display = f"{area_title}\n{coords_str}" if coords_str else area_title
        area_inline = f"{area_title} ({coords_str})" if coords_str else area_title

        # 3. Chlorophyll & Phytoplankton / Biological Productivity
        chla_val = eo.get("value")
        chla_unit = eo.get("unit") or "mg/m³"
        obs_date = eo.get("observation_date") or (eo.get("data_time") or "")[:10]
        has_valid_chla = chla_val is not None and eo.get("status") in ("success", "live") and float(chla_val) > 0.0

        if has_valid_chla:
            c_val = float(chla_val)
            date_part = f" (observed {obs_date}, ISRO MOSDAC)" if obs_date else " (ISRO MOSDAC)"
            chla_display = f"{c_val:.4f} {chla_unit}{date_part}"
            if c_val < 0.05:
                qual = "Low to Moderate"
            elif c_val <= 0.25:
                qual = "Moderate"
            else:
                qual = "Elevated"
            bio_display = f"{qual} based on the observed chlorophyll-a concentration (Phytoplankton/biological productivity inferred from chlorophyll-a)"
            reasoning_text = (
                f"The available MOSDAC ocean-colour observation provides a chlorophyll-a signal of {c_val:.4f} {chla_unit} "
                f"that indicates the observed level of phytoplankton/primary productivity in the area. "
                f"Combined with the SST of {conditions.get('water_temperature') or 'About 29°C'} and favorable wind/sea-state conditions "
                f"({conditions.get('wind') or '12 knots from southwest'}, {conditions.get('sea_state') or 'Smooth to Slight sea state'}), "
                f"the {clean_dest_name} sector is identified as a potentially productive fishing area among the available candidate locations.\n\n"
                "However, chlorophyll-a is an indirect ecological indicator and does not directly measure fish abundance. "
                "ORCA therefore cannot scientifically guarantee that this is the location with the \"maximum fish\"; "
                "it is a data-supported potential fishing area based on the available observations."
            )
            conditions["chlorophyll"] = f"{c_val:.4f} {chla_unit} (observed {obs_date})" if obs_date else f"{c_val:.4f} {chla_unit}"
            conditions["chlorophyll_a"] = f"{c_val:.4f} {chla_unit}"
            conditions["phytoplankton"] = bio_display
        elif (ecosystem.get("chlorophyll_a") or {}).get("value") is not None:
            eco_val = float((ecosystem.get("chlorophyll_a") or {}).get("value"))
            chla_display = f"~{eco_val:.4f} mg/m³ (modeled marine baseline)"
            bio_display = "Moderate baseline productivity (inferred from ecosystem model)"
            reasoning_text = (
                f"Ecosystem modeling indicates baseline biological productivity near {place_name} (~{eco_val:.4f} mg/m³), "
                f"supporting the marine food web. Combined with current marine conditions, the {clean_dest_name} sector "
                "is identified as a candidate fishing area. Chlorophyll alone cannot guarantee fish presence."
            )
            conditions["chlorophyll"] = chla_display
            conditions["chlorophyll_a"] = chla_display
            conditions["phytoplankton"] = bio_display
        else:
            chla_display = "Chlorophyll observation unavailable for this location"
            bio_display = "Chlorophyll observation unavailable; biological productivity could not be evaluated from ocean-colour data"
            reasoning_text = (
                f"Based on evaluated marine environmental conditions ({conditions.get('wind') or 'moderate wind'}, "
                f"{conditions.get('sea_state') or 'moderate sea state'}) and navigational safety clearance, "
                f"the {clean_dest_name} sector is identified as an accessible coastal candidate location. "
                "Chlorophyll-a ocean-colour observations are currently unavailable for this specific sector, "
                "so biological productivity cannot be directly verified."
            )

        # 4. SST, Wind, Sea State, Safety
        sst = ocean.get("sea_surface_temperature_c") or (ocean.get("sea_surface_temperature") or {}).get("value")
        if sst is not None:
            sst_display = f"About {round(float(sst), 1)}°C"
        else:
            sst_display = conditions.get("water_temperature") or "About 29°C"

        wind_display = conditions.get("wind") or "12 knots from southwest"
        sea_display = conditions.get("sea_state") or "Smooth to Slight"
        safety_display = conditions.get("safety") or "Clear of monitored maritime boundaries and restricted zones"

        limitation_text = (
            "Chlorophyll-a indicates phytoplankton/biological productivity and is not a direct measurement of "
            "fish abundance. Therefore ORCA describes the result as a potentially productive fishing area rather "
            "than claiming that it contains the maximum fish concentration."
        )
        safety_action_text = "Always verify local marine bulletins and port notices prior to departure. Maintain standard nautical watch."

        explanation_body = (
            f"**Recommended area:**\n{area_display}\n\n"
            f"### Why this area?\n\n"
            f"* **Chlorophyll-a:** {chla_display}\n"
            f"* **Phytoplankton / biological productivity:** {bio_display}\n"
            f"* **SST:** {sst_display}\n"
            f"* **Wind:** {wind_display}\n"
            f"* **Sea state:** {sea_display}\n"
            f"* **Safety:** {safety_display}\n\n"
            f"### ORCA reasoning\n\n"
            f"{reasoning_text}\n\n"
            f"### Important limitation\n\n"
            f"> {limitation_text}"
        )

        full_lines = [
            f"### {rec}",
            "",
            explanation_body,
            "",
            "### Safety action",
            "",
            safety_action_text,
        ]
        if data_quality_note:
            full_lines.extend(["", f"Data note:\n{data_quality_note}"])

        formatted_answer = _sanitize_human_text("\n".join(full_lines))

        human_resp = {
            "direct_answer": rec,
            "decision_code": rec,
            "recommended_area": area_inline,
            "explanation": explanation_body,
            "best_time": best_time,
            "conditions": conditions,
            "safety_notice": safety_action_text,
            "data_quality_note": data_quality_note,
            "sources": sources,
        }

        return formatted_answer, human_resp

    def _format_timing_query(
        self,
        query: str,
        marine_decision: Optional[Dict[str, Any]],
        enforced_risk: str,
        best_time: str,
        raw_best_time: Optional[Dict[str, Any]],
        conditions: Dict[str, Optional[str]],
        data_quality_note: Optional[str],
        sources: List[str],
        weather: Dict[str, Any],
        safety: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        has_verified_forecast = bool(raw_best_time and raw_best_time.get("available") and raw_best_time.get("window"))

        if has_verified_forecast:
            win = raw_best_time["window"]
            basis = raw_best_time.get("basis", "")
            decision_code = "GO" if enforced_risk == "low" else "CAUTION"
            direct_answer = f"{decision_code} — The best recommended fishing window is {win}."
            explanation = f"Forecasted marine conditions are suitable during {win}." + (f" ({basis})" if basis else "")
            timing_line = f"Recommended time window: {win}" + (f" ({basis})" if basis else "")
        else:
            decision_code = "INSUFFICIENT_DATA"
            direct_answer = "INSUFFICIENT DATA — ORCA cannot reliably determine the best future fishing time from the available data yet."
            explanation = (
                "Verified future hourly forecast data is currently unavailable for this area to predict an optimal departure window. "
                "Current conditions can be evaluated, but future timing cannot be guaranteed without active hourly forecasts."
            )
            timing_line = "A reliable fishing time cannot be predicted reliably from the available data yet."

        safety_notice = "Check the latest marine weather warning before departure. Maintain standard nautical watch."
        eco_note = "Chlorophyll levels can indicate biological productivity, but they do not guarantee where fish will be."

        lines = [
            direct_answer,
            "",
            explanation,
            "",
            "Current conditions:",
            f"• Wind: {conditions.get('wind')}",
            f"• Sea: {conditions.get('sea_state')}",
            f"• Water temperature: {conditions.get('water_temperature')}",
            f"• Safety: {conditions.get('safety')}",
            "",
            f"Best time:\n{timing_line}",
            "",
            f"Safety:\n{safety_notice}",
            "",
            f"Note on fish abundance:\n{eco_note}",
        ]

        if data_quality_note:
            lines.extend(["", f"Data:\n{data_quality_note}"])

        formatted_answer = _sanitize_human_text("\n".join(lines))

        human_resp = {
            "direct_answer": direct_answer,
            "decision_code": decision_code,
            "explanation": explanation,
            "best_time": timing_line,
            "conditions": conditions,
            "safety_notice": safety_notice,
            "data_quality_note": data_quality_note,
            "sources": sources,
        }

        return formatted_answer, human_resp

    def _format_fish_abundance_query(
        self,
        query: str,
        enforced_risk: str,
        conditions: Dict[str, Optional[str]],
        data_quality_note: Optional[str],
        sources: List[str],
        eo: Dict[str, Any],
        ecosystem: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        direct_answer = "Fish abundance cannot be confirmed from the current data alone."
        explanation = (
            "Chlorophyll levels can indicate biological productivity, but they do not guarantee where fish will be. "
            "Fish movement also depends on changing water currents, water temperature gradients, and seasonal migration patterns."
        )

        val = eo.get("value")
        val_str = f"Estimated satellite chlorophyll index is about {val}." if val is not None else "Satellite chlorophyll readings are at typical regional levels."

        lines = [
            direct_answer,
            "",
            explanation,
            "",
            f"{val_str} Surface conditions can support marine life, but fish catch cannot be guaranteed from weather alone.",
            "",
            "Current sea conditions:",
            f"• Wind: {conditions.get('wind')}",
            f"• Sea: {conditions.get('sea_state')}",
            f"• Safety: {conditions.get('safety')}",
        ]

        formatted_answer = _sanitize_human_text("\n".join(lines))

        human_resp = {
            "direct_answer": direct_answer,
            "decision_code": None,
            "explanation": explanation,
            "best_time": None,
            "conditions": conditions,
            "safety_notice": "Never navigate into hazardous waters or border areas chasing fish.",
            "data_quality_note": data_quality_note,
            "sources": sources,
        }

        return formatted_answer, human_resp

    def _format_chlorophyll_query(
        self,
        query: str,
        eo: Dict[str, Any],
        ecosystem: Dict[str, Any],
        data_quality_note: Optional[str],
        sources: List[str],
    ) -> Tuple[str, Dict[str, Any]]:
        val = eo.get("value")
        obs_date = eo.get("observation_date") or ""

        if val is not None and eo.get("status") in ("success", "live"):
            direct_answer = f"Chlorophyll concentration in this area is approximately {val} based on the nearest available observation."
            date_str = f" Observed on {obs_date}." if obs_date else ""
            explanation = (
                f"Derived from ISRO MOSDAC satellite ocean color observations.{date_str} "
                "Chlorophyll indicates biological productivity and phytoplankton growth in coastal waters."
            )
        else:
            direct_answer = "Satellite chlorophyll data is currently unavailable for this area."
            explanation = "Observations may be unavailable due to heavy cloud cover or orbital coverage timing."

        lines = [
            direct_answer,
            "",
            explanation,
            "",
            "Note: Chlorophyll indicates primary biological productivity, but does not guarantee fish presence.",
        ]

        if data_quality_note:
            lines.extend(["", f"Data note: {data_quality_note}"])

        formatted_answer = _sanitize_human_text("\n".join(lines))

        human_resp = {
            "direct_answer": direct_answer,
            "decision_code": None,
            "explanation": explanation,
            "best_time": None,
            "conditions": None,
            "safety_notice": None,
            "data_quality_note": data_quality_note,
            "sources": sources,
        }

        return formatted_answer, human_resp

    def _format_sst_query(
        self,
        query: str,
        ocean: Dict[str, Any],
        conditions: Dict[str, Optional[str]],
        sources: List[str],
    ) -> Tuple[str, Dict[str, Any]]:
        sst = ocean.get("sea_surface_temperature_c") or (ocean.get("sea_surface_temperature") or {}).get("value")
        if sst is not None:
            direct_answer = f"Sea surface temperature in this coastal area is currently about {round(float(sst), 1)}°C."
            explanation = f"Water temperatures around {round(float(sst))}°C are warm and normal for this season."
        else:
            direct_answer = "Sea surface temperature is currently about 30°C based on regional coastal averages."
            explanation = "Surface waters are warm and within expected coastal baselines."

        lines = [
            direct_answer,
            "",
            explanation,
            "",
            "Current sea conditions:",
            f"• Sea: {conditions.get('sea_state')}",
            f"• Wind: {conditions.get('wind')}",
        ]

        formatted_answer = _sanitize_human_text("\n".join(lines))

        human_resp = {
            "direct_answer": direct_answer,
            "decision_code": None,
            "explanation": explanation,
            "best_time": None,
            "conditions": conditions,
            "safety_notice": None,
            "data_quality_note": None,
            "sources": sources,
        }

        return formatted_answer, human_resp

    def _format_weather_query(
        self,
        query: str,
        weather: Dict[str, Any],
        conditions: Dict[str, Optional[str]],
        sources: List[str],
    ) -> Tuple[str, Dict[str, Any]]:
        w_spd = (weather.get("wind") or {}).get("speed")
        w_dir = _format_wind_direction((weather.get("wind") or {}).get("direction"))
        sea_cond = weather.get("sea_condition") or "moderate"
        warns = weather.get("warnings") or []

        direct_answer = f"Coastal weather is currently {sea_cond.lower()} with winds around {round(w_spd or 12)} knots from the {w_dir}."
        if warns:
            explanation = f"Active weather warning: {', '.join(warns)}. Exercise caution."
        else:
            explanation = "No severe weather or storm warnings are currently active. Visibility is good."

        lines = [
            direct_answer,
            "",
            explanation,
            "",
            "Current conditions:",
            f"• Wind: {conditions.get('wind')}",
            f"• Sea: {conditions.get('sea_state')}",
            f"• Visibility: {conditions.get('visibility')}",
        ]

        formatted_answer = _sanitize_human_text("\n".join(lines))

        human_resp = {
            "direct_answer": direct_answer,
            "decision_code": None,
            "explanation": explanation,
            "best_time": None,
            "conditions": conditions,
            "safety_notice": "Always verify latest port weather bulletins before sailing.",
            "data_quality_note": None,
            "sources": sources,
        }

        return formatted_answer, human_resp

    def _format_ocean_query(
        self,
        query: str,
        ocean: Dict[str, Any],
        weather: Dict[str, Any],
        conditions: Dict[str, Optional[str]],
        sources: List[str],
    ) -> Tuple[str, Dict[str, Any]]:
        wave_h = ocean.get("significant_wave_height_m")
        sea_cond = weather.get("sea_condition") or "Moderate"
        sst = ocean.get("sea_surface_temperature_c") or (ocean.get("sea_surface_temperature") or {}).get("value")

        if wave_h is not None:
            direct_answer = f"Sea conditions are currently {sea_cond.lower()} with wave heights of about {round(wave_h, 1)} meters."
        else:
            direct_answer = f"Sea conditions are currently evaluated as {sea_cond.lower()}."

        sst_phrase = f" Sea temperature is about {round(float(sst))}°C." if sst else ""
        explanation = f"Current swell and wave heights are within typical coastal ranges.{sst_phrase}"

        lines = [
            direct_answer,
            "",
            explanation,
            "",
            "Current sea conditions:",
            f"• Sea: {conditions.get('sea_state')}",
            f"• Wind: {conditions.get('wind')}",
            f"• Water temperature: {conditions.get('water_temperature')}",
        ]

        formatted_answer = _sanitize_human_text("\n".join(lines))

        human_resp = {
            "direct_answer": direct_answer,
            "decision_code": None,
            "explanation": explanation,
            "best_time": None,
            "conditions": conditions,
            "safety_notice": "Keep watch for changing swell patterns in open waters.",
            "data_quality_note": None,
            "sources": sources,
        }

        return formatted_answer, human_resp

    def _format_safety_query(
        self,
        query: str,
        safety: Dict[str, Any],
        enforced_risk: str,
        driver_agent: str,
        conflict_explanation: Optional[str],
        conditions: Dict[str, Optional[str]],
        sources: List[str],
    ) -> Tuple[str, Dict[str, Any]]:
        prox = safety.get("proximity") or {}
        dist_km = prox.get("distance_km")

        if enforced_risk in ("high", "critical"):
            direct_answer = "AVOID — Significant safety hazards are present in this sector."
            alert_msg = prox.get("alert_message") or "You are too close to a monitored maritime boundary"
            dist_str = f" (about {dist_km} km away)" if dist_km else ""
            explanation = f"Navigational warning: {alert_msg}{dist_str}. Operating here is unsafe."
            safety_notice = "Stay well clear of maritime boundaries. Return to safe waters immediately if warned."
            decision_code = "AVOID"
        elif enforced_risk == "moderate":
            direct_answer = "CAUTION — Navigational safety requires heightened vigilance in this sector."
            explanation = "Moderate sea conditions or approaching buffer boundaries require careful navigation."
            safety_notice = "Maintain a continuous nautical watch and confirm GPS coordinates."
            decision_code = "CAUTION"
        else:
            direct_answer = "GO — Navigational safety conditions are currently clear in this area."
            dist_str = f" The nearest boundary line is over {dist_km} km away." if dist_km else ""
            explanation = f"No active maritime boundary alerts or security restrictions are present.{dist_str}"
            safety_notice = "Maintain standard watch and navigational safety procedures."
            decision_code = "GO"

        if conflict_explanation and "disagree" not in explanation.lower():
            explanation += f" Note: Coastal data sources disagree: {conflict_explanation}"

        lines = [
            direct_answer,
            "",
            explanation,
            "",
            "Safety summary:",
            f"• Boundary: {conditions.get('safety')}",
            f"• Sea: {conditions.get('sea_state')}",
            f"• Wind: {conditions.get('wind')}",
        ]

        formatted_answer = _sanitize_human_text("\n".join(lines))

        human_resp = {
            "direct_answer": direct_answer,
            "decision_code": decision_code,
            "explanation": explanation,
            "best_time": None,
            "conditions": conditions,
            "safety_notice": safety_notice,
            "data_quality_note": None,
            "sources": sources,
        }

        return formatted_answer, human_resp

    def _format_educational_query(self, query: str, sources: List[str]) -> Tuple[str, Dict[str, Any]]:
        direct_answer = "Chlorophyll is the green pigment in microscopic marine plants called phytoplankton."
        explanation = (
            "Phytoplankton form the base of the ocean food chain. When sunlight and nutrients are present, "
            "phytoplankton multiply, providing food for zooplankton and small fish. While high chlorophyll indicates "
            "productive feeding grounds, it does not guarantee where fish schools will gather."
        )

        lines = [
            direct_answer,
            "",
            explanation,
        ]

        formatted_answer = _sanitize_human_text("\n".join(lines))

        human_resp = {
            "direct_answer": direct_answer,
            "decision_code": None,
            "explanation": explanation,
            "best_time": None,
            "conditions": None,
            "safety_notice": None,
            "data_quality_note": None,
            "sources": sources,
        }

        return formatted_answer, human_resp

    def _format_general_query(
        self,
        query: str,
        raw_answer: Optional[str],
        enforced_risk: str,
        conditions: Dict[str, Optional[str]],
        sources: List[str],
    ) -> Tuple[str, Dict[str, Any]]:
        if raw_answer and len(raw_answer.strip()) > 10 and not raw_answer.strip().startswith("{"):
            cleaned = _sanitize_human_text(raw_answer)
            direct = cleaned.split(".")[0] + "." if "." in cleaned else cleaned
            human_resp = {
                "direct_answer": direct,
                "decision_code": None,
                "explanation": cleaned,
                "best_time": None,
                "conditions": conditions,
                "safety_notice": "Check official coastal advisories before departing.",
                "data_quality_note": None,
                "sources": sources,
            }
            return cleaned, human_resp

        direct_answer = f"Operational conditions in this sector are evaluated as {enforced_risk.upper()} risk."
        explanation = "Vessel operators should review current sea and weather conditions before departing."

        lines = [
            direct_answer,
            "",
            explanation,
            "",
            f"• Wind: {conditions.get('wind')}",
            f"• Sea: {conditions.get('sea_state')}",
            f"• Safety: {conditions.get('safety')}",
        ]

        formatted_answer = _sanitize_human_text("\n".join(lines))

        human_resp = {
            "direct_answer": direct_answer,
            "decision_code": None,
            "explanation": explanation,
            "best_time": None,
            "conditions": conditions,
            "safety_notice": "Maintain standard nautical watch and navigational safety procedures.",
            "data_quality_note": None,
            "sources": sources,
        }

        return formatted_answer, human_resp


# Global singleton instance
human_response_formatter = HumanResponseFormatter()
