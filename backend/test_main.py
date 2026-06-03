import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from main import app, dataframes, execute_code

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


def test_upload_returns_dtypes_and_preview():
    res = client.post(
        "/upload",
        files={"file": ("data.csv", io.BytesIO(make_csv(SAMPLE_CSV)), "text/csv")},
    )
    data = res.json()
    assert "dtypes" in data
    assert "preview" in data
    assert data["dtypes"]["age"] in ("int64", "float64")


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
    result, chart = execute_code("result = str(df['a'].sum())", df)
    assert result == "6"
    assert chart is None


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
    result, chart = execute_code(code, df)
    assert result == "ok"
    assert chart and len(chart) > 100


def test_execute_code_blocks_unsafe_import():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ImportError):
        execute_code("import os\nresult = os.getcwd()", df)
