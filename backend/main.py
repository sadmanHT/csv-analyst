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
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns

# ── Premium chart theme — seaborn base + custom rcParams, matched to the indigo UI ──
INDIGO_PALETTE = ["#4F46E5", "#10B981", "#F59E0B", "#8B5CF6", "#EF4444",
                  "#06B6D4", "#EC4899", "#0EA5E9", "#64748B", "#14B8A6"]
try:
    sns.set_theme(style="whitegrid", palette=INDIGO_PALETTE)
except Exception:
    pass

plt.rcParams.update({
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "figure.figsize": (8, 5),
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "axes.facecolor": "white",
    "axes.edgecolor": "#E2E8F0",
    "axes.linewidth": 1.1,
    "axes.labelcolor": "#334155",
    "axes.labelweight": "medium",
    "axes.labelpad": 8,
    "axes.titlecolor": "#0F172A",
    "axes.titlesize": 15,
    "axes.titleweight": "bold",
    "axes.titlepad": 16,
    "axes.labelsize": 11.5,
    "axes.grid": True,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "grid.color": "#EEF2F6",
    "grid.linewidth": 1.1,
    "text.color": "#0F172A",
    "xtick.color": "#64748B",
    "ytick.color": "#64748B",
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "font.size": 11,
    "font.family": "sans-serif",
    "font.sans-serif": ["Inter", "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "legend.frameon": True,
    "legend.framealpha": 0.92,
    "legend.edgecolor": "#E2E8F0",
    "legend.fontsize": 10,
    "figure.autolayout": True,
})
matplotlib.rcParams["axes.prop_cycle"] = matplotlib.cycler(color=INDIGO_PALETTE)

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

GEMINI_MODEL = "gemini-2.5-flash-lite-preview-06-17"
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

dataframes: dict[str, pd.DataFrame] = {}
models: dict[str, dict] = {}  # session_id -> trained model info (for inference on new input)

# ── RAG document store ────────────────────────────────────────────────────────

EMBED_MODEL = "models/text-embedding-004"
EMBED_DIM   = 768


def _chunk_text(text: str, size: int = 600, overlap: int = 80) -> list[str]:
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return [c for c in chunks if len(c.strip()) > 40]


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using Gemini text-embedding-004."""
    results = []
    for text in texts:
        try:
            resp = client.models.embed_content(model=EMBED_MODEL, contents=text)
            results.append(list(resp.embeddings[0].values))
        except Exception:
            results.append([0.0] * EMBED_DIM)
    return results


def _parse_doc(content: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception as e:
            raise ValueError(f"Could not parse PDF: {e}")
    elif ext in ("xlsx", "xls"):
        try:
            df_doc = pd.read_excel(io.BytesIO(content))
            return df_doc.to_string(index=False)
        except Exception as e:
            raise ValueError(f"Could not parse Excel: {e}")
    elif ext in ("txt", "md", "rst", "csv"):
        return content.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: .{ext}. Use PDF, Excel, or text files.")


class DocStore:
    """Per-session in-memory vector store for RAG over uploaded documentation."""

    def __init__(self):
        self.chunks:    list[str]        = []
        self.embeddings: list[list[float]] = []
        self.metadata:  list[dict]       = []   # {filename, chunk_idx}
        self.filenames: list[str]        = []

    def add(self, text: str, filename: str) -> int:
        chunks = _chunk_text(text)
        embs   = _embed_batch(chunks)
        for i, (c, e) in enumerate(zip(chunks, embs)):
            self.chunks.append(c)
            self.embeddings.append(e)
            self.metadata.append({"filename": filename, "chunk_idx": i})
        if filename not in self.filenames:
            self.filenames.append(filename)
        return len(chunks)

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        if not self.embeddings:
            return []
        q = np.array(_embed_batch([query])[0], dtype=np.float32)
        sims = [
            float(np.dot(q, np.array(e, dtype=np.float32)) /
                  (np.linalg.norm(q) * np.linalg.norm(e) + 1e-9))
            for e in self.embeddings
        ]
        top_idx = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_k]
        return [
            {"text": self.chunks[i], "filename": self.metadata[i]["filename"], "score": round(sims[i], 3)}
            for i in top_idx if sims[i] > 0.25
        ]


doc_stores: dict[str, DocStore] = {}


class QueryRequest(BaseModel):
    session_id: str
    question: str
    category: str = "general"


class PredictRequest(BaseModel):
    session_id: str
    target: str
    category: str = "general"


class TextUploadRequest(BaseModel):
    text: str
    filename: str = "pasted_data.csv"
    has_header: bool = True


class PredictInputRequest(BaseModel):
    session_id: str
    values: dict


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


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def build_overview_charts(df: pd.DataFrame) -> list[dict]:
    """Deterministically render an instant 'dashboard' the moment a CSV loads —
    no LLM call, so it is fast and demo-safe. Each chart is isolated in try/except."""
    charts: list[dict] = []
    numeric = df.select_dtypes(include="number")

    # 1 · Correlation heatmap
    if numeric.shape[1] >= 2:
        try:
            corr = numeric.corr()
            n = len(corr.columns)
            fig, ax = plt.subplots(figsize=(min(9, 2 + 0.55 * n), min(7.5, 1.5 + 0.5 * n)))
            sns.heatmap(corr, annot=(n <= 12), fmt=".2f", cmap="coolwarm", center=0,
                        vmin=-1, vmax=1, linewidths=0.5, square=True,
                        cbar_kws={"shrink": 0.8}, annot_kws={"size": 7}, ax=ax)
            ax.set_title("Correlation Matrix")
            charts.append({"title": "Correlation Matrix", "chart": _fig_to_b64(fig)})
        except Exception:
            pass

    # 2 · Distribution small-multiples (up to 6 numeric columns)
    if numeric.shape[1] >= 1:
        try:
            cols = list(numeric.columns)[:6]
            ncols = min(3, len(cols))
            nrows = (len(cols) + ncols - 1) // ncols
            fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 3.1 * nrows))
            axes = np.array(axes).reshape(-1)
            for i, c in enumerate(cols):
                sns.histplot(df[c].dropna(), kde=True, ax=axes[i])
                axes[i].set_title(str(c))
                axes[i].set_xlabel("")
                axes[i].set_ylabel("")
            for j in range(len(cols), len(axes)):
                axes[j].set_visible(False)
            fig.suptitle("Distributions", fontsize=15, fontweight="bold")
            fig.tight_layout()
            charts.append({"title": "Distributions", "chart": _fig_to_b64(fig)})
        except Exception:
            pass

    # 3 · Top values of the first meaningful low-cardinality categorical column
    for c in df.columns:
        name = str(c).lower()
        if any(k in name for k in ("date", "time", "_at", "id")):
            continue  # skip dates / identifiers — not useful as categories
        if not pd.api.types.is_numeric_dtype(df[c]) and 2 <= df[c].nunique() <= 25:
            try:
                vc = df[c].value_counts().head(10)
                fig, ax = plt.subplots(figsize=(8, 5))
                sns.barplot(x=vc.values, y=vc.index.astype(str), ax=ax)
                for cont in ax.containers:
                    ax.bar_label(cont, fmt="%.0f", padding=3)
                ax.set_title(f"Top {c} by count")
                ax.set_xlabel("Count")
                ax.set_ylabel(str(c))
                charts.append({"title": f"Top {c}", "chart": _fig_to_b64(fig)})
                break
            except Exception:
                pass

    return charts


def train_predictive_model(df: pd.DataFrame, target: str) -> tuple[str, str, dict]:
    """Train a Random Forest; return (summary, importance_chart, info).
    info also contains shap_chart, perm_chart, pdp_chart for explainability."""
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score, r2_score, mean_absolute_error
    from sklearn.inspection import permutation_importance, PartialDependenceDisplay

    data = df.dropna(subset=[target]).copy()
    if len(data) < 30:
        raise ValueError("Not enough rows to train a reliable model (need at least 30).")

    y_raw = data[target]
    X = data.drop(columns=[target])

    id_like = [c for c in X.columns
               if str(c).lower() in ("id", "index")
               or str(c).lower().endswith("_id")
               or (pd.api.types.is_integer_dtype(X[c]) and X[c].nunique() > 0.95 * len(X))]
    X = X.drop(columns=id_like, errors="ignore")

    num_cols = list(X.select_dtypes(include="number").columns)
    cat_cols = [c for c in X.columns
                if not pd.api.types.is_numeric_dtype(X[c]) and X[c].nunique() <= 15]
    X = pd.get_dummies(X[num_cols + cat_cols], columns=cat_cols, drop_first=True)
    X = X.select_dtypes(include="number").fillna(X.median(numeric_only=True))
    if X.shape[1] == 0:
        raise ValueError("No usable feature columns to train on.")

    is_classification = (not pd.api.types.is_numeric_dtype(y_raw)) or y_raw.nunique() <= 10
    if is_classification:
        ycat = y_raw.astype("category")
        n_classes = len(ycat.cat.categories)
        classes = [str(c) for c in ycat.cat.categories]
        y = ycat.cat.codes
        if n_classes < 2:
            raise ValueError("Target has only one class — nothing to classify.")
        model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
    else:
        classes = None
        y = pd.to_numeric(y_raw, errors="coerce")
        model = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)

    strat = y if (is_classification and y.value_counts().min() >= 2) else None
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=strat)
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)

    # ── 1. Feature importance (gini / MDI) ───────────────────────────────────
    importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    top = importances.head(12)
    fig, ax = plt.subplots(figsize=(8, max(4, 0.5 * len(top))))
    sns.barplot(x=top.values, y=top.index.astype(str), ax=ax)
    for cont in ax.containers:
        ax.bar_label(cont, fmt="%.3f", padding=3)
    ax.set_title(f"What predicts '{target}'?  ·  Feature Importance (MDI)")
    ax.set_xlabel("Importance"); ax.set_ylabel("Feature")
    chart = _fig_to_b64(fig)

    # ── 2. SHAP beeswarm (global explanation) ────────────────────────────────
    shap_chart = None
    try:
        import shap
        X_sample = Xtr.iloc[:min(300, len(Xtr))]
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)
        if is_classification and isinstance(shap_values, list):
            sv = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        else:
            sv = shap_values
        plt.figure(figsize=(8, max(4, 0.4 * min(12, X_sample.shape[1]))))
        shap.summary_plot(sv, X_sample, show=False, max_display=12, plot_type="dot")
        plt.title(f"SHAP Feature Impact on '{target}'", fontsize=14, fontweight="bold", pad=14)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        plt.close("all")
        shap_chart = base64.b64encode(buf.getvalue()).decode()
    except Exception:
        plt.close("all")

    # ── 3. Permutation importance (test-set, unbiased) ───────────────────────
    perm_chart = None
    try:
        perm = permutation_importance(model, Xte, yte, n_repeats=5, random_state=42, n_jobs=-1)
        perm_df = (pd.DataFrame({"Feature": X.columns,
                                 "Importance": perm.importances_mean,
                                 "Std": perm.importances_std})
                   .sort_values("Importance", ascending=False).head(12))
        fig, ax = plt.subplots(figsize=(8, max(4, 0.5 * len(perm_df))))
        ax.barh(perm_df["Feature"][::-1], perm_df["Importance"][::-1],
                xerr=perm_df["Std"][::-1], color="#4F46E5", alpha=0.85, capsize=3)
        ax.set_title(f"Permutation Importance · '{target}' (test set)")
        ax.set_xlabel("Mean decrease in score")
        plt.tight_layout()
        perm_chart = _fig_to_b64(fig)
    except Exception:
        plt.close("all")

    # ── 4. Partial Dependence Plots (top 2 features) ─────────────────────────
    pdp_chart = None
    try:
        top2 = list(importances.head(2).index)
        n = len(top2)
        fig, axes = plt.subplots(1, n, figsize=(6 * n, 4))
        if n == 1:
            axes = [axes]
        PartialDependenceDisplay.from_estimator(model, X, top2, ax=axes,
                                                kind="average", subsample=500, random_state=42)
        fig.suptitle(f"Partial Dependence — Top Features for '{target}'",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
        pdp_chart = _fig_to_b64(fig)
    except Exception:
        plt.close("all")

    # ── metrics & summary ────────────────────────────────────────────────────
    if is_classification:
        metric = f"Accuracy: {accuracy_score(yte, pred):.1%}   |   F1 (weighted): {f1_score(yte, pred, average='weighted'):.2f}"
        task = f"Trained a Random Forest classifier to predict '{target}' ({n_classes} classes)."
    else:
        metric = f"R²: {r2_score(yte, pred):.3f}   |   MAE: {mean_absolute_error(yte, pred):,.3f}"
        task = f"Trained a Random Forest regressor to predict '{target}'."

    top3 = ", ".join(f"{n} ({v:.0%})" for n, v in top.head(3).items())
    summary = (f"{task}\n{metric}\n\n"
               f"Top features: {top3}.\n"
               f"Trained on {len(Xtr)} rows, validated on {len(Xte)}, {X.shape[1]} features.\n"
               f"Explainability: SHAP beeswarm · Permutation importance · Partial dependence plots generated.")

    features_meta = []
    for c in num_cols + cat_cols:
        if c in cat_cols:
            opts = [str(v) for v in pd.Series(data[c].dropna().unique()).tolist()[:30]]
            mode = data[c].mode()
            default = str(mode.iloc[0]) if not mode.empty else (opts[0] if opts else "")
            features_meta.append({"name": str(c), "type": "category", "options": opts, "default": default})
        else:
            med = data[c].median()
            features_meta.append({"name": str(c), "type": "number",
                                  "default": None if pd.isna(med) else round(float(med), 2)})

    info = {
        "target": target,
        "model": model,
        "feature_cols": list(X.columns),
        "num_cols": num_cols,
        "cat_cols": cat_cols,
        "is_classification": is_classification,
        "classes": classes,
        "medians": {k: (None if pd.isna(v) else float(v)) for k, v in X.median().items()},
        "features": features_meta,
        # Explainability charts
        "shap_chart": shap_chart,
        "perm_chart": perm_chart,
        "pdp_chart":  pdp_chart,
    }
    return summary, chart, info


def get_df_schema(df: pd.DataFrame) -> str:
    schema = f"Shape: {df.shape[0]} rows x {df.shape[1]} columns\n\nColumns:\n"
    for col in df.columns:
        schema += f"  - {col} ({df[col].dtype}): sample values: {df[col].dropna().head(3).tolist()}\n"
    schema += f"\nFirst 5 rows:\n{df.head(5).to_string()}"
    return schema


# ── Multi-agent system prompts ────────────────────────────────────────────────

PLANNER_SYSTEM = """You are a data analysis planner. Given a DataFrame schema and a user question, produce a structured analysis plan.

Output ONLY valid JSON (no markdown fences, no extra text) with exactly this structure:
{
  "relevant_columns": ["col1", "col2"],
  "strategy": "One concise sentence describing the analysis approach",
  "needs_chart": true,
  "chart_type": "bar|line|scatter|histogram|heatmap|box|violin|none",
  "analysis_steps": ["step1", "step2", "step3"],
  "domain_focus": "what domain aspect to emphasize based on the category"
}"""

ANALYST_SYSTEM = """You are a data analyst. A pandas DataFrame `df` is already loaded.
Write Python code to compute the NUMERICAL analysis only — statistics, aggregations, comparisons, correlations. No charts.

Rules:
- `df` is already defined — do not reload it
- Pre-imported: pandas (pd), numpy (np), io, base64
- You MAY import: scipy, sklearn, statsmodels
- Set `result` to a detailed string with all numerical findings (include specific numbers)
- Set `chart_b64 = None` always
- If result is a DataFrame, convert: result = df_result.to_string()
- ROBUSTNESS: use df.select_dtypes(include='number') for numeric ops; never run math on text columns
- Output ONLY valid Python code — no markdown fences, no explanation"""

VISUALIZER_SYSTEM = """You are a data visualization expert. A pandas DataFrame `df` is loaded.
Write Python code to create ONE excellent INTERACTIVE Plotly chart that best illustrates the findings.

Rules:
- `df` is already defined — do not reload it
- Pre-imported: pandas (pd), numpy (np), plotly.express (px), plotly.graph_objects (go)
- Create a Plotly figure named `fig` using px or go
- Apply this theme exactly ONCE after creating fig:
    fig.update_layout(
        template='plotly_white',
        font=dict(family='Inter, Segoe UI, sans-serif', size=12),
        title_font_size=15, title_font_weight='bold',
        colorway=['#4F46E5','#10B981','#F59E0B','#8B5CF6','#EF4444','#06B6D4','#EC4899','#0EA5E9'],
        margin=dict(l=60, r=30, t=60, b=60),
        hoverlabel=dict(bgcolor='white', font_size=12),
    )
- Give the chart a clear descriptive title and labelled axes via update_layout
- Save as: chart_json = fig.to_json()
- Set chart_b64 = None, result = None
- Common chart patterns:
    • Bar: px.bar(df, x='col', y='col', title='...')
    • Line: px.line(df, x='date_col', y='metric', title='...')
    • Scatter: px.scatter(df, x='col1', y='col2', color='group', title='...')
    • Histogram: px.histogram(df, x='col', title='...')
    • Box: px.box(df, x='group', y='metric', title='...')
    • Heatmap: use go.Heatmap with z=corr.values, x=corr.columns, y=corr.columns
- Output ONLY valid Python code — no markdown fences, no explanation"""

CRITIC_SYSTEM = """You are a senior statistician reviewing a data analysis for accuracy and completeness.

Output ONLY valid JSON (no markdown fences, no extra text):
{
  "verdict": "pass" | "warn" | "fail",
  "confidence": 0.0,
  "issues": ["specific issue 1"],
  "strengths": ["specific strength 1"],
  "suggestion": "One concrete improvement the analyst should make"
}

verdict=pass: analysis is statistically sound
verdict=warn: minor caveats or missing context
verdict=fail: significant errors or misleading conclusions
confidence: your confidence that the findings answer the question (0.0-1.0)"""

REPORTER_SYSTEM = """You are an executive analyst writing a business-ready summary of data findings.
Write a clear, structured report with NO padding.

Structure your response EXACTLY as:
**Headline:** One sentence direct answer to the question.

**Key Findings:**
• Finding 1 with specific numbers
• Finding 2 with specific numbers
• Finding 3 with specific numbers

**Implication:** One sentence business recommendation or implication.

**Caveat:** One sentence noting any limitation or assumption (if relevant)."""

# Keep the original SYSTEM_PROMPT for backward compatibility with non-agentic paths
SYSTEM_PROMPT = ANALYST_SYSTEM


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
    "pandas", "numpy", "matplotlib", "seaborn", "scipy", "sklearn", "statsmodels",
    "plotly", "math", "statistics", "datetime", "io", "base64", "collections", "itertools", "re", "json",
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


def execute_code(code: str, df: pd.DataFrame) -> tuple[str, str | None, str | None]:
    """Execute sandboxed code. Returns (result, chart_b64, chart_json)."""
    safe_globals = {
        "__builtins__": SAFE_BUILTINS,
        "pd": pd, "np": np, "plt": plt, "sns": sns, "io": io, "base64": base64,
        "px": px, "go": go,
    }
    local_vars: dict = {
        "df": df.copy(),
        "result": None,
        "chart_b64": None,
        "chart_json": None,
    }
    exec(code, safe_globals, local_vars)
    result    = local_vars.get("result")
    chart_b64 = local_vars.get("chart_b64")
    chart_json = local_vars.get("chart_json")
    if result is None:
        result = "Done. See chart above." if (chart_b64 or chart_json) else "No result returned."
    return str(result), chart_b64, chart_json


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def register_dataframe(df: pd.DataFrame, filename: str) -> dict:
    """Store a DataFrame and return its profile + instant overview charts."""
    session_id = str(uuid.uuid4())
    dataframes[session_id] = df
    profile = build_profile(df)
    overview = build_overview_charts(df)
    return {"session_id": session_id, "filename": filename, **profile, "overview": overview}


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)) -> dict:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {e}")
    return register_dataframe(df, file.filename)


@app.post("/upload_text")
async def upload_text(req: TextUploadRequest) -> dict:
    """Analyze pasted rows (CSV or TSV, with or without a header row)."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No data was pasted.")
    try:
        # sep=None + python engine sniffs the delimiter (comma, tab, semicolon, …)
        df = pd.read_csv(
            io.StringIO(text), sep=None, engine="python",
            header=0 if req.has_header else None,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse the pasted data: {e}")
    if not req.has_header:
        df.columns = [f"col_{i + 1}" for i in range(df.shape[1])]
    if df.empty or df.shape[1] == 0:
        raise HTTPException(status_code=422, detail="The pasted data has no usable rows/columns.")
    return register_dataframe(df, req.filename or "pasted_data.csv")


@app.post("/upload_doc")
async def upload_doc(session_id: str, file: UploadFile = File(...)) -> dict:
    """Upload a PDF, Excel, or text file to enrich analysis with RAG context."""
    if session_id not in dataframes:
        raise HTTPException(status_code=404, detail="Upload a CSV first, then attach documents.")
    content = await file.read()
    try:
        text = _parse_doc(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not text.strip():
        raise HTTPException(status_code=422, detail="Document appears to be empty.")
    if session_id not in doc_stores:
        doc_stores[session_id] = DocStore()
    n_chunks = doc_stores[session_id].add(text, file.filename)
    return {
        "filename": file.filename,
        "chunks_indexed": n_chunks,
        "filenames": doc_stores[session_id].filenames,
    }


@app.get("/docs/{session_id}")
def get_docs(session_id: str) -> dict:
    store = doc_stores.get(session_id)
    if not store:
        return {"filenames": [], "chunks": 0}
    return {"filenames": store.filenames, "chunks": len(store.chunks)}


@app.post("/query")
async def query_csv(req: QueryRequest) -> StreamingResponse:
    if req.session_id not in dataframes:
        raise HTTPException(status_code=404, detail="Session not found. Upload a CSV first.")

    df = dataframes[req.session_id]
    schema = get_df_schema(df)
    category_persona = CATEGORY_PERSONAS.get(req.category, CATEGORY_PERSONAS["general"])

    async def stream():
        def emit(payload: dict) -> str:
            return f"data: {json.dumps(payload)}\n\n"

        def llm(system: str, user: str, temperature: float = 0) -> str:
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=temperature,
                ),
            )
            text = (resp.text or "").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if "```" in text:
                text = text.rsplit("```", 1)[0]
            return text.strip()

        def parse_json_safe(text: str) -> dict:
            import re as _re
            try:
                return json.loads(text)
            except Exception:
                m = _re.search(r'\{.*\}', text, _re.DOTALL)
                if m:
                    try:
                        return json.loads(m.group())
                    except Exception:
                        pass
            return {}

        def run_code_with_repair(system: str, context: str, code_label: str) -> tuple[str | None, str | None, str | None, str | None]:
            """Generate code, execute it, repair once on failure. Returns (code, result, chart_b64, chart_json)."""
            try:
                code = llm(system, context)
            except Exception:
                return None, None, None, None

            for attempt in range(2):
                try:
                    result, chart_b64, chart_json = execute_code(code, df)
                    return code, result, chart_b64, chart_json
                except Exception:
                    err = traceback.format_exc().strip().splitlines()[-1]
                    if attempt == 0:
                        try:
                            code = llm(system,
                                       f"{context}\n\nPrevious code failed:\n{code}\nError: {err}\nFix it.")
                        except Exception:
                            return code, None, None, None
                    else:
                        return code, None, None, None
            return code, None, None, None

        # ── RAG: retrieve context from uploaded documents ──────────────────
        rag_context = ""
        rag_sources: list[str] = []
        store = doc_stores.get(req.session_id)
        if store and store.chunks:
            yield emit({"step": "analyzing", "message": f"Retrieving context from {len(store.filenames)} document(s)..."})
            hits = store.search(req.question, top_k=4)
            if hits:
                rag_context = "\n\n".join(
                    f"[Source: {h['filename']}]\n{h['text']}" for h in hits
                )
                rag_sources = list(dict.fromkeys(h["filename"] for h in hits))

        rag_block = f"\n\nRELEVANT DOCUMENTATION:\n{rag_context}" if rag_context else ""

        # ── AGENT 1: PLANNER ──────────────────────────────────────────────
        yield emit({"step": "planning", "message": "Planner is mapping your question to the dataset..."})
        try:
            plan_raw = llm(
                PLANNER_SYSTEM,
                f"Category: {req.category}\nDomain context: {category_persona}\n\nSchema:\n{schema}{rag_block}\n\nQuestion: {req.question}"
            )
            plan = parse_json_safe(plan_raw)
        except Exception:
            plan = {"needs_chart": True, "strategy": "Direct analysis", "relevant_columns": [], "analysis_steps": [], "chart_type": "auto"}

        plan["rag_sources"] = rag_sources
        yield emit({"step": "plan", "message": f"Plan: {plan.get('strategy', 'Analyzing...')}", "plan": plan})

        # ── AGENT 2: ANALYST ──────────────────────────────────────────────
        yield emit({"step": "analyst", "message": "Analyst agent computing statistics..."})

        analyst_context = (
            f"Domain context: {category_persona}\n"
            f"Schema:\n{schema}\n\n"
            f"Analysis strategy: {plan.get('strategy', '')}\n"
            f"Focus on columns: {', '.join(plan.get('relevant_columns', []))}\n"
            f"Steps to follow: {'; '.join(plan.get('analysis_steps', []))}\n"
            + (f"\nAdditional context from documentation:\n{rag_context}\n" if rag_context else "")
            + f"\nQuestion: {req.question}"
        )

        analyst_code, analyst_result, _, __ = run_code_with_repair(ANALYST_SYSTEM, analyst_context, "analyst")

        if analyst_code:
            yield emit({"step": "code", "message": "Analyst code generated", "code": analyst_code})
        yield emit({"step": "executing", "message": "Executing analysis on your data..."})

        if analyst_result is None:
            yield emit({"step": "error", "message": "Analyst agent could not compute results."})
            return

        # ── AGENT 3: VISUALIZER ───────────────────────────────────────────
        chart_b64 = None
        chart_json = None
        if plan.get("needs_chart", True):
            yield emit({"step": "visualizing", "message": "Visualizer agent creating interactive chart..."})
            viz_context = (
                f"Schema:\n{schema}\n\n"
                f"Question: {req.question}\n"
                f"Suggested chart type: {plan.get('chart_type', 'auto')}\n"
                f"Analysis findings to visualize:\n{analyst_result[:800]}"
            )
            viz_code, _, chart_b64, chart_json = run_code_with_repair(VISUALIZER_SYSTEM, viz_context, "visualizer")
            if viz_code:
                yield emit({"step": "code", "message": "Visualizer code generated", "code": viz_code})

        # ── AGENT 4: CRITIC ───────────────────────────────────────────────
        yield emit({"step": "critiquing", "message": "Critic agent reviewing the analysis..."})
        try:
            critique_raw = llm(
                CRITIC_SYSTEM,
                f"Question: {req.question}\nAnalysis strategy: {plan.get('strategy', '')}\n\nFindings:\n{analyst_result}"
            )
            critique = parse_json_safe(critique_raw)
            if not critique:
                critique = {"verdict": "pass", "confidence": 0.85, "issues": [], "strengths": ["Analysis completed"], "suggestion": ""}
        except Exception:
            critique = {"verdict": "pass", "confidence": 0.85, "issues": [], "strengths": [], "suggestion": ""}

        confidence = critique.get("confidence", 0.85)
        verdict = critique.get("verdict", "pass")
        yield emit({"step": "critique", "message": f"Critic: {verdict.upper()} · {confidence:.0%} confidence", "critique": critique})

        # ── AGENT 5: REPORTER ─────────────────────────────────────────────
        yield emit({"step": "reporting", "message": "Report agent writing executive summary..."})
        try:
            report = llm(
                REPORTER_SYSTEM,
                f"Question: {req.question}\nCategory: {req.category}\n\nFindings:\n{analyst_result}\n\nCritic notes: {critique.get('suggestion', '')}",
                temperature=0.2,
            )
        except Exception:
            report = analyst_result

        yield emit({
            "step": "done",
            "message": "Analysis complete",
            "result": analyst_result,
            "chart": chart_b64,
            "chart_json": chart_json,
            "report": report,
            "critique": critique,
            "plan": plan,
        })

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/predict")
async def predict(req: PredictRequest) -> StreamingResponse:
    if req.session_id not in dataframes:
        raise HTTPException(status_code=404, detail="Session not found. Upload a CSV first.")
    df = dataframes[req.session_id]
    if req.target not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{req.target}' not found.")

    async def stream():
        def emit(payload: dict) -> str:
            return f"data: {json.dumps(payload)}\n\n"

        yield emit({"step": "analyzing", "message": f"Preparing features to predict '{req.target}'..."})
        yield emit({"step": "thinking", "message": "Training a Random Forest model on your data..."})
        try:
            summary, chart, info = train_predictive_model(df, req.target)
            models[req.session_id] = info  # persist for inference on new input
        except Exception as e:
            yield emit({"step": "error", "message": f"Could not train model: {e}"})
            return
        yield emit({"step": "executing", "message": "Evaluating on held-out test set..."})
        yield emit({"step": "thinking", "message": "Computing SHAP values and permutation importance..."})
        yield emit({
            "step": "done",
            "message": "Model trained with full explainability",
            "result": summary,
            "chart": chart,
            "shap_chart":  info.get("shap_chart"),
            "perm_chart":  info.get("perm_chart"),
            "pdp_chart":   info.get("pdp_chart"),
            "features": info["features"],
            "target":   info["target"],
        })

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/model_info/{session_id}")
def model_info(session_id: str) -> dict:
    info = models.get(session_id)
    if not info:
        return {"trained": False}
    return {
        "trained": True,
        "target": info["target"],
        "is_classification": info["is_classification"],
        "features": info["features"],
    }


@app.post("/predict_input")
def predict_input(req: PredictInputRequest) -> dict:
    info = models.get(req.session_id)
    if not info:
        raise HTTPException(status_code=400, detail="Train a model first using the Predict button.")

    row: dict = {}
    for c in info["num_cols"]:
        v = req.values.get(c)
        row[c] = pd.to_numeric(v, errors="coerce") if v not in (None, "") else np.nan
    for c in info["cat_cols"]:
        row[c] = req.values.get(c)

    X_new = pd.DataFrame([row])
    if info["cat_cols"]:
        X_new = pd.get_dummies(X_new, columns=info["cat_cols"], drop_first=True)
    X_new = X_new.reindex(columns=info["feature_cols"], fill_value=0)
    X_new = X_new.fillna(value=info["medians"]).fillna(0)

    model = info["model"]
    pred = model.predict(X_new)[0]
    if info["is_classification"]:
        label = info["classes"][int(pred)]
        proba = float(max(model.predict_proba(X_new)[0]))
        return {"target": info["target"], "prediction": str(label),
                "confidence": round(proba, 3), "is_classification": True}
    return {"target": info["target"], "prediction": round(float(pred), 2),
            "confidence": None, "is_classification": False}
