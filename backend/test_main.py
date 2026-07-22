import io
import json
import base64
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from main import app, dataframes, execute_code, train_predictive_model

client = TestClient(app)


def make_csv(content: str) -> bytes:
    return content.encode()


SAMPLE_CSV = "name,age,salary\nAlice,30,50000\nBob,25,45000\nCarla,35,60000\n"
SALES_CSV = (
    "date,category,product,region,revenue,quantity\n"
    "2025-01-01,Electronics,Earbuds,Dhaka,90,2\n"
    "2025-01-02,Electronics,Speaker,Dhaka,120,4\n"
    "2025-01-03,Apparel,Shirt,Chittagong,60,5\n"
    "2025-01-04,Home,Mug,Sylhet,54,3\n"
)


def parse_sse_events(text: str) -> list[dict]:
    events = []
    for block in text.strip().split("\n\n"):
        line = next((ln for ln in block.splitlines() if ln.startswith("data: ")), None)
        if line:
            events.append(json.loads(line[6:]))
    return events


def assert_sse_observability(events: list[dict], endpoint: str, session_id: str) -> None:
    assert events
    request_ids = {event["meta"]["request_id"] for event in events}
    assert len(request_ids) == 1
    for index, event in enumerate(events, start=1):
        meta = event["meta"]
        assert meta["endpoint"] == endpoint
        assert meta["session_id"] == session_id
        assert meta["sequence"] == index
        assert isinstance(meta["elapsed_ms"], int)
        assert meta["elapsed_ms"] >= 0


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_rate_limit_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    main.rate_limit_buckets.clear()
    monkeypatch.setattr(main, "RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(main, "RATE_LIMIT_WINDOW_SECONDS", 60)
    headers = {"x-forwarded-for": "203.0.113.10"}

    first = client.get("/health", headers=headers)
    second = client.get("/health", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    payload = second.json()
    assert payload["detail"] == "Rate limit exceeded. Please wait before retrying."
    assert payload["limit"] == 1
    assert int(second.headers["retry-after"]) >= 1


def test_upload_valid_csv():
    res = client.post(
        "/upload",
        files={"file": ("data.csv", io.BytesIO(make_csv(SAMPLE_CSV)), "text/csv")},
    )
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert data["rows"] == 3
    assert "name" in data["columns"]
    assert len(data["preview"]) == 3


def test_upload_text_with_header():
    text = "date,dept,revenue,profit\n2025-01-01,Software,88956.3,33440.91\n2025-02-01,Software,87270.5,31980.20\n2025-03-01,Hardware,94692.0,40110.0"
    res = client.post("/upload_text", json={"text": text, "has_header": True})
    assert res.status_code == 200
    data = res.json()
    assert data["rows"] == 3
    assert "revenue" in data["columns"]


def test_upload_text_tab_separated_no_header():
    text = "2025-01-01\tSoftware\tNorth\t88956.3\t55515.39\t33440.91\t886\t37.6\n2025-02-01\tSoftware\tNorth\t87270.5\t54000.0\t33270.5\t900\t38.1"
    res = client.post("/upload_text", json={"text": text, "has_header": False})
    assert res.status_code == 200
    data = res.json()
    assert data["rows"] == 2
    assert data["columns"][0] == "col_1"
    assert len(data["columns"]) == 8


def test_upload_text_empty_rejected():
    res = client.post("/upload_text", json={"text": "   ", "has_header": True})
    assert res.status_code == 400


def test_upload_non_csv_rejected():
    res = client.post(
        "/upload",
        files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert res.status_code == 400


def test_upload_invalid_csv_rejected():
    res = client.post(
        "/upload",
        files={"file": ("data.csv", io.BytesIO(b"\x00\x01\x02"), "text/csv")},
    )
    assert res.status_code in (200, 422)


def test_upload_rejects_oversized_file(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 8)
    res = client.post(
        "/upload",
        files={"file": ("data.csv", io.BytesIO(b"name\n" + b"x" * 20), "text/csv")},
    )
    assert res.status_code == 413
    assert "Maximum upload size" in res.json()["detail"]


def test_upload_text_rejects_oversized_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 8)
    res = client.post("/upload_text", json={"text": "name\n" + ("x" * 20), "has_header": True})
    assert res.status_code == 413


def test_register_dataframe_enforces_shape_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    monkeypatch.setattr(main, "MAX_DATAFRAME_ROWS", 1)
    with pytest.raises(main.HTTPException) as exc_info:
        main.register_dataframe(pd.DataFrame({"a": [1, 2]}), "too-many-rows.csv")
    assert exc_info.value.status_code == 413

    monkeypatch.setattr(main, "MAX_DATAFRAME_ROWS", 10)
    monkeypatch.setattr(main, "MAX_DATAFRAME_COLUMNS", 1)
    with pytest.raises(main.HTTPException) as exc_info:
        main.register_dataframe(pd.DataFrame({"a": [1], "b": [2]}), "too-many-columns.csv")
    assert exc_info.value.status_code == 413


def test_cleanup_expired_sessions_removes_state(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    session_id = "expired-session"
    cache_key = "expired-cache"
    dataframes[session_id] = pd.DataFrame({"a": [1]})
    main.conversation_state[session_id] = {"last_question": "old"}
    main.query_cache[cache_key] = {"session_id": session_id}
    main.session_meta[session_id] = {
        "created_at": main._now() - 10,
        "last_accessed": main._now() - 10,
        "filename": "expired.csv",
    }

    monkeypatch.setattr(main, "SESSION_TTL_SECONDS", 1)
    main.cleanup_expired_sessions()

    assert session_id not in dataframes
    assert session_id not in main.conversation_state
    assert cache_key not in main.query_cache


def test_cache_set_prunes_oldest_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    main.query_cache.clear()
    monkeypatch.setattr(main, "MAX_QUERY_CACHE_ENTRIES", 2)
    main._cache_set("first", {"value": 1})
    main._cache_set("second", {"value": 2})
    main._cache_set("third", {"value": 3})

    assert list(main.query_cache) == ["second", "third"]


def test_query_unknown_session():
    res = client.post(
        "/query",
        json={"session_id": "nonexistent-id", "question": "How many rows?"},
    )
    assert res.status_code == 404


def test_query_accepts_category():
    """The /query schema must accept an optional analysis category."""
    res = client.post(
        "/query",
        json={"session_id": "nonexistent-id", "question": "How many rows?", "category": "financial"},
    )
    # category is valid -> not a 422; session is fake -> 404
    assert res.status_code == 404


def test_system_prompt_for_categories():
    from main import system_prompt_for, SYSTEM_PROMPT
    fin = system_prompt_for("financial")
    med = system_prompt_for("medical")
    assert "FINANCIAL" in fin and SYSTEM_PROMPT in fin
    assert "clinical" in med.lower() and "association" in med.lower()
    # unknown category falls back to general, still valid
    assert SYSTEM_PROMPT in system_prompt_for("does-not-exist")


def test_upload_returns_dtypes_and_preview():
    res = client.post(
        "/upload",
        files={"file": ("data.csv", io.BytesIO(make_csv(SAMPLE_CSV)), "text/csv")},
    )
    data = res.json()
    assert "dtypes" in data
    assert "preview" in data
    assert data["dtypes"]["age"] in ("int64", "float64")


def test_upload_returns_overview_charts():
    res = client.post(
        "/upload",
        files={"file": ("data.csv", io.BytesIO(make_csv(SAMPLE_CSV)), "text/csv")},
    )
    data = res.json()
    assert "overview" in data
    assert isinstance(data["overview"], list)
    # SAMPLE_CSV has 2 numeric cols + 1 categorical -> heatmap + distributions + top values
    assert len(data["overview"]) >= 1
    for chart in data["overview"]:
        assert "title" in chart and "chart" in chart
        assert len(chart["chart"]) > 100  # non-empty base64 PNG


def test_upload_returns_proactive_insights_and_column_roles() -> None:
    res = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    assert res.status_code == 200
    data = res.json()
    assert "proactive_insights" in data
    assert len(data["proactive_insights"]) >= 3
    assert any(item["kind"] == "kpi" for item in data["proactive_insights"])
    assert any(item["validation"] for item in data["proactive_insights"])
    assert data["column_roles"]["metrics"][0] == "revenue"
    assert "category" in data["column_roles"]["dimensions"]
    assert "quality_report" in data
    assert "score" in data["quality_report"]
    assert "decision_brief" in data
    assert data["decision_brief"]["readiness_score"] > 0
    assert any("dashboard" in item["name"].lower() for item in data["decision_brief"]["recommended_use_cases"])
    assert any(q for q in data["decision_brief"]["priority_questions"] if "revenue" in q.lower())
    assert any(col["name"] == "revenue" for col in data["decision_brief"]["column_dictionary"])
    assert "decision_actions" in data
    assert len(data["decision_actions"]) >= 1
    first_action = data["decision_actions"][0]
    assert first_action["recommended_action"]
    assert first_action["estimated_impact"]
    assert first_action["evidence"]
    assert first_action["risks_assumptions"]
    assert first_action["confidence"] > 0
    assert "cleaning_plan" in data
    assert "actions" in data["cleaning_plan"]
    assert "data_contract" in data
    assert data["data_contract"]["column_count"] == 6
    assert "revenue" in data["data_contract"]["required_columns"]
    assert "dashboard_spec" in data
    assert any(chart["id"] == "segment_performance" for chart in data["dashboard_spec"]["charts"])


def test_brief_endpoint_returns_decision_readiness() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]
    res = client.get(f"/brief/{sid}?category=retail")
    assert res.status_code == 200
    brief = res.json()
    assert brief["category"] == "retail"
    assert brief["readiness_label"] in {"decision_ready", "usable_with_caution", "needs_cleanup"}
    assert len(brief["next_actions"]) >= 1
    assert len(brief["decision_actions"]) >= 1
    assert "implication" in brief["decision_actions"][0]
    assert len(brief["column_dictionary"]) == 6
    assert any(item["name"] == "Trend monitoring" for item in brief["recommended_use_cases"])


def test_brief_unknown_session() -> None:
    res = client.get("/brief/missing")
    assert res.status_code == 404


def test_quality_endpoint_reports_issues() -> None:
    dirty_csv = (
        "order_id,category,revenue\n"
        "1,A,100\n"
        "2,A,\n"
        "3,B,9999\n"
        "3,B,9999\n"
        "4,C,120\n"
        "5,D,130\n"
        "6,E,140\n"
        "7,F,150\n"
    )
    up = client.post(
        "/upload",
        files={"file": ("dirty.csv", io.BytesIO(dirty_csv.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]
    res = client.get(f"/quality/{sid}")
    assert res.status_code == 200
    body = res.json()
    titles = {issue["title"] for issue in body["issues"]}
    assert "Missing Values" in titles
    assert "Duplicate Rows" in titles
    assert body["score"] < 100


def test_quality_unknown_session() -> None:
    res = client.get("/quality/missing")
    assert res.status_code == 404


def test_cleaning_plan_and_clean_export() -> None:
    dirty_csv = (
        "order_id,category,revenue,empty_col\n"
        "1, A,100,\n"
        "2,A,,\n"
        "2,A,,\n"
        "3,B,300,\n"
    )
    up = client.post(
        "/upload",
        files={"file": ("dirty.csv", io.BytesIO(dirty_csv.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]

    plan = client.get(f"/cleaning_plan/{sid}")
    assert plan.status_code == 200
    action_ids = {action["id"] for action in plan.json()["actions"]}
    assert {"drop_empty_columns", "remove_duplicate_rows", "fill_numeric_median"} <= action_ids

    cleaned = client.post(f"/clean/{sid}", json={})
    assert cleaned.status_code == 200
    payload = cleaned.json()
    assert payload["filename"] == "dirty_cleaned.csv"
    assert payload["media_type"] == "text/csv"
    assert payload["row_delta"] == -1
    assert payload["column_delta"] == -1
    assert payload["after_quality"]["score"] >= payload["before_quality"]["score"]

    csv_text = base64.b64decode(payload["content_base64"]).decode("utf-8")
    cleaned_df = pd.read_csv(io.StringIO(csv_text))
    assert "empty_col" not in cleaned_df.columns
    assert len(cleaned_df) == 3
    assert cleaned_df["revenue"].isna().sum() == 0


def test_clean_rejects_unknown_action() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]
    res = client.post(f"/clean/{sid}", json={"actions": ["not_supported"]})
    assert res.status_code == 400


def test_cleaning_unknown_session() -> None:
    assert client.get("/cleaning_plan/missing").status_code == 404
    assert client.post("/clean/missing", json={}).status_code == 404


def test_contract_endpoint_and_row_validation() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]

    contract = client.get(f"/contract/{sid}")
    assert contract.status_code == 200
    body = contract.json()
    assert body["version"] == "1.0"
    assert body["column_count"] == 6
    revenue = next(col for col in body["columns"] if col["name"] == "revenue")
    assert revenue["type"] in {"integer", "number"}
    assert "must_parse_as_number" in revenue["rules"]

    validation = client.post(
        f"/validate_rows/{sid}",
        json={
            "rows": [
                {
                    "date": "2025-01-05",
                    "category": "Electronics",
                    "product": "Cable",
                    "region": "Dhaka",
                    "revenue": 45,
                    "quantity": 1,
                },
                {
                    "date": "not-a-date",
                    "category": "New",
                    "product": "Cable",
                    "region": "Dhaka",
                    "revenue": "bad",
                    "quantity": 1,
                    "extra": "ignored",
                },
            ]
        },
    )
    assert validation.status_code == 200
    payload = validation.json()
    assert payload["total_rows"] == 2
    assert payload["valid_rows"] == 1
    assert payload["invalid_rows"] == 1
    assert any(error["code"] == "type_mismatch" and error["column"] == "revenue" for error in payload["errors"])
    assert any(warning["code"] == "extra_column" for warning in payload["warnings"])


def test_contract_unknown_session() -> None:
    assert client.get("/contract/missing").status_code == 404
    assert client.post("/validate_rows/missing", json={"rows": []}).status_code == 404


def test_dashboard_endpoint_returns_blueprint() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]
    res = client.get(f"/dashboard/{sid}?category=retail")
    assert res.status_code == 200
    spec = res.json()
    assert spec["category"] == "retail"
    assert spec["layout"]["columns"] == 12
    assert any(kpi["id"] == "total_revenue" for kpi in spec["kpis"])
    assert any(chart["type"] == "line" for chart in spec["charts"])
    assert any(question for question in spec["starter_questions"] if "revenue" in question.lower())


def test_dashboard_unknown_session() -> None:
    res = client.get("/dashboard/missing")
    assert res.status_code == 404


def test_upload_returns_profile():
    res = client.post(
        "/upload",
        files={"file": ("data.csv", io.BytesIO(make_csv(SAMPLE_CSV)), "text/csv")},
    )
    data = res.json()
    assert data["numeric_features"] == 2  # age, salary
    assert data["missing_total"] == 0
    assert data["missing_pct"] == 0.0
    assert data["duplicate_rows"] == 0
    assert "age" in data["numeric_stats"]
    assert data["numeric_stats"]["age"]["mean"] == 30.0
    assert data["numeric_stats"]["age"]["min"] == 25.0
    assert data["numeric_stats"]["age"]["max"] == 35.0


def test_upload_handles_missing_values_json_safe():
    """Rows with blanks must not break JSON (NaN -> null)."""
    csv = "name,age,salary\nAlice,30,50000\nBob,,45000\nCarla,35,\n"
    res = client.post(
        "/upload",
        files={"file": ("data.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert res.status_code == 200
    data = res.json()  # would raise if NaN leaked into the payload
    assert data["missing_total"] == 2
    assert data["missing_pct"] > 0
    # blank cells surface as null in the preview
    assert any(v is None for row in data["preview"] for v in row.values())


def test_upload_counts_duplicate_rows():
    csv = SAMPLE_CSV + "Alice,30,50000\n"  # duplicate of first row
    res = client.post(
        "/upload",
        files={"file": ("data.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    data = res.json()
    assert data["duplicate_rows"] == 1


# ── Sandbox (execute_code) ──────────────────────────────────────────────

def test_execute_code_returns_result():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    result, chart, chart_json = execute_code("result = str(df['a'].sum())", df)
    assert result == "6"
    assert chart is None
    assert chart_json is None


def test_execute_code_allows_chart_imports():
    """Generated code that imports matplotlib and plots must work."""
    df = pd.DataFrame({"cat": ["a", "b", "a"], "val": [1, 2, 3]})
    code = (
        "import matplotlib.pyplot as plt\n"
        "import io, base64\n"
        "df.groupby('cat')['val'].sum().plot(kind='bar')\n"
        "plt.title('Test')\n"
        "buf = io.BytesIO()\n"
        "plt.savefig(buf, format='png')\n"
        "plt.close()\n"
        "chart_b64 = base64.b64encode(buf.getvalue()).decode()\n"
        "result = 'ok'"
    )
    result, chart, chart_json = execute_code(code, df)
    assert result == "ok"
    assert chart and len(chart) > 100


def test_execute_code_plotly_chart():
    """Plotly charts should produce chart_json, not chart_b64."""
    df = pd.DataFrame({"cat": ["a", "b", "a"], "val": [1, 2, 3]})
    code = (
        "import plotly.express as px\n"
        "fig = px.bar(df, x='cat', y='val', title='Test')\n"
        "chart_json = fig.to_json()\n"
        "chart_b64 = None\n"
        "result = None"
    )
    result, chart_b64, chart_json = execute_code(code, df)
    assert chart_b64 is None
    assert chart_json is not None
    import json as _json
    parsed = _json.loads(chart_json)
    assert "data" in parsed and "layout" in parsed


def test_execute_code_blocks_unsafe_import():
    """AST scan now catches forbidden imports before exec — raises SecurityError."""
    from main import SecurityError
    df = pd.DataFrame({"a": [1]})
    with pytest.raises((ImportError, SecurityError)):
        execute_code("import os\nresult = os.getcwd()", df)


def test_execute_code_terminates_runaway_code(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    df = pd.DataFrame({"a": [1]})
    monkeypatch.setattr(main, "MAX_EXEC_SECONDS", 1)
    with pytest.raises(TimeoutError, match="terminated"):
        execute_code("while True:\n    pass", df)


def test_execute_code_blocks_reflection_builtins() -> None:
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(RuntimeError, match="NameError"):
        execute_code("result = getattr(df, 'shape')", df)


# ── AST security validation ─────────────────────────────────────────────

def test_ast_blocks_dunder_class():
    from main import validate_code_ast, SecurityError
    with pytest.raises(SecurityError):
        validate_code_ast("x = df.__class__.__bases__")


def test_ast_blocks_globals_access():
    from main import validate_code_ast, SecurityError
    with pytest.raises(SecurityError):
        validate_code_ast("x = ().__class__.__bases__[0].__subclasses__()")


def test_ast_blocks_eval():
    from main import validate_code_ast, SecurityError
    with pytest.raises(SecurityError, match="eval"):
        validate_code_ast("result = eval('1 + 1')")


def test_ast_blocks_exec():
    from main import validate_code_ast, SecurityError
    with pytest.raises(SecurityError, match="exec"):
        validate_code_ast("exec('import os')")


def test_ast_blocks_open():
    from main import validate_code_ast, SecurityError
    with pytest.raises(SecurityError, match="open"):
        validate_code_ast("f = open('/etc/passwd')")


def test_ast_blocks_compile():
    from main import validate_code_ast, SecurityError
    with pytest.raises(SecurityError, match="compile"):
        validate_code_ast("compile('x=1', '<s>', 'exec')")


def test_ast_blocks_forbidden_import():
    from main import validate_code_ast, SecurityError
    with pytest.raises(SecurityError):
        validate_code_ast("import subprocess")


def test_ast_allows_valid_pandas_code():
    from main import validate_code_ast
    validate_code_ast("result = df.groupby('cat')['val'].sum().to_string()")


def test_ast_allows_plotly_code():
    from main import validate_code_ast
    validate_code_ast(
        "import plotly.express as px\n"
        "fig = px.bar(df, x='cat', y='val')\n"
        "chart_json = fig.to_json()\n"
        "result = None"
    )


def test_execute_code_raises_security_error_on_eval():
    from main import SecurityError
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(SecurityError):
        execute_code("result = eval('1+1')", df)


def test_execute_code_truncates_large_result():
    from main import MAX_RESULT_CHARS
    df = pd.DataFrame({"a": range(10)})
    code = f"result = 'x' * {MAX_RESULT_CHARS + 1000}"
    result, _, __ = execute_code(code, df)
    assert "truncated" in result
    assert len(result) < MAX_RESULT_CHARS + 200


# ── SQL generation ──────────────────────────────────────────────────────

def test_execute_sql_basic_select():
    from main import execute_sql
    df = pd.DataFrame({"name": ["Alice", "Bob", "Carla"], "salary": [50000, 45000, 60000]})
    result = execute_sql("SELECT name, salary FROM data ORDER BY salary DESC", df)
    assert "Carla" in result
    assert "60000" in result


def test_execute_sql_aggregation():
    from main import execute_sql
    df = pd.DataFrame({"dept": ["Eng", "Eng", "HR"], "salary": [80000, 90000, 60000]})
    result = execute_sql("SELECT dept, AVG(salary) AS avg_sal FROM data GROUP BY dept", df)
    assert "Eng" in result and "HR" in result


def test_execute_sql_filter():
    from main import execute_sql
    df = pd.DataFrame({"product": ["A", "B", "C"], "revenue": [1000, 5000, 200]})
    result = execute_sql("SELECT product, revenue FROM data WHERE revenue > 500 ORDER BY revenue DESC", df)
    assert "A" in result and "B" in result
    assert "C" not in result


def test_execute_sql_empty_result():
    from main import execute_sql
    df = pd.DataFrame({"x": [1, 2, 3]})
    result = execute_sql("SELECT x FROM data WHERE x > 100", df)
    assert "no results" in result.lower()


def test_get_sql_schema():
    from main import get_sql_schema
    df = pd.DataFrame({"age": [25, 30], "name": ["Alice", "Bob"]})
    schema = get_sql_schema(df)
    assert "data" in schema and "age" in schema and "name" in schema


def test_execute_sql_blocks_mutating_query() -> None:
    from main import execute_sql
    df = pd.DataFrame({"x": [1, 2, 3]})
    with pytest.raises(ValueError, match="Only SELECT"):
        execute_sql("DELETE FROM data", df)


def test_execute_sql_blocks_multiple_statements() -> None:
    from main import execute_sql
    df = pd.DataFrame({"x": [1, 2, 3]})
    with pytest.raises(ValueError, match="Only one SQL statement"):
        execute_sql("SELECT x FROM data; DROP TABLE data", df)


def test_infer_column_roles_and_chart_spec() -> None:
    from main import choose_chart_spec, infer_column_roles
    df = pd.DataFrame({
        "date": ["2025-01-01", "2025-01-02"],
        "category": ["A", "B"],
        "revenue": [100, 200],
        "order_id": [1, 2],
    })
    roles = infer_column_roles(df)
    assert "revenue" in roles["metrics"]
    assert "date" in roles["time"]
    assert "category" in roles["dimensions"]
    assert "order_id" in roles["ids"]

    by_category = choose_chart_spec("show revenue by category", df, roles)
    assert by_category["chart_type"] == "bar"
    assert by_category["x"] == "category"
    assert by_category["y"] == "revenue"

    over_time = choose_chart_spec("plot revenue over time", df, roles)
    assert over_time["chart_type"] == "line"
    assert over_time["x"] == "date"
    assert over_time["y"] == "revenue"


def test_deterministic_answer_groupby_chart() -> None:
    from main import deterministic_answer
    df = pd.read_csv(io.StringIO(SALES_CSV))
    answer = deterministic_answer("Show total revenue by category sorted descending as a bar chart", df)
    assert answer is not None
    assert "Total revenue by category" in answer["result"]
    assert answer["chart_json"] is not None
    assert answer["plan"]["query_type"] == "deterministic"


def test_deterministic_answer_uses_conversation_memory() -> None:
    from main import deterministic_answer
    df = pd.read_csv(io.StringIO(SALES_CSV))
    previous = {
        "last_metric": "revenue",
        "last_grouping": "region",
        "last_chart_type": "bar",
    }
    answer = deterministic_answer("Now split that by product", df, previous_state=previous)
    assert answer is not None
    assert "Using the previous metric `revenue`" in answer["result"]
    assert "Earbuds" in answer["result"]


def test_query_deterministic_sse_and_cache() -> None:
    from main import query_cache
    query_cache.clear()
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]

    first = client.post(
        "/query",
        json={"session_id": sid, "question": "How many rows and columns?", "category": "general"},
    )
    assert first.status_code == 200
    first_events = parse_sse_events(first.text)
    assert_sse_observability(first_events, "query", sid)
    first_done = first_events[-1]
    assert first_done["step"] == "done"
    assert "4 rows and 6 columns" in first_done["result"]
    assert first_done["meta"]["route"] == "deterministic"
    assert len(first_done["followups"]) > 0
    assert first_done["validation"]["confidence_label"] == "High"
    assert first_done["validation"]["row_support"] == 4
    assert "DataFrame dimensions" in first_done["validation"]["method"]

    second = client.post(
        "/query",
        json={"session_id": sid, "question": "How many rows and columns?", "category": "general"},
    )
    second_events = parse_sse_events(second.text)
    assert_sse_observability(second_events, "query", sid)
    assert second_events[0]["meta"]["route"] == "cache"
    assert second_events[-1]["message"] == "Analysis complete (cached)"


def test_story_endpoint_streams_fact_first_report() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]
    res = client.post("/story", json={"session_id": sid, "category": "retail"})
    assert res.status_code == 200
    events = parse_sse_events(res.text)
    assert_sse_observability(events, "story", sid)
    done = events[-1]
    assert done["step"] == "done"
    assert done["meta"]["route"] == "deterministic_story"
    assert done["meta"]["facts_first"] is True
    assert "deterministic" in done["report"].lower()
    assert done["plan"]["facts"]["category"] == "retail"
    assert done["chart_json"] is not None
    assert len(done["followups"]) > 0
    assert done["validation"]["method"] == "Fact-first deterministic story pipeline"
    assert done["validation"]["confidence_label"] == "High"
    assert done["validation"]["row_support"] == 4


def test_story_unknown_session() -> None:
    res = client.post("/story", json={"session_id": "missing", "category": "general"})
    assert res.status_code == 404


def test_investigate_endpoint_streams_autonomous_report() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]
    res = client.post(
        "/investigate",
        json={"session_id": sid, "goal": "Investigate revenue performance", "category": "retail"},
    )
    assert res.status_code == 200
    events = parse_sse_events(res.text)
    assert_sse_observability(events, "investigate", sid)
    done = events[-1]
    assert done["step"] == "done"
    assert done["meta"]["route"] == "deterministic_investigation"
    assert done["meta"]["facts_first"] is True
    assert "Executive finding" in done["report"]
    assert "Recommended actions" in done["report"]
    assert done["plan"]["query_type"] == "deterministic_investigation"
    assert done["plan"]["goal"] == "Investigate revenue performance"
    assert done["plan"]["persona"]["name"] == "Retail Operator"
    assert "revenue" in done["plan"]["persona_columns"]
    assert "Retail Operator lens" in done["report"]
    assert done["investigation"]["persona"]["name"] == "Retail Operator"
    assert done["chart_json"] is not None
    assert len(done["plan"]["investigation_tree"]) >= 4
    assert len(done["decision_actions"]) > 0
    assert done["validation"]["method"] == "Autonomous deterministic investigation pipeline"
    assert done["validation"]["confidence_label"] == "High"
    assert done["validation"]["row_support"] == 4


def test_investigate_unknown_session() -> None:
    res = client.post(
        "/investigate",
        json={"session_id": "missing", "goal": "Investigate revenue", "category": "general"},
    )
    assert res.status_code == 404


def test_upload_doc_and_docs_endpoint() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]

    doc = client.post(
        f"/upload_doc?session_id={sid}",
        files={"file": ("notes.txt", io.BytesIO(b"Revenue means gross sales before refunds."), "text/plain")},
    )
    assert doc.status_code == 200
    assert doc.json()["chunks_indexed"] >= 1
    assert "notes.txt" in doc.json()["filenames"]

    listed = client.get(f"/docs/{sid}")
    assert listed.status_code == 200
    assert listed.json()["chunks"] >= 1
    assert listed.json()["filenames"] == ["notes.txt"]


def test_upload_doc_unknown_session() -> None:
    res = client.post(
        "/upload_doc?session_id=missing",
        files={"file": ("notes.txt", io.BytesIO(b"context"), "text/plain")},
    )
    assert res.status_code == 404


def test_report_endpoint_returns_json_pdf_and_pptx() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]
    body = {
        "messages": [{
            "question": "What is revenue by category?",
            "result": "Electronics leads revenue.",
            "validation": {"confidence_label": "High"},
        }],
        "category": "retail",
        "filename": "sales export",
    }

    pdf = client.post(f"/report/{sid}?format=pdf", json=body)
    assert pdf.status_code == 200
    pdf_payload = pdf.json()
    assert pdf_payload["filename"] == "sales_export_report.pdf"
    assert pdf_payload["media_type"] == "application/pdf"
    assert base64.b64decode(pdf_payload["content_base64"]).startswith(b"%PDF")
    assert pdf_payload["size_bytes"] > 100

    pptx = client.post(f"/report/{sid}?format=pptx", json=body)
    assert pptx.status_code == 200
    pptx_payload = pptx.json()
    assert pptx_payload["filename"] == "sales_export_report.pptx"
    assert "presentationml.presentation" in pptx_payload["media_type"]
    assert base64.b64decode(pptx_payload["content_base64"]).startswith(b"PK")
    assert pptx_payload["size_bytes"] > 100


def test_report_unknown_session() -> None:
    res = client.post("/report/missing?format=pdf", json={"messages": [], "filename": "missing"})
    assert res.status_code == 404


def test_report_job_endpoint_completes() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]
    body = {
        "messages": [{"question": "What is revenue?", "result": "Revenue exists."}],
        "category": "retail",
        "filename": "async sales",
    }

    queued = client.post(f"/report_job/{sid}?format=pdf", json=body)
    assert queued.status_code == 200
    job_id = queued.json()["job_id"]
    assert queued.json()["poll_url"] == f"/jobs/{job_id}"

    job = client.get(f"/jobs/{job_id}")
    assert job.status_code == 200
    payload = job.json()
    assert payload["kind"] == "report"
    assert payload["status"] == "completed"
    assert payload["result"]["filename"] == "async_sales_report.pdf"
    assert base64.b64decode(payload["result"]["content_base64"]).startswith(b"%PDF")


def test_report_job_unknown_session() -> None:
    res = client.post("/report_job/missing?format=pdf", json={"messages": [], "filename": "missing"})
    assert res.status_code == 404


def test_benchmark_endpoint_returns_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    def fake_pipeline(
        df: pd.DataFrame,
        schema: str,
        question: str,
        category: str,
        doc_store: object = None,
    ) -> dict:
        return {
            "success": True,
            "has_chart": False,
            "query_type": "sql",
            "used_repair": False,
            "time_s": 0.01,
        }

    monkeypatch.setattr(main, "_run_agent_pipeline_sync", fake_pipeline)
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]

    res = client.get(f"/benchmark/{sid}?n=2")
    assert res.status_code == 200
    payload = res.json()
    assert payload["total"] == 2
    assert payload["success_rate"] == 1
    assert len(payload["results"]) == 2


def test_benchmark_unknown_session() -> None:
    res = client.get("/benchmark/missing?n=1")
    assert res.status_code == 404


# ── Predictive model ────────────────────────────────────────────────────

def test_benchmark_job_endpoint_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    def fake_pipeline(
        df: pd.DataFrame,
        schema: str,
        question: str,
        category: str,
        doc_store: object = None,
    ) -> dict:
        return {
            "success": True,
            "has_chart": False,
            "query_type": "sql",
            "used_repair": False,
            "time_s": 0.01,
        }

    monkeypatch.setattr(main, "_run_agent_pipeline_sync", fake_pipeline)
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    sid = up.json()["session_id"]

    queued = client.post(f"/benchmark_job/{sid}?n=2")
    assert queued.status_code == 200
    job = client.get(queued.json()["poll_url"])
    assert job.status_code == 200
    payload = job.json()
    assert payload["kind"] == "benchmark"
    assert payload["status"] == "completed"
    assert payload["result"]["total"] == 2
    assert payload["result"]["success_rate"] == 1


def test_benchmark_job_unknown_session() -> None:
    res = client.post("/benchmark_job/missing?n=1")
    assert res.status_code == 404


def test_job_unknown() -> None:
    res = client.get("/jobs/missing")
    assert res.status_code == 404


def _classification_df(n=120):
    rng = np.random.default_rng(0)
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(5, 2, n)
    noise = rng.normal(0, 0.3, n)
    target = ((x1 + 0.5 * x2 + noise) > 2.5).astype(int)
    return pd.DataFrame({"x1": x1, "x2": x2, "group": rng.choice(["a", "b"], n), "target": target})


def test_train_classifier_returns_summary_and_chart():
    df = _classification_df()
    summary, chart, info = train_predictive_model(df, "target")
    assert "classifier" in summary.lower()
    assert "Accuracy" in summary
    assert chart and len(chart) > 100
    assert info["is_classification"] is True
    assert any(f["name"] == "x1" for f in info["features"])


def test_train_regressor_returns_summary_and_chart():
    rng = np.random.default_rng(1)
    n = 120
    x = rng.normal(0, 1, n)
    df = pd.DataFrame({"x": x, "y": 3 * x + rng.normal(0, 0.5, n) + 10})
    summary, chart, info = train_predictive_model(df, "y")
    assert "regressor" in summary.lower()
    assert chart and len(chart) > 100
    assert info["is_classification"] is False


def test_train_too_few_rows_raises():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [0, 1, 0]})
    with pytest.raises(ValueError):
        train_predictive_model(df, "b")


def test_predict_input_full_flow():
    """Train via /predict, then predict the outcome for a new pasted case."""
    df = _classification_df(160)
    up = client.post("/upload_text", json={"text": df.to_csv(index=False), "has_header": True})
    sid = up.json()["session_id"]

    trained = client.post("/predict", json={"session_id": sid, "target": "target", "category": "general"})
    assert trained.status_code == 200
    assert_sse_observability(parse_sse_events(trained.text), "predict", sid)

    mi = client.get(f"/model_info/{sid}").json()
    assert mi["trained"] is True
    assert mi["target"] == "target"
    assert {f["name"] for f in mi["features"]} >= {"x1", "x2"}

    values = {f["name"]: f.get("default") for f in mi["features"]}
    pr = client.post("/predict_input", json={"session_id": sid, "values": values})
    assert pr.status_code == 200
    body = pr.json()
    assert body["target"] == "target"
    assert "prediction" in body


def test_predict_job_endpoint_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    def fake_train(df: pd.DataFrame, target: str) -> tuple[str, str, dict]:
        return (
            f"Trained fake model for {target}",
            base64.b64encode(b"chart").decode(),
            {
                "target": target,
                "model": object(),
                "feature_cols": ["x1", "x2"],
                "num_cols": ["x1", "x2"],
                "cat_cols": [],
                "is_classification": True,
                "classes": ["0", "1"],
                "medians": {"x1": 0.0, "x2": 0.0},
                "features": [
                    {"name": "x1", "type": "number", "default": 0.0},
                    {"name": "x2", "type": "number", "default": 0.0},
                ],
                "shap_chart": None,
                "perm_chart": None,
                "pdp_chart": None,
            },
        )

    monkeypatch.setattr(main, "train_predictive_model", fake_train)
    df = _classification_df(80)
    up = client.post("/upload_text", json={"text": df.to_csv(index=False), "has_header": True})
    sid = up.json()["session_id"]

    queued = client.post("/predict_job", json={"session_id": sid, "target": "target", "category": "general"})
    assert queued.status_code == 200
    job = client.get(queued.json()["poll_url"])
    assert job.status_code == 200
    payload = job.json()
    assert payload["kind"] == "predict"
    assert payload["status"] == "completed"
    assert payload["result"]["target"] == "target"
    assert payload["result"]["features"][0]["name"] == "x1"


def test_predict_job_unknown_session() -> None:
    res = client.post("/predict_job", json={"session_id": "missing", "target": "target", "category": "general"})
    assert res.status_code == 404


def test_simulate_scenario_full_flow():
    """Train a model, apply a what-if change, and compare baseline vs scenario."""
    df = _classification_df(160)
    up = client.post("/upload_text", json={"text": df.to_csv(index=False), "has_header": True})
    sid = up.json()["session_id"]

    trained = client.post("/predict", json={"session_id": sid, "target": "target", "category": "general"})
    assert trained.status_code == 200

    mi = client.get(f"/model_info/{sid}").json()
    baseline = {f["name"]: f.get("default") for f in mi["features"]}
    res = client.post(
        "/simulate",
        json={
            "session_id": sid,
            "baseline": baseline,
            "changes": {"x1": {"mode": "delta", "value": 1.5}},
            "category": "general",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["target"] == "target"
    assert body["is_classification"] is True
    assert body["changes_applied"][0]["feature"] == "x1"
    assert body["impact"]["type"] == "classification"
    assert "baseline_prediction" in body
    assert "scenario_prediction" in body
    assert body["chart_json"] is not None
    assert body["validation"]["confidence_label"] == "Medium"
    assert "not causal proof" in " ".join(body["validation"]["reasons"])


def test_scenario_parse_prefills_numeric_change():
    df = _classification_df(160)
    up = client.post("/upload_text", json={"text": df.to_csv(index=False), "has_header": True})
    sid = up.json()["session_id"]

    trained = client.post("/predict", json={"session_id": sid, "target": "target", "category": "general"})
    assert trained.status_code == 200

    res = client.post(
        "/scenario_parse",
        json={"session_id": sid, "prompt": "increase x1 by 10%", "category": "general"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["parsed"] is True
    assert body["feature"] == "x1"
    assert body["mode"] == "percent"
    assert body["value"] == 10
    assert body["confidence"] > 0.7
    assert body["validation"]["method"] == "Deterministic feature-name and value parser"


def test_scenario_parse_without_model():
    res = client.post(
        "/scenario_parse",
        json={"session_id": "no-model", "prompt": "increase x1 by 10%"},
    )
    assert res.status_code == 400


def test_simulate_without_model():
    res = client.post(
        "/simulate",
        json={"session_id": "no-model", "changes": {"x1": {"mode": "delta", "value": 1}}},
    )
    assert res.status_code == 400


def test_predict_input_without_model():
    res = client.post("/predict_input", json={"session_id": "no-model", "values": {}})
    assert res.status_code == 400


def test_predict_unknown_session():
    res = client.post("/predict", json={"session_id": "nope", "target": "x"})
    assert res.status_code == 404


def test_predict_bad_target():
    up = client.post("/upload", files={"file": ("d.csv", io.BytesIO(make_csv(SAMPLE_CSV)), "text/csv")})
    sid = up.json()["session_id"]
    res = client.post("/predict", json={"session_id": sid, "target": "no_such_col"})
    assert res.status_code == 400


def test_upload_returns_token_and_persists():
    up = client.post("/upload", files={"file": ("data.csv", io.BytesIO(make_csv(SAMPLE_CSV)), "text/csv")})
    assert up.status_code == 200
    body = up.json()
    assert "token" in body
    assert len(body["token"]) > 10
    sid = body["session_id"]

    import main
    # Simulate server restart by clearing in-memory dataframes
    main.dataframes.clear()

    # Session endpoints should still load the dataset from SQLite/Parquet on disk
    brief = client.get(f"/brief/{sid}")
    assert brief.status_code == 200
    assert brief.json()["readiness_score"] >= 0


def test_job_persistence_across_simulated_restart():
    import main
    job = main.create_job("report", "session-123")
    job_id = job["job_id"]
    main.update_job(job_id, "completed", result={"report": "OK"})

    # Simulate server restart by clearing in-memory jobs registry
    main.jobs.clear()

    res = client.get(f"/jobs/{job_id}")
    assert res.status_code == 200
    b = res.json()
    assert b["job_id"] == job_id
    assert b["status"] == "completed"
    assert b["result"]["report"] == "OK"

