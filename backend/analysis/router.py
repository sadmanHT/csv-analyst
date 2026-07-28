"""
Query Complexity Router & Execution Budget Selection
"""

import re
import pandas as pd
from typing import tuple
from backend.core.schemas import ExecutionBudget

def classify_query_complexity(question: str, df: pd.DataFrame) -> tuple[str, dict]:
    """Classify user query into routing paths (direct, standard, deep)."""
    q = question.strip().lower()

    # Fast-Path 0: Model Recommendation
    if any(k in q for k in ["what model", "which model", "recommend model", "recommend algorithm", "ml algorithm"]):
        return "model_recommendation", {}

    # Fast-Path 0A: Unclear Query / Greeting
    if len(q) <= 2 or q in ["hi", "hello", "hey", "help", "gg"]:
        return "unclear_query", {}

    # Fast-Path 0B: Dataset Purpose
    if any(k in q for k in ["what is this dataset", "dataset purpose", "describe dataset", "overview of dataset"]):
        return "dataset_purpose", {}

    # Fast-Path 1: Direct Row Lookup ("show me row 5", "row 42")
    match_row = re.search(r"\brow\s*#?\s*(\d+)\b", q)
    if match_row:
        display_row = int(match_row.group(1))
        row_idx = display_row - 1
        if 0 <= row_idx < len(df):
            return "direct_row_lookup", {"display_row": display_row, "row_index": row_idx}

    # Standard-Path: Data Quality Guidance ("how to make this a good dataset", "how to improve this dataset")
    if any(k in q for k in ["good dataset", "improve this dataset", "quality guidance", "data quality issues"]):
        return "data_quality_guidance", {}

    # Deterministic aggregations / lookups
    if any(k in q for k in ["how many rows", "how many columns", "missing values", "duplicate rows", "summary statistics"]):
        return "deterministic", {}

    # Deep Analysis: Predictive modeling, forecasting, complex multi-step reasoning
    if any(k in q for k in ["predict", "train", "forecast", "machine learning", "regression", "classification", "investigate"]):
        return "deep_analysis", {}

    # Default to standard analysis
    return "standard_analysis", {}


def get_execution_budget(q_type: str) -> ExecutionBudget:
    """Assign an execution budget per query route type."""
    if q_type in ("model_recommendation", "unclear_query", "dataset_purpose", "direct_row_lookup", "deterministic"):
        return ExecutionBudget(
            route="direct",
            max_llm_calls=1,
            max_execution_time_s=3.0,
            timeout_s=5.0,
            allow_chart=False,
            allow_code_repair=False,
        )
    elif q_type in ("data_quality_guidance", "standard_analysis"):
        return ExecutionBudget(
            route="standard",
            max_llm_calls=1,
            max_execution_time_s=6.0,
            timeout_s=8.0,
            allow_chart=True,
            allow_code_repair=True,
        )
    else:
        return ExecutionBudget(
            route="deep",
            max_llm_calls=2,
            max_execution_time_s=12.0,
            timeout_s=15.0,
            allow_chart=True,
            allow_code_repair=True,
        )
