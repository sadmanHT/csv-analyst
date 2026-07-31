"""
Pydantic Schemas for Request/Response Models, Data Contracts, and Execution Evidence
"""

from typing import Any, Literal
import re
from pydantic import BaseModel, Field, model_validator
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
    "dataset_purpose": ExecutionBudget(route="dataset_purpose", max_llm_calls=1, max_execution_time_s=12.0, timeout_s=12.0, allow_chart=False, allow_code_repair=False),
    "standard": ExecutionBudget(route="standard", max_llm_calls=3, max_execution_time_s=15.0, timeout_s=20.0, allow_chart=True, allow_code_repair=True),
    "complex": ExecutionBudget(route="complex", max_llm_calls=5, max_execution_time_s=30.0, timeout_s=35.0, allow_chart=True, allow_code_repair=True),
    "fallback": ExecutionBudget(route="fallback", max_llm_calls=2, max_execution_time_s=10.0, timeout_s=15.0, allow_chart=False, allow_code_repair=False),
    "direct": ExecutionBudget(route="direct", max_llm_calls=1, max_execution_time_s=15.0, timeout_s=12.0, allow_chart=False, allow_code_repair=False),
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


class GeneratedFinding(BaseModel):
    label: str
    detail: str


class DirectAnswer(BaseModel):
    summary: str
    next_action: str = ""

    @model_validator(mode="after")
    def validate_direct_answer(self) -> "DirectAnswer":
        if not self.summary.strip():
            raise ValueError("Summary must be non-empty.")
        if len(self.summary.split()) > 70:
            raise ValueError("Summary must be 70 words or fewer.")
        if len(self.next_action.split()) > 25:
            raise ValueError("Next action must be 25 words or fewer.")
        html_pattern = re.compile(r"<[^>]+>")
        if html_pattern.search(self.summary) or html_pattern.search(self.next_action):
            raise ValueError("HTML is not allowed in generated text.")
        if "```" in self.summary or "```" in self.next_action:
            raise ValueError("Markdown fences are not allowed in generated text.")
        return self


class GeneratedAnswer(BaseModel):
    title: str = ""
    summary: str
    explanation: str = ""
    findings: list[GeneratedFinding] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    next_action: str = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_bounded_fields(cls, data: Any) -> Any:
        """Apply safe normalization before strict content validation."""
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        for key in ("title", "summary", "explanation", "next_action"):
            value = normalized.get(key, "")
            normalized[key] = re.sub(r"\s+", " ", str(value or "")).strip()

        findings = normalized.get("findings") or []
        if isinstance(findings, list):
            normalized["findings"] = findings[:4]
        else:
            normalized["findings"] = []

        caveats = normalized.get("caveats") or []
        if isinstance(caveats, list):
            normalized["caveats"] = [str(item) for item in caveats[:3]]
        else:
            normalized["caveats"] = []

        return normalized

    @model_validator(mode="after")
    def validate_content_quality(self) -> "GeneratedAnswer":
        if len(self.title.split()) > 8:
            raise ValueError("Title must be 8 words or fewer.")
        if not self.summary.strip():
            raise ValueError("Summary must be non-empty.")
        if len(self.summary.split()) > 80:
            raise ValueError("Summary must be 80 words or fewer.")
        if len(self.explanation.split()) > 120:
            raise ValueError("Explanation must be 120 words or fewer.")
            
        if len(self.findings) > 4:
            raise ValueError("Maximum four findings allowed.")
        for f in self.findings:
            if len(f.detail.split()) > 30:
                raise ValueError("Finding detail must be 30 words or fewer.")
                
        if len(self.caveats) > 3:
            raise ValueError("Maximum three caveats allowed.")
            
        html_pattern = re.compile(r"<[^>]+>")
        if html_pattern.search(self.summary) or html_pattern.search(self.explanation):
            raise ValueError("HTML is not allowed in generated text.")
            
        if "```" in self.summary or "```" in self.explanation:
            raise ValueError("Markdown fences are not allowed in generated text.")
            
        def has_repetition(text: str) -> bool:
            words = text.split()
            if len(words) < 20: return False
            seen = set()
            for i in range(len(words) - 5):
                phrase = " ".join(words[i:i+5]).lower()
                if phrase in seen:
                    return True
                seen.add(phrase)
            return False
            
        if has_repetition(self.summary) or has_repetition(self.explanation):
            raise ValueError("Excessive phrase repetition detected.")
            
        return self


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

    @model_validator(mode="before")
    @classmethod
    def unwrap_single_element_list(cls, data: Any) -> Any:
        if isinstance(data, list):
            if len(data) == 1 and isinstance(data[0], dict):
                return data[0]
            raise ValueError("AnalysisPlan must be a single object, not a multi-element list.")
        return data


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
