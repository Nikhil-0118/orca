"""
Common Evidence Model and Marine Decision Schemas (Phase 14).

Defines structured, normalized representations for observations across specialist agents
(Satellite EO, Ocean, Weather, Safety, Ecosystem, RAG), correlation findings, and
evidence-based marine operational decisions.
"""
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class FreshnessLevel(str, Enum):
    FRESH = "FRESH"
    RECENT = "RECENT"
    STALE = "STALE"
    VERY_STALE = "VERY_STALE"
    UNKNOWN = "UNKNOWN"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            o_upper = other.upper()
            if self.value == "VERY_STALE" and o_upper == "HISTORICAL":
                return True
            return self.value.upper() == o_upper
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.value)

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.upper()
            if val_upper == "HISTORICAL":
                return cls.VERY_STALE
            for member in cls:
                if member.value == val_upper or member.name == val_upper:
                    return member
            if val_upper == "UNAVAILABLE":
                return cls.UNKNOWN
        return super()._missing_(value)


class ReliabilityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value.upper() == other.upper()
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.value)

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.upper()
            for member in cls:
                if member.value == val_upper or member.name == val_upper:
                    return member
        return super()._missing_(value)


class DataSourceType(str, Enum):
    LIVE = "live"
    SIMULATED = "simulated"
    ARCHIVE = "archive"
    REMOTE_AUTHENTICATED = "remote_authenticated"
    UNAVAILABLE = "unavailable"
    DEMO = "demo"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            if self.value == "remote_authenticated" and other == "live":
                return True
            return self.value == other
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.value)

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_lower = value.lower()
            for member in cls:
                if member.value == val_lower or member.name.lower() == val_lower:
                    return member
        return super()._missing_(value)


ObservationStatus = Literal["available", "unavailable", "degraded", "stale"]
ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW", "high", "medium", "low"]
DecisionRecommendation = Literal["GO", "CAUTION", "AVOID", "INSUFFICIENT_DATA"]
DecisionRiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL", "UNKNOWN", "low", "moderate", "high", "critical", "none"]


class EvidenceMetadata(BaseModel):
    """
    Standardized, reusable metadata for tracking provenance, parameter-aware age,
    freshness tier, and deterministic reliability scoring across all ORCA agents.
    """
    source: str = Field(..., description="Reporting source identifier e.g. MOSDAC, INCOIS, IMD")
    source_type: str = Field(..., description="Source provenance e.g. remote_authenticated, archive, live, simulated, unavailable")
    dataset: Optional[str] = Field(None, description="Dataset identifier e.g. E06OCM_L4_AC, NOAA_AVHRR_AMSR_datasets")
    parameter: str = Field(..., description="Observed parameter e.g. chlorophyll_a, sea_surface_temperature, wind_speed")
    observation_time: Optional[str] = Field(None, description="Physical observation timestamp from sensor or satellite")
    retrieval_time: Optional[str] = Field(None, description="System timestamp when observation was downloaded or ingested")
    age_hours: Optional[float] = Field(None, description="Calculated age in elapsed hours from observation_time to reference time")
    freshness: FreshnessLevel = Field(FreshnessLevel.UNKNOWN, description="Parameter-aware freshness tier")
    reliability: ReliabilityLevel = Field(ReliabilityLevel.UNKNOWN, description="Deterministic source reliability score")
    status: ObservationStatus = Field("available", description="Parameter availability status")


class EvidenceItem(BaseModel):
    """
    Standardized atomic evidence unit representing a single marine observation or assessment.
    Truthfully preserves source, units (None when unspecified), freshness, and spatial provenance.
    """
    source: str = Field(..., description="Official reporting source e.g. MOSDAC, INCOIS, IMD, Local Geofence")
    agent: str = Field(..., description="Reporting specialist agent: eo | ocean | weather | safety | ecosystem | rag")
    parameter: str = Field(..., description="Observed parameter: chlorophyll_a | sst | wind_speed | wave_height | boundary_proximity | etc.")
    value: Optional[Any] = Field(None, description="Observed raw numeric or categorical value (None if missing/unavailable)")
    unit: Optional[str] = Field(None, description="Physical unit if explicitly specified by source metadata (None when unspecified, e.g. MOSDAC)")
    observation_time: Optional[str] = Field(None, description="Observation timestamp or date string (e.g. 2026-09-03)")
    retrieval_time: Optional[str] = Field(None, description="ISO timestamp when observation was retrieved or ingested")
    latitude: Optional[float] = Field(None, description="Observed grid or measurement latitude")
    longitude: Optional[float] = Field(None, description="Observed grid or measurement longitude")
    distance_km: Optional[float] = Field(None, description="Haversine distance from target/requested coordinates in km")
    freshness: FreshnessLevel = Field(FreshnessLevel.FRESH, description="Observation currency: FRESH | RECENT | STALE | VERY_STALE | UNKNOWN")
    data_source_type: DataSourceType = Field("archive", description="Data provenance: archive | live | simulated | demo | unavailable | remote_authenticated")
    confidence: ConfidenceLevel = Field("medium", description="Evidence confidence: high | medium | low")
    status: ObservationStatus = Field("available", description="Parameter availability: available | unavailable | degraded | stale")
    notes: Optional[str] = Field(None, description="Transparent metadata, data limitations, or quality notes")
    metadata: Optional[EvidenceMetadata] = Field(None, description="Structured evidence metadata and reliability scoring")


class SignalConflict(BaseModel):
    """Explicitly represents a detected disagreement between upstream agent signals."""
    parameter: str = Field(..., description="Parameter with divergent findings (e.g. wind, risk, swell)")
    sources_involved: List[str] = Field(default_factory=list, description="Agent names or sources involved")
    description: str = Field(..., description="Concise explanation of divergent observations")
    resolution: str = Field(..., description="Conservative safety resolution explanation")
    conflicting_sources: List[str] = Field(default_factory=list, description="Specific sources with divergent data")
    conflicting_parameters: List[str] = Field(default_factory=list, description="Parameters in conflict")
    reason: Optional[str] = Field(None, description="Physical or meteorological explanation of discrepancy")


class MarineDecision(BaseModel):
    """
    Evidence-based marine decision result tailored for maritime operations and fishing safety.
    Guaranteed to prioritize safety over convenience and never invent unobserved values.
    """
    recommendation: DecisionRecommendation = Field(
        ...,
        description="Operational action recommendation: GO | CAUTION | AVOID | INSUFFICIENT_DATA",
    )
    risk_level: DecisionRiskLevel = Field(
        ...,
        description="Enforced risk level: LOW | MODERATE | HIGH | CRITICAL | UNKNOWN",
    )
    confidence: ConfidenceLevel = Field(
        "MEDIUM",
        description="Decision confidence based on data completeness, freshness, and spatial relevance",
    )
    decision_summary: str = Field(
        ...,
        description="Direct 1-2 sentence plain-language operational decision summary",
    )
    conditions_summary: List[str] = Field(
        default_factory=list,
        description="Top 2-4 key environmental conditions directly affecting this decision",
    )
    reasoning: List[str] = Field(
        default_factory=list,
        description="Evidence-based reasoning points explaining why this decision was reached",
    )
    supporting_evidence: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of relevant evidence items underpinning this decision",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Active safety warnings, boundary alerts, or hazard advisories",
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Critical data parameters currently unavailable or unobserved",
    )
    conflicts: List[SignalConflict] = Field(
        default_factory=list,
        description="Detected disagreements between agent observations",
    )
    freshness_assessment: Dict[str, str] = Field(
        default_factory=dict,
        description="Freshness evaluation per parameter (e.g. {'chlorophyll_a': 'stale', 'sst': 'fresh'})",
    )


class MarineAnalysisResult(BaseModel):
    """
    Complete output of the Cross-Agent Marine Analysis Node.
    Separates data aggregation from domain analysis from final response generation.
    """
    query_category: str = Field(
        ...,
        description="Detected intent category: fishing | safety | weather | ocean | chlorophyll | general",
    )
    target_location: Optional[Dict[str, Any]] = Field(
        None,
        description="Target coordinates and place metadata evaluated during analysis",
    )
    evidence_items: List[EvidenceItem] = Field(
        default_factory=list,
        description="Normalized atomic evidence collected across all specialist agents",
    )
    conditions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Interpreted domain conditions: chlorophyll, sst, wind, wave, weather, safety",
    )
    conflicts: List[SignalConflict] = Field(
        default_factory=list,
        description="Disagreements surfaced during cross-agent correlation",
    )
    conflict_detected: bool = Field(
        False,
        description="True if any cross-agent signal conflicts were detected",
    )
    data_quality: Dict[str, Any] = Field(
        default_factory=dict,
        description="Audit of evidence completeness, freshness penalties, and spatial relevance",
    )
    decision: Optional[MarineDecision] = Field(
        None,
        description="Actionable marine decision (populated for fishing/safety/operational queries)",
    )
