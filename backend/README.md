# ORCA Backend — FastAPI Architecture

FastAPI-powered orchestrator and multi-agent service for marine intelligence queries, live background alert tracking, and emergency Coast Guard distress broadcasts.

---

## 🏗️ Architecture & Decoupling Principles

```text
backend/app/
├── api/            # HTTP/SSE/WebSocket routing (chat, alerts, sos, health)
├── agents/         # Multi-agent orchestrator & specialist agents (BaseAgent pattern)
├── connectors/     # Decoupled external API clients (MOSDAC, INCOIS, NavIC)
├── services/       # Domain business logic (Alerting, Geofencing, SMS, SOS)
├── schemas/        # Strict Pydantic models for incoming & outgoing contracts
├── core/           # Configuration, database connection pools, structured logging
└── jobs/           # Background scheduler & live re-alert poller
```

> **Strict Dependency Rule**:
> - `agents/` **must NOT** import `connectors/` directly.
> - `connectors/` are only consumed by `services/` or injected into agent runtimes as structured schemas.

---

## ⚡ Setup & Run

```bash
# 1. Create Virtual Environment
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Copy Environment Configuration
cp .env.example .env

# 4. Start Server
uvicorn app.main:app --reload --port 8000
```

---

## 🧪 Testing

```bash
pytest
```
