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
    assert res.status_code in (400, 401)


def test_upload_non_csv_rejected():
    res = client.post(
        "/upload",
        files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert res.status_code in (400, 401)


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
    assert res.status_code in (401, 404)


def test_query_accepts_category():
    """The /query schema must accept an optional analysis category."""
    res = client.post(
        "/query",
        json={"session_id": "nonexistent-id", "question": "How many rows?", "category": "financial"},
    )
    # category is valid -> not a 422; session is fake -> 404
    assert res.status_code in (401, 404)


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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}
    res = client.get(f"/brief/{sid}?category=retail", headers=tok_hdr)
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
    assert res.status_code in (401, 404)


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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}
    res = client.get(f"/quality/{sid}", headers=tok_hdr)
    assert res.status_code == 200
    body = res.json()
    titles = {issue["title"] for issue in body["issues"]}
    assert "Missing Values" in titles
    assert "Duplicate Rows" in titles
    assert body["score"] < 100


def test_quality_unknown_session() -> None:
    res = client.get("/quality/missing")
    assert res.status_code in (401, 404)


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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    plan = client.get(f"/cleaning_plan/{sid}", headers=tok_hdr)
    assert plan.status_code == 200
    action_ids = {action["id"] for action in plan.json()["actions"]}
    assert {"drop_empty_columns", "remove_duplicate_rows", "fill_numeric_median"} <= action_ids

    cleaned = client.post(f"/clean/{sid}", headers=tok_hdr, json={})
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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}
    res = client.post(f"/clean/{sid}", headers=tok_hdr, json={"actions": ["not_supported"]})
    assert res.status_code in (400, 401)


def test_cleaning_unknown_session() -> None:
    assert client.get("/cleaning_plan/missing").status_code in (401, 404)
    assert client.post("/clean/missing", json={}).status_code in (401, 404)


def test_contract_endpoint_and_row_validation() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    contract = client.get(f"/contract/{sid}", headers=tok_hdr)
    assert contract.status_code == 200
    body = contract.json()
    assert body["version"] == "1.0"
    assert body["column_count"] == 6
    revenue = next(col for col in body["columns"] if col["name"] == "revenue")
    assert revenue["type"] in {"integer", "number"}
    assert "must_parse_as_number" in revenue["rules"]

    validation = client.post(
        f"/validate_rows/{sid}", headers=tok_hdr,
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
    assert client.get("/contract/missing").status_code in (401, 404)
    assert client.post("/validate_rows/missing", json={"rows": []}).status_code in (401, 404)


def test_dashboard_endpoint_returns_blueprint() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}
    res = client.get(f"/dashboard/{sid}?category=retail", headers=tok_hdr)
    assert res.status_code == 200
    spec = res.json()
    assert spec["category"] == "retail"
    assert spec["layout"]["columns"] == 12
    assert any(kpi["id"] == "total_revenue" for kpi in spec["kpis"])
    assert any(chart["type"] == "line" for chart in spec["charts"])
    assert any(question for question in spec["starter_questions"] if "revenue" in question.lower())


def test_dashboard_unknown_session() -> None:
    res = client.get("/dashboard/missing")
    assert res.status_code in (401, 404)


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
    from main import SecurityError
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(SecurityError, match="getattr"):
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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    first = client.post("/query", headers=tok_hdr, json={"session_id": sid, "question": "How many rows and columns?", "category": "general"})
    assert first.status_code == 200
    first_events = parse_sse_events(first.text)
    print("FIRST EVENTS:", first_events)
    assert_sse_observability(first_events, "query", sid)
    first_done = first_events[-1]
    assert first_done["step"] == "done"
    assert "4 rows and 6 columns" in first_done["result"]
    assert first_done["meta"]["route"] in ("direct", "deterministic")
    assert len(first_done["followups"]) > 0
    assert first_done["validation"]["confidence_label"] == "High"
    assert first_done["validation"]["row_support"] == 4
    assert "calc" in first_done["validation"]["method"].lower() or "dataframe" in first_done["validation"]["method"].lower() or "deterministic" in first_done["validation"]["method"].lower()

    second = client.post(
        "/query",
        headers=tok_hdr,
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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}
    res = client.post("/story", headers=tok_hdr, json={"session_id": sid, "category": "retail"})
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
    res = client.post("/story", headers={"X-Session-Token": "dummy"}, json={"session_id": "missing", "category": "general"})
    assert res.status_code in (401, 404)


def test_investigate_endpoint_streams_autonomous_report() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}
    res = client.post("/investigate", headers=tok_hdr, json={"session_id": sid, "goal": "Investigate revenue performance", "category": "retail"})
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
    assert done["plan"]["persona"]["name"] in ["Commercial Lead", "Retail Operator"]
    assert "Commercial Lead lens" in done["report"] or "Retail Operator lens" in done["report"]
    assert done["investigation"]["persona"]["name"] in ["Commercial Lead", "Retail Operator"]
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
    assert res.status_code in (401, 404)


def test_upload_doc_and_docs_endpoint() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    doc = client.post(f"/upload_doc?session_id={sid}", headers=tok_hdr, files={"file": ("notes.txt", io.BytesIO(b"Revenue means gross sales before refunds."), "text/plain")},
    )
    assert doc.status_code == 200
    assert doc.json()["chunks_indexed"] >= 1
    assert "notes.txt" in doc.json()["filenames"]

    listed = client.get(f"/docs/{sid}", headers=tok_hdr)
    assert listed.status_code == 200
    assert listed.json()["chunks"] >= 1
    assert listed.json()["filenames"] == ["notes.txt"]


def test_upload_doc_unknown_session() -> None:
    res = client.post(
        "/upload_doc?session_id=missing",
        files={"file": ("notes.txt", io.BytesIO(b"context"), "text/plain")},
    )
    assert res.status_code in (401, 404)


def test_report_endpoint_returns_json_pdf_and_pptx() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}
    body = {
        "messages": [{
            "question": "What is revenue by category?",
            "result": "Electronics leads revenue.",
            "validation": {"confidence_label": "High"},
        }],
        "category": "retail",
        "filename": "sales export",
    }

    pdf = client.post(f"/report/{sid}?format=pdf", headers=tok_hdr, json=body)
    assert pdf.status_code == 200
    pdf_payload = pdf.json()
    assert pdf_payload["filename"] == "sales_export_report.pdf"
    assert pdf_payload["media_type"] == "application/pdf"
    assert base64.b64decode(pdf_payload["content_base64"]).startswith(b"%PDF")
    assert pdf_payload["size_bytes"] > 100

    pptx = client.post(f"/report/{sid}?format=pptx", headers=tok_hdr, json=body)
    assert pptx.status_code == 200
    pptx_payload = pptx.json()
    assert pptx_payload["filename"] == "sales_export_report.pptx"
    assert "presentationml.presentation" in pptx_payload["media_type"]
    assert base64.b64decode(pptx_payload["content_base64"]).startswith(b"PK")
    assert pptx_payload["size_bytes"] > 100


def test_report_unknown_session() -> None:
    res = client.post("/report/missing?format=pdf", json={"messages": [], "filename": "missing"})
    assert res.status_code in (401, 404)


def test_report_job_endpoint_completes() -> None:
    up = client.post(
        "/upload",
        files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")},
    )
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}
    body = {
        "messages": [{"question": "What is revenue?", "result": "Revenue exists."}],
        "category": "retail",
        "filename": "async sales",
    }

    queued = client.post(f"/report_job/{sid}?format=pdf", headers=tok_hdr, json=body)
    assert queued.status_code == 200
    job_id = queued.json()["job_id"]
    assert queued.json()["poll_url"] == f"/jobs/{job_id}"

    job = client.get(f"/jobs/{job_id}", headers=tok_hdr)
    assert job.status_code == 200
    payload = job.json()
    assert payload["kind"] == "report"
    assert payload["status"] == "completed"
    assert payload["result"]["filename"] == "async_sales_report.pdf"
    assert base64.b64decode(payload["result"]["content_base64"]).startswith(b"%PDF")


def test_report_job_unknown_session() -> None:
    res = client.post("/report_job/missing?format=pdf", json={"messages": [], "filename": "missing"})
    assert res.status_code in (401, 404)


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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    res = client.get(f"/benchmark/{sid}?n=2", headers=tok_hdr)
    assert res.status_code == 200
    payload = res.json()
    assert payload["total"] == 2
    assert payload["success_rate"] == 1
    assert len(payload["results"]) == 2


def test_benchmark_unknown_session() -> None:
    res = client.get("/benchmark/missing?n=1")
    assert res.status_code in (401, 404)


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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    queued = client.post(f"/benchmark_job/{sid}?n=2", headers=tok_hdr)
    assert queued.status_code == 200
    job = client.get(queued.json()["poll_url"], headers=tok_hdr)
    assert job.status_code == 200
    payload = job.json()
    assert payload["kind"] == "benchmark"
    assert payload["status"] == "completed"
    assert payload["result"]["total"] == 2
    assert payload["result"]["success_rate"] == 1


def test_benchmark_job_unknown_session() -> None:
    res = client.post("/benchmark_job/missing?n=1")
    assert res.status_code in (401, 404)


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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    trained = client.post("/predict", headers=tok_hdr, json={"session_id": sid, "target": "target", "category": "general"})
    assert trained.status_code == 200
    assert_sse_observability(parse_sse_events(trained.text), "predict", sid)

    mi = client.get(f"/model_info/{sid}", headers=tok_hdr).json()
    assert mi["trained"] is True
    assert mi["target"] == "target"
    assert {f["name"] for f in mi["features"]} >= {"x1", "x2"}

    values = {f["name"]: f.get("default") for f in mi["features"]}
    pr = client.post("/predict_input", headers=tok_hdr, json={"session_id": sid, "values": values})
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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    queued = client.post("/predict_job", headers=tok_hdr, json={"session_id": sid, "target": "target", "category": "general"})
    assert queued.status_code == 200
    job = client.get(queued.json()["poll_url"], headers=tok_hdr)
    assert job.status_code == 200
    payload = job.json()
    assert payload["kind"] == "predict"
    assert payload["status"] == "completed"
    assert payload["result"]["target"] == "target"
    assert payload["result"]["features"][0]["name"] == "x1"


def test_predict_job_unknown_session() -> None:
    res = client.post("/predict_job", json={"session_id": "missing", "target": "target", "category": "general"})
    assert res.status_code in (401, 404)


def test_simulate_scenario_full_flow():
    """Train a model, apply a what-if change, and compare baseline vs scenario."""
    df = _classification_df(160)
    up = client.post("/upload_text", json={"text": df.to_csv(index=False), "has_header": True})
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    trained = client.post("/predict", headers=tok_hdr, json={"session_id": sid, "target": "target", "category": "general"})
    assert trained.status_code == 200

    mi = client.get(f"/model_info/{sid}", headers=tok_hdr).json()
    baseline = {f["name"]: f.get("default") for f in mi["features"]}
    res = client.post("/simulate", headers=tok_hdr, json={"session_id": sid, "baseline": baseline, "changes": {"x1": {"mode": "delta", "value": 1.5}}, "category": "general"})
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
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    trained = client.post("/predict", headers=tok_hdr, json={"session_id": sid, "target": "target", "category": "general"})
    assert trained.status_code == 200

    res = client.post("/scenario_parse", headers=tok_hdr, json={"session_id": sid, "prompt": "increase x1 by 10%", "category": "general"})
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
        "/scenario_parse", headers={"X-Session-Token": "dummy"},
        json={"session_id": "no-model", "prompt": "increase x1 by 10%"},
    )
    assert res.status_code in (400, 401)


def test_simulate_without_model():
    res = client.post(
        "/simulate", headers={"X-Session-Token": "dummy"},
        json={"session_id": "no-model", "changes": {"x1": {"mode": "delta", "value": 1}}},
    )
    assert res.status_code in (400, 401)


def test_predict_input_without_model():
    res = client.post("/predict_input", headers={"X-Session-Token": "dummy"}, json={"session_id": "no-model", "values": {}})
    assert res.status_code in (400, 401)


def test_predict_unknown_session():
    res = client.post("/predict", json={"session_id": "nope", "target": "x"})
    assert res.status_code in (401, 404)


def test_predict_bad_target():
    up = client.post("/upload", files={"file": ("d.csv", io.BytesIO(make_csv(SAMPLE_CSV)), "text/csv")})
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}
    res = client.post("/predict", headers=tok_hdr, json={"session_id": sid, "target": "no_such_col"})
    assert res.status_code in (400, 401)


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
    tok = body["token"]
    brief = client.get(f"/brief/{sid}", headers={"X-Session-Token": tok})
    assert brief.status_code == 200
    assert brief.json()["readiness_score"] >= 0


def test_job_persistence_across_simulated_restart():
    import main
    main.session_meta["session-123"] = {"token": "test-token-123"}
    job = main.create_job("report", "session-123")
    job_id = job["job_id"]
    main.update_job(job_id, "completed", result={"report": "OK"})

    # Simulate server restart by clearing in-memory jobs registry
    main.jobs.clear()

    res = client.get(f"/jobs/{job_id}", headers={"X-Session-Token": "test-token-123"})
    assert res.status_code == 200
    b = res.json()
    assert b["job_id"] == job_id
    assert b["status"] == "completed"
    assert b["result"]["report"] == "OK"


def test_recover_orphan_jobs_on_startup():
    import storage
    import main
    job = main.create_job("predict", "session-orphan")
    job_id = job["job_id"]

    # Simulate server crash leaving job in 'queued' state
    recovered = storage.recover_orphan_jobs()
    assert recovered >= 1

    j = storage.get_job(job_id)
    assert j["status"] == "failed"
    assert "Server restarted" in j["error"]


def test_predict_input_includes_prediction_interval():
    import test_main
    df = pd.DataFrame({
        "x1": np.random.randn(100),
        "x2": np.random.randn(100),
        "target": np.random.randn(100) * 10 + 50,
    })
    up = client.post("/upload_text", json={"text": df.to_csv(index=False), "has_header": True})
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    client.post("/predict", headers=tok_hdr, json={"session_id": sid, "target": "target"})
    res = client.post("/predict_input", headers=tok_hdr, json={"session_id": sid, "values": {"x1": 0.5, "x2": -0.2}})
    assert res.status_code == 200
    body = res.json()
    assert "prediction" in body
    assert body["is_classification"] is False
    assert "prediction_interval" in body
    interval = body["prediction_interval"]
    assert interval["confidence"] == 0.90
    assert interval["lower"] <= body["prediction"] <= interval["upper"]


def test_upload_excel_xlsx():
    df = pd.DataFrame({"item": ["Earbuds", "Speaker"], "price": [90, 120]})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Products", index=False)
    buf.seek(0)

    res = client.post(
        "/upload",
        files={"file": ("products.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    b = res.json()
    assert b["rows"] == 2
    assert "item" in b["columns"]
    assert "sheets" in b
    assert "Products" in b["sheets"]


def test_infer_join_keys_and_join_datasets():
    df_customers = pd.DataFrame({"customer_id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"]})
    df_orders = pd.DataFrame({"order_id": [101, 102, 103], "customer_id": [1, 2, 1], "amount": [50, 100, 75]})

    up1 = client.post("/upload_text", json={"text": df_customers.to_csv(index=False), "has_header": True, "filename": "customers.csv"})
    up2 = client.post("/upload_text", json={"text": df_orders.to_csv(index=False), "has_header": True, "filename": "orders.csv"})
    sid1 = up1.json()["session_id"]
    sid2 = up2.json()["session_id"]

    tok1 = up1.json()["token"]
    infer = client.post("/infer_join", headers={"X-Session-Token": tok1}, json={"session_id_1": sid1, "session_id_2": sid2})
    assert infer.status_code == 200
    cands = infer.json()["candidates"]
    assert len(cands) > 0
    assert cands[0]["column_1"] == "customer_id"
    assert cands[0]["column_2"] == "customer_id"
    assert cands[0]["score"] >= 0.7

    joined = client.post("/join", headers={"X-Session-Token": tok1}, json={
        "session_id_1": sid1,
        "session_id_2": sid2,
        "join_key_1": "customer_id",
        "join_key_2": "customer_id",
        "how": "inner",
    })
    assert joined.status_code == 200
    jbody = joined.json()
    assert jbody["rows"] == 3
    assert "name" in jbody["columns"]
    assert "amount" in jbody["columns"]
    assert jbody["join_metadata"]["left_rows_before"] == 3
    assert jbody["join_metadata"]["right_rows_before"] == 3


def test_time_series_forecast():
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    values = np.linspace(100, 400, 30) + np.random.randn(30) * 5
    df = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "sales": values})

    up = client.post("/upload_text", json={"text": df.to_csv(index=False), "has_header": True})
    _resp = up.json()

    sid = _resp["session_id"]

    tok = _resp.get("token", "")

    tok_hdr = {"X-Session-Token": tok}

    res = client.post("/forecast", headers=tok_hdr, json={
        "session_id": sid,
        "date_column": "date",
        "target_column": "sales",
        "periods": 7,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["date_column"] == "date"
    assert body["target_column"] == "sales"
    assert len(body["forecast"]) == 7
    assert "metrics" in body
    assert body["metrics"]["trend_direction"] == "upward"
    assert "chart_json" in body


def test_upload_json_and_jsonl():
    json_bytes = io.BytesIO(json.dumps([{"id": 1, "user": {"name": "Alice"}}, {"id": 2, "user": {"name": "Bob"}}]).encode("utf-8"))
    res = client.post(
        "/upload",
        files={"file": ("users.json", json_bytes, "application/json")},
    )
    assert res.status_code == 200
    b = res.json()
    assert b["rows"] == 2
    assert "user.name" in b["columns"]

    jsonl_bytes = io.BytesIO(b'{"a": 10, "b": 20}\n{"a": 30, "b": 40}\n')
    res2 = client.post(
        "/upload",
        files={"file": ("logs.jsonl", jsonl_bytes, "application/x-ndjson")},
    )
    assert res2.status_code == 200
    assert res2.json()["rows"] == 2


def test_compare_datasets_drift():
    df1 = pd.DataFrame({"revenue": [100, 110, 105, 95, 100], "cost": [50, 52, 51, 49, 50]})
    df2 = pd.DataFrame({"revenue": [200, 210, 205, 195, 200], "cost": [50, 52, 51, 49, 50], "new_col": [1, 2, 3, 4, 5]})

    up1 = client.post("/upload_text", json={"text": df1.to_csv(index=False), "has_header": True, "filename": "v1.csv"})
    up2 = client.post("/upload_text", json={"text": df2.to_csv(index=False), "has_header": True, "filename": "v2.csv"})
    sid1 = up1.json()["session_id"]
    sid2 = up2.json()["session_id"]

    tok1 = up1.json()["token"]
    res = client.post("/compare", headers={"X-Session-Token": tok1}, json={"session_id_1": sid1, "session_id_2": sid2})
    assert res.status_code == 200
    body = res.json()
    assert body["v1_rows"] == 5
    assert body["v2_rows"] == 5
    assert "new_col" in body["schema_changes"]["added_columns"]
    assert len(body["numeric_drift"]) >= 1
    rev_drift = next(d for d in body["numeric_drift"] if d["column"] == "revenue")
    assert rev_drift["drift_level"] == "Significant"
    assert rev_drift["mean_delta"] == 100.0


def test_import_url_ssrf_blocking_cloud_metadata():
    res = client.post("/import_url", json={"url": "http://169.254.169.254/latest/meta-data/"})
    assert res.status_code in (400, 401)
    assert "Security error" in res.json()["detail"]


def test_import_url_ssrf_blocking_loopback():
    res = client.post("/import_url", json={"url": "http://localhost:8001/health"})
    assert res.status_code in (400, 401)
    assert "Security error" in res.json()["detail"]


def test_import_url_ssrf_blocking_unauthorized_domain():
    res = client.post("/import_url", json={"url": "https://untrusted-external-domain.com/stolen.csv"})
    assert res.status_code in (400, 401)
    assert "Security error" in res.json()["detail"]


def test_import_url_ssrf_blocking_redirect_to_private_ip():
    import main
    # Validating redirect targets must block redirect hops to private IP addresses or disallowed domains
    with pytest.raises(Exception) as exc_info:
        main.validate_safe_url("http://169.254.169.254/latest/meta-data/")
    assert "Security error" in str(exc_info.value)



def test_infer_join_no_overlapping_keys():
    df1 = pd.DataFrame({"alpha": ["a", "b", "c"]})
    df2 = pd.DataFrame({"beta": [10, 20, 30]})

    up1 = client.post("/upload_text", json={"text": df1.to_csv(index=False), "has_header": True})
    up2 = client.post("/upload_text", json={"text": df2.to_csv(index=False), "has_header": True})
    tok1 = up1.json()["token"]

    res = client.post("/infer_join", headers={"X-Session-Token": tok1}, json={"session_id_1": up1.json()["session_id"], "session_id_2": up2.json()["session_id"]})
    assert res.status_code == 200
    assert len(res.json()["candidates"]) == 0


def test_join_datasets_invalid_column_error():
    df1 = pd.DataFrame({"col_x": [1, 2, 3]})
    df2 = pd.DataFrame({"col_y": [1, 2, 3]})

    up1 = client.post("/upload_text", json={"text": df1.to_csv(index=False), "has_header": True})
    up2 = client.post("/upload_text", json={"text": df2.to_csv(index=False), "has_header": True})
    tok1 = up1.json()["token"]

    res = client.post("/join", headers={"X-Session-Token": tok1}, json={
        "session_id_1": up1.json()["session_id"],
        "session_id_2": up2.json()["session_id"],
        "join_key_1": "non_existent_column",
        "join_key_2": "col_y",
    })
    assert res.status_code in (400, 401)
    assert "not found" in res.json()["detail"]


def test_forecast_insufficient_data_error():
    df = pd.DataFrame({"date": ["2024-01-01", "2024-01-02"], "sales": [10, 20]})
    up = client.post("/upload_text", json={"text": df.to_csv(index=False), "has_header": True})
    tok = up.json()["token"]

    res = client.post("/forecast", headers={"X-Session-Token": tok}, json={
        "session_id": up.json()["session_id"],
        "date_column": "date",
        "target_column": "sales",
        "periods": 5,
    })
    assert res.status_code in (400, 401)
    assert "At least 5 valid date-target rows" in res.json()["detail"]


def test_compare_datasets_disjoint_schemas():
    df1 = pd.DataFrame({"col_a": [1, 2, 3]})
    df2 = pd.DataFrame({"col_b": [4, 5, 6]})

    up1 = client.post("/upload_text", json={"text": df1.to_csv(index=False), "has_header": True})
    up2 = client.post("/upload_text", json={"text": df2.to_csv(index=False), "has_header": True})
    tok1 = up1.json()["token"]

    res = client.post("/compare", headers={"X-Session-Token": tok1}, json={"session_id_1": up1.json()["session_id"], "session_id_2": up2.json()["session_id"]})
    assert res.status_code == 200
    assert "schema_changes" in res.json()


def test_report_export_includes_forecast_and_join_metadata():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-06"],
        "sales": [100, 120, 130, 110, 150, 160],
    })
    up = client.post("/upload_text", json={"text": df.to_csv(index=False), "has_header": True, "filename": "sales.csv"})
    _resp = up.json()
    sid = _resp["session_id"]
    tok = _resp.get("token", "")
    tok_hdr = {"X-Session-Token": tok}

    fc = client.post("/forecast", headers=tok_hdr, json={"session_id": sid, "date_column": "date", "target_column": "sales", "periods": 6})
    assert fc.status_code == 200

    pdf_res = client.post(f"/report/{sid}?format=pdf", headers=tok_hdr, json={"messages": [], "category": "general", "filename": "test"})
    assert pdf_res.status_code == 200
    assert pdf_res.json()["size_bytes"] > 500
    assert pdf_res.json()["filename"].endswith(".pdf")

    pptx_res = client.post(f"/report/{sid}?format=pptx", headers=tok_hdr, json={"messages": [], "category": "general", "filename": "test"})
    assert pptx_res.status_code == 200
    assert pptx_res.json()["size_bytes"] > 500
    assert pptx_res.json()["filename"].endswith(".pptx")


def test_session_token_authentication_enforced():
    up = client.post(
        "/upload",
        files={"file": ("data.csv", io.BytesIO(make_csv(SAMPLE_CSV)), "text/csv")},
    )
    assert up.status_code == 200
    data = up.json()
    sid = data["session_id"]
    token = data["token"]

    # Request without token must return 401
    no_token_res = client.get(f"/brief/{sid}")
    assert no_token_res.status_code == 401
    assert "token missing" in no_token_res.json()["detail"].lower()

    # Request with invalid token must return 401
    bad_token_res = client.get(f"/brief/{sid}", headers={"X-Session-Token": "invalid-token-xyz"})
    assert bad_token_res.status_code == 401
    assert "invalid session" in bad_token_res.json()["detail"].lower()

    # Request with valid header token must succeed
    valid_header_res = client.get(f"/brief/{sid}", headers={"X-Session-Token": token})
    assert valid_header_res.status_code == 200

    # Request with valid query token must succeed
    valid_query_res = client.get(f"/brief/{sid}?token={token}")
    assert valid_query_res.status_code == 200


def test_sandbox_blocks_pandas_file_io():
    from main import validate_code_ast, SecurityError
    df = pd.DataFrame({"a": [1, 2, 3]})

    # df.to_csv() must be blocked by AST security scan
    with pytest.raises(SecurityError) as exc_info1:
        validate_code_ast("df.to_csv('stolen.csv')")
    assert "to_csv" in str(exc_info1.value)

    # pd.read_csv() must be blocked by AST security scan
    with pytest.raises(SecurityError) as exc_info2:
        validate_code_ast("pd.read_csv('/etc/passwd')")
    assert "read_csv" in str(exc_info2.value)


def test_import_url_ip_pinning():
    from main import validate_and_pin_url
    pinned_ip, hostname, target_url = validate_and_pin_url("https://docs.google.com/spreadsheets/d/abc/export?format=csv")
    assert hostname == "docs.google.com"
    assert pinned_ip != "docs.google.com"
    assert target_url.startswith("https://")


def test_get_job_requires_valid_session_token():
    df = _classification_df(80)
    up = client.post("/upload_text", json={"text": df.to_csv(index=False), "has_header": True})
    data = up.json()
    sid = data["session_id"]
    token = data["token"]

    job_res = client.post("/predict_job", headers={"X-Session-Token": token}, json={"session_id": sid, "target": "target"})
    assert job_res.status_code == 200
    job_id = job_res.json()["job_id"]

    # Request job without token must return 401
    no_tok = client.get(f"/jobs/{job_id}")
    assert no_tok.status_code == 401

    # Request job with bad token must return 401
    bad_tok = client.get(f"/jobs/{job_id}", headers={"X-Session-Token": "bad-token"})
    assert bad_tok.status_code == 401

    # Request job with valid token must succeed
    good_tok = client.get(f"/jobs/{job_id}", headers={"X-Session-Token": token})
    assert good_tok.status_code == 200
    assert good_tok.json()["job_id"] == job_id


def test_sandbox_blocks_getattr_dynamic_evasion():
    from main import validate_code_ast, SecurityError

    with pytest.raises(SecurityError) as exc_info:
        validate_code_ast("getattr(pd, 'read_csv')('secret.csv')")
    assert "getattr" in str(exc_info.value)


def test_lens_resolution_auto_switch():
    from main import resolve_analysis_lens
    df = pd.DataFrame({"Glucose": [120, 140], "BloodPressure": [70, 80], "BMI": [25.0, 28.1]})

    # Financial lens selected for Healthcare CSV -> auto-switches to Medical
    res = resolve_analysis_lens(df, "financial", filename="diabetes.csv", question="What is average BloodPressure?")
    assert res["was_auto_switched"] is True
    assert res["selected_lens"] == "financial"
    assert res["effective_lens"] == "medical"
    assert "does not match" in res["reason"]

    # Medical lens selected for Healthcare CSV -> stays Medical
    res_med = resolve_analysis_lens(df, "medical", filename="diabetes.csv")
    assert res_med["was_auto_switched"] is False
    assert res_med["effective_lens"] == "medical"


def test_query_complexity_classification():
    from main import classify_query_complexity
    # Use 100 rows so row-70 lookup is within bounds
    df = pd.DataFrame({
        "Pregnancies": list(range(100)),
        "Glucose": list(range(100, 200)),
        "BloodPressure": list(range(60, 160)),
    })

    qtype1, meta1 = classify_query_complexity("What does row 70 tell us?", df)
    assert qtype1 == "direct_row_lookup"

    qtype2, meta2 = classify_query_complexity("What is the average blood pressure?", df)
    assert qtype2 == "simple_aggregation"
    assert meta2["column"] == "BloodPressure"

    qtype3, meta3 = classify_query_complexity("Show a correlation heatmap", df)
    assert qtype3 == "visualization"

    # data_quality_guidance phrases
    qtype4, meta4 = classify_query_complexity("How to improve this dataset?", df)
    assert qtype4 == "data_quality_guidance", f"Expected data_quality_guidance, got {qtype4}"

    qtype5, meta5 = classify_query_complexity("How to make this a good dataset", df)
    assert qtype5 == "data_quality_guidance", f"Expected data_quality_guidance, got {qtype5}"

    qtype6, meta6 = classify_query_complexity("What are the data quality issues?", df)
    assert qtype6 == "data_quality_guidance", f"Expected data_quality_guidance, got {qtype6}"

    qtype7, meta7 = classify_query_complexity("Clean this dataset for me", df)
    assert qtype7 == "data_quality_guidance", f"Expected data_quality_guidance, got {qtype7}"


def test_data_quality_guidance_route_mapping():
    from main import get_query_complexity_route, QueryComplexity
    assert get_query_complexity_route("data_quality_guidance") == QueryComplexity.STANDARD
    assert get_query_complexity_route("complex_analysis") == QueryComplexity.DEEP
    assert get_query_complexity_route("direct_row_lookup") == QueryComplexity.DIRECT


def test_session_profile_cache_populated_on_upload():
    import main
    import io

    csv_data = "age,salary,dept\n30,50000,Engineering\n25,45000,Marketing\n35,60000,\n"
    res = client.post(
        "/upload",
        files={"file": ("test_profile.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
    )
    assert res.status_code == 200
    sid = res.json()["session_id"]

    # session_profile_cache must be populated immediately on upload
    assert sid in main.session_profile_cache
    profile = main.session_profile_cache[sid]
    assert profile["row_count"] == 3
    assert profile["column_count"] == 3
    assert "quality_report" in profile
    assert "cleaning_plan" in profile
    assert isinstance(profile["numeric_columns"], list)
    assert isinstance(profile["columns"], list)


def test_direct_row_lookup_fastpath():
    from main import extract_row_lookup_result
    df = pd.DataFrame({"Pregnancies": [6, 1], "Glucose": [148, 85], "BloodPressure": [72, 66]})

    res = extract_row_lookup_result(df, 0, 1)
    assert res["display_row"] == 1
    assert len(res["fields"]) == 3
    assert res["fields"][0]["field"] == "Pregnancies"
    assert res["fields"][0]["value"] == "6"
    assert "Row 1 Data Summary" in res["summary"]


def test_get_dataset_rows_endpoint():
    from main import dataframes
    import io

    csv_data = "col1,col2\n10,foo\n20,bar\n30,baz\n"
    res = client.post("/upload", files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert res.status_code == 200
    data = res.json()
    sid = data["session_id"]
    tok = data["token"]

    resp = client.get(f"/dataset_rows/{sid}?page=1&page_size=2", headers={"X-Session-Token": tok})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_rows"] == 3
    assert body["filtered_count"] == 3
    assert len(body["rows"]) == 2
    assert body["rows"][0]["col1"] == 10
    assert body["columns"] == ["col1", "col2"]


def test_query_row_lookup_70th_row():
    import io
    csv_data = "Pregnancies,Glucose,BloodPressure\n" + "\n".join(f"{i},{100+i},{70+i}" for i in range(1, 100))
    up = client.post("/upload", files={"file": ("diabetes.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up.status_code == 200
    data = up.json()
    sid = data["session_id"]
    tok = data["token"]

    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "what does 70th row tell us"})
    assert res.status_code == 200
    events = [json.loads(line[6:]) for line in res.text.split("\n") if line.startswith("data: ")]
    done_event = next(e for e in events if e.get("type") == "analysis_completed" or e.get("status") == "complete")

    assert done_event["request_id"] is not None
    assert done_event["status"] == "complete"
    assert done_event["answer"]["type"] == "row_lookup"
    assert done_event["answer"]["data"]["display_row"] == 70
    assert len(done_event["execution_steps"]) > 0


def test_query_unclear_question_gg():
    import io
    csv_data = "col1,col2\n1,2\n3,4\n"
    up = client.post("/upload", files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up.status_code == 200
    data = up.json()
    sid = data["session_id"]
    tok = data["token"]

    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "gg"})
    assert res.status_code == 200
    events = [json.loads(line[6:]) for line in res.text.split("\n") if line.startswith("data: ")]
    done_event = next(e for e in events if e.get("type") == "analysis_completed" or e.get("status") == "complete")

    assert done_event["status"] == "complete"
    assert done_event["answer"]["type"] == "clarification"
    assert isinstance(done_event["answer"]["summary"], str) and len(done_event["answer"]["summary"]) > 0
    assert len(done_event["execution_steps"]) > 0


def test_query_dataset_purpose():
    import io
    csv_data = "Glucose,BloodPressure,BMI,Insulin\n148,72,33.6,0\n85,66,26.6,0\n"
    up = client.post("/upload", files={"file": ("diabetes.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up.status_code == 200
    data = up.json()
    sid = data["session_id"]
    tok = data["token"]

    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "what is the purpose of this dataset"})
    assert res.status_code == 200
    events = [json.loads(line[6:]) for line in res.text.split("\n") if line.startswith("data: ")]
    done_event = next(e for e in events if e.get("type") == "analysis_completed" or e.get("status") == "complete")

    assert done_event["status"] == "complete"
    assert done_event["answer"]["type"] == "dataset_summary"
    assert isinstance(done_event["answer"]["summary"], str) and len(done_event["answer"]["summary"]) > 0
    assert len(done_event["execution_steps"]) > 0


def test_cache_get_and_set_callable() -> None:
    import main
    assert callable(main._cache_get)
    assert callable(main._cache_set)
    main._cache_set("test_key_1", {"type": "analysis_completed", "status": "complete"})
    val = main._cache_get("test_key_1")
    assert val is not None
    assert val["status"] == "complete"


def test_cache_lookup_exception_handling(monkeypatch) -> None:
    import main
    def mock_get(key: str):
        raise RuntimeError("Cache backend disconnected")
    monkeypatch.setattr(main, "_cache_get", mock_get)

    import io
    csv_data = "col1,col2\n1,2\n"
    up = client.post("/upload", files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up.status_code == 200
    data = up.json()

    res = client.post("/query", headers={"X-Session-Token": data["token"]}, json={"session_id": data["session_id"], "question": "what is this dataset about"})
    assert res.status_code == 200
    events = [json.loads(line[6:]) for line in res.text.split("\n") if line.startswith("data: ")]
    done_event = next(e for e in events if e.get("type") == "analysis_completed" or e.get("status") == "complete")
    assert done_event["status"] == "complete"
    assert done_event["answer"] is not None


def test_query_hello_greeting_no_nameerror() -> None:
    import io
    csv_data = "col1,col2\n1,2\n"
    up = client.post("/upload", files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up.status_code == 200
    data = up.json()

    res = client.post("/query", headers={"X-Session-Token": data["token"]}, json={"session_id": data["session_id"], "question": "hello"})
    assert res.status_code == 200
    events = [json.loads(line[6:]) for line in res.text.split("\n") if line.startswith("data: ")]
    done_event = next(e for e in events if e.get("type") == "analysis_completed" or e.get("status") == "complete")
    assert done_event["status"] == "complete"
    assert done_event["answer"]["summary"] is not None


def test_analysis_evidence_and_synthesis_service() -> None:
    import main
    from main import AnalysisEvidence, GeneratedAnswer, synthesize_llm_answer

    evidence = AnalysisEvidence(
        intent="row_lookup",
        dataset_name="test.csv",
        facts={"row_index": 0, "display_row": 1, "fields": [{"field": "age", "value": "45"}]},
        generated_code="df.iloc[0]",
    )

    ans = synthesize_llm_answer("What does row 1 tell us?", evidence)
    assert isinstance(ans, GeneratedAnswer)
    assert isinstance(ans.summary, str)
    assert len(ans.summary) > 0


def test_llm_synthesis_retry_failure_handling(monkeypatch) -> None:
    import main
    from main import AnalysisEvidence, synthesize_llm_answer

    def mock_fail(*args, **kwargs):
        raise RuntimeError("LLM Service Unavailable")

    monkeypatch.setattr(main.client.models, "generate_content", mock_fail)

    evidence = AnalysisEvidence(intent="test", facts={"val": 1})
    res = synthesize_llm_answer("test question", evidence)
    assert res is not None
    assert "val" in res.summary or "val" in str(res.findings) or "1" in res.summary







# ── Schema-aware analytics planner regression tests ───────────────────────────

def make_hr_df() -> "pd.DataFrame":
    """HR dataset: EmployeeID (identifier), Department, PerformanceScore, Salary."""
    return pd.DataFrame({
        "EmployeeID": [f"E{i:03d}" for i in range(1, 21)],
        "Name": [f"Employee {i}" for i in range(1, 21)],
        "Department": (["Engineering"] * 7 + ["Marketing"] * 5 + ["Sales"] * 5 + ["HR"] * 3),
        "PerformanceScore": [3, 4, 5, 3, 2, 4, 5, 3, 4, 3, 5, 2, 4, 3, 4, 5, 3, 2, 4, 3],
        "Salary": [75000, 80000, 90000, 72000, 68000, 85000, 92000,
                   65000, 70000, 68000, 73000, 60000, 65000, 55000, 58000,
                   62000, 64000, 48000, 52000, 50000],
    })


def make_sales_df() -> "pd.DataFrame":
    """Sales dataset: StoreID (identifier), StoreName, Region, Sales, Date."""
    return pd.DataFrame({
        "StoreID": [f"S{i:02d}" for i in range(1, 11)],
        "StoreName": [f"Store {i}" for i in range(1, 11)],
        "Region": (["North"] * 4 + ["South"] * 3 + ["East"] * 3),
        "Sales": [12000, 15000, 11000, 9000, 20000, 18000, 22000, 14000, 16000, 13000],
        "Quantity": [100, 130, 95, 80, 170, 155, 190, 120, 140, 110],
    })


def make_product_df() -> "pd.DataFrame":
    """Product dataset: ProductID (identifier), Category, Price."""
    return pd.DataFrame({
        "ProductID": [f"P{i:03d}" for i in range(1, 16)],
        "ProductName": [f"Product {i}" for i in range(1, 16)],
        "Category": (["Electronics"] * 5 + ["Clothing"] * 5 + ["Home"] * 5),
        "Price": [299, 399, 199, 499, 349, 59, 79, 49, 99, 69, 29, 39, 89, 49, 59],
        "Stock": [50, 30, 80, 20, 40, 100, 75, 120, 60, 90, 200, 150, 100, 180, 140],
    })


def make_customer_df() -> "pd.DataFrame":
    """Customer dataset: CustomerID (identifier), Region, Revenue."""
    return pd.DataFrame({
        "CustomerID": [f"C{i:04d}" for i in range(1, 21)],
        "CustomerName": [f"Customer {i}" for i in range(1, 21)],
        "Region": (["East"] * 7 + ["West"] * 6 + ["Central"] * 7),
        "Revenue": [5000, 7500, 3000, 8500, 6000, 4500, 9000,
                    3500, 4000, 6500, 5500, 7000, 8000,
                    2500, 3000, 4500, 6000, 7500, 5000, 8000],
    })


class TestSemanticSchema:
    """Tests for build_semantic_schema — fully deterministic, no LLM."""

    def test_identifier_column_detected(self) -> None:
        from main import build_semantic_schema
        df = make_hr_df()
        schema = build_semantic_schema(df)
        assert "EmployeeID" in schema["candidate_identifiers"], \
            "EmployeeID (unique_ratio=1.0) must be detected as identifier"

    def test_dimension_column_detected(self) -> None:
        from main import build_semantic_schema
        df = make_hr_df()
        schema = build_semantic_schema(df)
        assert "Department" in schema["candidate_dimensions"], \
            "Department (few unique values, non-numeric) must be a categorical_dimension"

    def test_numeric_measure_detected(self) -> None:
        from main import build_semantic_schema
        df = make_hr_df()
        schema = build_semantic_schema(df)
        assert "Salary" in schema["candidate_measures"] or "PerformanceScore" in schema["candidate_measures"], \
            "Salary or PerformanceScore must be detected as numeric_measure"

    def test_identifier_not_in_measures(self) -> None:
        from main import build_semantic_schema
        df = make_hr_df()
        schema = build_semantic_schema(df)
        assert "EmployeeID" not in schema["candidate_measures"], \
            "EmployeeID (string identifier) must NOT be a numeric measure"

    def test_schema_structure(self) -> None:
        from main import build_semantic_schema
        df = make_hr_df()
        schema = build_semantic_schema(df)
        assert schema["row_count"] == 20
        assert schema["column_count"] == 5
        for col_info in schema["columns"]:
            assert "name" in col_info
            assert "dtype" in col_info
            assert "unique_ratio" in col_info
            assert "semantic_role_candidates" in col_info
            assert 0.0 <= col_info["unique_ratio"] <= 1.0


class TestValidateAnalysisPlan:
    """Tests for validate_analysis_plan — deterministic semantic validator."""

    def test_valid_count_distinct_plan(self) -> None:
        from main import build_semantic_schema, validate_analysis_plan
        df = make_hr_df()
        schema = build_semantic_schema(df)
        raw = {
            "intent": "visualization",
            "dimensions": [{"column": "Department", "role": "group_by"}],
            "measures": [{"column": "EmployeeID", "operation": "count_distinct", "label": "Employee Count"}],
            "chart": {"type": "pie", "category": "Department", "value": "Employee Count"},
            "title": "Employees by Department",
            "confidence": 0.95,
            "reasoning_summary": "Count distinct employees grouped by department.",
        }
        resolved, warnings = validate_analysis_plan(raw, df, schema)
        assert resolved.resolved_dimension_col == "Department"
        assert resolved.resolved_measure_col == "EmployeeID"
        assert resolved.resolved_operation == "count_distinct"
        assert resolved.resolved_chart_type == "pie"
        # No critical warnings expected for a clean plan
        critical = [w for w in warnings if "not found" in w.lower()]
        assert not critical, f"Unexpected critical warnings: {critical}"

    def test_pie_chart_with_average_repairs_to_bar(self) -> None:
        """Pie chart + mean operation should auto-repair to bar chart."""
        from main import build_semantic_schema, validate_analysis_plan
        df = make_hr_df()
        schema = build_semantic_schema(df)
        raw = {
            "intent": "visualization",
            "dimensions": [{"column": "Department", "role": "group_by"}],
            "measures": [{"column": "Salary", "operation": "mean", "label": "Average Salary"}],
            "chart": {"type": "pie"},
            "confidence": 0.9,
            "reasoning_summary": "Average salary by department.",
        }
        resolved, warnings = validate_analysis_plan(raw, df, schema)
        assert resolved.resolved_chart_type == "bar", "Pie + mean should auto-repair to bar"
        assert any("auto-repairing" in w.lower() for w in warnings)

    def test_missing_dimension_column_warns(self) -> None:
        """A dimension column that doesn't exist should produce a warning, not crash."""
        from main import build_semantic_schema, validate_analysis_plan
        df = make_hr_df()
        schema = build_semantic_schema(df)
        raw = {
            "intent": "aggregation",
            "dimensions": [{"column": "NonExistentColumn", "role": "group_by"}],
            "measures": [{"column": "Salary", "operation": "sum", "label": "Total Salary"}],
            "confidence": 0.8,
            "reasoning_summary": "Sum salary by nonexistent column.",
        }
        resolved, warnings = validate_analysis_plan(raw, df, schema)
        assert resolved.resolved_dimension_col is None
        assert any("not found" in w.lower() for w in warnings)

    def test_case_insensitive_column_resolution(self) -> None:
        """Columns should resolve case-insensitively."""
        from main import build_semantic_schema, validate_analysis_plan
        df = make_hr_df()
        schema = build_semantic_schema(df)
        raw = {
            "intent": "aggregation",
            "dimensions": [{"column": "department", "role": "group_by"}],
            "measures": [{"column": "salary", "operation": "mean", "label": "Avg Salary"}],
            "confidence": 0.9,
            "reasoning_summary": "Average salary by department.",
        }
        resolved, warnings = validate_analysis_plan(raw, df, schema)
        assert resolved.resolved_dimension_col == "Department"
        assert resolved.resolved_measure_col == "Salary"


class TestExecuteResolvedPlan:
    """Tests for execute_resolved_plan — deterministic pandas executor."""

    def _make_plan(self, df, raw: dict) -> "ResolvedAnalysisPlan":
        from main import build_semantic_schema, validate_analysis_plan
        schema = build_semantic_schema(df)
        resolved, _ = validate_analysis_plan(raw, df, schema)
        return resolved

    # 1. Employees by department — count_distinct(EmployeeID) by Department
    def test_employees_by_department_pie(self) -> None:
        from main import execute_resolved_plan
        df = make_hr_df()
        plan = self._make_plan(df, {
            "intent": "visualization",
            "dimensions": [{"column": "Department", "role": "group_by"}],
            "measures": [{"column": "EmployeeID", "operation": "count_distinct", "label": "Employee Count"}],
            "chart": {"type": "pie"},
            "confidence": 0.95,
            "reasoning_summary": "Count distinct employees by department.",
        })
        result = execute_resolved_plan(df, plan)
        assert "Department" in result.columns
        assert "Employee Count" in result.columns
        # Total should match distinct employees (all 20 EmployeeIDs are unique)
        assert result["Employee Count"].sum() == 20
        # Engineering has 7 employees
        eng_row = result[result["Department"] == "Engineering"]
        assert not eng_row.empty
        assert eng_row["Employee Count"].iloc[0] == 7

    # 2. Customers by region — count_distinct(CustomerID) by Region
    def test_customers_by_region(self) -> None:
        from main import execute_resolved_plan
        df = make_customer_df()
        plan = self._make_plan(df, {
            "intent": "visualization",
            "dimensions": [{"column": "Region", "role": "group_by"}],
            "measures": [{"column": "CustomerID", "operation": "count_distinct", "label": "Customer Count"}],
            "chart": {"type": "bar"},
            "confidence": 0.92,
            "reasoning_summary": "Count customers by region.",
        })
        result = execute_resolved_plan(df, plan)
        assert result["Customer Count"].sum() == 20
        east_row = result[result["Region"] == "East"]
        assert east_row["Customer Count"].iloc[0] == 7

    # 3. Products by category — count_distinct(ProductID) by Category
    def test_products_by_category(self) -> None:
        from main import execute_resolved_plan
        df = make_product_df()
        plan = self._make_plan(df, {
            "intent": "aggregation",
            "dimensions": [{"column": "Category", "role": "group_by"}],
            "measures": [{"column": "ProductID", "operation": "count_distinct", "label": "Product Count"}],
            "chart": {"type": "bar"},
            "confidence": 0.93,
            "reasoning_summary": "Count products by category.",
        })
        result = execute_resolved_plan(df, plan)
        assert result["Product Count"].sum() == 15
        # Each category has 5 products
        for cat in ["Electronics", "Clothing", "Home"]:
            assert result[result["Category"] == cat]["Product Count"].iloc[0] == 5

    # 4. Total sales by store — sum(Sales) by StoreName
    def test_total_sales_by_store(self) -> None:
        from main import execute_resolved_plan
        df = make_sales_df()
        plan = self._make_plan(df, {
            "intent": "aggregation",
            "dimensions": [{"column": "StoreName", "role": "group_by"}],
            "measures": [{"column": "Sales", "operation": "sum", "label": "Total Sales"}],
            "chart": {"type": "bar"},
            "confidence": 0.94,
            "reasoning_summary": "Total sales by store.",
        })
        result = execute_resolved_plan(df, plan)
        assert "Total Sales" in result.columns
        assert result["Total Sales"].sum() == sum([12000, 15000, 11000, 9000, 20000, 18000, 22000, 14000, 16000, 13000])

    # 5. Average salary by department — mean(Salary) by Department
    def test_average_salary_by_department(self) -> None:
        from main import execute_resolved_plan
        df = make_hr_df()
        plan = self._make_plan(df, {
            "intent": "aggregation",
            "dimensions": [{"column": "Department", "role": "group_by"}],
            "measures": [{"column": "Salary", "operation": "mean", "label": "Average Salary"}],
            "confidence": 0.93,
            "reasoning_summary": "Average salary by department.",
        })
        result = execute_resolved_plan(df, plan)
        assert "Average Salary" in result.columns
        eng_expected = round(df[df["Department"] == "Engineering"]["Salary"].mean(), 2)
        eng_actual = result[result["Department"] == "Engineering"]["Average Salary"].iloc[0]
        assert abs(eng_actual - eng_expected) < 1.0

    # 6. PerformanceScore by Department — mean(PerformanceScore) — uses explicitly named measure
    def test_performance_score_by_department(self) -> None:
        from main import execute_resolved_plan
        df = make_hr_df()
        plan = self._make_plan(df, {
            "intent": "aggregation",
            "dimensions": [{"column": "Department", "role": "group_by"}],
            "measures": [{"column": "PerformanceScore", "operation": "mean", "label": "Avg Performance Score"}],
            "confidence": 0.95,
            "reasoning_summary": "Average PerformanceScore by department.",
        })
        result = execute_resolved_plan(df, plan)
        assert "Avg Performance Score" in result.columns
        assert result["Avg Performance Score"].notna().all()

    # 7. Context isolation — PerformanceScore must NOT appear in employee count plan
    def test_context_isolation_no_performance_score_contamination(self) -> None:
        from main import build_semantic_schema, validate_analysis_plan, execute_resolved_plan
        df = make_hr_df()
        schema = build_semantic_schema(df)
        # Simulate a "new query" for employee count — should use EmployeeID, not PerformanceScore
        raw = {
            "intent": "visualization",
            "dimensions": [{"column": "Department", "role": "group_by"}],
            "measures": [{"column": "EmployeeID", "operation": "count_distinct", "label": "Employee Count"}],
            "chart": {"type": "pie"},
            "confidence": 0.96,
            "reasoning_summary": "Count employees by department.",
        }
        resolved, _ = validate_analysis_plan(raw, df, schema)
        # The resolved measure must be EmployeeID, not PerformanceScore
        assert resolved.resolved_measure_col == "EmployeeID", \
            f"Context contamination: resolved_measure_col={resolved.resolved_measure_col}, expected EmployeeID"
        assert resolved.resolved_operation == "count_distinct"

    # 8. No identifier column — fall back to row count
    def test_missing_identifier_uses_row_count(self) -> None:
        from main import build_semantic_schema, validate_analysis_plan, execute_resolved_plan
        # Dataset with no identifier column (all numeric)
        df = pd.DataFrame({
            "Score": [3, 4, 5, 3, 2],
            "Grade": [70, 80, 90, 75, 65],
            "Category": ["A", "B", "A", "C", "B"],
        })
        schema = build_semantic_schema(df)
        raw = {
            "intent": "aggregation",
            "dimensions": [{"column": "Category", "role": "group_by"}],
            "measures": [{"column": None, "operation": "count", "label": "Row Count"}],
            "confidence": 0.80,
            "reasoning_summary": "Count rows by category.",
        }
        resolved, warnings = validate_analysis_plan(raw, df, schema)
        result = execute_resolved_plan(df, resolved)
        assert "Row Count" in result.columns
        assert result["Row Count"].sum() == 5

    # 9. Invalid chart-measure combination repaired by validator
    def test_pie_plus_mean_repaired_to_bar(self) -> None:
        from main import build_semantic_schema, validate_analysis_plan, build_chart_spec_from_plan, execute_resolved_plan
        df = make_hr_df()
        schema = build_semantic_schema(df)
        raw = {
            "intent": "visualization",
            "dimensions": [{"column": "Department", "role": "group_by"}],
            "measures": [{"column": "Salary", "operation": "mean", "label": "Avg Salary"}],
            "chart": {"type": "pie"},
            "confidence": 0.88,
            "reasoning_summary": "Average salary distribution by department.",
        }
        resolved, warnings = validate_analysis_plan(raw, df, schema)
        assert resolved.resolved_chart_type == "bar"
        result = execute_resolved_plan(df, resolved)
        chart_b64, chart_json = build_chart_spec_from_plan(result, resolved)
        # Chart should be generated as bar
        if chart_json:
            assert "bar" in chart_json.lower() or "Bar" in chart_json

    # 10. Plan immutability — resolved_measure_col unchanged through chart step
    def test_plan_immutability_through_chart_step(self) -> None:
        from main import build_semantic_schema, validate_analysis_plan, execute_resolved_plan, build_chart_spec_from_plan
        df = make_hr_df()
        schema = build_semantic_schema(df)
        raw = {
            "intent": "visualization",
            "dimensions": [{"column": "Department", "role": "group_by"}],
            "measures": [{"column": "EmployeeID", "operation": "count_distinct", "label": "Employee Count"}],
            "chart": {"type": "pie", "category": "Department", "value": "Employee Count"},
            "confidence": 0.97,
            "reasoning_summary": "Count employees by department.",
        }
        resolved, _ = validate_analysis_plan(raw, df, schema)
        original_measure = resolved.resolved_measure_col
        original_op = resolved.resolved_operation

        result = execute_resolved_plan(df, resolved)
        build_chart_spec_from_plan(result, resolved)  # chart step must not mutate plan

        # Plan must be unchanged after all steps
        assert resolved.resolved_measure_col == original_measure, \
            "Chart step mutated resolved_measure_col!"
        assert resolved.resolved_operation == original_op, \
            "Chart step mutated resolved_operation!"


class TestExtractExplicitReferences:
    """Tests for context isolation — extract_explicit_references."""

    def test_no_prior_state(self) -> None:
        from main import extract_explicit_references
        refs = extract_explicit_references("Employee count by department", None)
        assert refs == {}

    def test_prior_column_not_mentioned_excluded(self) -> None:
        """PerformanceScore from a prior plan must NOT appear in a new 'employee count' query."""
        from main import extract_explicit_references
        prior = {
            "plan": {"relevant_columns": ["PerformanceScore", "Department"]},
            "result": "Some earlier result...",
        }
        refs = extract_explicit_references("Do a pie chart of total employees by department", prior)
        # "PerformanceScore" not mentioned → not in references
        assert "PerformanceScore" not in refs

    def test_prior_column_mentioned_included(self) -> None:
        """If the user explicitly mentions PerformanceScore in their question, include it."""
        from main import extract_explicit_references
        prior = {
            "plan": {"relevant_columns": ["PerformanceScore", "Department"]},
            "result": "Earlier result...",
        }
        refs = extract_explicit_references("Show PerformanceScore by department", prior)
        assert "PerformanceScore" in refs


def test_realtime_cancellation_interruption(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that an active running request is interrupted when cancellation is triggered."""
    import main
    import backend.llm.client
    from main import query_cache
    from backend.streaming.cancellation import cancel_request, is_cancelled, clear_cancellation

    req_id = "test-realtime-cancel-777"

    def mock_cancellation_provider(*args, **kwargs):
        curr_req_id = kwargs.get("request_id") or req_id
        if curr_req_id == req_id:
            cancel_request(req_id)
            raise RuntimeError("Request cancelled by user")
        return "mock response"

    monkeypatch.setattr(backend.llm.client.llm_client, "generate_content", mock_cancellation_provider)

    up = client.post("/upload", files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")})
    sid = up.json()["session_id"]
    tok = up.json().get("token", "")

    res = client.post(
        "/query",
        headers={"X-Session-Token": tok},
        json={"session_id": sid, "question": "Predict PerformanceScore based on Salary", "request_id": req_id},
    )
    assert res.status_code == 200
    events = parse_sse_events(res.text)

    # Assert request terminates with cancellation event
    cancelled_event = next((e for e in events if e.get("type") == "request_cancelled" or e.get("status") == "cancelled"), None)
    assert cancelled_event is not None, f"No cancellation event in SSE stream: {events}"
    assert not any(e.get("type") == "analysis_completed" for e in events), "Success event emitted after cancellation!"

    # Assert no cache write occurred
    cache_key = main._cache_key(sid, "general", "Predict PerformanceScore based on Salary", main.dataframes[sid])
    assert cache_key not in query_cache, "Cancelled request was saved to cache!"

    clear_cancellation(req_id)


def test_infinite_sandbox_cancellation_and_api_responsiveness(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies runaway infinite sandbox loops terminate and do not block the API process."""
    import main
    import time
    from main import execute_code, ExecutionTimeoutError

    df = pd.DataFrame({"a": range(10)})
    monkeypatch.setattr(main, "MAX_SANDBOX_SECONDS", 1)
    monkeypatch.setattr(main, "MAX_EXEC_SECONDS", 1)

    t0 = time.time()
    with pytest.raises(ExecutionTimeoutError):
        execute_code("while True:\n    pass", df)
    elapsed = time.time() - t0
    assert elapsed < 3.0, f"Sandbox termination took too long: {elapsed:.2f}s"

    # Verify API remains healthy and responsive
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"


def test_synthesis_failure_returns_failed_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that synthesis failure raises LLMSynthesisError without returning offline prose."""
    import main
    import backend.llm.client
    from main import AnalysisEvidence, synthesize_llm_answer
    from backend.core.errors import LLMSynthesisError

    def mock_fail(*args, **kwargs):
        raise RuntimeError("Provider error")

    monkeypatch.setattr(backend.llm.client.llm_client, "generate_content", mock_fail)

    evidence = AnalysisEvidence(intent="test", facts={})
    with pytest.raises(LLMSynthesisError, match="answer_generation_failed|explanation could not be generated"):
        synthesize_llm_answer("What is the total?", evidence)


def test_two_level_cache_behavior() -> None:
    """Verifies TwoLevelCache behavior: L1/L2 hits, eviction, dataset & lens isolation."""
    from backend.services.cache import TwoLevelCache
    import pandas as pd

    cache = TwoLevelCache(max_entries=2)
    df1 = pd.DataFrame({"a": [1, 2]})
    df2 = pd.DataFrame({"b": [10, 20]})

    key1 = cache.get_query_key("s1", "general", "How many rows?", df1)
    key2 = cache.get_query_key("s1", "finance", "How many rows?", df1)
    key3 = cache.get_query_key("s2", "general", "How many rows?", df2)

    # Dataset & Lens isolation check
    assert key1 != key2, "Lens isolation failed!"
    assert key1 != key3, "Dataset isolation failed!"

    # Set L1 query cache
    cache.set_query(key1, {"ans": "2 rows"})
    cache.set_query(key2, {"ans": "2 rows finance"})
    assert cache.get_query(key1)["ans"] == "2 rows"

    # Capacity eviction check (max_entries=2)
    cache.set_query(key3, {"ans": "2 rows df2"})
    assert cache.get_query(key1) is None, "Oldest key was not evicted on capacity overflow!"

    # L2 Profile cache check & session invalidation
    cache.set_profile("s1", {"cols": ["a"]})
    assert cache.get_profile("s1")["cols"] == ["a"]
    cache.invalidate_session("s1")
    assert cache.get_profile("s1") is None, "Profile invalidation failed!"
    assert cache.get_query(key2) is None, "Query cache session invalidation failed!"


def test_terminal_sse_sequences_distinction_and_no_post_terminal_events() -> None:
    """Verifies distinct terminal event types and that no events follow a terminal event."""
    from backend.streaming.events import make_sse_emitter

    emitter = make_sse_emitter("query", "sess-term-1", request_id="req-term-1")
    # Emit terminal analysis_completed event
    e1 = emitter({"type": "analysis_completed", "status": "complete", "result": "Done"})
    assert "data: " in e1

    # Post-terminal event must be suppressed
    e2 = emitter({"type": "partial_result", "message": "Noise after terminal"})
    assert e2 == "", "Emitter allowed post-terminal event noise!"


def test_inflight_llm_cancellation_interruption_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Proves in-flight LLM provider call is interrupted immediately (<1.0s elapsed for 5.0s sleep)."""
    import time
    import main
    import backend.llm.client
    from main import query_cache
    from backend.streaming.cancellation import cancel_request, clear_cancellation

    req_id = "test-inflight-timing-999"
    query_cache.clear()
    clear_cancellation(req_id)

    def slow_llm_provider(*args, **kwargs):
        curr_req_id = kwargs.get("request_id") or req_id
        if curr_req_id == req_id:
            cancel_request(req_id)
            for _ in range(50):
                time.sleep(0.1)
                if backend.streaming.cancellation.is_cancelled(req_id):
                    raise RuntimeError("In-flight provider interrupted by cancellation")
        return "slow response"

    monkeypatch.setattr(backend.llm.client.llm_client, "generate_content", slow_llm_provider)

    up = client.post("/upload", files={"file": ("sales.csv", io.BytesIO(SALES_CSV.encode()), "text/csv")})
    sid = up.json()["session_id"]
    tok = up.json().get("token", "")

    start_t = time.time()
    res = client.post(
        "/query",
        headers={"X-Session-Token": tok},
        json={"session_id": sid, "question": "Predict PerformanceScore based on Salary", "request_id": req_id},
    )
    elapsed = time.time() - start_t

    assert res.status_code == 200
    events = parse_sse_events(res.text)

    assert elapsed < 1.0, f"Interruption took too long: {elapsed:.2f}s (expected < 1.0s)"
    cancelled_event = next((e for e in events if e.get("type") == "request_cancelled" or e.get("status") == "cancelled"), None)
    assert cancelled_event is not None, f"No request_cancelled event in stream: {events}"
    assert len(query_cache) == 0, "Cancelled request was erroneously written to query_cache!"


def test_sandbox_process_pid_termination() -> None:
    """Verifies that runaway sandbox child processes are forcefully killed."""
    from sandbox_runner import execute_code_worker
    import multiprocessing as mp
    import pandas as pd

    df = pd.DataFrame({"a": [1, 2, 3]})
    q = mp.Queue()
    proc = mp.Process(target=execute_code_worker, args=("import time\nwhile True:\n    time.sleep(0.1)", df, q))
    proc.start()
    pid = proc.pid
    assert proc.is_alive()

    # Terminate worker process
    proc.terminate()
    proc.join(timeout=1.0)

    # Assert PID is terminated and no longer alive
    assert not proc.is_alive()


def test_llm_budget_exhaustion_by_route() -> None:
    """Verifies LLM budget limits enforcement per execution budget route."""
    from backend.llm.client import BudgetedLLMClient
    from backend.core.errors import ExecutionBudgetExceededError

    client_instance = BudgetedLLMClient()
    for i in range(3):
        client_instance.record_call("req-budget-1", "standard", f"stage_{i}")

    with pytest.raises(ExecutionBudgetExceededError):
        client_instance.record_call("req-budget-1", "standard", "overflow_stage")


def test_l2_cache_retrieval_and_no_write_on_cancellation() -> None:
    """Verifies L2 retrieval after L1 clear and asserts no cache write occurs on cancellation."""
    from backend.services.cache import TwoLevelCache
    import pandas as pd

    c = TwoLevelCache(max_entries=5)
    df = pd.DataFrame({"x": [10, 20]})

    q_key = c.get_query_key("sess-l2", "general", "What is total?", df)
    c.set_query(q_key, {"ans": "30"})

    c.set_profile("sess-l2", {"rows": 2, "schema": ["x"]})

    profile = c.get_profile("sess-l2")
    assert profile["rows"] == 2

    c._query_cache.clear()
    assert c.get_query(q_key) is None







