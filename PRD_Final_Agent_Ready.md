# Product Requirements Document (BUILD-READY)
## Business Analytics Assistant — 9-Hour Hackathon
**Organized by:** Nyrix Technologies Private Limited
**Audience for this doc:** a coding agent implementing this end-to-end. Every decision below is locked — do not re-litigate connector choice, chart types, or scope. Build exactly this.

---

## 1. One-Line Pitch

A tool that lets a non-technical multi-branch business owner connect a CSV export and a live PostgreSQL database, ask questions in plain English, and get back the right chart automatically plus a grounded plain-English insight — with branch/location as a first-class, comparable dimension, and a standing Executive Summary that synthesizes performance across all branches without being asked.

---

## 2. Locked Decisions (do not change)

| Decision | Value |
|---|---|
| Connector A | **CSV/Excel upload** — parsed with pandas |
| Connector B | **PostgreSQL** — a live Postgres database holding `orders` and `footfall` tables, queried directly |
| LLM | **OpenAI API** (key available) — used for (a) NL question → structured query spec, (b) grounded insight text generation, (c) Executive Summary generation |
| Query engine | pandas + **DuckDB** for Connector A (CSV → in-memory DataFrame → SQL); **direct SQL against Postgres** for Connector B via `psycopg2`/SQLAlchemy — both paths normalize into the same result-DataFrame shape so downstream chart-selection/insight logic is source-agnostic |
| Chart selection | **Deterministic rule engine**, not LLM — see §8 |
| Frontend | React (Vite) + Tailwind + ShadCN + Recharts |
| Backend | FastAPI (Python) |
| Sample dataset | Provided — see §6 and attached files `orders.csv`, `footfall.csv` |
| New killer feature | **Executive Summary (multi-branch)** — see §9 |

---

## 3. Problem & Target User

Non-technical owners/managers of multi-location businesses (food chains, retail chains, clinics) need answers like "which branch is underperforming" without a data team, SQL, or a BI consultant. This tool answers in plain English with the correct visualization chosen automatically.

---

## 4. Required Features (judged, must ship — in priority order)

1. **2 working connectors**: CSV upload (→ DuckDB) + live PostgreSQL database, both resolving to the same queryable result shape.
2. **Natural language query interface**: single text input, plain English in, chart + insight out.
3. **Adaptive visualizations**: system infers chart type from result shape — user never picks a chart type.
4. **Multi-entity support**: branch/city is a queryable, comparable, rankable dimension.
5. **Insight text on every visual**: 1–2 sentence grounded takeaway, always present.
6. **Executive Summary (new)**: standing multi-branch synthesis panel — see §9.

### Bonus (only after 1–6 are solid)
- Cross-source queries spanning both connectors in one answer
- Proactive anomaly detection without a query
- Conversational follow-ups with retained context
- Exportable report per branch or across all branches

---

## 5. Environment & Secrets

```
OPENAI_API_KEY=<provided by user, set in .env, never hardcoded or logged>
OPENAI_MODEL=gpt-4o-mini   # fast + cheap, good enough for structured extraction; use gpt-4o if quality issues appear

POSTGRES_HOST=<host, e.g. localhost or a hosted instance like Neon/Supabase/Render>
POSTGRES_PORT=5432
POSTGRES_DB=business_analytics
POSTGRES_USER=<user>
POSTGRES_PASSWORD=<password>
```
Agent instructions:
- Stand up Postgres fast: use a free hosted instance (Neon, Supabase, or Render Postgres) to avoid local install/config time pressure — any of these give a connection string in under 2 minutes. Local Postgres is fine too if already installed.
- Run `dataset/setup_postgres.sql` (provided) against the database to create the `orders` and `footfall` tables and indexes.
- Load the provided CSVs into those tables — either via `psql \copy` (see comments in the SQL file) or via a small Python loader script using `psycopg2.copy_expert` at backend startup.
- Load `.env` via `python-dotenv` in FastAPI; never commit credentials. Use SQLAlchemy or `psycopg2` with a connection pool (e.g. `asyncpg` + `databases`, or plain `psycopg2` with a simple connection-per-request pattern) — don't over-engineer connection pooling under a 9-hour budget.
- Test the connection and a basic `SELECT COUNT(*) FROM orders` round-trip before building anything on top of it — this is the single most likely "flaky demo" failure point (network/DB access from wherever the backend is hosted).

---

## 6. Sample Dataset (provided — use as-is)

Two CSV files are attached: `orders.csv` and `footfall.csv`, plus a `setup_postgres.sql` schema/load script. Use `orders.csv` for Connector A (direct upload) and load both `orders` and `footfall` into the Postgres database for Connector B (via the provided SQL script), so both connectors serve the same underlying business and cross-source queries make sense — e.g. Connector A holds a fresh/re-uploadable CSV snapshot while Connector B represents the "live system of record" a real business would already have running.

### `orders.csv` schema
| column | type | notes |
|---|---|---|
| order_id | int | unique |
| branch | string | e.g. `KHI-01`, `LHR-02` — 6 branches total |
| city | string | `Karachi` or `Lahore` |
| date | date (YYYY-MM-DD) | 8 weeks of history, 2026-05-25 → 2026-07-19 |
| item | string | 8 menu items across categories |
| category | string | Burgers, Wraps, Rice, Main Course, BBQ, Sides, Beverages |
| quantity | int | includes a few intentional `-1` rows (data-quality test case) |
| revenue | float | includes a few intentional `NaN` rows (data-quality test case) |
| order_value | float | same as revenue at row level |

~5,090 rows across 6 branches, 8 weeks. Contains a handful of intentionally duplicated rows and a ~1% slice of missing/invalid values — use these to demonstrate basic data-quality handling if time allows (don't crash on nulls/negatives; optionally surface a one-line data-quality note).

### `footfall.csv` schema
| column | type | notes |
|---|---|---|
| branch | string | matches orders.branch |
| city | string | |
| week_start | date | 8 weekly rows per branch |
| footfall_count | int | weekly foot traffic |

### Intentional patterns baked into the data (use these to validate your build — see §10 test queries)
- **Branch `KHI-02`** has a footfall drop of **~26% week-over-week** in the week starting `2026-07-06`, and order volume drops correspondingly from that week onward. This is the anomaly-detection test case.
- **`Zinger Wrap`** sells heavily in Lahore branches (293 orders, ~PKR 278,698 revenue) and barely at all in Karachi branches (40 orders, ~PKR 36,261 revenue), despite similar total order volume per city. This is the "underperforming in Karachi but doing well in Lahore" test case.
- 6 branches across 2 cities gives geo/heatmap and cross-branch ranking real data to work with.

Branches: `KHI-01, KHI-02, KHI-03` (Karachi), `LHR-01, LHR-02, LHR-03` (Lahore).

---

## 7. Architecture

```
React Frontend (chat-style query box + chart/insight feed + Executive Summary panel)
         │
         ▼
FastAPI Backend
         │
   ┌─────┴──────────────────────┐
   │                            │
Connector A: CSV upload    Connector B: PostgreSQL (live DB)
   │  (→ DuckDB in-memory)      │  (direct SQL query)
   └─────────────┬──────────────┘
                 ▼
     Unified query layer (same result-DataFrame shape
     regardless of source: DuckDB for CSV, psycopg2/
     SQLAlchemy for Postgres)
                 ▼
   NL question ─► OpenAI (function-calling) ─► structured query spec
                 ▼
        Structured spec executed as SQL against the active source
        (DuckDB if querying the uploaded CSV, Postgres if querying
        the connected database — or both, for cross-source queries)
                 ▼
        Result DataFrame
                 │
     ┌───────────┼────────────────┐
     ▼           ▼                ▼
Chart-type    OpenAI insight   (on load / refresh)
rule engine   generation,      OpenAI Executive
(§8)          grounded in      Summary generation
              the result       (§9), grounded in
                                full dataset aggregates
     ▼           ▼                ▼
  Recharts    Insight text     Executive Summary panel
  render      under chart
```

---

## 8. Adaptive Visualization Engine — Implementation Spec

After the structured query spec is executed and returns a result DataFrame, run it through a pure-code classifier (no LLM) before rendering:

```python
def select_chart(question: str, result_df: pd.DataFrame, query_spec: dict) -> dict:
    n_rows = len(result_df)
    has_time_col = any(col in result_df.columns for col in ["date", "week_start"])
    has_geo_col = "city" in result_df.columns
    entity_col = "branch" if "branch" in result_df.columns else None
    n_metric_cols = len([c for c in result_df.columns if result_df[c].dtype != "object"])

    q = question.lower()
    wants_share = any(w in q for w in ["share", "percentage", "%", "proportion"])
    wants_rank = any(w in q for w in ["top", "lowest", "highest", "compare", "rank", "which"])

    if n_rows == 1 and n_metric_cols == 1:
        return {"chart_type": "kpi_scorecard"}
    if has_time_col and (entity_col is None or result_df[entity_col].nunique() <= 3):
        return {"chart_type": "line"}
    if has_geo_col and entity_col and result_df[entity_col].nunique() > 1 and not wants_share:
        return {"chart_type": "geo_heatmap"}
    if wants_share and entity_col:
        return {"chart_type": "pie"}
    if entity_col and n_metric_cols >= 2:
        return {"chart_type": "ranked_table"}
    if entity_col and n_metric_cols == 1:
        return {"chart_type": "bar"}
    return {"chart_type": "ranked_table"}  # safe universal fallback
```

Chart type → required Recharts component mapping (build all six, no exceptions — this is 20% of the grade):

| chart_type | Recharts component |
|---|---|
| `kpi_scorecard` | Custom card component (big number + delta arrow, not a Recharts chart) |
| `bar` | `<BarChart>` |
| `pie` | `<PieChart>` |
| `geo_heatmap` | Simplified as a color-intensity table/grid keyed by city+branch (a literal map is out of scope for 9 hours — a heatmap grid is an acceptable, judge-legible substitute; label it clearly) |
| `line` | `<LineChart>` |
| `ranked_table` | Sortable HTML table, sorted by primary metric descending, with rank number column |

Every chart render must be immediately followed by the insight text — never render a chart with nothing underneath it.

---

## 9. NEW Killer Feature: Executive Summary (Multi-Branch)

A standing panel — not query-triggered — visible as soon as data is loaded (and refreshable via a button), synthesizing performance **across all branches** into a short narrative. This is the feature that makes a branch manager open the app even with no question in mind.

### Behavior
- On dataset load (or "Refresh Summary" click), backend computes real aggregates across all branches: total revenue, revenue by branch (ranked), top/bottom performer, WoW footfall change per branch, top-selling item overall and its branch-level variance.
- These **computed numbers** (never raw rows) are passed to OpenAI with a prompt that asks it to write 4–6 bullet points in the same style as: "Revenue increased 14% this period. LHR-01 is the top-performing branch. KHI-02 footfall dropped 26% week-over-week — investigate. Zinger Wrap is a Lahore-specific bestseller, underperforming in Karachi."
- The LLM is grounded — every number in its output must trace back to a number in the computed aggregate object passed into the prompt. Explicitly instruct it: "Only state numbers present in the data below. Do not estimate or invent figures."

### Backend endpoint
```
GET /api/executive-summary
```
**Response:**
```json
{
  "generated_at": "2026-07-23T10:00:00Z",
  "summary_bullets": [
    "Total revenue across all 6 branches this period was PKR X, up/down Y% vs the prior period.",
    "LHR-01 is the top-performing branch by revenue; KHI-03 is the lowest.",
    "KHI-02 footfall dropped 26% week-over-week in the most recent week — flagged for review.",
    "Zinger Wrap drives strong sales in Lahore branches but is nearly absent from Karachi branches."
  ],
  "computed_aggregates": { "...": "the raw numbers used, for transparency/debugging" }
}
```

### Frontend
- A card/panel at the top of the main view, above the chat/query box, titled "Executive Summary."
- Bulleted list, a small "Refresh" button, and a timestamp.
- Should visually read as the first thing a manager sees before they ask anything.

---

## 10. Must-Pass Test Queries (validate against the provided dataset before demo)

1. "Which of my branches had the lowest revenue last month?" → `bar` or `ranked_table` + insight
2. "Compare average order value across all locations this quarter." → `bar` + insight
3. "Which menu item is underperforming in Karachi but doing well in Lahore?" → `ranked_table` (or grouped `bar`) + insight — should surface **Zinger Wrap**
4. "Flag any branch where footfall dropped more than 20% week-over-week." → should surface **KHI-02**, week of `2026-07-06`, ~26% drop
5. "Show revenue trend for LHR-01 over the last 8 weeks." → `line` + insight
6. "What's each branch's share of total revenue this month?" → `pie` + insight
7. Executive Summary panel loads on its own and correctly names KHI-02 and Zinger Wrap without being asked
8. (Bonus) A query that requires joining CSV-sourced `orders` data with Postgres-sourced `footfall` data in one answer, e.g. "Which branch has both declining footfall and declining revenue?"

---

## 11. API Surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/sources/upload-csv` | POST | Connector A — upload orders.csv, loads into DuckDB |
| `/api/sources/connect-postgres` | POST | Connector B — test/establish Postgres connection, confirm `orders`/`footfall` tables are reachable |
| `/api/query` | POST | `{ "question": "..." }` → NL→spec→SQL→result→chart_type→insight |
| `/api/executive-summary` | GET | Returns standing multi-branch summary (§9) |
| `/api/sources/status` | GET | Which connectors are loaded, row counts — for UI state |

### `/api/query` response contract
```json
{
  "question": "Which of my branches had the lowest revenue last month?",
  "chart_type": "bar",
  "chart_data": [ { "branch": "KHI-03", "revenue": 41200 }, ... ],
  "insight": "KHI-03 had the lowest revenue last month at PKR 41,200, roughly 22% below the branch average.",
  "sql_used": "SELECT branch, SUM(revenue) as revenue FROM orders WHERE ... GROUP BY branch ORDER BY revenue ASC"
}
```
Include `sql_used` in the response (even if not shown prominently in UI) — useful for debugging live and for the architecture walkthrough in the demo.

---

## 12. Build Order (9 hours)

| Hours | Task |
|---|---|
| 0–0.5 | Stand up Postgres (hosted free tier — Neon/Supabase/Render — recommended for speed); run `setup_postgres.sql`; load `orders.csv`/`footfall.csv` into it; confirm connection + `SELECT COUNT(*)` works |
| 0.5–1.5 | Connector A (CSV upload → DuckDB) + Connector B (direct Postgres query) both working end-to-end |
| 1.5–3 | NL → structured query spec via OpenAI function-calling; execute as SQL against DuckDB (CSV) or Postgres (live DB) depending on target source; test against queries 1–6 in §10 |
| 3–4 | Chart-selection rule engine (§8) + all 6 chart components in Recharts/table form |
| 4–5 | Insight generation grounded in query results, wired to every chart |
| 5–6 | Executive Summary endpoint + panel (§9) |
| 6–7 | Frontend polish: query box, chat-style result feed, Executive Summary card, connector status indicators |
| 7–8 | Full dry run against all 8 test queries in §10; fix breakage; attempt one bonus item if ahead of schedule (cross-source join query is highest value) |
| 8–9 | Final polish, kill anything flaky, rehearse the 7-minute demo script |

---

## 13. Explicit Cut List (cut in this order if behind schedule)

1. Cross-source joint queries (bonus)
2. Conversational follow-up context retention (bonus)
3. Exportable reports (bonus)
4. Geo/heatmap as a literal map — fall back further to a plain colored table
5. Data-quality handling sophistication — just don't crash on nulls/negatives

**Never cut:** both connectors, the NL query box, at least bar/line/pie/KPI-scorecard/ranked-table chart types, insight text per chart, and the Executive Summary panel. These map to the 6 required/differentiating features this PRD is built around.

---

## 14. Judging Criteria Self-Check

| Criterion | Weight | Where it's satisfied |
|---|---|---|
| Demo quality | 25% | §12 build order ends with a dedicated dry-run hour; §10 test queries are the demo script |
| Insight value | 25% | Every chart has grounded insight text; Executive Summary adds standing value with no query needed |
| Visualization intelligence | 20% | Deterministic rule engine (§8) covering all 6 required chart types |
| UX & usability | 15% | Single query box, no config, chart+insight always paired, Executive Summary visible immediately |
| Technical execution | 15% | Both connectors converge into one unified query layer (DuckDB + Postgres behind a common interface); SQL-grounded LLM calls avoid hallucination; `sql_used` field shows real query execution for the architecture walkthrough |

---

## 15. Attached Files
- `dataset/orders.csv` — Connector A source, also loaded into Postgres for Connector B
- `dataset/footfall.csv` — weekly footfall per branch, also loaded into Postgres for Connector B
- `dataset/setup_postgres.sql` — schema + load instructions for Connector B