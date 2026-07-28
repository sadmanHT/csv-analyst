"""
Semantic Schema Extraction & Column Role Profiling
"""

import pandas as pd
import numpy as np

def infer_column_roles(df: pd.DataFrame) -> dict[str, list[str]]:
    """Classify DataFrame columns into semantic roles: metrics, dimensions, dates, identifiers."""
    metrics: list[str] = []
    dimensions: list[str] = []
    dates: list[str] = []
    identifiers: list[str] = []

    for col in df.columns:
        col_str = str(col)
        lower = col_str.lower()

        # Dates / Timestamps
        if any(kw in lower for kw in ["date", "time", "year", "month", "day", "created_at", "updated_at"]):
            dates.append(col_str)
            continue

        # Identifiers
        if lower == "id" or lower.endswith("_id") or lower.endswith("id"):
            identifiers.append(col_str)
            continue

        # Numeric Metrics vs Categorical Dimensions
        if pd.api.types.is_numeric_dtype(df[col]):
            # If numeric with very low unique count (e.g. 2-5 unique values), may be a categorical dimension
            if df[col].nunique() <= 5 and len(df) > 20:
                dimensions.append(col_str)
            else:
                metrics.append(col_str)
        else:
            dimensions.append(col_str)

    return {
        "metrics": metrics,
        "dimensions": dimensions,
        "dates": dates,
        "identifiers": identifiers,
    }

def build_semantic_schema(df: pd.DataFrame) -> dict[str, Any]:
    """Build a rich, structured schema payload for LLM planning."""
    roles = infer_column_roles(df)
    cols_desc = []
    for col in df.columns:
        col_str = str(col)
        dtype = str(df[col].dtype)
        nunique = int(df[col].nunique())
        missing = int(df[col].isna().sum())

        role = "metric" if col_str in roles["metrics"] else \
               "dimension" if col_str in roles["dimensions"] else \
               "date" if col_str in roles["dates"] else "identifier"

        samples = df[col].dropna().astype(str).unique()[:5].tolist()
        cols_desc.append({
            "name": col_str,
            "dtype": dtype,
            "role": role,
            "nunique": nunique,
            "missing": missing,
            "sample_values": samples,
        })

    return {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "roles": roles,
        "columns": cols_desc,
    }
