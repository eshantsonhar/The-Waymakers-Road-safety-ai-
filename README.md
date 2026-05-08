# 🚨 RoadSoS — AI-Assisted Emergency Response & Road Accident Intelligence Platform

> **Hackathon Prototype** | Localhost-Only | Optimized for Indian Road Conditions

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-cyan?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue?logo=typescript)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+PostGIS-blue?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://docker.com)

---

## 🎯 What is RoadSoS?

RoadSoS is a **full-stack AI-powered emergency response platform** that addresses India's road safety crisis — the country with the highest road accident fatalities in the world (1,68,491 deaths in 2022 per MoRTH data).

The platform provides:
- **Real-time crash detection** from vehicle sensor data
- **Intelligent emergency coordination** with automated ambulance dispatch
- **AI-powered hospital routing** using multi-factor suitability scoring
- **Predictive risk analytics** with ML-generated danger heatmaps
- **Live command center dashboard** for emergency operators
- **Citizen mobile interface** for SOS triggering and ambulance tracking
- **Admin analytics dashboard** for road safety administrators

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RoadSoS Platform                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Command     │  │  Citizen     │  │  Admin Analytics     │  │
│  │  Center      │  │  Interface   │  │  Dashboard           │  │
│  │  Dashboard   │  │  (Mobile)    │  │                      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                       │              │
│         └─────────────────┼───────────────────────┘              │
│                           │ React + Vite + TypeScript            │
│                           │ TailwindCSS + Framer Motion          │
│                           │ Leaflet Maps + Recharts              │
│                           │ Zustand State Management             │
│                           │                                      │
│  ┌────────────────────────▼──────────────────────────────────┐  │
│  │                   WebSocket Layer                          │  │
│  │              Real-time bidirectional events                │  │
│  └────────────────────────┬──────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼──────────────────────────────────┐  │
│  │                  FastAPI Backend                           │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │  │
│  │  │  Accident   │  │  Emergency   │  │  Hospital       │  │  │
│  │  │  Detection  │  │  Coord.      │  │  Intelligence   │  │  │
│  │  │  Engine     │  │  Engine      │  │  Engine         │  │  │
│  │  └─────────────┘  └──────────────┘  └─────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │  │
│  │  │  Risk       │  │  Notification│  │  Demo           │  │  │
│  │  │  Prediction │  │  Engine      │  │  Simulator      │  │  │
│  │  │  Engine     │  │  (SMS/Push)  │  │                 │  │  │
│  │  └─────────────┘  └──────────────┘  └─────────────────┘  │  │
│  └────────────────────────┬──────────────────────────────────┘  │
│                           │ SQLAlchemy ORM + AsyncPG             │
│  ┌────────────────────────▼──────────────────────────────────┐  │
│  │              PostgreSQL 15 + PostGIS 3.3                   │  │
│  │                                                            │  │
│  │  incidents │ hospitals │ ambulances │ road_segments        │  │
│  │  users │ emergency_contacts │ risk_zones │ accident_events │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (recommended) OR
- Python 3.11+, Node.js 20+, PostgreSQL 15 with PostGIS

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd road-safety-hackathon

# Copy environment file
cp backend/.env.example backend/.env

# Start everything
docker-compose up --build

# Access the platform:
# Frontend:  http://localhost:5173
# Backend:   http://localhost:8000
# API Docs:  http://localhost:8000/api/docs
```

### Option 2: Manual Setup

#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### Database Setup
```bash
# Create PostgreSQL database with PostGIS
psql -U postgres -c "CREATE DATABASE roadsos_db;"
psql -U postgres -d roadsos_db -c "CREATE EXTENSION postgis;"

# Run seed script
cd scripts
python seed.py
```

---

## 🎮 Demo Mode

RoadSoS ships with `DEMO_MODE=true` by default, which:

1. **Auto-generates crashes** every 45 seconds at Bangalore hotspots
2. **Simulates ambulance movement** with real-time GPS updates every 5 seconds
3. **Fluctuates hospital loads** to simulate real-world capacity changes
4. **Sends WebSocket events** to all connected dashboard clients

### Running Demo Scenarios

```bash
# Run the demo scenario generator
python scripts/demo_scenario.py

# Available scenarios:
# 1. Rush Hour Multi-Crash (3 simultaneous incidents)
# 2. Highway Rollover (critical severity)
# 3. Chain Collision (multiple vehicles)
```

### Citizen App Demo

In the Citizen Interface, use the **Demo Crash Simulator** panel to trigger:
- Minor Collision
- Moderate Crash
- Severe Crash
- Rollover

---

## 📡 API Documentation

Full interactive docs available at: `http://localhost:8000/api/docs`

### Key Endpoints

#### Accident Detection
```
POST /api/detection/analyze
  Body: { device_id, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z,
          latitude, longitude, speed_kmh, sound_db }
  Returns: { crash_probability_score, severity, confidence_level,
             event_classification, is_crash, action_required }

POST /api/detection/simulate/{scenario}
  Scenarios: NORMAL_BRAKING, POTHOLE, SPEED_BREAKER, MINOR_COLLISION,
             MODERATE_CRASH, SEVERE_CRASH, ROLLOVER
```

#### Incidents
```
POST /api/incidents/          Create new incident
GET  /api/incidents/          List incidents (with filters)
GET  /api/incidents/stats     Aggregate statistics
GET  /api/incidents/{id}      Get specific incident
PATCH /api/incidents/{id}     Update incident
POST /api/incidents/{id}/resolve  Resolve incident
```

#### Hospitals
```
POST /api/hospitals/rank      Rank hospitals for incident
GET  /api/hospitals/          List all hospitals
GET  /api/hospitals/stats     Hospital statistics
GET  /api/hospitals/{id}      Get specific hospital
```

#### Ambulances
```
GET  /api/ambulances/         List all ambulances
GET  /api/ambulances/nearby   Find nearest available ambulances
GET  /api/ambulances/stats    Ambulance statistics
PATCH /api/ambulances/{id}/position  Update GPS position
```

#### Risk Prediction
```
GET  /api/risk/heatmap        GeoJSON danger heatmap
GET  /api/risk/blackspots     Active blackspot list
GET  /api/risk/segments       Road segments with risk scores
GET  /api/risk/analytics      Risk analytics summary
```

#### Analytics
```
GET  /api/analytics/trends              Accident trend data
GET  /api/analytics/response-efficiency Response time metrics
GET  /api/analytics/district-stats      District-wise statistics
GET  /api/analytics/prediction-metrics  ML model performance
GET  /api/analytics/infrastructure-insights  Road maintenance priorities
```

---

## 🔌 WebSocket Events

Connect to: `ws://localhost:8000/ws/{client_id}`

### Event Schema
```json
{
  "type": "EVENT_TYPE",
  "channel": "incidents|ambulances|hospitals|risk_zones|notifications",
  "payload": { ... },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Event Types

| Event | Channel | Description |
|-------|---------|-------------|
| `STATE_SNAPSHOT` | general | Initial state on connection |
| `INCIDENT_CREATED` | incidents | New crash detected |
| `INCIDENT_UPDATED` | incidents | Status/assignment change |
| `INCIDENT_RESOLVED` | incidents | Incident closed |
| `AMBULANCE_POSITION_UPDATE` | ambulances | GPS position update |
| `AMBULANCE_STATUS_CHANGE` | ambulances | Status change |
| `AMBULANCE_ASSIGNED` | ambulances | Assigned to incident |
| `HOSPITAL_STATUS_UPDATE` | hospitals | Load/availability change |
| `EMERGENCY_ALERT` | notifications | Critical alert |
| `HEARTBEAT` | general | Keep-alive ping |

### Sample WebSocket Messages

```json
// Incident Created
{
  "type": "INCIDENT_CREATED",
  "channel": "incidents",
  "payload": {
    "id": "uuid",
    "incident_number": "INC-BLR-20240101-0001",
    "latitude": 12.9177,
    "longitude": 77.6228,
    "severity": "HIGH",
    "status": "DETECTED",
    "crash_probability_score": 0.89,
    "address": "Near Silk Board Junction, Bangalore"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}

// Ambulance Position Update
{
  "type": "AMBULANCE_POSITION_UPDATE",
  "channel": "ambulances",
  "payload": {
    "ambulances": [
      {
        "ambulance_id": "uuid",
        "latitude": 12.9200,
        "longitude": 77.6250,
        "heading": 45.0,
        "speed_kmh": 65.0,
        "status": "EN_ROUTE_TO_SCENE"
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:05Z"
}
```

---

## 🧠 AI/ML Components

### Accident Detection Engine

**Algorithm**: Multi-signal weighted scoring with sliding window filter

**Inputs**:
- Accelerometer (X, Y, Z axes) — impact force detection
- Gyroscope (X, Y, Z axes) — rollover detection
- GPS speed — sudden deceleration
- Sound intensity — impact sound detection

**Thresholds**:
- Crash confirmed: probability ≥ 0.75
- Suspected crash: 0.40 ≤ probability < 0.75
- False positive filter: 3-reading sliding window

**Event Classifications**:
- `CRASH`, `ROLLOVER_CRASH`, `HIGH_IMPACT_CRASH`
- `SUSPECTED_CRASH`
- `NORMAL_BRAKING`, `POTHOLE`, `SPEED_BREAKER`, `NORMAL`

### Hospital Intelligence Engine

**Algorithm**: Weighted multi-factor scoring (0-100)

| Factor | Weight |
|--------|--------|
| Trauma capability | 25% |
| ICU availability | 20% |
| Travel time (with traffic) | 20% |
| Distance | 15% |
| Hospital load | 10% |
| Blood availability | 5% |
| Specialist availability | 5% |

**Special rules**:
- ICU occupancy > 90% → -20 point penalty
- CRITICAL severity → exclude non-trauma hospitals

### Risk Prediction Engine

**Algorithm**: Rule-based scoring + Random Forest Classifier

**Input features**:
1. Historical accident frequency
2. Road surface condition
3. Rainfall intensity
4. Ambient lighting level
5. Traffic density
6. Road curvature index
7. Pothole density

**Output**: Risk score (0-100) + prediction confidence + blackspot classification

---

## 🗄️ Database Schema

```sql
-- Core tables with PostGIS geometry support

incidents (
  id UUID PRIMARY KEY,
  location GEOMETRY(POINT, 4326),  -- PostGIS
  severity ENUM(LOW, MEDIUM, HIGH, CRITICAL),
  status ENUM(DETECTED, CONFIRMED, DISPATCHED, ...),
  crash_probability_score FLOAT,
  timeline JSONB,
  ...
)

hospitals (
  id UUID PRIMARY KEY,
  location GEOMETRY(POINT, 4326),
  trauma_level INTEGER,
  total_icu_beds INTEGER,
  available_icu_beds INTEGER,
  available_blood_types JSONB,
  active_specialists JSONB,
  ...
)

ambulances (
  id UUID PRIMARY KEY,
  location GEOMETRY(POINT, 4326),
  status ENUM(AVAILABLE, EN_ROUTE_TO_SCENE, ...),
  current_route JSONB,
  ...
)

road_segments (
  id UUID PRIMARY KEY,
  geometry GEOMETRY(LINESTRING, 4326),
  risk_score FLOAT,
  is_blackspot BOOLEAN,
  risk_factors JSONB,
  ...
)

accident_events (
  id UUID PRIMARY KEY,
  location GEOMETRY(POINT, 4326),
  severity VARCHAR,
  sensor_snapshot JSONB,
  is_historical BOOLEAN,
  ...
)
```

---

## 📊 Indian Road Safety Context

### Why RoadSoS Matters

India accounts for **~11% of global road accident deaths** despite having only 1% of the world's vehicles.

**Key statistics (MoRTH 2022)**:
- 4,61,312 road accidents
- 1,68,491 fatalities
- 4,43,366 injured
- Average: 1 death every 3 minutes

**Karnataka (Bangalore's state)**:
- 11,131 accidents
- 5,765 fatalities
- Bangalore Urban: ~2,800 accidents/year

**Primary causes**:
1. Over-speeding (66.5% of accidents)
2. Driving on wrong side (4.7%)
3. Jumping red lights (2.8%)
4. Drunk driving (2.3%)

**RoadSoS addresses**:
- Slow emergency response (avg 15-20 min in Indian cities)
- Poor hospital routing (nearest ≠ best)
- Lack of real-time accident intelligence
- No predictive risk mapping for preventive action

---

## 🏆 Hackathon Pitch

### Problem Statement
India loses 1 life every 3 minutes to road accidents. Emergency response is slow, hospital selection is suboptimal, and there's no real-time intelligence layer for prevention.

### Solution
RoadSoS is a **full-stack AI platform** that:
1. **Detects crashes automatically** using vehicle sensor fusion (no manual reporting)
2. **Dispatches the right ambulance** to the right hospital in seconds
3. **Predicts danger zones** before accidents happen
4. **Gives operators real-time intelligence** to coordinate response

### Innovation
- **Multi-signal crash detection** with false positive filtering
- **AI hospital routing** with 7-factor suitability scoring
- **Predictive blackspot mapping** using ML + historical data
- **Offline-first design** for India's connectivity challenges
- **Indian-specific data** (Bangalore hotspots, MoRTH statistics)

### Impact Potential
- Reduce average response time from 15 min → 8 min
- Improve hospital match accuracy by 40%
- Enable preventive infrastructure investment
- Scale to any Indian city with local data

### Technical Excellence
- Production-grade architecture (FastAPI + React + PostgreSQL/PostGIS)
- Real-time WebSocket infrastructure
- Docker containerization for easy deployment
- Comprehensive API documentation
- ML-powered risk prediction

---

## 🗺️ Future Roadmap

### Phase 1 (MVP - Current)
- [x] Accident detection engine
- [x] Emergency coordination
- [x] Hospital intelligence
- [x] Risk prediction heatmaps
- [x] Command center dashboard
- [x] Citizen interface
- [x] Admin analytics

### Phase 2 (Production)
- [ ] Integration with real vehicle OBD-II sensors
- [ ] SMS gateway integration (MSG91/Twilio)
- [ ] Integration with 108 ambulance service API
- [ ] Real-time traffic data (Google Maps/HERE)
- [ ] Mobile app (React Native)
- [ ] Multi-city support

### Phase 3 (Scale)
- [ ] State government integration
- [ ] NHAI highway monitoring
- [ ] Insurance company API
- [ ] Predictive maintenance alerts
- [ ] AI-powered traffic signal optimization
- [ ] Drone dispatch for remote areas

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + TypeScript |
| Styling | TailwindCSS + Framer Motion |
| Maps | Leaflet + OpenStreetMap |
| Charts | Recharts |
| State | Zustand |
| Backend | Python FastAPI |
| WebSockets | FastAPI WebSockets |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 + PostGIS 3.3 |
| ML | scikit-learn + pandas + numpy |
| Containerization | Docker + docker-compose |

---

## 📁 Project Structure

```
road-safety-hackathon/
├── frontend/                    # React + Vite frontend
│   ├── src/
│   │   ├── views/               # Main page views
│   │   │   ├── CommandCenter.tsx    # Operator dashboard
│   │   │   ├── CitizenInterface.tsx # Citizen app
│   │   │   └── AdminDashboard.tsx   # Analytics dashboard
│   │   ├── components/          # Reusable UI components
│   │   ├── hooks/               # Custom React hooks
│   │   ├── store/               # Zustand state management
│   │   └── types/               # TypeScript type definitions
│   ├── Dockerfile
│   └── package.json
│
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI app + WebSocket
│   │   ├── config.py            # Settings management
│   │   ├── database.py          # DB connection + init
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── incident.py
│   │   │   ├── hospital.py
│   │   │   ├── ambulance.py
│   │   │   ├── user.py
│   │   │   ├── road_segment.py
│   │   │   ├── risk_zone.py
│   │   │   └── accident_event.py
│   │   ├── engines/             # Core AI/ML engines
│   │   │   ├── accident_detection.py
│   │   │   ├── hospital_intelligence.py
│   │   │   ├── risk_prediction.py
│   │   │   └── notification.py
│   │   ├── api/                 # REST API routes
│   │   │   ├── detection.py
│   │   │   ├── incidents.py
│   │   │   ├── hospitals.py
│   │   │   ├── ambulances.py
│   │   │   ├── risk.py
│   │   │   └── analytics.py
│   │   ├── websocket/           # WebSocket manager
│   │   │   └── manager.py
│   │   └── demo/                # Demo simulator
│   │       └── simulator.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker/                      # Docker configuration
│   └── init-db.sql              # PostGIS initialization
│
├── scripts/                     # Utility scripts
│   ├── seed.py                  # Database seeder
│   └── demo_scenario.py         # Demo scenario generator
│
├── datasets/                    # Data documentation
│   └── README.md
│
├── .kiro/specs/road-sos/        # Spec documents
│   ├── requirements.md
│   └── .config.kiro
│
├── docker-compose.yml
├── .gitignore
├── README.md
└── GITHUB_PUSH_CHECKLIST.md
```

---

## 🔧 Configuration

All configuration is via environment variables. See `backend/.env.example` for full list.

Key settings:
```bash
DEMO_MODE=true                    # Enable demo simulation
DEMO_CRASH_INTERVAL_SECONDS=45   # How often to generate demo crashes
CRASH_CONFIRM_THRESHOLD=0.75     # Probability threshold for crash confirmation
BLACKSPOT_RISK_THRESHOLD=70.0    # Risk score threshold for blackspot classification
BANGALORE_LAT=12.9716            # Map center latitude
BANGALORE_LON=77.5946            # Map center longitude
```

---

## 🤝 Contributing

This is a hackathon prototype. For production deployment:
1. Replace mock notification engine with real SMS gateway
2. Integrate real vehicle sensor APIs
3. Connect to 108 ambulance service
4. Add authentication and authorization
5. Implement proper database migrations with Alembic

---

## 📄 License

MIT License — Built for the Road Safety Hackathon

---

*Built with ❤️ for India's road safety | Data sources: MoRTH, NCRB, data.gov.in*
