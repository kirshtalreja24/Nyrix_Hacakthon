"""
Business Analytics Assistant — FastAPI Backend
Connectors: CSV/DuckDB + PostgreSQL
NL Query → OpenAI → SQL → Result → Chart + Insight
Cross-source queries, Anomaly detection, Follow-ups, Exportable reports
"""

import os
import json
import traceback
import logging
import time
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd

from connectors import UnifiedSource, CSVConnector, PostgresConnector
from chart_rules import select_chart, chart_type_label
from insights import nl_to_query_spec, generate_insight
from executive import generate_executive_summary

load_dotenv()

app = FastAPI(title="Business Analytics Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("api")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every API request with method, path, and status."""
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    status = getattr(response, "status_code", 200)
    method = request.method
    path = request.url.path
    log.info("%s %s → %s (%.0fms)", method, path, status, elapsed * 1000)
    return response


# ─── Global state ────────────────────────────────────────────────────────────

source = UnifiedSource()

# In-memory conversation context for follow-ups (no auth DB needed)
# Keyed by session_id, stores list of {role, content, metadata} dicts
_conversation_store = {}


# ─── Models ───────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class PostgresConnectRequest(BaseModel):
    host: str = None
    port: str = None
    dbname: str = None
    user: str = None
    password: str = None

class ReportExportRequest(BaseModel):
    scope: str  # "branch" or "all"
    branch: Optional[str] = None

class SuggestionRequest(BaseModel):
    question: str
    result_summary: str  # first 10 rows of result as string
    chart_type: str
    source: str  # 'csv_duckdb', 'postgresql', or 'cross_source'


# ─── Conversation Context (in-memory, for follow-ups) ────────────────────────

def _save_conversation_turn(session_id: str, role: str, content: str, meta: dict = None):
    """Save a conversation turn in memory."""
    if session_id not in _conversation_store:
        _conversation_store[session_id] = []
    _conversation_store[session_id].append({
        "role": role,
        "content": content,
        "metadata": meta or {},
    })
    # Keep only last 20 turns per session
    if len(_conversation_store[session_id]) > 20:
        _conversation_store[session_id] = _conversation_store[session_id][-20:]


def _get_conversation_history(session_id: str, limit: int = 6) -> list:
    """Get recent conversation history for a session (most recent first)."""
    turns = _conversation_store.get(session_id, [])
    return turns[-limit:] if turns else []


# ─── Core Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/sources/status")
async def sources_status():
    """Return status of both connectors."""
    return source.status()


@app.post("/api/sources/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Connector A — upload a CSV file and load into DuckDB."""
    content = await file.read()
    log.info("CSV upload: %s (%d bytes)", file.filename, len(content))
    result = source.csv.load_csv(content, file.filename)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    log.info("CSV loaded: table=%s rows=%d cols=%d", result["table"], result["rows"], len(result["columns"]))
    return result


@app.post("/api/sources/connect-postgres")
async def connect_postgres(req: PostgresConnectRequest):
    """Connector B — establish or test PostgreSQL connection."""
    if req.host:
        source.postgres.host = req.host
    if req.port:
        source.postgres.port = req.port
    if req.dbname:
        source.postgres.db = req.dbname
    if req.user:
        source.postgres.user = req.user
    if req.password:
        source.postgres.password = req.password

    log.info("Postgres connect: host=%s db=%s user=%s", source.postgres.host, source.postgres.db, source.postgres.user)
    result = source.postgres.connect()
    if not result["connected"]:
        log.warning("Postgres connect FAILED: %s", result.get("error"))
        return {
            "connected": False,
            "error": result.get("error", "Connection failed"),
            "hint": "Make sure PostgreSQL is running and credentials in .env are correct.",
        }
    log.info("Postgres connected: %d tables found", len(result.get("tables", [])))
    return result


@app.post("/api/sources/clear-csv")
async def clear_csv():
    """Clear uploaded CSV data from DuckDB."""
    result = source.clear_csv()
    log.info("CSV data cleared")
    return result


@app.post("/api/sources/disconnect-postgres")
async def disconnect_postgres():
    """Disconnect PostgreSQL source."""
    result = source.disconnect_postgres()
    log.info("PostgreSQL disconnected")
    return result


@app.get("/api/sources/preview")
async def get_preview(source_type: str = Query("csv", alias="source")):
    """Preview the connected data source — columns, row count, sample rows."""
    if source_type == "csv":
        if not source.csv._loaded:
            raise HTTPException(status_code=400, detail="No CSV data loaded. Upload a CSV file first.")
        tables = source.csv.tables
        if not tables:
            raise HTTPException(status_code=400, detail="No tables found in CSV data.")
        table_name = list(tables.keys())[0]
        df = tables[table_name]

        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            if "int" in dtype:
                pg_type = "INTEGER"
            elif "float" in dtype:
                pg_type = "NUMERIC"
            elif "datetime" in dtype:
                pg_type = "TIMESTAMP"
            else:
                pg_type = "TEXT"
            columns.append({"name": col, "type": pg_type})

        sample_rows = df.head(15).fillna("").to_dict(orient="records")
        for row in sample_rows:
            for k, v in row.items():
                if isinstance(v, (pd.Timestamp, datetime)):
                    row[k] = str(v)

        return {
            "source": "csv",
            "table_name": table_name,
            "row_count": len(df),
            "columns": columns,
            "sample_rows": sample_rows,
        }

    elif source_type == "postgres":
        if not source.postgres._connected:
            raise HTTPException(status_code=400, detail="PostgreSQL not connected. Connect first.")
        tables = source.postgres.tables
        if not tables:
            raise HTTPException(status_code=400, detail="No tables found in PostgreSQL.")

        results = []
        for tbl in tables:
            try:
                info_df = source.postgres.query(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{tbl}' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """)
                columns = [{"name": r[0], "type": r[1]} for _, r in info_df.iterrows()]

                count_df = source.postgres.query(f'SELECT COUNT(*) AS c FROM "{tbl}"')
                row_count = int(count_df.iloc[0]["c"])

                sample_df = source.postgres.query(f'SELECT * FROM "{tbl}" LIMIT 15')
                sample_rows = sample_df.fillna("").to_dict(orient="records")
                for row in sample_rows:
                    for k, v in row.items():
                        if isinstance(v, (pd.Timestamp, datetime)):
                            row[k] = str(v)

                results.append({
                    "source": "postgres",
                    "table_name": tbl,
                    "row_count": row_count,
                    "columns": columns,
                    "sample_rows": sample_rows,
                })
            except Exception as e:
                results.append({"source": "postgres", "table_name": tbl, "error": str(e)})

        if len(results) == 1:
            return results[0]
        return {"tables": results}

    else:
        raise HTTPException(status_code=400, detail="Invalid source type. Use 'csv' or 'postgres'.")


@app.post("/api/query")
async def query_endpoint(req: QueryRequest):
    """
    NL question → structured query spec → SQL → result → chart_type → insight.
    Accepts optional session_id for conversational follow-ups.
    """
    connector, source_type = source.get_active_connector()
    if connector is None:
        raise HTTPException(
            status_code=400,
            detail="No data source connected. Upload a CSV or connect to PostgreSQL first.",
        )

    log.info("Query: %s", req.question[:80])

    try:
        schema_text = source.get_schema()

        # Inject conversation context for follow-ups
        context_text = ""
        if req.session_id:
            history = _get_conversation_history(req.session_id)
            if history:
                context_lines = []
                for h in history:
                    context_lines.append(f"[{h['role']}]: {h['content']}")
                context_text = "\n\nRecent conversation context (resolve pronouns/references):\n" + "\n".join(context_lines[-6:])

        # Step 1: NL → structured query spec
        spec = nl_to_query_spec(req.question, schema_text, source_hint=source_type, context=context_text)

        sql = spec.get("sql", "")
        if not sql:
            raise HTTPException(status_code=422, detail="Could not generate a SQL query for this question.")

        log.info("SQL: %s", sql[:120])

        # Step 2: Execute SQL — support cross-source queries
        is_cross_source = spec.get("cross_source", False)
        effective_source = source_type
        if is_cross_source and source.csv._loaded and source.postgres._connected:
            log.info("Cross-source query — DuckDB with postgres_scanner")
            result = source.attach_postgres_for_cross_source()
            if result.get("attached"):
                result_df = source.query_cross_source(sql)
            else:
                log.warning("Cross-source attach failed: %s", result.get("error"))
                result_df = connector.query(sql)
            effective_source = "cross_source"
        else:
            result_df = connector.query(sql)

        if result_df.empty:
            log.info("Query result: empty")
            return {
                "question": req.question,
                "chart_type": "empty",
                "chart_data": [],
                "insight": "No results found for this query. Try rephrasing or check your data.",
                "sql_used": sql,
                "source": effective_source,
            }

        # Step 3: Chart type
        chart_info = select_chart(req.question, result_df, spec)

        # Step 4: Chart data
        chart_data = result_df.fillna(0).to_dict(orient="records")

        # Step 5: Insight
        result_summary = result_df.head(20).to_string(index=False)
        insight = generate_insight(req.question, sql, result_summary, chart_info["chart_type"])

        log.info("Query result: %d rows, chart=%s", len(result_df), chart_info["chart_type"])

        # Save conversation context for follow-ups
        if req.session_id:
            _save_conversation_turn(req.session_id, "user", req.question)
            meta = {"entity": None, "metric": None}
            if "branch" in result_df.columns:
                meta["entity"] = result_df["branch"].iloc[0] if len(result_df) > 0 else None
            numeric_cols = [c for c in result_df.columns if pd.api.types.is_numeric_dtype(result_df[c])]
            if numeric_cols:
                meta["metric"] = numeric_cols[0]
            _save_conversation_turn(req.session_id, "assistant",
                f"Resolved: {chart_info['chart_type']} showing {', '.join(result_df.columns[:3])}", meta)

        return {
            "question": req.question,
            "chart_type": chart_info["chart_type"],
            "chart_type_label": chart_type_label(chart_info["chart_type"]),
            "chart_data": chart_data,
            "insight": insight,
            "sql_used": sql,
            "source": effective_source,
        }

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        log.error("Query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}\n\n{tb}")


@app.get("/api/executive-summary")
async def executive_summary():
    """Standing multi-branch Executive Summary panel."""
    log.info("Executive summary requested")
    try:
        result = generate_executive_summary(source)
        log.info("Executive summary: %d bullets", len(result.get("summary_bullets", [])))
        return result
    except Exception as e:
        tb = traceback.format_exc()
        log.error("Executive summary failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Executive Summary failed: {str(e)}\n\n{tb}")


# ─── Anomaly Detection ───────────────────────────────────────────────────────

def _compute_anomalies() -> list:
    """
    Universal anomaly detection — works with ANY table regardless of column names.
    Strategy 1: Entity + Date + Numeric → week-over-week per entity
    Strategy 2: Entity + Numeric (no date) → split-half mean comparison per entity
    Strategy 3: Date + Numeric (no entity) → overall period-over-period
    Strategy 4: Numeric only → outlier detection (z-score based)
    """
    anomalies = []
    connector, source_type = source.get_active_connector()
    if connector is None:
        return anomalies

    try:
        if source_type == "csv_duckdb":
            tables = list(source.csv.tables.keys())
        else:
            tables = list(source.postgres.tables) if source.postgres.tables else []

        for table_name in tables:
            try:
                if source_type == "csv_duckdb":
                    df = source.csv.tables[table_name].copy()
                else:
                    df = connector.query(f'SELECT * FROM "{table_name}" LIMIT 5000')
            except Exception:
                continue

            if len(df) < 4:
                continue

            # ── Detect column roles ──────────────────────────────────────
            ID_KEYWORDS = {"id", "order_id", "index", "row_id", "row_num", "serial", "key"}
            ENTITY_KEYWORDS = {"branch", "city", "store", "location", "item", "category",
                               "product", "department", "region", "team", "segment", "type",
                               "group", "name", "label", "country", "state", "zone", "area"}
            DATE_KEYWORDS = {"date", "time", "week", "month", "year", "quarter", "period",
                             "timestamp", "datetime", "day", "hour", "minute", "second", "_at"}

            ignore_cols = set()
            entity_cols = []
            date_cols = []
            numeric_cols = []

            for col in df.columns:
                cl = col.lower().strip()
                if cl in ID_KEYWORDS:
                    ignore_cols.add(col)
                    continue
                if any(kw in cl for kw in ("name", "label", "title", "desc")):
                    ignore_cols.add(col)
                    continue
                if any(kw in cl for kw in ENTITY_KEYWORDS):
                    entity_cols.append(col)
                elif any(kw in cl for kw in DATE_KEYWORDS):
                    date_cols.append(col)
                elif pd.api.types.is_numeric_dtype(df[col]):
                    numeric_cols.append(col)

            # Remove ignored columns from other lists
            entity_cols = [c for c in entity_cols if c not in ignore_cols]
            date_cols = [c for c in date_cols if c not in ignore_cols]

            # ── Strategy 1: Entity + Date + Numeric ──────────────────────
            if entity_cols and date_cols and numeric_cols:
                entity_col = entity_cols[0]  # Pick first entity column
                date_col = date_cols[0]      # Pick first date column

                try:
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                    df = df.dropna(subset=[date_col])
                    if len(df) >= 6:
                        df["_week"] = df[date_col].dt.isocalendar().week.astype(int)
                        df["_year"] = df[date_col].dt.year

                        weekly = df.groupby([entity_col, "_year", "_week"]).agg(
                            {m: "sum" for m in numeric_cols}
                        ).reset_index()

                        for entity_val in weekly[entity_col].unique():
                            edf = weekly[weekly[entity_col] == entity_val].sort_values(["_year", "_week"])
                            for i in range(1, len(edf)):
                                prev = edf.iloc[i - 1]
                                curr = edf.iloc[i]
                                for metric in numeric_cols:
                                    try:
                                        if prev[metric] and curr[metric] and prev[metric] > 0 and not pd.isna(curr[metric]):
                                            pct = ((curr[metric] - prev[metric]) / prev[metric]) * 100
                                            if abs(pct) >= 20:
                                                anomalies.append({
                                                    "entity": str(entity_val),
                                                    "metric": metric,
                                                    "table": table_name,
                                                    "change_pct": round(pct, 1),
                                                    "previous_value": round(float(prev[metric]), 2),
                                                    "current_value": round(float(curr[metric]), 2),
                                                    "severity": "high" if abs(pct) >= 40 else "medium",
                                                    "week": f"week {int(curr['_week'])}, {int(curr['_year'])}",
                                                })
                                    except Exception:
                                        continue
                except Exception:
                    pass

            # ── Strategy 2: Entity + Numeric (no date) ───────────────────
            if not anomalies and entity_cols and numeric_cols:
                entity_col = entity_cols[0]
                for metric in numeric_cols[:3]:
                    try:
                        entity_means = df.groupby(entity_col)[metric].mean()
                        overall_mean = entity_means.mean()
                        if overall_mean == 0 or pd.isna(overall_mean):
                            continue
                        for entity_val, entity_mean in entity_means.items():
                            if pd.isna(entity_mean) or entity_mean == 0:
                                continue
                            pct = ((entity_mean - overall_mean) / overall_mean) * 100
                            if abs(pct) >= 30:
                                anomalies.append({
                                    "entity": str(entity_val),
                                    "metric": metric,
                                    "table": table_name,
                                    "change_pct": round(pct, 1),
                                    "severity": "high" if abs(pct) >= 60 else "medium",
                                    "week": "overall",
                                })
                    except Exception:
                        continue

            # ── Strategy 3: Date + Numeric (no entity) ───────────────────
            if not anomalies and date_cols and numeric_cols and not entity_cols:
                date_col = date_cols[0]
                try:
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                    df = df.dropna(subset=[date_col])
                    if len(df) >= 6:
                        df["_week"] = df[date_col].dt.isocalendar().week.astype(int)
                        df["_year"] = df[date_col].dt.year
                        weekly = df.groupby(["_year", "_week"]).agg(
                            {m: "sum" for m in numeric_cols}
                        ).reset_index().sort_values(["_year", "_week"])

                        for metric in numeric_cols[:3]:
                            for i in range(1, len(weekly)):
                                prev = weekly.iloc[i - 1]
                                curr = weekly.iloc[i]
                                if prev[metric] and curr[metric] and prev[metric] > 0 and not pd.isna(curr[metric]):
                                    pct = ((curr[metric] - prev[metric]) / prev[metric]) * 100
                                    if abs(pct) >= 20:
                                        anomalies.append({
                                            "entity": "overall",
                                            "metric": metric,
                                            "table": table_name,
                                            "change_pct": round(pct, 1),
                                            "severity": "high" if abs(pct) >= 40 else "medium",
                                            "week": f"week {int(curr['_week'])}, {int(curr['_year'])}",
                                        })
                except Exception:
                    pass

            # ── Strategy 4: Numeric only (outlier detection) ─────────────
            if not anomalies and numeric_cols:
                for metric in numeric_cols[:3]:
                    try:
                        vals = df[metric].dropna()
                        if len(vals) < 4:
                            continue
                        mean = vals.mean()
                        std = vals.std()
                        if std == 0 or pd.isna(std):
                            continue

                        # Find values that are > 2 standard deviations from mean
                        for idx in vals.index:
                            v = vals[idx]
                            if pd.isna(v):
                                continue
                            z = abs((v - mean) / std)
                            if z > 2:
                                pct = ((v - mean) / mean) * 100
                                if abs(pct) >= 30:
                                    anomalies.append({
                                        "entity": f"row {idx}",
                                        "metric": f"{metric} (outlier)",
                                        "table": table_name,
                                        "change_pct": round(pct, 1),
                                        "current_value": round(float(v), 2),
                                        "severity": "high" if abs(pct) >= 60 else "medium",
                                        "week": f"z-score: {z:.1f}",
                                    })
                    except Exception:
                        continue

    except Exception as e:
        log.warning("Anomaly detection failed: %s", e)

    # Deduplicate — keep strongest per entity+metric
    seen = {}
    for a in anomalies:
        key = f"{a['entity']}_{a['metric']}"
        if key not in seen or abs(a["change_pct"]) > abs(seen[key]["change_pct"]):
            seen[key] = a
    anomalies = list(seen.values())
    anomalies.sort(key=lambda x: (-1 if x["severity"] == "high" else 0, -abs(x["change_pct"])))

    # Cap at top 15 to avoid overwhelming the UI
    return anomalies[:15]


@app.get("/api/anomalies")
async def get_anomalies():
    """Return detected anomalies with LLM-generated explanations."""
    anomalies = _compute_anomalies()
    if not anomalies:
        return {"anomalies": [], "count": 0}

    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    for a in anomalies:
        try:
            prompt = f"""Write a one-line explanation for this anomaly.
{json.dumps(a)} — using only the provided numbers, no invented figures."""
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            a["explanation"] = resp.choices[0].message.content.strip()
        except Exception:
            a["explanation"] = f"{a['entity']}: {a['metric']} changed {a['change_pct']}% week-over-week."

    return {"anomalies": anomalies, "count": len(anomalies)}


# ─── Report Export ───────────────────────────────────────────────────────────

@app.post("/api/reports/export")
async def export_report(req: ReportExportRequest):
    """Generate and return a styled PDF report with KPIs, charts, and anomalies."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, mm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, HRFlowable, KeepTogether,
        )
        from reportlab.graphics.shapes import Drawing, Rect, String, Line
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.graphics import renderPDF
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF library not installed. Run: pip install reportlab")

    connector, source_type = source.get_active_connector()
    if connector is None:
        raise HTTPException(status_code=400, detail="No data source connected.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=45, leftMargin=45, topMargin=40, bottomMargin=40,
    )
    styles = getSampleStyleSheet()
    elements = []

    # ── Custom styles ──────────────────────────────────────────────────────
    DARK = colors.HexColor('#111111')
    MEDIUM = colors.HexColor('#787774')
    LIGHT = colors.HexColor('#EAEAEA')
    BG = colors.HexColor('#F7F6F3')
    WHITE = colors.white
    ACCENT = colors.HexColor('#346538')

    title_style = ParagraphStyle('ReportTitle', fontSize=22, leading=28, fontName='Helvetica-Bold',
                                  textColor=DARK, spaceAfter=4)
    subtitle_style = ParagraphStyle('Subtitle', fontSize=10, leading=14, fontName='Helvetica',
                                    textColor=MEDIUM, spaceAfter=2)
    h2 = ParagraphStyle('H2', fontSize=13, leading=18, fontName='Helvetica-Bold',
                        textColor=DARK, spaceBefore=16, spaceAfter=8)
    h3 = ParagraphStyle('H3', fontSize=10, leading=14, fontName='Helvetica-Bold',
                        textColor=DARK, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle('Body', fontSize=9.5, leading=13, fontName='Helvetica',
                          textColor=DARK, spaceAfter=4)
    body_bold = ParagraphStyle('BodyBold', fontSize=9.5, leading=13, fontName='Helvetica-Bold',
                                textColor=DARK, spaceAfter=4)
    small = ParagraphStyle('Small', fontSize=8, leading=10, fontName='Helvetica',
                           textColor=MEDIUM, spaceAfter=2)

    # ── Header bar ─────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("Nyrix Analytics", ParagraphStyle('Brand', fontSize=14, fontName='Helvetica-Bold', textColor=WHITE)),
        Paragraph("Business Report", ParagraphStyle('BrandSub', fontSize=10, fontName='Helvetica', textColor=colors.HexColor('#AAAAAA'), alignment=TA_RIGHT)),
    ]]
    header_table = Table(header_data, colWidths=[260, 260])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK),
        ('TEXTCOLOR', (0, 0), (-1, -1), WHITE),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 14))

    # ── Report info ─────────────────────────────────────────────────────────
    scope_label = f"Branch: {req.branch}" if req.scope == "branch" and req.branch else "All Branches"
    elements.append(Paragraph(f"Report: {scope_label}", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%d %B %Y at %H:%M UTC')}", subtitle_style))
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=1, color=LIGHT, spaceAfter=12))

    # ── Revenue by Branch bar chart ──────────────────────────────────────────
    try:
        # Find the first table that has entity + numeric columns
        available_tables = list(source.csv.tables.keys()) if source_type == "csv_duckdb" else (source.postgres.tables if source.postgres.tables else [])
        chart_table = None
        chart_entity_col = None
        chart_metric_col = None

        for tbl in available_tables:
            try:
                if source_type == "csv_duckdb":
                    sample = source.csv.tables[tbl]
                else:
                    sample = connector.query(f'SELECT * FROM "{tbl}" LIMIT 1')

                # Find entity column (string, low cardinality)
                str_cols = [c for c in sample.columns if pd.api.types.is_object_dtype(sample[c]) and c.lower() not in ("id", "order_id")]
                num_cols = [c for c in sample.columns if pd.api.types.is_numeric_dtype(sample[c]) and c.lower() not in ("id", "order_id", "index")]

                if str_cols and num_cols:
                    chart_table = tbl
                    chart_entity_col = str_cols[0]
                    chart_metric_col = num_cols[0]
                    break
            except Exception:
                continue

        if chart_table:
            chart_sql = f'SELECT "{chart_entity_col}", SUM("{chart_metric_col}") as total FROM "{chart_table}" GROUP BY "{chart_entity_col}" ORDER BY total DESC'
            rev_df = connector.query(chart_sql)
            if len(rev_df) > 0:
                elements.append(Paragraph(f"{chart_metric_col} by {chart_entity_col}", h2))

                labels = [str(r[0]) for _, r in rev_df.iterrows()]
                values = [float(r[1]) for _, r in rev_df.iterrows()]

                d = Drawing(460, 180)
                bc = VerticalBarChart()
                bc.x = 50
                bc.y = 30
                bc.height = 130
                bc.width = 380
                bc.data = [values]
                bc.categoryAxis.categoryNames = labels
                bc.categoryAxis.labels.fontSize = 8
                bc.valueAxis.valueMin = 0
                bc.valueAxis.valueMax = max(values) * 1.15
                bc.valueAxis.labels.fontSize = 7
                bc.bars[0].fillColor = colors.HexColor('#346538')
                bc.bars[0].strokeColor = None
                bc.barWidth = 28
                bc.groupSpacing = 18
                d.add(bc)
                elements.append(d)
                elements.append(Spacer(1, 14))
    except Exception as e:
        log.warning("Report chart error: %s", e)

    # ── Executive Summary ──────────────────────────────────────────────────
    try:
        summary = generate_executive_summary(source)
        if summary.get("summary_bullets"):
            elements.append(Paragraph("Executive Summary", h2))
            for bullet in summary["summary_bullets"]:
                elements.append(Paragraph(f"• {bullet}", body))
                elements.append(Spacer(1, 3))
            elements.append(Spacer(1, 10))
    except Exception as e:
        log.warning("Report exec summary error: %s", e)

    # ── Anomalies ──────────────────────────────────────────────────────────
    try:
        anomalies = _compute_anomalies()
        if anomalies:
            elements.append(Paragraph("Active Anomalies", h2))
            for a in anomalies:
                if req.scope == "branch" and req.branch and a["entity"] != req.branch:
                    continue

                sev_color = colors.HexColor('#9F2F2D') if a["severity"] == "high" else colors.HexColor('#956400')
                sev_bg = colors.HexColor('#FDEBEC') if a["severity"] == "high" else colors.HexColor('#FBF3DB')
                sev_label = a["severity"].upper()

                anomaly_data = [[
                    Paragraph(f"<b>{a['entity']}</b>", body_bold),
                    Paragraph(f"{a['metric']}", body),
                    Paragraph(f"{a['change_pct']:+.1f}%", ParagraphStyle('ap', fontSize=10, fontName='Helvetica-Bold',
                                    textColor=sev_color, spaceAfter=2)),
                    Paragraph(f"<font size='7' color='{sev_color.hexval()}'>{sev_label}</font>",
                              ParagraphStyle('as', fontSize=7, fontName='Helvetica-Bold', textColor=sev_color)),
                ]]
                at = Table(anomaly_data, colWidths=[80, 100, 80, 60])
                at.setStyle(TableStyle([
                    ('BACKGROUND', (3, 0), (3, 0), sev_bg),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(at)
                elements.append(Paragraph(f"<font size='8' color='{MEDIUM.hexval()}'>Week: {a.get('week', 'N/A')}</font>", small))

            elements.append(Spacer(1, 10))
    except Exception:
        pass

    # ── Footer ─────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT, spaceAfter=6))
    elements.append(Paragraph(
        "Nyrix Analytics · Business Analytics Assistant",
        ParagraphStyle('footer', fontSize=7, fontName='Helvetica', textColor=MEDIUM, alignment=TA_CENTER)
    ))

    # Build the PDF
    doc.build(elements)
    buffer.seek(0)

    filename = f"analytics_report_{req.scope}_{req.branch or 'all'}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/suggestions")
async def get_suggestions(session_id: Optional[str] = None):
    """Generate 5 tailored question suggestions using LLM based on schema and context."""
    connector, source_type = source.get_active_connector()
    if connector is None:
        return {
            "suggestions": [
                "Upload a CSV file to get started",
                "Connect to PostgreSQL to query live data"
            ]
        }

    schema_text = source.get_schema()
    context_text = ""
    if session_id:
        history = _get_conversation_history(session_id)
        if history:
            context_lines = []
            for h in history:
                context_lines.append(f"[{h['role']}]: {h['content']}")
            context_text = "\n".join(context_lines[-6:])

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if context_text:
            prompt = f"""You are a business analytics assistant.
Based on the database schema below and the recent conversation history, generate exactly 5 logical, high-value natural language follow-up questions that the user might want to ask next.
Keep them concise, professional, and direct.

Do not write markdown block quotes, explainers, or prefixes. Return ONLY a valid JSON list of strings.
Example output format:
["...and what about branch LHR-02?", "What is the category breakdown for that?", "How does that compare to the previous week?", "Show me the trend of the top item there", "Which other city has a similar revenue pattern?"]

Schema:
{schema_text}

Recent Conversation:
{context_text}"""
        else:
            prompt = f"""You are a business analytics assistant.
Based on the database schema below, generate exactly 5 diverse, high-value, realistic natural language business questions that a user can ask to query this database.
Keep them concise, professional, and practical.

Do not write markdown block quotes, explainers, or prefixes. Return ONLY a valid JSON list of strings.
Example output format:
["What is the total revenue per branch?", "Show the top 5 items sold by quantity", "Compare average order value across cities", "Which category has the highest sales?", "Which month had the highest revenue?"]

Schema:
{schema_text}"""

        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        suggestions = json.loads(content)
        if isinstance(suggestions, list):
            return {"suggestions": [str(s) for s in suggestions[:6]]}
    except Exception as e:
        log.warning("Failed to generate LLM suggestions: %s", e)

    # Fallback static suggestions
    if context_text:
        return {
            "suggestions": [
                "...and what about footfall there?",
                "How does that compare to last week?",
                "Show me the trend for that branch.",
                "What's the top item there?",
                "Compare it to LHR-01."
            ]
        }
    else:
        return {
            "suggestions": [
                "Which branch had the lowest revenue last month?",
                "Compare average order value across all locations this quarter.",
                "Which menu item is underperforming in Karachi?",
                "Show revenue trend for LHR-01 over the last 8 weeks.",
                "What's each branch's share of total revenue this month?"
            ]
        }


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    import subprocess, signal

    PORT = 8000
    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if f":{PORT}" in line and "LISTENING" in line:
                pid = int(line.strip().split()[-1])
                if pid != os.getpid():
                    os.kill(pid, signal.SIGTERM)
                    log.info("Killed existing process on port %d (PID %d)", PORT, pid)
    except Exception:
        pass

    uvicorn.run(app, host="0.0.0.0", port=PORT, access_log=False)
