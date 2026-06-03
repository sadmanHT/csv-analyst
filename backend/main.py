import io
import os
import uuid
import json
import base64
import traceback

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Clean Apple-style chart theme to match the dashboard UI
plt.rcParams.update({
    "figure.facecolor": "white",
    "figure.figsize": (7, 4.2),
    "figure.dpi": 120,
    "axes.facecolor": "white",
    "axes.edgecolor": "#d2d2d7",
    "axes.linewidth": 0.8,
    "axes.labelcolor": "#1d1d1f",
    "axes.titlecolor": "#1d1d1f",
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.grid": True,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "grid.color": "#ececef",
    "grid.linewidth": 1.0,
    "text.color": "#1d1d1f",
    "xtick.color": "#8a8a8f",
    "ytick.color": "#8a8a8f",
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "font.size": 11,
    "font.family": "sans-serif",
    "font.sans-serif": ["Inter", "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "legend.frameon": False,
    "legend.fontsize": 10,
})
matplotlib.rcParams["axes.prop_cycle"] = matplotlib.cycler(
    color=["#4F46E5", "#10B981", "#F59E0B", "#8B5CF6", "#EF4444",
           "#06B6D4", "#EC4899", "#0EA5E9", "#64748B", "#14B8A6"]
)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI(title="CSV Analyst Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_MODEL = "gemini-2.0-flash"
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

dataframes: dict[str, pd.DataFrame] = {}


class QueryRequest(BaseModel):
    session_id: str
    question: str
    category: str = "general"


def _num(x) -> float | None:
    """Coerce to a JSON-safe float (NaN/inf -> None)."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return round(f, 2)


def build_profile(df: pd.DataFrame) -> dict:
    """Compute a JSON-safe data profile for the insights panel."""
    numeric_df = df.select_dtypes(include=[np.number])

    total_cells = int(df.shape[0] * df.shape[1])
    missing_total = int(df.isna().sum().sum())
    missing_pct = round(100 * missing_total / total_cells, 1) if total_cells else 0.0
    duplicate_rows = int(df.duplicated().sum())

    numeric_stats: dict[str, dict] = {}
    for col in numeric_df.columns:
        s = numeric_df[col].dropna()
        if s.empty:
            continue
        numeric_stats[str(col)] = {
            "mean": _num(s.mean()),
            "median": _num(s.median()),
            "std": _num(s.std()),
            "min": _num(s.min()),
            "max": _num(s.max()),
        }

    # NaN-safe preview rows
    head = df.head(5).astype(object).where(pd.notna(df.head(5)), None)
    preview = head.to_dict(orient="records")

    return {
        "rows": int(len(df)),
        "columns": [str(c) for c in df.columns],
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
        "preview": preview,
        "numeric_features": int(numeric_df.shape[1]),
        "missing_total": missing_total,
        "missing_pct": missing_pct,
        "duplicate_rows": duplicate_rows,
        "numeric_stats": numeric_stats,
    }


def get_df_schema(df: pd.DataFrame) -> str:
    schema = f"Shape: {df.shape[0]} rows x {df.shape[1]} columns\n\nColumns:\n"
    for col in df.columns:
        schema += f"  - {col} ({df[col].dtype}): sample values: {df[col].dropna().head(3).tolist()}\n"
    schema += f"\nFirst 5 rows:\n{df.head(5).to_string()}"
    return schema


SYSTEM_PROMPT = """You are a data analyst agent. A pandas DataFrame `df` is already loaded in memory.
Write Python code to answer the user's question.

Rules:
- `df` is already defined — do not reload it
- Use only: pandas (pd), numpy (np), matplotlib.pyplot (plt), io, base64
- For charts: create the figure, then save it like this exactly:
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=120)
    plt.close()
    chart_b64 = base64.b64encode(buf.getvalue()).decode()
- Chart style: always add a clear, descriptive title via plt.title(...). Do NOT set custom
  colors, styles, or grids — a clean Apple-style theme is applied globally. Just plot the data.
  Rotate x labels with plt.xticks(rotation=30, ha='right') when category names are long.
- Always assign a string to `result` with a plain-English answer or summary
- Always set `chart_b64 = None` unless you create a chart
- If the result is a DataFrame, convert it: result = df_result.to_string()
- ROBUSTNESS: for correlations or numeric aggregations across columns, use numeric
  columns only — e.g. df.select_dtypes(include='number') or pass numeric_only=True.
  Never run numeric operations on text/identifier columns (names, IDs). Coerce with
  pd.to_numeric(..., errors='coerce') when a column may be mixed.
- Output ONLY valid Python code — no markdown fences, no explanation"""


# Domain lenses — the selected category turns the agent into a domain expert,
# shaping which computations it prefers and how it narrates the result.
CATEGORY_PERSONAS = {
    "general": (
        "ANALYSIS LENS: General. You are a meticulous general-purpose data analyst. "
        "Provide clear, neutral, statistically sound insights."
    ),
    "financial": (
        "ANALYSIS LENS: Financial. You are a senior FINANCIAL analyst. Interpret the data "
        "through a financial lens — revenue, costs, margins, growth rates (YoY/MoM), volatility "
        "and risk, and key ratios. Prefer computations like growth %, cumulative totals, moving "
        "averages, and standard deviation as a risk proxy. Format money clearly and, in the "
        "written answer, call out financial implications, risks, and opportunities."
    ),
    "medical": (
        "ANALYSIS LENS: Medical. You are a clinical / healthcare data analyst. Interpret the data "
        "through a medical lens — prevalence, risk factors, patient cohorts, and distributions of "
        "clinical measurements. Prefer group-wise comparisons (outcome vs. non-outcome), "
        "correlation of features with the outcome, and distribution analysis. ALWAYS describe "
        "relationships as associations, NOT causation. Flag clinically meaningful or at-risk groups."
    ),
    "retail": (
        "ANALYSIS LENS: Retail. You are a retail & e-commerce analyst. Interpret the data through "
        "a commerce lens — sales and revenue by product/category/region, order volume, basket "
        "size, ratings, and customer behavior. Prefer top-N rankings, revenue breakdowns, and trends."
    ),
    "marketing": (
        "ANALYSIS LENS: Marketing. You are a marketing & growth analyst. Interpret the data through "
        "a marketing lens — acquisition, conversion, retention, segmentation, channels, and campaign "
        "performance. Prefer funnel/segment breakdowns, rates, and cohort-style comparisons."
    ),
    "hr": (
        "ANALYSIS LENS: HR. You are an HR / people-analytics specialist. Interpret the data through "
        "a workforce lens — headcount, attrition/turnover, tenure, demographics, performance, and "
        "compensation equity. Prefer group comparisons and distribution analysis; be sensitive about fairness."
    ),
}


def system_prompt_for(category: str) -> str:
    persona = CATEGORY_PERSONAS.get(category, CATEGORY_PERSONAS["general"])
    return f"{persona}\n\n{SYSTEM_PROMPT}"


# Modules the generated analysis code is allowed to import.
ALLOWED_MODULES = {
    "pandas", "numpy", "matplotlib", "math", "statistics",
    "datetime", "io", "base64", "collections", "itertools", "re", "json",
}


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Whitelisted __import__ for the sandbox — blocks os, sys, subprocess, etc."""
    root = name.split(".")[0]
    if root in ALLOWED_MODULES:
        return __import__(name, globals, locals, fromlist, level)
    raise ImportError(f"Import of '{name}' is not allowed in the sandbox")


SAFE_BUILTINS = {
    "__import__": _safe_import,
    "len": len, "range": range, "enumerate": enumerate, "zip": zip,
    "list": list, "dict": dict, "set": set, "frozenset": frozenset, "tuple": tuple,
    "str": str, "int": int, "float": float, "bool": bool, "complex": complex,
    "type": type, "print": print, "round": round, "abs": abs, "min": min, "max": max,
    "sum": sum, "sorted": sorted, "reversed": reversed, "isinstance": isinstance,
    "map": map, "filter": filter, "any": any, "all": all, "getattr": getattr,
    "hasattr": hasattr, "repr": repr, "format": format, "slice": slice,
    "iter": iter, "next": next, "divmod": divmod, "pow": pow, "chr": chr, "ord": ord,
    "True": True, "False": False, "None": None, "Exception": Exception,
    "ValueError": ValueError, "KeyError": KeyError, "TypeError": TypeError,
}


def execute_code(code: str, df: pd.DataFrame) -> tuple[str, str | None]:
    safe_globals = {
        "__builtins__": SAFE_BUILTINS,
        "pd": pd, "np": np, "plt": plt, "io": io, "base64": base64,
    }
    local_vars: dict = {
        "df": df.copy(),
        "result": None,
        "chart_b64": None,
    }
    exec(code, safe_globals, local_vars)
    result = local_vars.get("result")
    chart_b64 = local_vars.get("chart_b64")
    if result is None:
        result = "Done. See chart above." if chart_b64 else "No result returned."
    return str(result), chart_b64


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)) -> dict:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {e}")
    session_id = str(uuid.uuid4())
    dataframes[session_id] = df
    profile = build_profile(df)
    return {"session_id": session_id, "filename": file.filename, **profile}


@app.post("/query")
async def query_csv(req: QueryRequest) -> StreamingResponse:
    if req.session_id not in dataframes:
        raise HTTPException(status_code=404, detail="Session not found. Upload a CSV first.")

    df = dataframes[req.session_id]
    schema = get_df_schema(df)

    async def stream():
        def emit(payload: dict) -> str:
            return f"data: {json.dumps(payload)}\n\n"

        yield emit({"step": "analyzing", "message": "Analyzing your dataset..."})

        yield emit({"step": "thinking", "message": "Agent is writing pandas code..."})

        def generate(user_text: str) -> str:
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_text,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt_for(req.category),
                    temperature=0,
                ),
            )
            text = (resp.text or "").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if "```" in text:
                text = text.rsplit("```", 1)[0]
            return text.strip()

        base_prompt = f"DataFrame schema:\n{schema}\n\nQuestion: {req.question}"

        try:
            code = generate(base_prompt)
        except Exception as e:
            yield emit({"step": "error", "message": f"Model error: {e}"})
            return

        # Execute, with one self-correcting repair attempt on failure.
        for attempt in range(2):
            yield emit({"step": "code", "message": "Code generated", "code": code})
            yield emit({"step": "executing", "message": "Executing code on your data..."})
            try:
                result, chart_b64 = execute_code(code, df)
                yield emit({"step": "done", "message": "Analysis complete", "result": result, "chart": chart_b64})
                return
            except Exception:
                err = traceback.format_exc().strip().splitlines()[-1]
                if attempt == 0:
                    yield emit({"step": "thinking", "message": f"Hit an error — agent is fixing the code… ({err})"})
                    try:
                        code = generate(
                            f"{base_prompt}\n\nYou previously wrote this code:\n{code}\n\n"
                            f"It failed with this error:\n{err}\n\n"
                            "Fix the code so it runs correctly. Output ONLY the corrected Python code."
                        )
                        continue
                    except Exception as e:
                        yield emit({"step": "error", "message": f"Model error during repair: {e}"})
                        return
                yield emit({"step": "error", "message": f"Execution error: {err}"})
                return

    return StreamingResponse(stream(), media_type="text/event-stream")
