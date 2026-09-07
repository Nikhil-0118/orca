# ORCA — Multi-Agent Marine Intelligence Platform

**Smart India Hackathon (SIH) 2026 — Under Indian Space Research Organisation (ISRO)**

ORCA is an AI-powered marine decision-support system and live intelligence hub built for fishermen, coastal disaster management teams, and maritime researchers. It fuses real-time satellite oceanography from **MOSDAC (ISRO)**, **INCOIS (ERDDAP)**, and satellite distress/messaging beacons (**NavIC / DAT-SG**) into plain-language conversational answers and interactive high-seas geospatial intelligence.

---

## 🏛️ System Architecture

```text
                                 +-----------------------+
                                 |   Fishermen / Users   |
                                 +-----------+-----------+
                                             |
                                 +-----------v-----------+
                                 |  ORCA Frontend (SPA)  |
                                 | React + TS + Vite Map |
                                 +-----------+-----------+
                                             | HTTP / SSE / WS
                                 +-----------v-----------+
                                 | FastAPI Backend Router|
                                 +-----------+-----------+
                                             |
                   +-------------------------+-------------------------+
                   |                                                   |
        +----------v----------+                             +----------v----------+
        | Master Orchestrator |                             | Background Services |
        +----------+----------+                             +----------+----------+
                   |                                                   |
  +----------------+----------------+                     +------------+------------+
  |        Specialist Agents        |                     |        Core Services    |
  |  - Weather & Storm Agent        |                     |  - Live Alert Poller    |
  |  - Fishing Zone (PFZ) Agent     |                     |  - Geofencing / IMBL    |
  |  - Ocean Temperature Agent      |                     |  - SMS Fallback Gateway |
  |  - Safety & Boundary Agent      |                     |  - Priority SOS MRCC    |
  +----------------+----------------+                     +------------+------------+
                   |                                                   |
                   +-------------------------+-------------------------+
                                             |
                                 +-----------v-----------+
                                 |  Isolated Connectors  |
                                 |  (MOSDAC/INCOIS/NavIC)|
                                 +-----------------------+
```

---

## 📂 Repository Structure

- [`backend/`](./backend): FastAPI service containing the multi-agent orchestrator, decoupled connector adapters, background re-alerting workers, and domain services.
- [`frontend/`](./frontend): React + TypeScript dashboard with live MapLibre/Leaflet geospatial layers, conversational reasoning trace visualizer, SMS fallback badges, and isolated safety-critical SOS trigger.
- [`.github/workflows/`](./.github/workflows): Automated CI workflows for backend test suites and frontend type-checking/linting.

---

## 🚀 Quick Start with Docker Compose

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)

### Run Locally
```bash
# 1. Clone repository
git clone https://github.com/your-org/orca.git
cd orca

# 2. Setup environment variables
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Spin up all services
docker-compose up --build
```

- **Frontend App**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛠️ Local Development (Without Docker)

### Backend
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🔒 Architectural Principles & Decoupling Guarantees

1. **One-Way Dependency**: `agents/` **never** import `connectors/` directly. Connectors feed standardized schemas into the service layer, keeping agent logic resilient to external API changes.
2. **Safety-Critical SOS Isolation**: The SOS distress subsystem has zero non-essential UI or middleware dependencies. It dispatches directly through redundant channels (Internet -> Webhook/SMS -> NavIC/DAT-SG uplink).
3. **Low-Bandwidth Fallback**: Automatic detection of poor network signals shifts rich visual alerts to compressed SMS text streams.
