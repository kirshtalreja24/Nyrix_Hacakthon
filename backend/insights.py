"""
NL → structured query spec, and SQL generation via OpenAI.
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """You are a business analytics query planner. Given a user's natural language question
about their business data and the available database schema, produce a JSON object that specifies
how to answer the question.

The output must be valid JSON with this exact schema:
{
  "sql": "<SELECT statement>",
  "source": "csv" or "postgres",
  "cross_source": false,
  "explanation": "<one sentence explaining what this query returns>",
  "time_column": "<column name if grouping by time, else null>",
  "entity_column": "<column name if grouping by entity like branch, else null>",
  "metric_columns": ["<numeric columns used>"]
}

CRITICAL — Include columns needed for the correct chart type:

1. **Trends / over time ("trend", "over time", "daily", "weekly", "monthly")**
   → ALWAYS include the date/time column in SELECT and GROUP BY (e.g. GROUP BY date)
   → sql example: SELECT date, SUM(revenue) AS total_revenue FROM ... GROUP BY date ORDER BY date

2. **Share / percentage ("share", "percentage", "%", "proportion", "distribution")**
   → ALWAYS compute the percentage in SQL. Include both the raw value AND percentage column.
   → sql example: SELECT branch, SUM(revenue) AS total_revenue, (SUM(revenue) * 100.0 / (SELECT SUM(revenue) FROM orders)) AS revenue_share FROM ... GROUP BY branch ORDER BY total_revenue DESC

3. **Comparison by branch/city ("compare", "by branch", "by city", "each branch")**
   → ALWAYS group by the entity column (branch/city etc.)
   → Include city and branch columns together when available (needed for geo heatmap)

4. **Ranking ("top", "lowest", "highest", "worst", "best")**
   → Include ORDER BY and at least 2 metrics if available (needed for ranked table)

5. **Single metric across all data ("total revenue", "total orders", "average")**
   → Single row aggregated result is fine (will show KPI card)

6. **Time series for a specific entity (e.g. "revenue trend for KHI-01")**
   → ALWAYS include date + branch columns. Filter by entity.
   → sql example: SELECT date, branch, SUM(revenue) AS total_revenue FROM orders WHERE branch = 'KHI-01' GROUP BY date, branch ORDER BY date

General SQL rules:
- Use standard PostgreSQL-compatible SQL syntax (works with both DuckDB and Postgres).
- Always SELECT the columns you GROUP BY first, then aggregated metrics.
- Use meaningful aliases (e.g., SUM(revenue) AS total_revenue).
- For "this month" or "last month", use date filters relative to the dataset range (2026-05-25 to 2026-07-19).
- For "this quarter", use Q3 2026 (July 1 - July 19, 2026) since data only extends into July.
- Never use SELECT *. Always be explicit.
- Include ORDER BY for ranking questions.
- Handle NULLs gracefully with COALESCE where needed.
- Do not hallucinate columns. Only use columns that exist in the schema.

Cross-source queries:
- If both CSV and PostgreSQL sources are connected, and the question references data from BOTH sources
  (e.g. revenue from orders AND footfall from footfall table where they live in different sources),
  set "cross_source": true and write the SQL using DuckDB syntax with "pg_" prefix for Postgres tables.
  For example: SELECT a.branch, a.revenue, b.footfall_count
               FROM orders a JOIN pg.footfall b ON a.branch = b.branch
- If the question only references one source, set "cross_source": false.
- Always include the "cross_source" field.
"""


def nl_to_query_spec(question: str, schema_text: str, source_hint: str = None, context: str = "") -> dict:
    """Convert a natural language question to a structured query spec via OpenAI."""
    user_msg = f"Available schema:\n{schema_text}\n\n"
    if source_hint:
        user_msg += f"Data source hint: use {source_hint}\n\n"
    if context:
        user_msg += f"{context}\n\n"
    user_msg += f"User question: {question}"

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    spec = json.loads(content)

    # Validate required fields
    if "sql" not in spec:
        raise ValueError(f"LLM did not return SQL. Response: {content}")

    return spec


def generate_insight(question: str, sql_used: str, result_summary: str, chart_type: str) -> str:
    """Generate a grounded plain-English insight from query results."""
    prompt = f"""You are a business analyst writing a concise insight for a dashboard.

User asked: "{question}"
SQL executed: {sql_used}
Chart type: {chart_type}
Result data summary:
{result_summary}

Write 1-2 sentences that:
1. Directly answer the user's question with specific numbers from the data.
2. Call out anything notable (highest/lowest, unusual patterns, significant differences).
3. Use real numbers — never estimate or invent figures. Only state what's in the data.
4. Keep it plain, specific, and actionable. No corporate jargon.

Response should be just the insight text, no labels or prefixes."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()
