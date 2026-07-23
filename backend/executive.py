"""
Executive Summary — multi-branch performance synthesis.
Computes real aggregates from the data, then uses OpenAI to generate
grounded bullet-point insights.
"""

import os
import json
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SUMMARY_PROMPT = """You are a business analytics assistant writing an Executive Summary for a multi-branch restaurant chain.

Based on the following computed aggregates from the dataset, write 4-6 concise bullet points
synthesizing performance across all branches. Each bullet should be specific and grounded in the numbers below.

RULES:
- Only state numbers that appear in the data below. Do not estimate or invent figures.
- Call out the top and bottom performing branches by name.
- Flag any notable anomalies (e.g., large week-over-week drops).
- Note product-level patterns that differ across cities/branches.
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
    Compute real aggregates across all branches from whichever source is active.
    Returns a dict of computed numbers for the LLM prompt.
    """
    agg = {}

    connector, source_type = source.get_active_connector()
    if connector is None:
        return {"error": "No data source connected."}

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

        # Top and bottom
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

            # Flag large drops
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

        # Detect city-specific bestsellers
        if len(items_df) > 0:
            for city in items_df["city"].unique():
                city_items = items_df[items_df["city"] == city]
                if len(city_items) > 0:
                    best = city_items.iloc[0]
                    agg[f"best_item_{city}"] = {"item": best["item"], "revenue": float(best["item_revenue"])}
    except Exception as e:
        agg["items_error"] = str(e)

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
