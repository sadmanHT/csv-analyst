import io
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from main import app, dataframes, execute_code, train_predictive_model

client = TestClient(app)


def make_csv(content: str) -> bytes:
    return content.encode()


SAMPLE_CSV = "name,age,salary\nAlice,30,50000\nBob,25,45000\nCarla,35,60000\n"


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


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
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ImportError):
        execute_code("import os\nresult = os.getcwd()", df)


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


# ── Predictive model ────────────────────────────────────────────────────

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
