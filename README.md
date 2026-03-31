<div align="center">

# Gen AI Academy APAC Edition — Cohort 1

### Three production-grade AI solutions tackling real-world problems using Google Cloud + Gemini

[![Track 1](https://img.shields.io/badge/Track_1-FirstResponse_AI-ff2d2d?style=for-the-badge&logo=google-cloud&logoColor=white)](#-track-1--firstresponse-ai)
[![Track 2](https://img.shields.io/badge/Track_2-AgroAdvisor-4ade80?style=for-the-badge&logo=google-cloud&logoColor=white)](#-track-2--agroadvisor)
[![Track 3](https://img.shields.io/badge/Track_3-EduPulse-8b5cf6?style=for-the-badge&logo=google-cloud&logoColor=white)](#-track-3--edupulse)

</div>

---

## Overview

This repository contains three AI-powered solutions built for the **Google Gen AI Academy APAC Edition** hackathon. Each solution targets a different track, uses a distinct Google Cloud stack, and solves a **real, measurable problem** affecting millions of people.

| Track | Solution | Stack | Problem Scale |
|:-----:|----------|-------|---------------|
| 1 | **FirstResponse AI** — Emergency Triage | ADK + Gemini + Cloud Run | 150K+ die annually from delayed triage |
| 2 | **AgroAdvisor** — Smart Farming Advisory | ADK + MCP + Weather API | 500M farmers, $50B+ annual crop loss |
| 3 | **EduPulse** — Student Analytics | AlloyDB + Gemini NL-to-SQL | 1.2M students drop out/year in India |

**Total test coverage: 44 tests passing across all tracks.**

---

## 🔴 Track 1 — FirstResponse AI

> *Instant AI triage for when every second counts*

**Problem**: In mass casualty events — earthquakes, floods, bombings — non-medical volunteers must decide who gets treated first. Wrong decisions cost lives. 150,000+ people die annually from delayed or incorrect triage.

**Solution**: An ADK agent on Cloud Run that applies the **START triage protocol** to free-form emergency descriptions and returns structured, actionable triage in under 2 seconds.

```
POST /triage
{"situation": "Male, 40s, found under rubble, not breathing, no pulse detected"}
→ { severity: "BLACK", category: "EXPECTANT", immediate_actions: [...] }
```

### Architecture
```
User → Cloud Run → Flask → ADK Agent → Gemini 2.0 Flash → Structured Triage
```

### Features
- **4-tier START classification**: RED (Immediate) · YELLOW (Delayed) · GREEN (Minor) · BLACK (Expectant)
- Natural language input — describe what you see, no forms
- Structured output: severity, symptoms, actions, transport priority, resource estimates
- Military command center UI with radar sweep, heartbeat animation, scanline effects
- Preset scenario buttons for rapid demo

### Quick Start
```bash
cd cohort-1/track-1/firstresponse-ai
pip install -r requirements.txt
export GOOGLE_API_KEY=your_key
python app.py
# → http://localhost:8080
```

### Tests
```bash
pytest tests/ -v  # 10/10 passing
```

<details>
<summary>📸 UI Preview</summary>

Dark ops command center with animated radar sweep, color-coded triage result cards, heartbeat line SVG, and glitch-effect title. Four preset emergency scenarios for quick testing.

</details>

---

## 🟢 Track 2 — AgroAdvisor

> *Weather-aware crop diagnosis for the world's farmers*

**Problem**: 500M+ smallholder farmers lose **$50 billion annually** to preventable crop diseases. Most have zero access to agronomists. Generic advice ignores weather — the #1 factor in disease spread and treatment timing.

**Solution**: An ADK agent using **MCP** to connect to OpenWeatherMap, correlating real-time weather with crop symptoms to provide diagnosis, treatment plans, and **optimal spraying windows** that avoid upcoming rain.

```
POST /advise
{"crop": "Rice", "stage": "Flowering", "location": "Punjab", "symptoms": "Brown spots on leaves, yellowing tips"}
→ { diagnosis: "Blast Fungus", confidence: 87, spraying_window: "Apr 1-2 (dry)", treatment_plan: [...] }
```

### Architecture
```
User → Cloud Run → Flask → ADK Agent ↔ MCP Server → OpenWeatherMap API
                              ↓
                        Gemini 2.0 Flash (Agronomist prompt)
```

### Features
- **MCP weather integration**: real-time conditions + 5-day forecast via Model Context Protocol
- Weather-crop correlation: humidity, temperature, rainfall mapped to disease vectors
- **Spraying window optimizer**: finds 2-3 day dry windows for treatment application
- 20 crops × 6 growth stages supported
- 35+ APAC locations pre-mapped for instant geocoding
- Botanical field guide UI with growing plant animation, confidence meters, treatment cards

### Quick Start
```bash
cd cohort-1/track-2/agroadvisor
pip install -r requirements.txt
export GOOGLE_API_KEY=your_key
export OPENWEATHER_API_KEY=your_key  # optional, has demo fallback
python app.py
# → http://localhost:8080
```

### Tests
```bash
pytest tests/ -v  # 16/16 passing
```

<details>
<summary>📸 UI Preview</summary>

Warm earth-to-forest gradient with SVG leaf patterns, sun/moon time indicator, field report form with crop/stage dropdowns, animated growing plant loader, confidence bar, weather grid, spraying timeline with rain badges, and leaf-shaped preventive measure tags with dew-drop hover.

</details>

---

## 🟣 Track 3 — EduPulse

> *Ask your student data anything — in plain English*

**Problem**: Teachers spend **5+ hours/week** on manual data analysis. At-risk students slip through cracks because insights are trapped in spreadsheets. **1.2 million students** drop out annually in India alone due to undetected academic struggles.

**Solution**: AlloyDB stores student performance data (200 students, 15 subjects, 4 semesters). Teachers ask questions in English → Gemini converts to SQL → AlloyDB executes → Gemini summarizes results.

```
POST /query
{"question": "Which students have attendance below 60% and are failing?"}
→ { sql: "SELECT ...", results: [...], summary: "12 students are at risk...", row_count: 12 }
```

### Architecture
```
User → Cloud Run → Flask → Gemini (NL→SQL) → AlloyDB → Gemini (Summary) → Response
```

### Features
- **Natural language queries** — zero SQL knowledge required
- **Dual-AI pipeline**: NL→SQL generation + Results→Summary interpretation
- Custom dataset: 200 students, 15 subjects, 2,388 enrollments, 159 risk alerts
- **SQL safety enforcement**: regex rejects DELETE/DROP/UPDATE/INSERT/TRUNCATE
- Connection pooling via `ThreadedConnectionPool` (1-10 connections)
- 12 database indexes including composites for sub-second queries
- Neo-academic dashboard with constellation background, glowing search portal, syntax-highlighted SQL
- 5 suggested query pills for common analytics questions

### Quick Start
```bash
cd cohort-1/track-3/edupulse
pip install -r requirements.txt
# Set up AlloyDB or local PostgreSQL:
psql -f schema.sql && psql -f seed_data.sql
export DATABASE_URL=postgresql://user:pass@host:5432/edupulse
export GOOGLE_API_KEY=your_key
python app.py
# → http://localhost:8080
```

### Tests
```bash
pytest tests/ -v  # 18/18 passing
```

<details>
<summary>📸 UI Preview</summary>

Deep navy constellation-themed dashboard with pulsing search portal, suggested query pills, orbital ring loading animation, syntax-highlighted SQL block, data table with sticky headers, and AI insight summary card with purple accent.

</details>

---

## Project Structure

```
apac-genaiacademy/
├── cohort-1/
│   ├── track-1/                          # ADK + Gemini + Cloud Run
│   │   ├── firstresponse-ai/
│   │   │   ├── agent.py                  # ADK triage agent definition
│   │   │   ├── app.py                    # Flask HTTP server
│   │   │   ├── templates/index.html      # Command center UI
│   │   │   ├── tests/test_agent.py       # 10 tests
│   │   │   ├── Dockerfile
│   │   │   ├── cloudbuild.yaml
│   │   │   └── requirements.txt
│   │   └── FirstResponse_AI_Submission.pptx
│   │
│   ├── track-2/                          # ADK + MCP + Weather API
│   │   ├── agroadvisor/
│   │   │   ├── agent.py                  # ADK agent with MCP toolset
│   │   │   ├── mcp_weather.py            # MCP weather tool server
│   │   │   ├── app.py                    # Flask HTTP server
│   │   │   ├── templates/index.html      # Botanical field guide UI
│   │   │   ├── tests/test_agent.py       # 16 tests
│   │   │   ├── Dockerfile
│   │   │   ├── cloudbuild.yaml
│   │   │   └── requirements.txt
│   │   └── AgroAdvisor_Submission.pptx
│   │
│   ├── track-3/                          # AlloyDB + Gemini NL-to-SQL
│   │   ├── edupulse/
│   │   │   ├── app.py                    # Flask + NL-to-SQL pipeline
│   │   │   ├── schema.sql               # 4 tables, 12 indexes
│   │   │   ├── seed_data.py             # Deterministic data generator
│   │   │   ├── seed_data.sql            # 2,775 INSERT statements
│   │   │   ├── templates/index.html      # Neo-academic dashboard UI
│   │   │   ├── tests/test_app.py         # 18 tests
│   │   │   ├── Dockerfile
│   │   │   ├── cloudbuild.yaml
│   │   │   └── requirements.txt
│   │   └── EduPulse_Submission.pptx
│   │
│   └── hackathon/                        # Multi-agent bonus track
│       └── problem-statement.md
└── README.md
```

## Deployment

Each track deploys independently to **Google Cloud Run**:

```bash
# From any track's project directory:
gcloud builds submit --config cloudbuild.yaml
```

Or manually:
```bash
docker build -t gcr.io/PROJECT_ID/firstresponse-ai .
docker push gcr.io/PROJECT_ID/firstresponse-ai
gcloud run deploy firstresponse-ai --image gcr.io/PROJECT_ID/firstresponse-ai --region asia-southeast1
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Model | Gemini 2.0 Flash |
| Agent Framework | Google ADK (Agent Development Kit) |
| Tool Protocol | Model Context Protocol (MCP) |
| Database | AlloyDB for PostgreSQL |
| Runtime | Google Cloud Run |
| Server | Flask + Gunicorn |
| Container | Docker |
| CI/CD | Cloud Build |
| Frontend | Vanilla HTML/CSS/JS (zero dependencies) |
| Testing | pytest (44 total tests) |

---

<div align="center">

Built for **Google Gen AI Academy APAC Edition** — Cohort 1

*Three problems. Three solutions. Zero compromises.*

</div>
