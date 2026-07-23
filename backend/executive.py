"""
Executive Summary — multi-branch performance synthesis.
Computes real aggregates from the data, then uses OpenAI to generate
grounded bullet-point insights.
"""

import os
import json
from datetime import datetime, timezone
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SUMMARY_PROMPT = """You are a business analytics assistant writing an Executive Summary.

Based on the following computed aggregates from the dataset, write 4-6 concise bullet points
synthesizing the data. Each bullet should be specific and grounded in the numbers below.

RULES:
- Only state numbers that appear in the data below. Do not estimate or invent figures.
- Call out the top and bottom performing entities by name.
- Flag any notable anomalies (e.g., large week-over-week drops, outliers).
- Note patterns that differ across categories/segments.
- Keep each bullet to 1-2 sentences. Plain, specific language. No jargon.
- Start each bullet with the key fact, not a label.

Computed aggregates:
{aggregates}

Return JSON with the structure:
{{
  "summary_bullets": ["bullet 1", "bullet 2", ...]
}}"""


def compute_aggregates(source) -> dict:
    """
    Compute aggregates from whichever source is active.
    Adapts to any table schema — if the expected orders/footfall tables
    exist, uses the specialized queries; otherwise does generic aggregation.
    """
    agg = {}

    connector, source_type = source.get_active_connector()
    if connector is None:
        return {"error": "No data source connected."}

    # Discover what tables are available
    if source_type == "csv_duckdb":
        available_tables = list(source.csv.tables.keys())
    else:
        # PostgreSQL — get discovered tables from the connector
        available_tables = list(source.postgres.tables) if hasattr(source.postgres, 'tables') and source.postgres.tables else []
    agg["available_tables"] = available_tables

    # ── Try specialized branch/revenue queries (orders.footfall schema) ──
    if any(t in available_tables for t in ["orders", "footfall"]):
        # --- Revenue aggregates ---
        try:
            revenue_df = connector.query("""
                SELECT
                    branch,
                    city,
                    SUM(revenue) AS total_revenue,
                    COUNT(*) AS order_count,
                    AVG(order_value) AS avg_order_value
                FROM orders
                WHERE revenue IS NOT NULL AND revenue > 0
                GROUP BY branch, city
                ORDER BY total_revenue DESC
            """)

            agg["total_revenue"] = float(revenue_df["total_revenue"].sum())
            agg["revenue_by_branch"] = revenue_df.to_dict(orient="records")

            if len(revenue_df) > 0:
                agg["top_branch"] = revenue_df.iloc[0]["branch"]
                agg["top_branch_revenue"] = float(revenue_df.iloc[0]["total_revenue"])
                agg["bottom_branch"] = revenue_df.iloc[-1]["branch"]
                agg["bottom_branch_revenue"] = float(revenue_df.iloc[-1]["total_revenue"])
        except Exception as e:
            agg["revenue_error"] = str(e)

        # --- Revenue by city ---
        try:
            city_df = connector.query("""
                SELECT city, SUM(revenue) AS city_revenue
                FROM orders
                WHERE revenue IS NOT NULL AND revenue > 0
                GROUP BY city
                ORDER BY city_revenue DESC
            """)
            agg["revenue_by_city"] = city_df.to_dict(orient="records")
        except Exception as e:
            agg["city_error"] = str(e)

        # --- Footfall WoW change ---
        try:
            footfall_df = connector.query("""
                SELECT branch, week_start, footfall_count
                FROM footfall
                ORDER BY branch, week_start
            """)

            if len(footfall_df) > 0:
                footfall_agg = []
                for branch in footfall_df["branch"].unique():
                    branch_data = footfall_df[footfall_df["branch"] == branch].sort_values("week_start")
                    if len(branch_data) >= 2:
                        latest = branch_data.iloc[-1]["footfall_count"]
                        prev = branch_data.iloc[-2]["footfall_count"]
                        if prev > 0:
                            pct_change = ((latest - prev) / prev) * 100
                        else:
                            pct_change = 0
                        footfall_agg.append({
                            "branch": branch,
                            "latest_footfall": int(latest),
                            "previous_footfall": int(prev),
                            "wow_change_pct": round(pct_change, 1),
                            "week_start": str(branch_data.iloc[-1]["week_start"]),
                        })

                agg["footfall_wow"] = footfall_agg
                large_drops = [f for f in footfall_agg if f["wow_change_pct"] < -15]
                agg["footfall_anomalies"] = large_drops
        except Exception as e:
            agg["footfall_error"] = str(e)

        # --- Top items ---
        try:
            items_df = connector.query("""
                SELECT
                    item,
                    city,
                    SUM(revenue) AS item_revenue,
                    COUNT(*) AS order_count
                FROM orders
                WHERE revenue IS NOT NULL AND revenue > 0
                GROUP BY item, city
                ORDER BY item_revenue DESC
            """)
            agg["top_items_by_city"] = items_df.head(10).to_dict(orient="records")

            if len(items_df) > 0:
                for city in items_df["city"].unique():
                    city_items = items_df[items_df["city"] == city]
                    if len(city_items) > 0:
                        best = city_items.iloc[0]
                        agg[f"best_item_{city}"] = {"item": best["item"], "revenue": float(best["item_revenue"])}
        except Exception as e:
            agg["items_error"] = str(e)

    # ── Generic fallback: analyze any other table ──
    for table in available_tables:
        if table in ("orders", "footfall"):
            continue  # already handled above

        try:
            df = connector.query(f"SELECT * FROM \"{table}\" LIMIT 100")

            # Find numeric and categorical columns
            numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            str_cols = [c for c in df.columns if pd.api.types.is_object_dtype(df[c])]
            date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]

            info = {
                "table": table,
                "total_rows": int(connector.query(f"SELECT COUNT(*) AS c FROM \"{table}\"").iloc[0]["c"]),
                "columns": list(df.columns),
                "numeric_columns": numeric_cols,
            }

            # Basic numeric aggregates
            if numeric_cols:
                agg_sql = ", ".join([
                    f"SUM(\"{c}\") AS sum_{c}, AVG(\"{c}\") AS avg_{c}, MIN(\"{c}\") AS min_{c}, MAX(\"{c}\") AS max_{c}"
                    for c in numeric_cols
                ])
                summary = connector.query(f"SELECT {agg_sql} FROM \"{table}\"").fillna(0).to_dict(orient="records")[0]
                info["numeric_summary"] = {k: float(v) if not isinstance(v, str) else v for k, v in summary.items()}

            # Categorical breakdown (top 5 per string column)
            if str_cols:
                breakdowns = {}
                for col in str_cols[:3]:
                    top5 = connector.query(f"""
                        SELECT "{col}", COUNT(*) AS count
                        FROM \"{table}\"
                        GROUP BY "{col}"
                        ORDER BY count DESC
                        LIMIT 5
                    """).fillna("").to_dict(orient="records")
                    breakdowns[col] = top5
                info["categorical_breakdown"] = breakdowns

            agg[f"table_{table}"] = info

        except Exception as e:
            agg[f"{table}_error"] = str(e)

    return agg


def generate_executive_summary(source) -> dict:
    """Generate the Executive Summary: compute aggregates → LLM → bullets."""
    aggregates = compute_aggregates(source)

    if "error" in aggregates:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary_bullets": ["No data source connected. Upload a CSV or connect to PostgreSQL first."],
            "computed_aggregates": aggregates,
        }

    # Call OpenAI with the grounded aggregates
    prompt = SUMMARY_PROMPT.format(aggregates=json.dumps(aggregates, indent=2, default=str))

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    content = json.loads(response.choices[0].message.content)
    bullets = content.get("summary_bullets", [])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary_bullets": bullets,
        "computed_aggregates": aggregates,
    }
