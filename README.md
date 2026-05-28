# 🚨 RoadSoS — AI-Powered Emergency Response Intelligence Platform

> **One-Click Hackathon Demo** | Zero Manual Setup | Bangalore, India

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18.3-cyan?logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue?logo=typescript)
![Leaflet](https://img.shields.io/badge/Leaflet-1.9-green?logo=leaflet)
![PostGIS](https://img.shields.io/badge/PostGIS-3.3-blue?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-red)

---

**Live Demo** → [localhost:5173](http://localhost:5173) (after one-click setup)

</div>

---

## 📋 Table of Contents

1. [One-Click Setup](#-one-click-setup)
2. [What is RoadSoS?](#-what-is-roadsos)
3. [System Architecture](#-system-architecture)
4. [Key Features](#-key-features)
5. [Data Flow](#-data-flow)
6. [The 3 UIs](#-the-3-uis)
7. [Running the System](#-running-the-system)
8. [Tech Stack](#-tech-stack)
9. [Project Structure](#-project-structure)
10. [API Documentation](#-api-documentation)
11. [Hardware Module](#-hardware-module)
12. [Troubleshooting](#-troubleshooting)
13. [Future Extensions](#-future-extensions)

---

## ⚡ ONE-CLICK SETUP

### Prerequisites (install once)

| Dependency | Minimum Version | Download |
|-----------|----------------|----------|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| npm | comes with Node.js | - |

### Launch RoadSoS

```bash
# 1. Double-click this file in the project root:
START_ROADSOS.bat
```

**That's it.** The script automates everything:

| Step | Action |
|-----|--------|
| [1/7] | Detects Python, Node.js, npm |
| [2/7] | Creates Python virtual environment |
| [3/7] | Installs all Python packages (FastAPI, httpx, etc.) |
| [4/7] | Installs all frontend packages (React, Leaflet, etc.) |
| [5/7] | Clears any existing processes on ports 8000 and 5173 |
| [6/7] | Starts FastAPI backend → waits for health check OK |
| [7/7] | Opens http://localhost:5173 in your browser |

**Result:** A fully operational emergency command center with:
- Live map showing Bangalore road network
- Auto-generating accidents every 45 seconds
- Ambulances moving along real OSM roads
- Hospital intelligence ranking system
- Risk heatmap overlays
- Mobile sensor telemetry dashboard

> **No Docker required. No PostgreSQL required. No API keys required.**
> The system runs entirely in memory with demo mode.

---

## 🎯 What is RoadSoS?

RoadSoS is a **full-stack AI-powered emergency response intelligence platform** built for the Road Safety Hackathon.

India loses **1 life every 3 minutes** to road accidents (1,68,491 fatalities in 2022). The average emergency response time in Indian cities is **15-20 minutes** — far too slow for trauma victims where every minute counts.

RoadSoS solves this by providing:

| Problem | RoadSoS Solution |
|---------|-----------------|
| 🚨 Slow accident reporting | Automatic crash detection from vehicle sensors |
| 🚑 Poor ambulance routing | OSM-based road-following routes + real-time tracking |
| 🏥 Wrong hospital selection | AI-powered 7-factor hospital ranking engine |
| 🗺️ No situational awareness | Live command center with all resources visible |
| 📱 No citizen connection | Mobile telemetry + SOS + ambulance ETA tracking |
| ⚠️ No preventive intelligence | ML-based risk heatmaps and blackspot prediction |

### What makes RoadSoS different from typical hackathon projects?

- **Real road geometry** from OpenStreetMap (no fake lines)
- **OSRM-based routing** on actual road network
- **Production-grade architecture** with WebSocket real-time layer
- **Mobile sensor simulation** with realistic accelerometer/gyro
- **Hardware telemetry module** for IoT integration
- **3 complete UIs** — Command Center, Citizen App, Admin Dashboard
- **One-click startup** — zero manual configuration

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ROADSOS PLATFORM ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌───────────────────┐   │
│  │   COMMAND CENTER    │  │   CITIZEN INTERFACE  │  │ ADMIN ANALYTICS   │   │
│  │                     │  │                      │  │                   │   │
│  │ • Live Map (Leaflet)│  │ • SOS Button         │  │ • Trend Charts    │   │
│  │ • Incident Feed     │  │ • Crash Simulator    │  │ • District Stats  │   │
│  │ • Ambulance Track   │  │ • Sensor Telemetry   │  │ • Risk Analytics  │   │
│  │ • Hospital Status   │  │ • Ambulance ETA      │  │ • Response Times  │   │
│  └──────────┬──────────┘  └──────────┬───────────┘  └────────┬──────────┘   │
│             │                       │                        │              │
│             └───────────────────────┼────────────────────────┘              │
│                                     │  React 18 + TypeScript + Vite        │
│                                     │  TailwindCSS + Framer Motion         │
│                                     │  Leaflet + OpenStreetMap             │
│                                     │  Zustand State Management            │
│  ┌──────────────────────────────────▼────────────────────────────────────┐ │
│  │                      WEBSOCKET LAYER                                   │ │
│  │              Real-time bidirectional event streaming                    │ │
│  │   Events: INCIDENT_CREATED │ AMBULANCE_POSITION_UPDATE │               │ │
│  │           HOSPITAL_STATUS  │ EMERGENCY_ALERT │ HARDWARE_TELEMETRY      │ │
│  └──────────────────────────────────┬────────────────────────────────────┘ │
│                                     │                                      │
│  ┌──────────────────────────────────▼────────────────────────────────────┐ │
│  │                      FASTAPI BACKEND                                   │ │
│  │                                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │ │
│  │  │  Accident    │  │  Emergency   │  │  Hospital    │  │  Risk     │ │ │
│  │  │  Detection   │  │  Dispatch    │  │  Intelligence│  │  Predict  │ │ │
│  │  │  Engine      │  │  Engine      │  │  Engine      │  │  Engine   │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │ │
│  │                                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │ │
│  │  │  Geospatial  │  │  Route       │  │  Telemetry   │  │  Demo     │ │ │
│  │  │  Engine      │  │  Service     │  │  Ingestion   │  │  Simulator│ │ │
│  │  │  (OSM)       │  │  (OSRM)      │  │  (HW/Mobile) │  │           │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │ │
│  └──────────────────────────────────┬────────────────────────────────────┘ │
│                                     │                                      │
│  ┌──────────────────────────────────▼────────────────────────────────────┐ │
│  │                     IN-MEMORY STATE STORE                              │ │
│  │   incidents │ ambulances │ hospitals │ active_routes │ telemetry_buf  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    EXTERNAL DATA SOURCES                                ││
│  │  OpenStreetMap (Overpass API)  ←  Road Geometry                        ││
│  │  OSRM Router (public)          ←  Road-following routes                ││
│  │  Hardware Module (simulated)   ←  Telemetry packets                    ││
│  │  Mobile Sensor Simulator       ←  Sensor data                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 1. 🗺️ Real Road Routing
- Routes computed using **OSRM** (Open Source Routing Machine) on actual road networks
- No straight-line approximations — ambulances follow real roads
- Falls back to straight-line if OSRM is unavailable

### 2. 🚑 Intelligent Ambulance Dispatch
- Nearest available ambulance is automatically assigned
- Continuous position tracking with smooth interpolation along route
- Real-time ETA updates via WebSocket push
- Phase tracking: `to_scene` → `at_scene` → `to_hospital` → `at_hospital`

### 3. 🏥 AI Hospital Ranking
- 7-factor scoring: trauma capability (25%), ICU availability (20%), travel time (20%), distance (15%), hospital load (10%), blood availability (5%), specialist availability (5%)
- ICU occupancy > 90% triggers -20 point penalty
- CRITICAL severity incidents exclude non-trauma hospitals

### 4. ⚡ Real-Time WebSocket Layer
- All state changes broadcast to all connected clients
- Connection recovery with automatic state snapshot reconstruction
- Event types: incidents, ambulances, hospitals, notifications, telemetry

### 5. 📱 Mobile Sensor Telemetry
- Realistic accelerometer, gyroscope, GPS, and speed simulation
- Crash/pothole/braking event detection
- Live dashboard with circular gauges and sparkline history
- SOS trigger with configurable impact force

### 6. 🔥 Risk Heatmap from Real OSM Data
- Road segments fetched from **OpenStreetMap Overpass API**
- Risk scores derived from: accident density, curvature index, intersection density, road type
- Color-coded: Red (80+) → Orange (60+) → Yellow (40+) → Green (<20)
- **No random lines** — all geometry follows real roads

### 7. 🔧 Hardware Telemetry Module
- Full embedded firmware for **Raspberry Pi Pico 2W** with SIM7600E-H and MPU-9250
- Laptop simulation mode for demo
- Same backend pipeline as mobile sensor data

---

## 🔄 Data Flow

```
ACCIDENT SCENARIO
═════════════════

  1. Demo Simulator triggers crash at Bangalore hotspot
     │
     ▼
  2. Incident created with severity, location, classification
     │
     ▼
  3. Nearest available ambulance found from station
     │
     ▼
  4. OSRM computes road-following route: station → scene
     │
     ▼
  5. Hospital Intelligence Engine ranks hospitals by 7 factors
     │
     ▼
  6. Ambulance dispatches → WebSocket broadcasts to all UIs
     │
     ▼
  7. Ambulance position updates every second along route
     │
     ├──→ Command Center: Map marker moves + route polyline
     ├──→ Citizen Interface: ETA countdown updates
     └──→ Admin Dashboard: Response time metrics refresh
     │
     ▼
  8. Ambulance arrives at scene (pauses 3-6 seconds)
     │
     ▼
  9. Transitions to hospital phase: scene → hospital
     │
     ▼
  10. Arrives at hospital → incident resolved → ambulance available
     │
     ▼
  11. Hospital load updated (ICU bed decremented)


HARDWARE/MOBILE TELEMETRY FLOW
═══════════════════════════════

  Device (mobile/hardware) → POST /api/telemetry/hardware
     │
     ├── Store raw telemetry in buffer
     ├── Update device position
     ├── Run crash detection on accelerometer data
     │
     └── If crash detected:
           ├── Create incident (same pipeline as demo)
           ├── Dispatch nearest ambulance
           └── Broadcast via WebSocket


WEBSOCKET SYNCHRONIZATION
══════════════════════════

  Client connects → STATE_SNAPSHOT with full state
     │
     ▼
  Server pushes events in real-time
     │
     ▼
  On disconnect/reconnect → new STATE_SNAPSHOT
     │
     ▼
  Client reconstructs all active routes + incidents + ambulances
```

---

## 🖥️ The 3 UIs

### 1. Command Center (default view)

The main operational dashboard for emergency coordinators.

| Component | Description |
|-----------|-------------|
| 🗺️ Live Map | Leaflet map with dark CartoDB tiles, incident markers, ambulance positions, hospital icons, route polylines, risk heatmap |
| 📋 Incident Feed | Scrollable list of all active incidents with severity badges |
| 🚑 Active Routes | Real-time ambulance tracking with phase, ETA, speed |
| 🏥 Hospital Panel | ICU availability, load percentage, alert status |
| 📊 Stats Bar | Active incidents count, units deployed, response times |
| 🎯 Focus Mode | Click an incident to focus its route (fades others) |

### 2. Citizen Interface

Mobile-first emergency app for citizens.

| Feature | Description |
|---------|-------------|
| 🆘 SOS Button | 3-second countdown then dispatch (with cancel) |
| 📱 Sensor Telemetry Dashboard | Live accelerometer, gyroscope, GPS, speed gauges |
| 💥 Crash Simulator | Trigger demo crashes: Minor/Moderate/Severe/Rollover |
| 🚑 Ambulance Tracker | ETA countdown, distance remaining, elapsed time |
| 🏥 Nearby Hospitals | Ranked list with distance, ETA, ICU availability |
| 👥 Emergency Contacts | Notify pre-configured contacts |
| 📶 Offline Mode | Works with cached data when disconnected |

### 3. Admin Dashboard

Analytics view for road safety administrators.

| Feature | Description |
|---------|-------------|
| 📈 Trend Charts | Accident trends over time |
| 📊 District Stats | Per-district breakdown with blackspot counts |
| 🔥 Risk Analytics | Infrastructure alerts, segment risk distribution |
| ⏱️ Response Metrics | Average, fastest, and slowest response times |
| 🗺️ District Map | Color-coded risk visualization by district |

---

## 🚀 Running the System

### How `START_ROADSOS.bat` Works Internally

```
START_ROADSOS.bat
│
├── 1. DETECT SYSTEM
│   ├── python --version  (must be 3.11+)
│   ├── node --version    (must be 20+)
│   └── npm --version
│
├── 2. SETUP PYTHON ENV
│   ├── Create backend\.venv if not exists
│   ├── Activate virtual environment
│   └── Upgrade pip
│
├── 3. INSTALL BACKEND
│   ├── Check existing packages (fastapi, uvicorn, httpx, websockets)
│   ├── pip install -r backend/requirements.txt
│   └── Verify critical packages
│
├── 4. INSTALL FRONTEND
│   ├── Check node_modules exists
│   ├── npm install (if needed)
│   └── Verify Vite is installed
│
├── 5. CLEAR PORTS
│   ├── Kill any processes on port 8000
│   └── Kill any processes on port 5173
│
├── 6. START SERVICES
│   ├── Start backend:  uvicorn app.main:app --port 8000
│   ├── Health check retry loop (up to 12 attempts, 2s apart)
│   ├── Start frontend: npm run dev
│   └── Health check retry loop
│
└── 7. LAUNCH BROWSER
    ├── Open http://localhost:5173
    ├── Open http://localhost:8000/api/docs
    └── Show success screen
```

### Ports Used

| Port | Service | URL |
|------|---------|-----|
| 8000 | FastAPI Backend | [http://localhost:8000](http://localhost:8000) |
| 5173 | Vite Frontend | [http://localhost:5173](http://localhost:5173) |

### Manual Start (if bat fails)

```bash
# Terminal 1: Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + TypeScript | UI framework |
| | Vite 5 | Build tool and dev server |
| | TailwindCSS | Styling |
| | Framer Motion | Animations |
| | Leaflet + react-leaflet | Interactive maps |
| | OpenStreetMap | Map tile provider |
| | Zustand | State management |
| | Lucide React | Icons |
| **Backend** | Python FastAPI | REST API + WebSocket |
| | Uvicorn | ASGI server |
| | httpx | Async HTTP client (OSRM, Overpass) |
| | Pydantic | Data validation |
| | python-dotenv | Configuration |
| **GIS** | Overpass API | Road network fetch |
| | OSRM (public) | Road-following routes |
| | Haversine | Distance calculations |
| **Simulation** | Demo Simulator | Auto-generated incidents |
| | Mobile Sensor Simulator | Accelerometer/gyro simulation |
| | Hardware Module | Embedded telemetry simulation |
| **Hardware** | RPi Pico 2W | Target microcontroller |
| | MPU-9250 | IMU sensor |
| | SIM7600E-H | 4G LTE + GPS + SMS |
| | NEO-M8N | GPS module |

---

## 📁 Project Structure

```
RoadSoS/
│
├── START_ROADSOS.bat               # 🚀 ONE-CLICK LAUNCH
├── README.md                       # This file
├── GITHUB_PUSH_CHECKLIST.md         # Pre-publish security guide
├── .gitignore                      # Strict git exclusion rules
│
├── backend/                        # FastAPI Backend
│   ├── app/
│   │   ├── main.py                 # App entry + WebSocket endpoint
│   │   ├── config.py               # Settings (env vars)
│   │   ├── api/                    # REST API routes
│   │   │   ├── detection.py        # Accident detection
│   │   │   ├── incidents.py        # Incident CRUD
│   │   │   ├── hospitals.py        # Hospital management
│   │   │   ├── ambulances.py       # Ambulance tracking
│   │   │   ├── risk.py             # Risk heatmap (REAL OSM data)
│   │   │   ├── analytics.py        # Analytics endpoints
│   │   │   ├── routes.py           # Active route management
│   │   │   └── telemetry.py        # 📡 HARDWARE/MOBILE TELEMETRY
│   │   ├── geospatial/             # 🌍 REAL OSM ROAD NETWORK
│   │   │   ├── __init__.py
│   │   │   └── road_network.py     # Overpass API + risk scoring
│   │   ├── engines/                # Core AI/ML engines
│   │   ├── websocket/              # WebSocket manager
│   │   ├── demo/                   # Demo simulator
│   │   ├── services/               # Routing service (OSRM)
│   │   └── models/                 # Data models
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                       # React + Vite Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── LiveMap.tsx         # 🗺️ Main map component
│   │   │   ├── IncidentFeed.tsx    # Incident list
│   │   │   ├── NavBar.tsx          # 3-UI navigation
│   │   │   └── ...                 # Other components
│   │   ├── mobile/                 # 📱 MOBILE SIMULATION
│   │   │   ├── sensor_simulator.ts # Realistic sensor simulation
│   │   │   └── MobileTelemetryDashboard.tsx  # Live dashboard UI
│   │   ├── views/
│   │   │   ├── CommandCenter.tsx   # Main ops dashboard
│   │   │   ├── CitizenInterface.tsx # Citizen emergency app
│   │   │   └── AdminDashboard.tsx  # Analytics dashboard
│   │   ├── store/                  # Zustand state
│   │   ├── hooks/                  # WebSocket + API hooks
│   │   └── types/                  # TypeScript definitions
│   ├── package.json
│   └── vite.config.ts
│
├── hardware_module_code/           # 🔧 EMBEDDED HARDWARE
│   ├── main.cpp                    # Pico 2W firmware
│   ├── sensors/
│   │   ├── imu_driver.py           # MPU-9250 Python driver
│   │   └── gps_driver.py           # NEO-M8N GPS driver
│   ├── network/
│   │   └── sim7600_handler.py      # SIM7600E-H LTE handler
│   ├── protocol/
│   │   └── telemetry_schema.md     # Packet specification
│   └── simulation_mode/
│       └── hardware_simulator.py   # Laptop simulator
│
├── scripts/                        # Utility scripts
├── docker/                         # Docker config
└── datasets/                       # Dataset docs
```

---

## 📡 API Documentation

Once running, full interactive docs at: **[http://localhost:8000/api/docs](http://localhost:8000/api/docs)**

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Backend health check |
| `GET` | `/api/status` | System status with all endpoints |
| `POST` | `/api/detection/analyze` | Analyze crash sensor data |
| `POST` | `/api/detection/simulate/{scenario}` | Simulate a crash scenario |
| `GET` | `/api/incidents` | List all incidents |
| `POST` | `/api/incidents` | Create incident |
| `GET` | `/api/incidents/stats` | Incident statistics |
| `GET` | `/api/hospitals` | List hospitals |
| `POST` | `/api/hospitals/rank` | Rank hospitals for incident |
| `GET` | `/api/ambulances` | List ambulances |
| `GET` | `/api/risk/heatmap` | 🔥 Road risk GeoJSON (OSM data) |
| `GET` | `/api/risk/blackspots` | Blackspot locations |
| `GET` | `/api/analytics/trends` | Accident trend data |
| `POST` | `/api/telemetry/hardware` | 📡 Ingest hardware/mobile telemetry |
| `GET` | `/api/telemetry/devices` | List telemetry devices |
| `POST` | `/api/telemetry/simulate/crash` | Simulate hardware crash |

### WebSocket

```
ws://localhost:8000/ws/{client_id}
```

Auto-generates ID if connected via `ws://localhost:8000/ws`.

---

## 🔧 Hardware Module

The `hardware_module_code/` directory contains a complete embedded system simulation for **Raspberry Pi Pico 2W** with:

### Hardware Target

| Component | Purpose |
|-----------|---------|
| Raspberry Pi Pico 2W | Dual-core microcontroller |
| MPU-9250 | 9-axis IMU (accel + gyro + magnetometer) |
| SIM7600E-H | 4G LTE modem + GPS receiver + SMS |
| NEO-M8N | External GPS module (backup) |

### Included Files

| File | Description |
|------|-------------|
| `main.cpp` | Full embedded firmware (C++ with Pico SDK) |
| `sensors/imu_driver.py` | MPU-9250 driver (hardware + simulation) |
| `sensors/gps_driver.py` | NEO-M8N NMEA parser (hardware + simulation) |
| `network/sim7600_handler.py` | SIM7600E-H LTE/SMS handler |
| `protocol/telemetry_schema.md` | JSON + binary packet specifications |
| `simulation_mode/hardware_simulator.py` | **Run on laptop** for demo |

### Run Hardware Simulator

```bash
# From project root
cd hardware_module_code/simulation_mode
python hardware_simulator.py --crash-after 10

# This sends telemetry to http://localhost:8000/api/telemetry/hardware
# Same pipeline as the demo simulator and mobile sensor data
```

**No real hardware required.** The simulation mode generates identical telemetry packets.

---

## 🔍 Troubleshooting

### Port Already In Use

```
Error: [WinError 10048] Address already in use
```

The startup script automatically kills existing processes on ports 8000 and 5173. If issues persist:

```bash
# Manual kill
netstat -ano | findstr :8000
taskkill /PID <PID> /F
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

### Backend Fails to Start

```bash
# Try starting manually
cd backend
.venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Fails to Start

```bash
# Check node_modules exists
cd frontend
dir node_modules

# If missing, reinstall
npm install

# Start manually
npm run dev
```

### OSRM Routing Fails

The system uses the public OSRM server at `router.project-osrm.org`. If it's unreachable, it falls back to straight-line interpolation automatically. The system will still work.

### Overpass API (OSM Data) Fails

If the Overpass API is unreachable, the risk engine falls back to a hardcoded set of Bangalore's major road axes (Bellary Road, Outer Ring Road, Hosur Road, etc.). These are real road alignments, not random lines.

---

## 🗺️ Future Extensions

### Phase 2 (Production-Ready)

- **Real IoT Integration**: Deploy `hardware_module_code/main.cpp` on actual Pico 2W hardware
- **Database Persistence**: Switch from in-memory stores to PostgreSQL + PostGIS
- **Authentication**: Add JWT-based auth for command center and admin roles
- **Traffic Data**: Integrate real-time traffic API for ETA calculation
- **SMS Gateway**: Replace mock notification with MSG91/Twilio integration
- **108 Ambulance API**: Connect to government emergency services

### Phase 3 (City-Scale)

- **Multi-City Support**: Parameterize for any Indian city with OSM data
- **NHAI Integration**: Highway-specific monitoring and response
- **Machine Learning**: Train crash prediction models on real accident data
- **Mobile App**: React Native app with actual hardware sensor access
- **Drone Dispatch**: Coordinate drone delivery of AEDs and supplies
- **Insurance API**: Automated claim filing and accident reporting

### Phase 4 (Government Integration)

- **State Command Center**: Multi-district coordination
- **Aarogya Setu Integration**: Health data for patient history
- **Traffic Signal Control**: Emergency vehicle preemption
- **Road Maintenance Alerts**: Send infrastructure alerts to PWD/BBMP

---

## 📄 License

**MIT License** — Built for the Road Safety Hackathon

---

<div align="center">

**Built with ❤️ for India's road safety**

*Data sources: MoRTH 2022, NCRB, data.gov.in*

---

[⬆ Back to Top](#-roadsos--ai-powered-emergency-response-intelligence-platform)

</div>