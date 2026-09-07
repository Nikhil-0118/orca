"""
Multi-Agent reasoning engine for ORCA marine intelligence.
Contains master orchestrator and specialist domain agents.

Note: Legacy agents (BaseAgent, orchestrator, etc.) require structlog and are
imported lazily. The new LangGraph node functions (ocean_agent, etc.) are
imported directly by the graph module and do NOT depend on this __init__.
"""
