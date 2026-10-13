<div align="center">

# 🔥 ThermaSense

### AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources
**Using NASA FIRMS, OpenStreetMap (OSM) & Satellite Data**

![Smart India Hackathon 2026](https://img.shields.io/badge/Smart%20India%20Hackathon-2026-orange?style=for-the-badge)
![Problem Statement](https://img.shields.io/badge/Problem%20Statement-SIH26162-blue?style=for-the-badge)
![Theme](https://img.shields.io/badge/Theme-Disaster%20Management-red?style=for-the-badge)
![Category](https://img.shields.io/badge/Category-Software-green?style=for-the-badge)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-339933?logo=nodedotjs&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![Next.js](https://img.shields.io/badge/Next.js-000000?logo=nextdotjs&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-06B6D4?logo=tailwindcss&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![PostGIS](https://img.shields.io/badge/PostGIS-336791)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?logo=tensorflow&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

**Team NIRMANX · Team ID 165585**

</div>

---

## 📑 Table of Contents

1. [Project Information](#-project-information)
2. [Team & Mentor](#-team--mentor)
3. [Abstract](#-abstract)
4. [Problem Statement](#-problem-statement)
5. [Our Solution](#-our-solution)
6. [Key Features](#-key-features)
7. [System Architecture](#-system-architecture)
8. [Data Sources](#-data-sources)
9. [Methodology (Step-by-Step)](#-methodology-step-by-step)
10. [Machine Learning & Classification Engine](#-machine-learning--classification-engine)
11. [Technology Stack – Deep Dive](#-technology-stack--deep-dive)
12. [Database Design](#-database-design)
13. [API Reference](#-api-reference)
14. [Project Structure](#-project-structure)
15. [Installation & Setup](#-installation--setup)
16. [Configuration](#-configuration)
17. [Usage Guide](#-usage-guide)
18. [How We Are Different](#-how-we-are-different)
19. [Impact & Benefits](#-impact--benefits)
20. [Feasibility & Viability](#-feasibility--viability)
21. [Project Roadmap](#-project-roadmap)
22. [Research & References](#-research--references)
23. [Limitations & Future Scope](#-limitations--future-scope)
24. [Acknowledgements](#-acknowledgements)
25. [License](#-license)

---

## 📌 Project Information

| Field | Details |
|---|---|
| **Project Name** | ThermaSense |
| **Project Type** | AI Lab Project |
| **Event** | Smart India Hackathon 2026 |
| **Problem Statement ID** | SIH26162 |
| **Problem Statement Title** | AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data |
| **Theme** | Disaster Management |
| **PS Category** | Software |
| **Team Name** | NIRMANX |
| **Team ID** | 165585 |
| **Mentor** | Anjali Srivastava |

---

## 👥 Team & Mentor

### 🧭 Mentor

| Name | Role |
|---|---|
| **Anjali Srivastava** | Project Mentor, AI Lab |

### 👨‍💻 Team NIRMANX

| Name | Role |
|---|---|
| **Naman Singh** | Team Leader |
| **Naitik Jain** | Team Member |
| **Nishtha** | Team Member |

> 📝 *Add GitHub / LinkedIn profile links and specific module ownership per member here.*

---

## 📖 Abstract

Satellite fire-monitoring systems such as **NASA FIRMS** (Fire Information for Resource Management System) publish thousands of thermal hotspots every day. However, a raw hotspot is only a *coordinate with a temperature*. It does not say **what** is burning — a forest, a farmer's paddy stubble, a gas flare, a steel furnace, a cement kiln, or an actual industrial accident.

**ThermaSense** is a GIS-first, AI-powered platform that turns raw thermal hotspots into **classified, context-aware, investigation-ready intelligence**. It fuses:

- 🛰️ **NASA FIRMS** thermal anomaly data (VIIRS / MODIS),
- 🗺️ **OpenStreetMap (OSM)** industrial infrastructure and land-use data,
- 🌍 **Multi-spectral satellite imagery**, and
- ☁️ **Real-time weather data**,

and applies **spatial and temporal analysis plus deep learning** to separate *industrial fires and persistent industrial heat sources* from *wildfires, crop-residue burning, and other thermal anomalies*. Results are delivered through an interactive web dashboard with confidence scores, risk levels, alerts, and exportable reports.

---

## ❓ Problem Statement

Government agencies, pollution-control boards and disaster-management authorities face the following challenges:

| # | Challenge | Consequence |
|---|---|---|
| 1 | FIRMS hotspots are **raw points** with no source information | Officials cannot tell industrial fires from forest/crop fires |
| 2 | **High volume** of daily hotspots across India | Manual screening is slow, repetitive and error-prone |
| 3 | **Persistent thermal sources** (furnaces, kilns, flares) look like fires | Constant false alarms in fire-monitoring workflows |
| 4 | Fire data, industrial maps and weather live in **separate tools** | No single operational picture for decision-making |
| 5 | Existing practice is **reactive** (analysis after the fire) | Delayed response, higher damage to people and environment |

**SIH26162 asks for** an AI-based solution that detects and classifies industrial fires and persistent thermal sources by combining FIRMS, OSM and satellite data.

---

## 💡 Our Solution

ThermaSense goes **beyond raw hotspots** to deliver *actionable insight*:

1. **Adds geospatial context** — every FIRMS hotspot is spatially joined with OSM industrial sites, land-cover, and nearby infrastructure.
2. **Adds temporal context** — each location's detection history is analysed to measure *persistence* (does this spot burn every night for months?).
3. **Uses AI/ML** — a hybrid model fuses spatial, temporal and imagery features to predict the **likely source type** with a **confidence score**.
4. **Estimates risk** — each hotspot is rated **Low / Medium / High** using fire intensity, persistence, facility type, weather and surroundings.
5. **Delivers outputs** — interactive GIS map, dashboards, email/SMS alerts, an AI chatbot, and CSV/PDF reports.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔥 **Hotspot Detection** | Ingests and identifies thermal anomaly pixels from NASA FIRMS (VIIRS 375 m, MODIS 1 km). |
| 🏭 **Industrial vs Natural Fire Classification** | Classifies each hotspot as *Industrial Fire*, *Persistent Industrial Heat Source*, *Wildfire / Forest Fire*, *Crop-Residue Burning*, or *Other*. |
| ♾️ **Persistent Thermal Source Detection** | Detects repeat-detection locations such as furnaces, kilns and gas flares using time-series persistence. |
| 🎯 **Confidence Scoring** | Every classification includes a probability/confidence value for transparent decision-making. |
| ⚠️ **Hotspot Risk Level Estimation** | Low / Medium / High risk score from multi-factor analysis. |
| 🗺️ **Interactive GIS Dashboard** | Layered map (hotspots, industrial sites, land cover, satellite basemap). |
| 🏗️ **Industrial Infrastructure Mapping** | Auto-pulls factories, power plants, refineries, chimneys, etc. from OSM. |
| 📍 **Custom Coordinate Prediction** | Enter any latitude/longitude and get the predicted fire risk level. |
| ☁️ **Live Weather Service** | Temperature, wind speed/direction and humidity at each hotspot. |
| 🔔 **Alert & Notification Service** | Automatic **email and SMS** alerts for critical events. |
| 🤖 **AI Chatbot (Fire Monitoring Assistant)** | Natural-language queries over fire data and risk insights. |
| 📊 **Historical Trend Analysis** | Time-series, seasonal patterns and region-wise statistics. |
| 📄 **Report & Export Engine** | One-click **CSV and PDF** reports for hotspots, risks and facilities. |
| 🧩 **Modular, Scalable Pipeline** | Pilot in one industrial zone → scale to multiple states. |

---

## 🏛️ System Architecture

### High-Level Workflow

```
 INPUT                 PROCESSING                    OUTPUT                     IMPACT
┌──────────────┐     ┌────────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│ NASA FIRMS   │     │ Data Cleaning          │    │ Classified Hotspots │    │ Safer Industries │
│ Satellite    │ ──▶ │ Spatial & Temporal     │ ─▶ │ GIS Map Dashboard   │ ─▶ │ Cleaner          │
│ OSM          │     │   Analysis             │    │ Alerts & Reports    │    │   Environment    │
│ Weather API  │     │ AI/ML Classification   │    │                     │    │ Stronger India   │
└──────────────┘     └────────────────────────┘    └─────────────────────┘    └──────────────────┘
```

### Detailed Architecture (Mermaid)

```mermaid
flowchart TD
    A1[NASA FIRMS<br/>CSV/JSON/API] --> B
    A2[Satellite Imagery<br/>Optical + Thermal] --> B
    A3[OpenStreetMap<br/>Land use + Infrastructure] --> B
    A4[Weather API<br/>Real-time] --> B
    A5[Other Climate Data<br/>Optional] --> B

    B[Data Preprocessing<br/>Cleaning → Georeferencing → Normalization → Temporal Alignment] --> C

    C[(PostgreSQL + PostGIS<br/>Spatial Database)]
    C --> D[Classification & Detection Model]
    C --> E[Model Training Pipeline]
    E --> D

    D --> F[Backend API<br/>FastAPI / Node.js]
    F --> G[Frontend<br/>React + Next.js + Leaflet]

    F --> H1[Live Weather Service]
    F --> H2[Custom Coordinate Prediction]
    F --> H3[Alert & Notification Service]
    F --> H4[AI Chatbot]
    F --> H5[Report & Export Engine]
```

### Layered View

| Layer | Responsibility | Technologies |
|---|---|---|
| **Presentation** | Dashboard, map, charts, chatbot UI | React, Next.js, Tailwind CSS, Leaflet |
| **API / Service** | REST endpoints, auth, orchestration, alerts, reports | Node.js, Python FastAPI |
| **Intelligence** | Feature engineering, inference, training | Python, TensorFlow, PyTorch |
| **Data** | Spatial storage, historical records, fused dataset | PostgreSQL + PostGIS |
| **Analysis / GIS** | Offline spatial analysis, validation, cartography | QGIS |
| **DevOps** | Containerization, hosting, version control | Docker, Vercel, GitHub |

---

## 🛰️ Data Sources

| Source | What we use it for | Format / Access |
|---|---|---|
| **NASA FIRMS** | Active fire / thermal anomaly detections (VIIRS S-NPP, NOAA-20, NOAA-21 @ 375 m; MODIS @ 1 km). Key fields: latitude, longitude, brightness temperature, FRP (Fire Radiative Power), acquisition date/time, satellite, confidence, day/night flag. | CSV / JSON via FIRMS Area API (requires a free `MAP_KEY`) |
| **OpenStreetMap (OSM)** | Industrial polygons and points: `landuse=industrial`, `man_made=works`, `power=plant`, `man_made=chimney`, refineries, petroleum wells, kilns, etc. Also roads and settlements for proximity analysis. | Overpass API / Geofabrik PBF extracts |
| **Satellite Imagery** | Multi-spectral optical + thermal context (e.g., Sentinel-2 MSI for SWIR/flare signatures, Landsat/VIIRS for thermal) for CNN-based verification. | GeoTIFF / COG tiles |
| **Land-Cover Layers** | Differentiate cropland, forest, built-up, bare land (e.g., ESA WorldCover or equivalent). | Raster (GeoTIFF) |
| **Weather API** | Real-time temperature, wind speed/direction, humidity (e.g., Open-Meteo / OpenWeatherMap). | REST JSON |
| **Historical Records** | Archived FIRMS detections for time-series persistence and trend analysis. | Stored in PostGIS |

---

## 🔬 Methodology (Step-by-Step)

The methodology follows the **five-stage pipeline** from our technical approach.

### 1️⃣ Data Collection
- Scheduled jobs pull the latest FIRMS detections for the configured region (India bounding box / state / industrial zone).
- OSM industrial layers are downloaded once and refreshed periodically.
- Satellite tiles and weather data are fetched on demand per hotspot.

### 2️⃣ Preprocessing
| Step | What happens |
|---|---|
| **Data Cleaning** | Remove duplicates, null coordinates, low-quality detections; standardize schemas. |
| **Georeferencing** | Convert everything to a common CRS (EPSG:4326 for storage, projected CRS for distance calculations). |
| **Normalization** | Scale numerical features (brightness, FRP, distances) for model training. |
| **Temporal Alignment** | Align FIRMS, satellite and OSM snapshots on a common time axis (day/night passes). |

### 3️⃣ Fire Detection
Hotspot identification and clustering — adjacent FIRMS pixels from the same overpass are grouped into a single *event* (e.g., DBSCAN / spatial clustering) so that one large fire is not counted as dozens of points.

### 4️⃣ Classification & Prediction
The classification engine assigns a **source class**, **confidence**, and **risk level** (see [next section](#-machine-learning--classification-engine)).

### 5️⃣ Decision Support
Results flow into the map dashboard, alert service, chatbot, and report engine to support prioritization and field investigation.

---

## 🧠 Machine Learning & Classification Engine

### Output Classes

| Class | Description |
|---|---|
| `INDUSTRIAL_FIRE` | Abnormal / event-like thermal activity at or near an industrial facility. |
| `PERSISTENT_INDUSTRIAL_SOURCE` | Stable, repeatedly detected heat source (furnace, kiln, gas flare, power plant) — **not** an emergency by itself. |
| `FOREST_WILDFIRE` | Fire in forest / natural vegetation land cover. |
| `CROP_BURNING` | Agricultural residue burning in cropland, usually seasonal and short-lived. |
| `OTHER` | Everything else (e.g., landfill, brick kiln outside industrial polygons — configurable). |

### Feature Engineering

| Feature Group | Examples |
|---|---|
| **Thermal** | Brightness temperature, FRP, scan/track pixel size, day/night flag, satellite confidence |
| **Spatial** | Distance to nearest OSM industrial polygon, facility type (power / refinery / steel / cement…), facility area, cluster size, distance to settlements/roads |
| **Land Cover** | Dominant land-cover class within a buffer (cropland / forest / built-up / bare) |
| **Temporal (persistence)** | Detections in last *N* days, **persistence ratio** = days with detection ÷ days observed, mean/variance of FRP, revisit regularity, longest consecutive streak |
| **Seasonality** | Month, day-of-year, regional crop-burning calendar flags |
| **Weather** | Wind speed/direction, temperature, humidity (for risk and spread context) |
| **Imagery** | Patch embeddings from satellite imagery around the hotspot |

### Hybrid Model Design

```
 ┌────────────────────────┐
 │ Tabular features       │──▶ Dense / MLP encoder ─────────┐
 │ (thermal + spatial)    │                                  │
 └────────────────────────┘                                  │
 ┌────────────────────────┐                                  ▼
 │ Time-series features   │──▶ Transformer encoder ──▶  Fusion layer ──▶ Softmax ─▶ Class + Confidence
 │ (persistence history)  │                                  ▲                  └▶ Risk score head
 └────────────────────────┘                                  │
 ┌────────────────────────┐                                  │
 │ Satellite image patch  │──▶ CNN encoder ──────────────────┘
 └────────────────────────┘
```

- **CNN** — learns visual patterns around the hotspot (plant layouts, smoke/burn scars, vegetation context).
- **Transformer** — models the temporal sequence of detections to separate one-off fires from continuous industrial heat.
- **Fusion head** — concatenates all embeddings and predicts class probabilities (confidence) and a risk score.
- **Rule-based pre-filters** (e.g., hotspots inside an OSM industrial polygon with very high persistence) provide interpretable baselines and sanity checks.

### Training Pipeline

| Stage | Details |
|---|---|
| **Labels** | Built from published industrial heat-source datasets (see [References](#-research--references)), OSM-verified facilities, and manually verified samples. |
| **Hyperparameter Tuning** | Learning rate, depth, heads, dropout, window length *N* — tuned via grid/random/Bayesian search. |
| **Validation** | Spatial block cross-validation (avoids leakage between neighbouring pixels) plus a temporal hold-out. |
| **Metrics** | Precision, Recall, F1 (per class), PR-AUC, confusion matrix, false-alarm rate. |
| **Continuous Improvement** | Periodic re-training with newly verified events and user feedback. |
| **Historical Trend Analysis** | Time-series analysis, seasonal patterns, region-wise statistics. |

> 📊 **Results:** *(Insert evaluation metrics and confusion matrix after final training.)*

### Hotspot Risk Level Estimation

| Risk | Typical Drivers |
|---|---|
| 🟢 **Low** | Known persistent source, low FRP, stable history, no sensitive surroundings |
| 🟡 **Medium** | Elevated FRP, anomalous change from baseline, or proximity to settlements |
| 🔴 **High** | Event-like spike near hazardous facility (refinery, chemical, power), strong wind, nearby population / infrastructure |

---

## 🧰 Technology Stack – Deep Dive

### 🖥️ 1. Frontend

#### ⚛️ React
- **What it is:** A component-based JavaScript library for building user interfaces.
- **Why we use it:** Our dashboard is made of many reusable, state-driven pieces (map, filters, charts, alert panel, chatbot). React's component model and virtual DOM keep updates fast even when hundreds of hotspots re-render.
- **Where it is used:** Map container, hotspot detail drawer, filter panel, analytics widgets, report-download buttons, chatbot window.

#### ▲ Next.js
- **What it is:** A React framework offering routing, server-side rendering (SSR), static generation and API routes.
- **Why we use it:** File-based routing keeps the app organized; SSR/ISR improves first-load performance and SEO for public pages; built-in image/code-splitting optimizations help on low-bandwidth government networks.
- **Where it is used:** App shell, page routing (`/dashboard`, `/analytics`, `/reports`, `/predict`), server-side data fetching, and deployment on Vercel.

#### 🎨 Tailwind CSS
- **What it is:** A utility-first CSS framework.
- **Why we use it:** Rapid, consistent styling with a design-token approach; responsive layouts out of the box; tiny production CSS because unused classes are purged.
- **Where it is used:** Layouts, risk-level colour badges (green/amber/red), dark/light themes, mobile-responsive dashboard.

---

### ⚙️ 2. Backend

#### 🟢 Node.js
- **What it is:** A JavaScript runtime with a non-blocking, event-driven I/O model.
- **Why we use it:** Excellent for I/O-heavy gateway tasks — user sessions, WebSocket/real-time push of new hotspots, orchestrating alerts, and calling external services without blocking.
- **Where it is used:** API gateway / BFF (backend-for-frontend), notification dispatching (email & SMS), real-time updates to the dashboard, scheduled job triggers.

#### 🐍 Python (FastAPI)
- **What it is:** A modern, high-performance Python web framework built on Starlette and Pydantic, with automatic OpenAPI docs.
- **Why we use it:** Python is the native language of our geospatial and ML ecosystem (GeoPandas, Shapely, Rasterio, TensorFlow, PyTorch). FastAPI gives async performance, type-validated requests, and auto-generated Swagger docs at `/docs`.
- **Where it is used:** Data ingestion (FIRMS/OSM/weather), feature engineering, model inference endpoints, custom-coordinate risk prediction, PDF/CSV report generation.

> **Why two backends?** Node.js handles real-time, I/O-bound web concerns; FastAPI handles compute-heavy, ML-bound work. They communicate through REST/internal calls, keeping each service independently scalable.

---

### 🗄️ 3. Database

#### 🐘 PostgreSQL
- **What it is:** An open-source, ACID-compliant relational database.
- **Why we use it:** Reliable transactional storage, rich indexing (B-tree, GiST, BRIN), JSONB support for semi-structured payloads, and strong time-series query performance for historical hotspot analysis.
- **Where it is used:** Hotspot records, classification results, alerts log, users, reports metadata, model-run metadata.

#### 🌐 PostGIS
- **What it is:** A spatial extension that adds geometry/geography types and hundreds of GIS functions to PostgreSQL.
- **Why we use it:** Our core operations are spatial — *"which industrial polygon is within 1 km of this point?"*, *"how many detections fell inside this grid cell last 90 days?"* PostGIS answers these in-database with GiST spatial indexes instead of slow application-side loops.
- **Key functions used:** `ST_DWithin`, `ST_Intersects`, `ST_Distance`, `ST_Buffer`, `ST_ClusterDBSCAN`, `ST_SnapToGrid`, `ST_Transform`, `ST_AsGeoJSON`.
- **Stored layers:** Thermal points (FIRMS), industrial infrastructure (OSM), land-cover layers, and the multi-source fused dataset.

---

### 🤖 4. Machine Learning / AI

#### 🟧 TensorFlow
- **What it is:** Google's end-to-end open-source ML framework (with Keras high-level API).
- **Why we use it:** Mature production tooling — SavedModel export, TensorFlow Serving, TF-Lite — and strong performance for CNN-based image models.
- **Where it is used:** CNN encoder for satellite image patches, deployment-ready inference graphs.

#### 🔥 PyTorch
- **What it is:** A dynamic-graph deep-learning framework popular in research.
- **Why we use it:** Flexible, Pythonic experimentation — ideal for building and tuning the **Transformer** time-series encoder and the multi-modal fusion head; large ecosystem of pretrained models.
- **Where it is used:** Temporal Transformer, fusion model, experimentation and ablation studies.

#### Supporting Python libraries (geospatial & data)
| Library | Purpose |
|---|---|
| **Pandas / NumPy** | Tabular processing and numerical computation |
| **GeoPandas / Shapely** | Vector spatial operations and geometry handling |
| **Rasterio** | Reading and windowing satellite GeoTIFF imagery |
| **scikit-learn** | Scaling, clustering (DBSCAN), metrics, train/validation splits |
| **ReportLab / WeasyPrint** | PDF report generation |

---

### 🗺️ 5. Mapping & GIS

#### 🟢 QGIS
- **What it is:** A free, open-source desktop GIS application.
- **Why we use it:** Visual inspection and validation of datasets, ad-hoc spatial analysis, cartographic styling, and verifying that PostGIS queries/model outputs make geographic sense.
- **Where it is used:** Data exploration, ground-truth labelling, quality checks, styled map exports for documentation.

#### 🍃 Leaflet
- **What it is:** A lightweight, open-source JavaScript library for interactive web maps.
- **Why we use it:** Small footprint, mobile-friendly, vast plugin ecosystem (marker clustering, heatmaps, drawing tools), and easy layering of GeoJSON/WMS/tiles.
- **Where it is used:** The interactive map — toggleable layers (hotspots, industrial sites, land cover, satellite imagery), colour-coded markers by class/risk, click-to-inspect popups, and click-to-predict for custom coordinates.

---

### ☁️ 6. Cloud & Deployment

#### 🐳 Docker
- **What it is:** A containerization platform that packages apps with their dependencies.
- **Why we use it:** "Works on every machine" reproducibility — the FastAPI service, Node.js service, and PostGIS database run identically on a laptop, a lab server, or a cloud VM. Docker Compose spins up the whole system with one command.
- **Where it is used:** Containers for `frontend`, `api-node`, `api-ml` (FastAPI), `postgis`, and a scheduled `worker` for ingestion jobs.

#### ▲ Vercel
- **What it is:** A cloud platform optimized for Next.js deployments.
- **Why we use it:** Zero-config CI/CD from GitHub, global CDN, instant preview deployments for every pull request, and automatic HTTPS.
- **Where it is used:** Hosting the Next.js frontend (backend services run in Docker on a server/VM).

---

### 🛠️ 7. Developer Tools

| Tool | Role |
|---|---|
| **GitHub** | Version control, issue tracking, pull-request reviews, CI workflows, and project documentation. |
| **VS Code** | Primary IDE for the team, with Python, ESLint, Prettier and Docker extensions. |

---

### 🧾 Technology Stack Summary

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React, Next.js, Tailwind CSS | Responsive dashboard UI |
| Backend | Node.js, Python (FastAPI) | Real-time services + ML/data services |
| Database | PostgreSQL + PostGIS | Spatial storage and queries |
| ML / AI | TensorFlow, PyTorch | CNN + Transformer classification |
| Mapping & GIS | QGIS, Leaflet | Analysis/validation + web mapping |
| Cloud & Deployment | Docker, Vercel | Containerization + hosting |
| Tools | GitHub, VS Code | Collaboration + development |

---

## 🗃️ Database Design

> Illustrative schema — adjust to match the final implementation.

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

-- Raw thermal detections from NASA FIRMS
CREATE TABLE hotspots (
    id              BIGSERIAL PRIMARY KEY,
    geom            GEOMETRY(Point, 4326) NOT NULL,
    acq_datetime    TIMESTAMPTZ NOT NULL,
    satellite       TEXT,
    instrument      TEXT,           -- VIIRS / MODIS
    brightness      REAL,
    frp             REAL,           -- Fire Radiative Power (MW)
    confidence      TEXT,           -- low / nominal / high (VIIRS)
    daynight        CHAR(1),
    UNIQUE (geom, acq_datetime, satellite)
);
CREATE INDEX idx_hotspots_geom ON hotspots USING GIST (geom);
CREATE INDEX idx_hotspots_time ON hotspots (acq_datetime);

-- Industrial infrastructure from OSM
CREATE TABLE industrial_sites (
    osm_id      BIGINT PRIMARY KEY,
    name        TEXT,
    site_type   TEXT,               -- power_plant, refinery, steel, cement, chimney, ...
    geom        GEOMETRY(Geometry, 4326) NOT NULL,
    tags        JSONB
);
CREATE INDEX idx_industrial_geom ON industrial_sites USING GIST (geom);

-- Model output per hotspot / event
CREATE TABLE classifications (
    id               BIGSERIAL PRIMARY KEY,
    hotspot_id       BIGINT REFERENCES hotspots(id),
    predicted_class  TEXT NOT NULL,   -- INDUSTRIAL_FIRE, PERSISTENT_INDUSTRIAL_SOURCE, ...
    confidence       REAL NOT NULL,
    risk_level       TEXT NOT NULL,   -- LOW / MEDIUM / HIGH
    nearest_site_id  BIGINT REFERENCES industrial_sites(osm_id),
    distance_m       REAL,
    persistence_ratio REAL,
    model_version    TEXT,
    created_at       TIMESTAMPTZ DEFAULT now()
);

-- Alerts sent to users
CREATE TABLE alerts (
    id               BIGSERIAL PRIMARY KEY,
    classification_id BIGINT REFERENCES classifications(id),
    channel          TEXT,            -- email / sms
    recipient        TEXT,
    status           TEXT,
    sent_at          TIMESTAMPTZ DEFAULT now()
);
```

**Example spatial query — nearest industrial site within 2 km:**
```sql
SELECT h.id, s.name, ST_Distance(h.geom::geography, s.geom::geography) AS dist_m
FROM hotspots h
JOIN LATERAL (
    SELECT * FROM industrial_sites s
    WHERE ST_DWithin(h.geom::geography, s.geom::geography, 2000)
    ORDER BY h.geom <-> s.geom
    LIMIT 1
) s ON TRUE
WHERE h.acq_datetime > now() - interval '24 hours';
```

---

## 🔌 API Reference

> Base URL (local): `http://localhost:8000` — interactive docs at `/docs` (Swagger UI).

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/hotspots` | List hotspots (filters: `bbox`, `date_from`, `date_to`, `class`, `risk`) |
| `GET` | `/api/hotspots/{id}` | Hotspot details with classification, nearest facility, weather |
| `GET` | `/api/industrial-sites` | OSM industrial facilities within a bounding box |
| `GET` | `/api/persistent-sources` | List detected persistent thermal sources |
| `POST` | `/api/predict` | Predict risk for a custom coordinate `{ "lat": .., "lon": .. }` |
| `GET` | `/api/weather` | Live weather at `lat`, `lon` |
| `GET` | `/api/analytics/trends` | Time-series, seasonal and region-wise statistics |
| `POST` | `/api/alerts/subscribe` | Subscribe an email / phone number to alerts for a region |
| `POST` | `/api/chatbot/query` | Ask the Fire Monitoring Assistant a question |
| `GET` | `/api/reports/export?format=csv\|pdf` | Export hotspots, risks and facilities |

**Sample request**
```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"lat": 23.2599, "lon": 77.4126}'
```

**Sample response**
```json
{
  "lat": 23.2599,
  "lon": 77.4126,
  "predicted_class": "PERSISTENT_INDUSTRIAL_SOURCE",
  "confidence": 0.91,
  "risk_level": "MEDIUM",
  "nearest_facility": { "name": "Example Steel Works", "distance_m": 340 },
  "persistence_ratio": 0.87
}
```

---

## 📁 Project Structure

> Suggested layout — adapt to your repository.

```
ThermaSense/
├── frontend/                  # Next.js + React + Tailwind
│   ├── app/                   # Routes: dashboard, analytics, reports, predict
│   ├── components/            # Map, FilterPanel, RiskBadge, Chatbot, Charts
│   └── lib/                   # API clients, map helpers
├── backend-node/              # Node.js gateway, alerts, WebSocket
│   ├── src/routes/
│   ├── src/services/          # emailService, smsService
│   └── src/jobs/
├── backend-ml/                # FastAPI service
│   ├── app/api/               # REST endpoints
│   ├── app/ingestion/         # firms.py, osm.py, weather.py
│   ├── app/features/          # spatial.py, temporal.py, imagery.py
│   ├── app/models/            # cnn.py, transformer.py, fusion.py
│   ├── app/reports/           # CSV / PDF generators
│   └── app/chatbot/
├── ml-training/               # Notebooks and training scripts
│   ├── notebooks/
│   └── train.py
├── database/
│   ├── init.sql               # Schema + PostGIS extension
│   └── seeds/
├── docs/                      # Architecture diagrams, screenshots, SIH PPT
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Installation & Setup

### Prerequisites

| Requirement | Version |
|---|---|
| Docker & Docker Compose | Latest |
| Node.js | 18+ |
| Python | 3.10+ |
| PostgreSQL + PostGIS (if running without Docker) | 14+ / 3.x |
| NASA FIRMS MAP_KEY | Free — request at the NASA FIRMS website |

### Option A — Docker (recommended)

```bash
# 1. Clone the repository
git clone <your-repository-url>
cd ThermaSense

# 2. Configure environment variables
cp .env.example .env
# edit .env and add your FIRMS_MAP_KEY and other secrets

# 3. Build and start all services
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Node.js API | http://localhost:5000 |
| FastAPI (ML) + Swagger | http://localhost:8000/docs |
| PostGIS | localhost:5432 |

### Option B — Manual setup

**1. Database**
```bash
createdb thermasense
psql -d thermasense -f database/init.sql
```

**2. ML / Data backend (FastAPI)**
```bash
cd backend-ml
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**3. Node.js backend**
```bash
cd backend-node
npm install
npm run dev
```

**4. Frontend**
```bash
cd frontend
npm install
npm run dev
```

**5. Load initial data**
```bash
python -m app.ingestion.firms --days 10 --region india
python -m app.ingestion.osm --region india
```

---

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# Database
POSTGRES_USER=thermasense
POSTGRES_PASSWORD=change_me
POSTGRES_DB=thermasense
DATABASE_URL=postgresql://thermasense:change_me@postgis:5432/thermasense

# NASA FIRMS
FIRMS_MAP_KEY=your_firms_map_key
FIRMS_SOURCE=VIIRS_SNPP_NRT

# Weather
WEATHER_API_KEY=your_weather_api_key

# Alerts
SMTP_HOST=smtp.example.com
SMTP_USER=alerts@example.com
SMTP_PASSWORD=your_password
SMS_API_KEY=your_sms_gateway_key

# Chatbot (LLM provider key)
LLM_API_KEY=your_llm_api_key

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MAP_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
```

> 🔒 **Never commit your `.env` file.** Keep it in `.gitignore`.

---

## 🧭 Usage Guide

1. **Open the dashboard** and select a region (state / industrial zone).
2. **Toggle map layers** — Hotspots, Industrial Facilities, Land Cover, Satellite Imagery.
3. **Click any hotspot** to see: predicted class, confidence, risk level, nearest facility, persistence history and live weather.
4. **Filter** by class (Industrial / Persistent / Wildfire / Crop Burning), risk level, date range.
5. **Predict for a location** — click the map or type coordinates to get a risk estimate.
6. **Subscribe to alerts** for a region to receive email/SMS on high-risk events.
7. **Ask the chatbot** — e.g., *"Show high-risk industrial hotspots in the last 48 hours."*
8. **Export** a CSV or PDF report for investigation or record-keeping.

---

## 🆚 How We Are Different

| Existing Solutions | ✅ ThermaSense |
|---|---|
| Provide basic satellite hotspot data and visualization | Integrated hotspot detection with **persistent fire source identification** |
| Show fire data without local context | Detects nearby facilities and analyzes **industrial context using GIS** |
| Weather information on separate platforms | **Live weather** (temperature, wind, humidity) at each hotspot |
| Mostly descriptive reports (historical data) | **ML-based risk prediction** for any custom coordinate |
| Manual monitoring and checking | **Automatic email and SMS alerts** for critical events |
| Data scattered across multiple tools | **Unified dashboard** for real-time monitoring, risk analysis and decision support |
| Limited or manual report generation | **One-click CSV and PDF reports** (hotspots, risks, facilities) |
| Reactive approach (after fire occurs) | **Proactive** risk prediction and early warnings |

---

## 🌍 Impact & Benefits

### Potential Impact

| # | Impact | Description |
|---|---|---|
| 1 | **Early Industrial Fire Detection** | Flags suspicious thermal hotspots near industrial facilities for faster investigation and response. |
| 2 | **Reduced False Alarms** | Combines thermal, spatial and temporal context to separate industrial events from wildfires, crop burning and other heat sources. |
| 3 | **Faster Decision-Making** | GIS maps, classification and confidence information help authorities prioritize high-risk events. |
| 4 | **Public & Environmental Safety** | Early identification of abnormal thermal activity reduces risks to communities, infrastructure and ecosystems. |

### Benefits

- **Operational Situational Awareness** — FIRMS + OSM + satellite context in a single GIS view.
- **Evidence-Based Classification** — spatial proximity and temporal persistence support reliable identification.
- **Scalable Monitoring** — screening across multiple industrial zones with less manual inspection.
- **Actionable GIS Outputs** — classified hotspot maps, confidence information, event history and investigation-ready reports.
- **Disaster Risk Reduction** — earlier identification of potentially hazardous industrial thermal events.

---

## ✅ Feasibility & Viability

| Dimension | Summary |
|---|---|
| **Technical** | Built on openly available data (NASA FIRMS, OSM, satellite imagery) and standard GIS/AI/geospatial tools; modular architecture can integrate with existing government systems. |
| **Operational** | Fits existing monitoring/investigation workflows; easy-to-use GIS interface; minimal manual intervention thanks to automated processing and alerts; can be piloted in selected zones and scaled gradually. |
| **Scalability & Viability** | Cost-effective due to open data and standard technologies; extendable to multiple states/regions; improves over time with historical data and model refinement; supports long-term monitoring and policy planning. |

**Government benefits:** faster screening, better decision support, lower manual workload, scalable deployment, and improved monitoring & safety.

---

## 🗓️ Project Roadmap

| Status | Milestone |
|---|---|
| ✅ **Done** | Problem study & requirement analysis |
| ✅ **Done** | Data collection (FIRMS + OSM) |
| ✅ **Done** | System design and UI prototype |
| 🔄 **Now** | Data preprocessing and storage setup |
| 🔄 **Now** | Fire classification and risk prediction model |
| 🔄 **Now** | Integrate GIS map with alerts and notifications |
| ⏭️ **Next** | Deploy and test with historical fire data |
| ⏭️ **Next** | Scale to multiple regions |
| ⏭️ **Next** | Add AI chatbot and report export |

---

## 📚 Research & References

| # | Reference |
|---|---|
| 1 | **Liu et al., 2018** — *Identifying Industrial Heat Sources Using Time-Series of the VIIRS Nightfire Product with an Object-Oriented Approach.* |
| 2 | **Ma, Li, Sui et al., 2024** — *Annual Dynamics of Global Remote Industrial Heat Sources Dataset from 2012 to 2021.* |
| 3 | **Hu et al., 2023** — *An Approach to Detect Gas Flaring Sites Using Sentinel-2 MSI and NOAA-20 VIIRS Images.* |
| 4 | **Ma et al., 2019** — *Assessing the Distribution of Heavy Industrial Heat Sources in India between 2012 and 2018.* ISPRS |
| 5 | **Xia et al., 2018** — *A Simple Method Based on the Thermal Anomaly Index to Detect Industrial Heat Sources.* |

**Data & tools:** [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) · [OpenStreetMap](https://www.openstreetmap.org/) · [PostGIS](https://postgis.net/) · [Leaflet](https://leafletjs.com/) · [QGIS](https://qgis.org/)

**Prototype links:**
- 🎥 Demo video: `<add YouTube link>`
- 💻 Repository: `<add GitHub link>`

---

## ⚠️ Limitations & Future Scope

### Current Limitations
- FIRMS resolution (375 m VIIRS / 1 km MODIS) limits precision for small facilities.
- Cloud cover and satellite revisit time can delay or hide detections.
- OSM completeness varies by region; some industrial sites may be missing or mis-tagged.
- Classification quality depends on the amount and quality of verified labels.

### Future Scope
- Integration with additional sensors (Sentinel-2 SWIR, Landsat thermal, geostationary fire products) for higher temporal resolution.
- Facility-level baselines to detect *deviations* from each plant's normal heat signature.
- Mobile app / progressive web app for field officers.
- Smoke-plume and air-quality modelling using wind data.
- Integration with state/national disaster-management and pollution-control portals.
- Multilingual chatbot and alerts (Hindi and regional languages).
- Explainable AI (feature-importance, SHAP) for audit-ready decisions.

---

## 🙏 Acknowledgements

- **Smart India Hackathon 2026** — for the problem statement **SIH26162**.
- **Mentor Anjali Srivastava** — for guidance and support throughout the AI Lab project.
- **NASA FIRMS / LANCE** — for open fire and thermal anomaly data.
- **OpenStreetMap contributors** — for open industrial and land-use data.
- The open-source communities behind PostgreSQL, PostGIS, QGIS, Leaflet, TensorFlow, PyTorch, FastAPI, React and Next.js.

---

## 📄 License

This project is developed for educational and hackathon purposes as part of an AI Lab project.
License: **MIT** *(change if required)* — see the `LICENSE` file for details.

---

<div align="center">

**Made with ❤️ by Team NIRMANX**
Naman Singh (Team Leader) · Naitik Jain · Nishtha
*Under the mentorship of Anjali Srivastava*

🔥 *ThermaSense — From satellite data to actionable insights.* 🔥

</div>
