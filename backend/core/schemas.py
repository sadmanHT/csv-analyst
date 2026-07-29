"""
Pydantic Schemas for Request/Response Models, Data Contracts, and Execution Evidence
"""

from typing import Any, Literal
from pydantic import BaseModel, Field
from backend.core.config import APP_BUILD_ID


class ExecutionBudget(BaseModel):
    """Budget limits assigned per query route type."""
    route: str
    max_llm_calls: int = 1
    max_execution_time_s: float = 10.0
    timeout_s: float = 12.0
    allow_chart: bool = True
    allow_code_repair: bool = True


ROUTE_BUDGETS: dict[str, ExecutionBudget] = {
    "fast_path": ExecutionBudget(route="fast_path", max_llm_calls=1, max_execution_time_s=5.0, timeout_s=8.0, allow_chart=False, allow_code_repair=False),
    "standard": ExecutionBudget(route="standard", max_llm_calls=3, max_execution_time_s=15.0, timeout_s=20.0, allow_chart=True, allow_code_repair=True),
    "complex": ExecutionBudget(route="complex", max_llm_calls=5, max_execution_time_s=30.0, timeout_s=35.0, allow_chart=True, allow_code_repair=True),
    "fallback": ExecutionBudget(route="fallback", max_llm_calls=2, max_execution_time_s=10.0, timeout_s=15.0, allow_chart=False, allow_code_repair=False),
}


class QueryRequest(BaseModel):
    session_id: str
    question: str
    category: str = "general"
    request_id: str | None = None


class ExecutionStepResponse(BaseModel):
    id: str
    label: str
    status: Literal["pending", "running", "complete", "warning", "failed", "skipped"] = "complete"
    detail: str | None = None
    duration_ms: int | None = None


class AnswerResponse(BaseModel):
    type: str
    title: str | None = None
    summary: str | None = None
    explanation: str | None = None
    text: str | None = None
    data: Any | None = None
    findings: list[dict[str, Any]] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    next_action: str | None = None


class QueryResponse(BaseModel):
    request_id: str
    status: Literal["running", "partial", "complete", "failed", "cancelled"] = "complete"
    answer: AnswerResponse | None = None
    execution_steps: list[ExecutionStepResponse] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    effective_lens: str = "general"
    generated_code: str | None = None
    error: str | None = None
    debug_build_id: str = APP_BUILD_ID


class AnalysisEvidence(BaseModel):
    intent: str
    dataset_name: str | None = None
    facts: dict[str, Any] = Field(default_factory=dict)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unavailable_information: list[str] = Field(default_factory=list)
    generated_code: str | None = None


class GeneratedAnswer(BaseModel):
    title: str | None = None
    summary: str
    explanation: str | None = None
    findings: list[dict[str, Any]] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    next_action: str | None = None


# ── Schema-aware Analytics Plan Models ──────────────────────────────────────

class PlanDimension(BaseModel):
    column: str
    role: Literal["group_by", "x_axis", "category"] = "group_by"


class PlanMeasure(BaseModel):
    column: str | None = None
    operation: Literal["count", "count_distinct", "sum", "mean", "median", "min", "max", "percentage"]
    label: str


class PlanFilter(BaseModel):
    column: str
    operator: str   # "==", "!=", ">", "<", ">=", "<=", "contains", "in"
    value: Any


class PlanChart(BaseModel):
    type: Literal["bar", "line", "pie", "scatter", "histogram", "box"]
    x: str | None = None
    y: str | None = None
    category: str | None = None
    value: str | None = None


class AnalysisPlan(BaseModel):
    intent: Literal["lookup", "aggregation", "comparison", "visualization", "data_quality", "modeling", "forecasting"] = "aggregation"
    dimensions: list[PlanDimension] = Field(default_factory=list)
    measures: list[PlanMeasure] = Field(default_factory=list)
    filters: list[PlanFilter] = Field(default_factory=list)
    chart: PlanChart | None = None
    title: str | None = None
    confidence: float = 0.8
    ambiguity: list[str] = Field(default_factory=list)
    reasoning_summary: str = ""


class ResolvedAnalysisPlan(AnalysisPlan):
    """Immutable after semantic validation. All downstream stages use this validated plan."""
    validated: bool = True
    validation_warnings: list[str] = Field(default_factory=list)
    resolved_dimension_col: str | None = None
    resolved_measure_col: str | None = None
    resolved_operation: str | None = None
    resolved_chart_type: str | None = None


# ── Additional Request Models ────────────────────────────────────────────────

class StoryRequest(BaseModel):
    session_id: str
    category: str = "general"


class InvestigationRequest(BaseModel):
    session_id: str
    goal: str = "Investigate the strongest decision opportunity in this dataset."
    category: str = "general"


class PredictRequest(BaseModel):
    session_id: str
    target: str
    category: str = "general"


class TextUploadRequest(BaseModel):
    text: str
    filename: str = "pasted_data.csv"
    has_header: bool = True


class InferJoinRequest(BaseModel):
    session_id_1: str
    session_id_2: str


class JoinRequest(BaseModel):
    session_id_1: str
    session_id_2: str
    join_key_1: str
    join_key_2: str
    how: str = "inner"


class ForecastRequest(BaseModel):
    session_id: str
    date_column: str
    target_column: str
    periods: int = 12
    freq: str = "auto"


class UrlImportRequest(BaseModel):
    url: str
    filename: str = "imported_dataset.csv"


class CompareRequest(BaseModel):
    session_id_1: str
    session_id_2: str


class PredictInputRequest(BaseModel):
    session_id: str
    values: dict


class ScenarioRequest(BaseModel):
    session_id: str
    baseline: dict = Field(default_factory=dict)
    changes: dict = Field(default_factory=dict)
    category: str = "general"


class ScenarioParseRequest(BaseModel):
    session_id: str
    prompt: str
    category: str = "general"


class CleanRequest(BaseModel):
    actions: list[str] | None = None


class ValidateRowsRequest(BaseModel):
    rows: list[dict]


class QualityPayload(BaseModel):
    """Canonical data quality payload sent by backend to frontend."""
    health_score: int
    readiness_score: int
    health_label: str
    readiness_label: str
    missing_pct: float
    duplicate_rows: int
    outlier_cols_count: int
    total_outliers: int
    issues: list[dict[str, Any]] = Field(default_factory=list)
