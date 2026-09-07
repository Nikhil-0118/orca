# ORCA Frontend — React + TypeScript (Vite)

Client-side application for the ORCA Marine Intelligence Platform, providing conversational decision support, real-time oceanographic maps, push/SMS alert monitoring, and a safety-critical SOS trigger.

---

## 📂 Component Directory Breakdown

```text
src/
├── components/
│   ├── chat/        # Conversational agent chat & reasoning trace inspector
│   ├── map/         # Geospatial layers (Danger zones, PFZ coordinates, vessel marker)
│   ├── alerts/      # Live re-alert stream, push toggles, SMS status indicator
│   ├── sos/         # Safety-critical isolated emergency trigger (minimal dependencies)
│   └── common/      # App layout, header, connectivity badges
├── hooks/           # Custom React hooks (GPS tracking, SOS dispatch, live chat)
├── services/        # Isolated API client layer communicating with FastAPI
├── store/           # Global state slices (Chat, Map layers, Alerts)
├── styles/          # Marine dark-mode theme & geospatial layer styling
└── types/           # TypeScript contracts matching backend Pydantic models
```

---

## ⚡ Development Setup

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Run local development server
npm run dev
```
