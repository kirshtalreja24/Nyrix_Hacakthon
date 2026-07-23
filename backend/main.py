"""
Business Analytics Assistant — FastAPI Backend
Connectors: CSV/DuckDB + PostgreSQL
NL Query → OpenAI → SQL → Result → Chart + Insight
"""

import os
import json
import traceback
import logging
import time
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    # Use 200 if response is a StreamingResponse without status_code
    status = getattr(response, "status_code", 200)
    method = request.method
    path = request.url.path
    log.info("%s %s → %s (%.0fms)", method, path, status, elapsed * 1000)
    return response

# Global state
source = UnifiedSource()


# ─── Models ───────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str

class PostgresConnectRequest(BaseModel):
    host: str = None
    port: str = None
    dbname: str = None
    user: str = None
    password: str = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

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
    # Allow overriding env values with request params
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
            "hint": "Make sure PostgreSQL is running and credentials in .env are correct. "
                    "You can use Neon, Supabase, or Render free tiers for a hosted instance.",
        }
    log.info("Postgres connected: %d tables found", len(result.get("tables", [])))
    return result


@app.post("/api/query")
async def query(req: QueryRequest):
    """
    NL question → structured query spec → SQL → result → chart_type → insight.
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

        # Step 1: NL → structured query spec
        spec = nl_to_query_spec(req.question, schema_text, source_hint=source_type)

        sql = spec.get("sql", "")
        if not sql:
            raise HTTPException(status_code=422, detail="Could not generate a SQL query for this question.")

        log.info("SQL: %s", sql[:120])

        # Step 2: Execute SQL
        result_df = connector.query(sql)

        if result_df.empty:
            log.info("Query result: empty")
            return {
                "question": req.question,
                "chart_type": "empty",
                "chart_data": [],
                "insight": "No results found for this query. Try rephrasing or check your data.",
                "sql_used": sql,
                "source": source_type,
            }

        # Step 3: Determine chart type
        chart_info = select_chart(req.question, result_df, spec)

        # Step 4: Prepare chart data for frontend
        chart_data = result_df.fillna(0).to_dict(orient="records")

        # Step 5: Generate insight
        result_summary = result_df.head(20).to_string(index=False)
        insight = generate_insight(req.question, sql, result_summary, chart_info["chart_type"])

        log.info("Query result: %d rows, chart=%s", len(result_df), chart_info["chart_type"])

        return {
            "question": req.question,
            "chart_type": chart_info["chart_type"],
            "chart_type_label": chart_type_label(chart_info["chart_type"]),
            "chart_data": chart_data,
            "insight": insight,
            "sql_used": sql,
            "source": source_type,
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


@app.get("/api/schema")
async def get_schema():
    """Return the schema of the connected data sources."""
    return {"schema": source.get_schema()}


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    import subprocess, signal

    # Kill any existing process on port 8000 to avoid "address already in use"
    PORT = 8000
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if f":{PORT}" in line and "LISTENING" in line:
                pid = int(line.strip().split()[-1])
                if pid != os.getpid():
                    os.kill(pid, signal.SIGTERM)
                    log.info("Killed existing process on port %d (PID %d)", PORT, pid)
    except Exception:
        pass  # If cleanup fails, uvicorn will report the error normally

    uvicorn.run(app, host="0.0.0.0", port=PORT, access_log=False)
