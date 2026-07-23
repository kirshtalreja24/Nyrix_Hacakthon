# 📊 Business Analytics Assistant

> A tool that lets a non-technical multi-branch business owner connect a CSV export and a live PostgreSQL database, ask questions in plain English, and get back the right chart automatically plus a grounded plain-English insight — with branch/location as a first-class, comparable dimension, and a standing Executive Summary that synthesizes performance across all branches without being asked.

---

## 🚀 Features

### Core Features
1. **Two Data Connectors** — CSV upload (→ DuckDB) + live PostgreSQL database
2. **Natural Language Query Interface** — single text input, plain English in, chart + insight out
3. **Adaptive Visualizations** — system infers chart type from result shape (no manual selection)
4. **Multi-entity Support** — branch/city is a queryable, comparable, rankable dimension
5. **Grounded Insight Text** — 1-2 sentence takeaway on every chart, always using real numbers
6. **Executive Summary** — standing multi-branch synthesis panel visible on load

### Bonus Features
7. **Cross-Source Queries** — single NL question can pull from both CSV and PostgreSQL in one answer (via DuckDB `postgres_scanner`)
8. **Proactive Anomaly Detection** — automatically surfaces anomalies on data load without user asking
9. **Conversational Follow-ups** — retains context across questions (e.g. "that branch", "there", "it")
10. **Exportable PDF Reports** — per branch or all locations, with charts, executive summary, and anomalies
11. **Data Preview** — shows column types, row count, and sample data after upload/connect
12. **Remove/Disconnect** — clear uploaded CSV or disconnect PostgreSQL to switch data sources anytime

### Supported Chart Types
| Chart | When Used |
|---|---|
| KPI Scorecard | Single metric, one row |
| Bar Chart | Comparison by entity |
| Line Chart | Trend over time |
| Pie Chart | Share / percentage distribution |
| Geographic Heatmap | City + branch grid |
| Ranked Table | Multiple metrics per entity |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React (Vite) + Tailwind CSS |
| **Backend** | FastAPI (Python 3.11+) |
| **NL → SQL** | OpenAI API (GPT-4o-mini) |
| **CSV Engine** | DuckDB (in-memory SQL) |
| **PostgreSQL Connector** | SQLAlchemy + psycopg2 |
| **Cross-source** | DuckDB `postgres_scanner` extension |
| **PDF Export** | ReportLab |
| **Chart Rendering** | ReportLab Graphics (server-side PDF) |
| **Deployment** | Local development (uvicorn) |

---

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- An OpenAI API key
- PostgreSQL instance (optional — can use Supabase, Neon, Render free tiers)

### 1. Clone the repository
```bash
git clone https://github.com/your-org/business-analytics-assistant.git
cd business-analytics-assistant
```

### 2. Backend setup
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment configuration
Create `backend/.env`:
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

POSTGRES_HOST=your-postgres-host.supabase.co
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

### 4. Frontend setup
```bash
cd frontend
npm install
```

---

## ▶ How to Run

### Start the backend
```bash
cd backend
venv\Scripts\activate   # Windows
python main.py
```
Backend runs at `http://localhost:8000`

### Start the frontend
```bash
cd frontend
npm run dev
```
Frontend runs at `http://localhost:5173` and proxies API calls to the backend.

### Access the app
Open `http://localhost:5173` in your browser.

---

## 🤖 AI Models Used

| Model | Purpose |
|---|---|
| **OpenAI GPT-4o-mini** | NL → structured SQL query generation |
| **OpenAI GPT-4o-mini** | Grounded insight text generation (per chart) |
| **OpenAI GPT-4o-mini** | Executive Summary generation (multi-branch synthesis) |
| **OpenAI GPT-4o-mini** | Anomaly explanations (grounded in computed numbers) |
| **OpenAI GPT-4o-mini** | Conversational context resolution (pronoun/reference resolution) |

> All LLM calls use function-calling / JSON mode with `temperature: 0.0–0.2` for deterministic outputs. Every generated number is grounded in real computed data passed into the prompt — the model never invents statistics.

---

## 🔌 Data Connectors

### Connector A: CSV → DuckDB
- Accepts CSV or Excel file upload
- Auto-cleans data (fills NaN, clamps negatives, auto-detects date columns)
- Loads into DuckDB in-memory for fast SQL queries
- Table name derived from filename

### Connector B: PostgreSQL
- Connects to any PostgreSQL instance (Supabase, Neon, Render, local)
- Discovers all tables in the `public` schema
- Queries directly via SQLAlchemy
- Supports the same SQL syntax as DuckDB

### Cross-Source (DuckDB + PostgreSQL)
- Uses DuckDB's `postgres_scanner` extension to `ATTACH` the live PostgreSQL database
- Enables single SQL queries joining CSV data with PostgreSQL data
- Example: "Which branch has both declining footfall AND declining revenue?"

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/sources/status` | GET | Status of both connectors |
| `/api/sources/upload-csv` | POST | Upload CSV file |
| `/api/sources/connect-postgres` | POST | Connect to PostgreSQL |
| `/api/sources/preview` | GET | Preview connected data (columns, rows, sample) |
| `/api/sources/clear-csv` | POST | Clear uploaded CSV data |
| `/api/sources/disconnect-postgres` | POST | Disconnect PostgreSQL |
| `/api/query` | POST | NL question → chart + insight |
| `/api/executive-summary` | GET | Multi-branch executive summary |
| `/api/anomalies` | GET | Proactive anomaly detection |
| `/api/suggestions` | GET | Context-aware follow-up suggestions |
| `/api/reports/export` | POST | Generate PDF report |

---

## ⚠️ Known Limitations

1. **No persistent storage** — data sources (CSV, PostgreSQL connections) are in-memory; restarting the backend clears everything.
2. **No user authentication** — all data is shared across sessions (no per-user isolation).
3. **No query history persistence** — conversational context is stored in-memory per browser tab; refreshing the page loses history.
4. **Cross-source requires postgres_scanner** — DuckDB's PostgreSQL extension must be installable on the host machine.
5. **PDF charts are static** — server-side rendered bar charts in the PDF; no interactive elements.
6. **LLM latency** — each query involves 1-2 OpenAI API calls (SQL generation + insight generation), adding 1-3 seconds of latency.
7. **Single-file CSV upload** — currently handles one CSV at a time; multi-file upload requires sequential uploads.
8. **Anomaly detection threshold** — hardcoded at 20% week-over-week change; not configurable without code changes.
9. **No real-time data sync** — PostgreSQL data is fetched at query time; no live polling or WebSocket updates.
10. **ReportLab charts are simple** — PDF bar charts are basic; no pie/line charts in the exported report (only data tables + executive summary).

---

## 📋 AI Usage Declaration

### Where AI is used in this application:

1. **Natural Language to SQL Conversion** — Every user question is sent to OpenAI GPT-4o-mini with the database schema to generate a structured SQL query. The LLM also determines cross-source flagging, time/entity columns, and query intent.

2. **Insight Generation** — After each query returns results, the SQL executed, result summary, and chart type are sent to the LLM to generate a 1-2 sentence grounded insight.

3. **Executive Summary** — Computed aggregates (total revenue, top/bottom branches, footfall changes, item distributions) are passed to the LLM to generate 4-6 bullet points synthesizing performance.

4. **Anomaly Explanations** — Each detected anomaly (entity, metric, % change, severity) is sent to the LLM for a one-line grounded explanation.

5. **Conversational Context Resolution** — Previous conversation turns (entity, metric, time range) are included in the LLM prompt so pronouns like "there", "that branch", "it" resolve correctly.

### Models used:
- **GPT-4o-mini** — primary model for all NL-to-SQL, insight generation, and anomaly explanations (chosen for speed + cost efficiency)
- No fine-tuning or custom training — all prompts are zero-shot with structured output schemas
