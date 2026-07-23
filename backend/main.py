"""
Business Analytics Assistant — FastAPI Backend
Connectors: CSV/DuckDB + PostgreSQL
NL Query → OpenAI → SQL → Result → Chart + Insight
"""

import os
import json
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException
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
    result = source.csv.load_csv(content, file.filename)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
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

    result = source.postgres.connect()
    if not result["connected"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Connection failed"))
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

    try:
        schema_text = source.get_schema()

        # Step 1: NL → structured query spec
        spec = nl_to_query_spec(req.question, schema_text, source_hint=source_type)

        sql = spec.get("sql", "")
        if not sql:
            raise HTTPException(status_code=422, detail="Could not generate a SQL query for this question.")

        # Step 2: Execute SQL
        result_df = connector.query(sql)

        if result_df.empty:
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
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}\n\n{tb}")


@app.get("/api/executive-summary")
async def executive_summary():
    """Standing multi-branch Executive Summary panel."""
    try:
        result = generate_executive_summary(source)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Executive Summary failed: {str(e)}\n\n{tb}")


@app.get("/api/schema")
async def get_schema():
    """Return the schema of the connected data sources."""
    return {"schema": source.get_schema()}


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
