"""
ORCA Vector Store — ChromaDB knowledge repository for marine domain data and safety rules.

Stores factual knowledge chunks covering:
1. Real Data Sources: INCOIS, MOSDAC, ISRO Bhuvan/Bhoonidhi STAC, and IMD (capabilities, uses, limitations).
2. Marine Safety & Navigational Principles: Boundary awareness, wave thresholds, storm/gale rules,
   tsunami/storm surge advisories, visibility, and compound hazard multipliers.

Provides idempotent seeding and deterministic semantic similarity search.
"""
import logging
import os
from typing import Any, Dict, List, Optional

import chromadb

logger = logging.getLogger("orca.core.vector_store")

_DEFAULT_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db"
)
_COLLECTION_NAME = "orca_marine_knowledge"


SEED_KNOWLEDGE_DOCUMENTS = [
    {
        "id": "src_incois_ocean",
        "document": (
            "Source: INCOIS (Indian National Centre for Ocean Information Services). "
            "Provides: Ocean State Forecast (OSF), Sea Surface Temperature (SST) via NOAA AVHRR/AMSR, "
            "daily ocean surface winds via ASCAT scatterometer, significant wave heights, swell, "
            "and Potential Fishing Zones (PFZ). "
            "Uses: Marine navigation, operational sea state planning, and thermal/ocean condition tracking. "
            "Limitations: Live real-time ERDDAP feeds may reflect recent satellite passes; archival datasets "
            "represent historical baselines."
        ),
        "metadata": {
            "source": "INCOIS",
            "type": "oceanographic_data",
            "category": "data_source",
        },
    },
    {
        "id": "src_imd_weather",
        "document": (
            "Source: IMD (India Meteorological Department). "
            "Provides: Coastal weather bulletins, sea area bulletins, marine wind speed and direction, "
            "visibility, sea conditions (smooth to rough), port warning signals, and cyclonic storm advisories. "
            "Uses: Tactical weather monitoring, gale warnings, and pre-departure marine safety advisories. "
            "Limitations: Bulletins are issued periodically (12-24h cycles) by Regional Specialized/ACWC centres; "
            "requires valid API access."
        ),
        "metadata": {
            "source": "IMD",
            "type": "marine_meteorology",
            "category": "data_source",
        },
    },
    {
        "id": "src_bhoonidhi_eo",
        "document": (
            "Source: ISRO / NRSC Bhoonidhi STAC API. "
            "Provides: Earth Observation (EO) satellite pass discovery and scene metadata for Indian satellites "
            "including Oceansat-3 (EOS-06 OCM-3), EOS-04 (Radar SAR), and Resourcesat series. "
            "Uses: Identifying satellite scene coverage, acquisition timestamps, sensor type, and cloud cover. "
            "Limitations: STAC catalog provides metadata/discovery; does not directly produce in-situ pixel "
            "measurements without full Level-2 raster processing."
        ),
        "metadata": {
            "source": "ISRO_Bhoonidhi",
            "type": "earth_observation",
            "category": "data_source",
        },
    },
    {
        "id": "src_mosdac_satellite",
        "document": (
            "Source: MOSDAC (Meteorological and Oceanographic Satellite Data Archival Centre / SAC ISRO). "
            "Provides: Spaceborne meteorological and oceanographic products, INSAT-3D/3DR atmospheric soundings, "
            "and satellite-derived ocean surface winds and temperature. "
            "Uses: Regional weather surveillance and synoptic satellite observations. "
            "Limitations: Spacecraft pass frequency, geostationary vs polar orbits, and downlink processing latency."
        ),
        "metadata": {
            "source": "MOSDAC",
            "type": "space_applications",
            "category": "data_source",
        },
    },
    {
        "id": "rule_boundary_awareness",
        "document": (
            "Topic: Maritime Boundary Awareness & Geofencing. "
            "Rule: Operating near international maritime boundary lines (IMBL) or protected EEZ limits "
            "presents elevated operational and legal risk. Vessels within 15 km must exercise heightened vigilance. "
            "Distinction: Demonstration boundary datasets are sample approximations for software evaluation and "
            "are strictly NOT FOR NAVIGATION."
        ),
        "metadata": {
            "source": "ORCA_Safety_Guidelines",
            "type": "navigational_safety",
            "category": "safety_rule",
        },
    },
    {
        "id": "rule_wave_and_sea_state",
        "document": (
            "Topic: Wave Height and Sea State Hazards. "
            "Rule: Significant wave heights between 2.0m and 3.0m indicate moderate sea states requiring caution "
            "for small to medium craft. Wave heights exceeding 3.0m represent rough/hazardous seas; open sea transit "
            "should be avoided and deck operations secured."
        ),
        "metadata": {
            "source": "WMO_Marine_Safety",
            "type": "sea_state",
            "category": "safety_rule",
        },
    },
    {
        "id": "rule_high_winds_and_gales",
        "document": (
            "Topic: High Marine Winds and Gale Warnings. "
            "Rule: Wind speeds exceeding 25 knots (Force 6+ on Beaufort scale) generate rough seas, spray, and reduced "
            "vessel stability. Official IMD squall/storm warnings mandate immediate precautionary maneuvers or returning to harbor."
        ),
        "metadata": {
            "source": "IMD_Marine_Guidelines",
            "type": "severe_weather",
            "category": "safety_rule",
        },
    },
    {
        "id": "rule_tsunami_and_storm_surge",
        "document": (
            "Topic: Tsunami and Storm Surge Emergencies. "
            "Rule: Tsunami and severe storm surge advisories represent critical maritime emergencies. Vessels in shallow "
            "coastal waters must immediately navigate to deep water (>100m depth) or secure craft and evacuate personnel "
            "to elevated terrain according to disaster management directives."
        ),
        "metadata": {
            "source": "INCOIS_Tsunami_Advisory",
            "type": "disaster_management",
            "category": "safety_rule",
        },
    },
    {
        "id": "rule_compound_hazards",
        "document": (
            "Topic: Multi-Signal Compound Risk Synergy. "
            "Rule: Simultaneous occurrence of multiple adverse factors—such as boundary proximity during severe "
            "weather or rough seas with poor visibility—multiplies overall risk beyond individual hazards alone. "
            "The system enforces the highest applicable risk tier and highlights cross-signal conflicts."
        ),
        "metadata": {
            "source": "ORCA_Risk_Engine",
            "type": "risk_synergy",
            "category": "safety_rule",
        },
    },
]


class ORCAVectorStore:
    """
    ChromaDB wrapper managing knowledge indexing and semantic retrieval.
    """

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or _DEFAULT_PERSIST_DIR
        os.makedirs(self.persist_directory, exist_ok=True)

        try:
            self._client = chromadb.PersistentClient(path=self.persist_directory)
        except Exception:
            self._client = chromadb.EphemeralClient()

        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self.add_seed_documents()

    def add_seed_documents(self) -> None:
        """Seed default factual domain and safety chunks idempotently."""
        try:
            existing_count = self._collection.count()
            if existing_count >= len(SEED_KNOWLEDGE_DOCUMENTS):
                logger.debug("vector_store_already_seeded", extra={"count": existing_count})
                return

            ids = [d["id"] for d in SEED_KNOWLEDGE_DOCUMENTS]
            docs = [d["document"] for d in SEED_KNOWLEDGE_DOCUMENTS]
            metas = [d["metadata"] for d in SEED_KNOWLEDGE_DOCUMENTS]

            self._collection.upsert(
                ids=ids,
                documents=docs,
                metadatas=metas,
            )
            logger.info("vector_store_seeded", extra={"documents_seeded": len(ids)})
        except Exception as e:
            logger.warning("vector_store_seed_failed", extra={"error": str(e)})

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Query vector store for relevant context chunks.
        Returns formatted list of matching documents.
        """
        if not query or not query.strip():
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k, max(1, self._collection.count())),
            )

            hits: List[Dict[str, Any]] = []
            if results and "documents" in results and results["documents"]:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
                ids = results["ids"][0] if results.get("ids") else [""] * len(docs)
                dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

                for doc_id, doc, meta, dist in zip(ids, docs, metas, dists):
                    hits.append({
                        "id": doc_id,
                        "document": doc,
                        "metadata": meta,
                        "distance": round(float(dist), 4),
                    })

            return hits
        except Exception as e:
            logger.warning("vector_store_query_failed", extra={"error": str(e)})
            return []


# Global singleton instance
vector_store = ORCAVectorStore()
