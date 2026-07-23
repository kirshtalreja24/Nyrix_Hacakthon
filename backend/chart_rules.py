"""
Deterministic chart-type selection rule engine (no LLM involved).
Auto-detects column roles by name AND dtype for maximum compatibility.
"""

import pandas as pd


def select_chart(question: str, result_df: pd.DataFrame, query_spec: dict = None) -> dict:
    """
    Pure-code classifier to determine chart type from result shape and question intent.
    Returns dict with 'chart_type' and optional 'params'.
    """

    # ── Column role detection (flexible — by name AND dtype) ──────────────

    # Time columns — check both known names and datetime dtype
    TIME_NAMES = {"date", "week_start", "month", "year", "day", "week", "timestamp", "period", "quarter"}
    has_time_col = False
    for col in result_df.columns:
        if col.lower() in TIME_NAMES:
            has_time_col = True
            break
        if pd.api.types.is_datetime64_any_dtype(result_df[col]):
            has_time_col = True
            break

    # Geo columns
    GEO_NAMES = {"city", "state", "province", "region", "country", "area", "zone"}
    geo_col = None
    for col in result_df.columns:
        if col.lower() in GEO_NAMES:
            geo_col = col
            break

    # Entity columns (grouping columns)
    ENTITY_NAMES = {"branch", "store", "location", "outlet", "department", "team",
                    "item", "product", "category", "segment", "type", "class", "name"}
    entity_col = None
    for col in result_df.columns:
        if col.lower() in ENTITY_NAMES:
            entity_col = col
            break

    n_metric_cols = len([c for c in result_df.columns if pd.api.types.is_numeric_dtype(result_df[c])])

    # Detect percentage/share columns in result data
    share_col = None
    for col in result_df.columns:
        cl = col.lower()
        if any(kw in cl for kw in ["share", "pct", "percentage", "proportion", "distribution", "ratio"]):
            share_col = col
            break

    n_rows = len(result_df)
    q = question.lower()

    wants_share = any(w in q for w in ["share", "percentage", "%", "proportion", "distribution", "breakdown"])
    wants_rank = any(w in q for w in ["top", "lowest", "highest", "compare", "rank", "which", "worst", "best"])
    wants_trend = any(w in q for w in ["trend", "over time", "trajectory", "change over", "time series", "daily", "weekly", "monthly"])


    # ── Decision logic ────────────────────────────────────────────────────

    # Empty result
    if n_rows == 0:
        return {"chart_type": "empty", "params": {}}

    # Single row, ≤2 metrics → KPI scorecard
    if n_rows == 1 and n_metric_cols <= 2:
        return {"chart_type": "kpi_scorecard", "params": {}}

    # Share/proportion: keyword in question OR share column in result → pie
    if (wants_share or share_col) and entity_col and n_rows > 1:
        return {"chart_type": "pie", "params": {}}

    # Trend explicit keyword → line (even without time col detected)
    if wants_trend and has_time_col:
        return {"chart_type": "line", "params": {}}

    # Any time column → line chart
    if has_time_col:
        return {"chart_type": "line", "params": {}}

    # Geo + entity → heatmap grid
    if geo_col and entity_col and n_rows > 1:
        return {"chart_type": "geo_heatmap", "params": {}}

    # 2+ metrics per entity → ranked table
    if entity_col and n_metric_cols >= 2:
        return {"chart_type": "ranked_table", "params": {}}

    # Entity with single metric → bar chart
    if entity_col and n_metric_cols == 1:
        return {"chart_type": "bar", "params": {}}

    # Categorical with single metric → bar
    if n_metric_cols == 1 and n_rows <= 20:
        return {"chart_type": "bar", "params": {}}

    # Fallback
    return {"chart_type": "ranked_table", "params": {}}


def chart_type_label(chart_type: str) -> str:
    labels = {
        "kpi_scorecard": "Key Metric",
        "bar": "Bar Chart",
        "pie": "Pie Chart",
        "line": "Line Chart",
        "geo_heatmap": "Geographic Heatmap",
        "ranked_table": "Ranked Table",
        "empty": "No Results",
    }
    return labels.get(chart_type, chart_type)
