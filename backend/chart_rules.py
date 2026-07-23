"""
Deterministic chart-type selection rule engine (no LLM involved).
"""

import pandas as pd


def select_chart(question: str, result_df: pd.DataFrame, query_spec: dict = None) -> dict:
    """
    Pure-code classifier to determine chart type from result shape and question intent.

    Returns dict with 'chart_type' and optional 'params'.
    """
    n_rows = len(result_df)
    has_time_col = any(col in result_df.columns for col in ["date", "week_start", "month", "year"])
    has_geo_col = "city" in result_df.columns
    entity_col = "branch" if "branch" in result_df.columns else None
    n_metric_cols = len([c for c in result_df.columns if pd.api.types.is_numeric_dtype(result_df[c])])

    q = question.lower()
    wants_share = any(w in q for w in ["share", "percentage", "%", "proportion", "distribution"])
    wants_rank = any(w in q for w in ["top", "lowest", "highest", "compare", "rank", "which"])
    wants_trend = any(w in q for w in ["trend", "over time", "trajectory", "change over"])

    # Edge case: empty result
    if n_rows == 0:
        return {"chart_type": "empty", "params": {}}

    # Single row, single metric → KPI scorecard
    if n_rows == 1 and n_metric_cols <= 2:
        return {"chart_type": "kpi_scorecard", "params": {}}

    # Trend over time → line chart (even if many entities)
    if wants_trend and has_time_col:
        return {"chart_type": "line", "params": {"time_col": "date" if "date" in result_df.columns else "week_start"}}

    # Time series with few entities → line
    if has_time_col:
        n_entities = result_df[entity_col].nunique() if entity_col else 1
        if n_entities <= 3:
            return {"chart_type": "line", "params": {"time_col": "date" if "date" in result_df.columns else "week_start"}}
        else:
            # Many entities over time → line chart with multiple lines
            return {"chart_type": "line", "params": {"time_col": "date" if "date" in result_df.columns else "week_start"}}

    # Geo + entity comparison → heatmap grid
    if has_geo_col and entity_col and n_rows > 1 and not wants_share:
        return {"chart_type": "geo_heatmap", "params": {}}

    # Share/proportion → pie
    if wants_share and entity_col:
        return {"chart_type": "pie", "params": {}}

    # Ranking or comparison with 2+ metrics → ranked table
    if entity_col and n_metric_cols >= 2:
        return {"chart_type": "ranked_table", "params": {}}

    # Entity with single metric → bar
    if entity_col and n_metric_cols == 1:
        return {"chart_type": "bar", "params": {}}

    # Categorical → bar
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
