"""
ORCA LangGraph Coordinator & Multi-Agent Graph Compilation.

Builds and compiles the complete Phase 5 StateGraph that routes queries through agent nodes.

Phase 5 graph topology:
  START
    │
    ▼
  coordinator_node
    │
   ┌──────────────┼──────────────┐
   ▼              ▼              ▼
  eo_node     ocean_node    weather_node
   └──────────────┼──────────────┘
                  │ (Fan-In Join)
                  ▼
              safety_node
                  │
                  ▼
               rag_node
                  │
                  ▼
            reasoner_node
                  │
                  ▼
                 END

Concurrency and Synchronization Invariants:
- The coordinator fans out to three specialist nodes (EO, Ocean, Weather) which execute concurrently.
- All three specialist nodes fan in to safety_node, which executes only after all three finish.
- safety_node executes deterministic multi-signal proximity and risk evaluation.
- rag_node queries the ChromaDB vector store and augments evidence.
- reasoner_node performs final risk maximization, conflict explanation, and answer synthesis.
- Each node writes only to its dedicated state keys.
"""
from langgraph.graph import StateGraph, START, END

from app.core.state import OrcaState
from app.agents.coordinator import coordinator_node
from app.agents.eo_agent import eo_node
from app.agents.ocean_agent import ocean_node
from app.agents.weather_agent import weather_node
from app.agents.marine_ecosystem_agent import ecosystem_node
from app.agents.safety_agent import safety_node
from app.agents.marine_analysis_agent import marine_analysis_node
from app.agents.rag_agent import rag_node
from app.agents.reasoner_agent import reasoner_node

# ── Build the graph ───────────────────────────────────────────────────────
builder = StateGraph(OrcaState)

builder.add_node("coordinator_node", coordinator_node)
builder.add_node("eo_node", eo_node)
builder.add_node("ocean_node", ocean_node)
builder.add_node("weather_node", weather_node)
builder.add_node("ecosystem_node", ecosystem_node)
builder.add_node("safety_node", safety_node)
builder.add_node("analysis_node", marine_analysis_node)
builder.add_node("rag_node", rag_node)
builder.add_node("reasoner_node", reasoner_node)

# START → coordinator
builder.add_edge(START, "coordinator_node")

# coordinator fans out to specialist nodes (concurrent execution)
builder.add_edge("coordinator_node", "eo_node")
builder.add_edge("coordinator_node", "ocean_node")
builder.add_edge("coordinator_node", "weather_node")
builder.add_edge("coordinator_node", "ecosystem_node")

# Specialist nodes converge into safety_node (fan-in join)
builder.add_edge("eo_node", "safety_node")
builder.add_edge("ocean_node", "safety_node")
builder.add_edge("weather_node", "safety_node")
builder.add_edge("ecosystem_node", "safety_node")

# safety_node → analysis_node (Cross-Agent Marine Analysis & Decision)
builder.add_edge("safety_node", "analysis_node")

# analysis_node → rag_node
builder.add_edge("analysis_node", "rag_node")

# rag_node → reasoner_node
builder.add_edge("rag_node", "reasoner_node")

# reasoner_node → END
builder.add_edge("reasoner_node", END)

# ── Compile ───────────────────────────────────────────────────────────────
orca_graph = builder.compile()
