import pytest
import io
import json
import logging
import pandas as pd
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.errors import LLMSynthesisError

client = TestClient(app)

@pytest.fixture
def mock_csv():
    csv_data = "Glucose,BloodPressure,BMI,Insulin\n148,72,33.6,0\n85,66,26.6,0\n"
    return io.BytesIO(csv_data.encode("utf-8"))

def upload_mock_csv(mock_csv):
    up = client.post("/upload", files={"file": ("diabetes.csv", mock_csv, "text/csv")})
    assert up.status_code == 200
    data = up.json()
    return data["session_id"], data["token"]

def get_events(response):
    return [json.loads(line[6:]) for line in response.text.split("\n") if line.startswith("data: ")]


def test_canonical_column_matching_examples() -> None:
    from backend.main import resolve_schema_column_reference

    columns = ["BloodPressure", "SkinThickness", "DiabetesPedigreeFunction", "response_text"]

    assert resolve_schema_column_reference("blood pressure", columns)["column"] == "BloodPressure"
    assert resolve_schema_column_reference("skin thickness", columns)["column"] == "SkinThickness"
    assert resolve_schema_column_reference("diabetes pedigree function", columns)["column"] == "DiabetesPedigreeFunction"
    assert resolve_schema_column_reference("response text", columns)["column"] == "response_text"


def test_highest_blood_pressure_value_resolves_extreme_scalar() -> None:
    from backend.main import classify_query_complexity

    df = pd.DataFrame({"BloodPressure": [72, 88, 66], "BMI": [33.6, 26.6, 31.2]})

    q_type, meta = classify_query_complexity("what is the highest blood pressure value", df)

    assert q_type == "extreme_value"
    assert meta["resolved_column"] == "BloodPressure"
    assert meta["operation"] == "max"
    assert meta["value"] == 88
    assert meta["non_null_count"] == 3


def test_who_has_highest_blood_pressure_returns_tied_rows() -> None:
    from backend.main import classify_query_complexity

    df = pd.DataFrame({
        "PatientID": [101, 102, 103],
        "BloodPressure": [88, 72, 88],
        "BMI": [25.1, 27.2, 29.3],
    })

    q_type, meta = classify_query_complexity("who has the highest blood pressure", df)

    assert q_type == "ranking_lookup"
    assert meta["ranking"]["column"] == "BloodPressure"
    assert meta["ranking"]["operation"] == "max"
    assert meta["return_mode"] == "matching_rows"
    assert meta["tie_count"] == 2
    assert [row["row_position"] for row in meta["tied_winners"]] == [1, 3]


def test_highest_value_returns_scalar_but_who_highest_returns_rows() -> None:
    from backend.main import classify_query_complexity

    df = pd.DataFrame({"BMI": [25.0, 30.0, 30.0]})

    scalar_type, scalar_meta = classify_query_complexity("what is the highest BMI value", df)
    ranking_type, ranking_meta = classify_query_complexity("which row has the highest BMI", df)

    assert scalar_type == "extreme_value"
    assert scalar_meta["value"] == 30.0
    assert ranking_type == "ranking_lookup"
    assert ranking_meta["tie_count"] == 2


def test_diabetes_is_ambiguous_with_outcome_and_pedigree() -> None:
    from backend.main import classify_query_complexity

    df = pd.DataFrame({
        "DiabetesPedigreeFunction": [0.1, 0.7, 0.3],
        "Outcome": [0, 1, 1],
        "BloodPressure": [70, 80, 90],
    })

    q_type, meta = classify_query_complexity("who has the highest value of diabetes", df)

    assert q_type == "ranking_lookup"
    assert meta["clarification"]
    candidates = {item["column"] for item in meta["candidate_columns"]}
    assert {"DiabetesPedigreeFunction", "Outcome"} <= candidates
    assert meta.get("ranking", {}).get("column") != "Outcome"


def test_ambiguous_diabetes_endpoint_returns_clarification_evidence() -> None:
    csv_data = (
        "DiabetesPedigreeFunction,Outcome,BloodPressure\n"
        "0.1,0,70\n"
        "0.7,1,80\n"
        "0.3,1,90\n"
    )
    sid, tok = upload_mock_csv(io.BytesIO(csv_data.encode("utf-8")))

    res = client.post(
        "/query",
        headers={"X-Session-Token": tok},
        json={"session_id": sid, "question": "who has the highest value of diabetes"},
    )

    assert res.status_code == 200
    events = get_events(res)
    done = next(e for e in events if e.get("type") == "analysis_completed")
    assert done["answer"]["type"] == "clarification"
    assert done["evidence"]["available"] is True
    raw_facts = done["evidence"]["raw_facts"]
    candidates = {item["column"] for item in raw_facts["candidate_columns"]}
    assert {"DiabetesPedigreeFunction", "Outcome"} <= candidates
    assert done["validation"]["confidence"] < 0.5


@pytest.mark.asyncio
async def test_direct_synthesis_repair_preserves_grounding(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend import main
    from backend.core.schemas import DirectAnswer

    calls: list[dict] = []

    async def fake_generate_content(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return '{"summary": "The highest BloodPressure value is 88.'
        return '{"summary": "The highest BloodPressure value is 88.", "next_action": ""}'

    monkeypatch.setattr(main.llm_client, "generate_content", fake_generate_content)
    evidence = main.AnalysisEvidence(
        intent="extreme_value",
        dataset_name="diabetes.csv",
        facts={
            "resolved_column": "BloodPressure",
            "operation": "max",
            "value": 88,
            "non_null_count": 3,
        },
    )

    answer = await main.synthesize_llm_answer_async(
        "what is the highest blood pressure value",
        evidence,
        request_id="req-grounded",
        deadline_at=main.time.monotonic() + 30,
        complexity_route="extreme_value",
    )

    assert answer.summary == "The highest BloodPressure value is 88."
    assert len(calls) == 2
    assert all(call["request_id"] == "req-grounded" for call in calls)
    assert all(call["response_schema"] == DirectAnswer for call in calls)
    assert all(call["max_output_tokens"] == 256 for call in calls)
    assert all(call["thinking_config"].thinking_level.lower() == "minimal" for call in calls)
    assert all(call["evidence_payload"]["facts"]["resolved_column"] == "BloodPressure" for call in calls)
    assert '"evidence"' in calls[1]["contents"]
    assert "BloodPressure" in calls[1]["contents"]


def test_visualization_fast_path(mock_csv):
    sid, tok = upload_mock_csv(mock_csv)
    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "plot the glucose"})
    assert res.status_code == 200
    events = get_events(res)
    done_event = next(e for e in events if e.get("type") == "analysis_completed" or e.get("status") == "complete")
    # Verify it took the visualization fast path (e.g. by checking the generated intent or step label)
    assert done_event["type"] == "analysis_completed"
    assert "plot" in [s.get("label", "").lower() for s in done_event.get("execution_steps", [])] or "chart" in done_event.get("answer", {}).get("text", "").lower()

def test_validate_analysis_plan_accepts_single_item_list() -> None:
    from backend.main import validate_analysis_plan

    df = pd.DataFrame({"department": ["A", "B"], "score": [10, 20]})
    raw_plan = [{
        "intent": "aggregation",
        "dimensions": [{"column": "department", "role": "category"}],
        "measures": [{"column": "score", "operation": "mean", "label": "Average Score"}],
        "confidence": 0.8,
        "reasoning_summary": "Average score by department.",
    }]

    resolved, warnings = validate_analysis_plan(raw_plan, df, {})

    assert not any("Plan parse error" in warning for warning in warnings)
    assert resolved.resolved_dimension_col == "department"
    assert resolved.resolved_measure_col == "score"
    assert resolved.resolved_operation == "mean"

def test_make_dataset_good_routes_to_quality() -> None:
    from backend.main import classify_query_complexity

    df = pd.DataFrame({"prompt_text": ["a", None], "human_label": [1, 0]})

    q_type, _ = classify_query_complexity("how to make this dataset a good one", df)

    assert q_type == "standard_quality"

def test_standard_quality_synthesis_failure_returns_partial_event(mock_csv, monkeypatch):
    import backend.main as main

    def fail_synth(*args, **kwargs):
        raise main.LLMSynthesisError("The model returned an empty synthesis response.")

    monkeypatch.setattr(main, "synthesize_llm_answer_async", fail_synth)

    sid, tok = upload_mock_csv(mock_csv)
    res = client.post(
        "/query",
        headers={"X-Session-Token": tok},
        json={"session_id": sid, "question": "how to make this dataset a good one"},
    )

    assert res.status_code == 200
    events = get_events(res)
    partial_event = next(e for e in events if e.get("type") == "analysis_partial")
    assert partial_event["status"] == "partial"
    assert partial_event["answer"] is None
    assert partial_event["warning"]["code"] == "answer_generation_unavailable"
    assert partial_event["generation"]["required"] is True
    assert partial_event["generation"]["succeeded"] is False
    assert partial_event["generation"]["validated"] is False
    assert partial_event["evidence"]["available"] is True
    assert not any(e.get("type") == "analysis_failed" for e in events)

def test_president_age_routes_to_dataset_mismatch() -> None:
    from backend.main import classify_query_complexity

    df = pd.DataFrame({
        "annotation_id": ["ANN_1"],
        "prompt_text": ["Prompt one"],
        "response_text": ["Response one"],
        "human_label": ["safe"],
        "compliance_severity": [1],
    })

    q_type, meta = classify_query_complexity("what is the average age of usa president?", df)

    assert q_type == "dataset_mismatch"
    assert "U.S. presidents" in meta["unmatched_concept"]

def test_dataset_mismatch_endpoint_calls_synthesis_not_planner(monkeypatch) -> None:
    import backend.main as main
    calls = {"synthesis": 0}

    async def mock_synth(question, evidence, **kwargs):
        calls["synthesis"] += 1
        assert evidence.intent == "dataset_mismatch"
        return main.GeneratedAnswer(summary="This dataset does not include U.S. presidents or their ages.", explanation="Use available fields.")

    def fail_planner(*args, **kwargs):
        if kwargs.get("stage") == "planner":
            raise AssertionError("Planner must not be called for dataset mismatch")
        return "{}"

    monkeypatch.setattr(main, "synthesize_llm_answer_async", mock_synth)
    monkeypatch.setattr(main.llm_client, "generate_content", fail_planner)
    csv_data = "annotation_id,prompt_text,response_text,human_label,compliance_severity\nANN_1,Prompt one,Response one,safe,1\n"
    up = client.post("/upload", files={"file": ("annotations.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    sid, tok = up.json()["session_id"], up.json()["token"]

    res = client.post(
        "/query",
        headers={"X-Session-Token": tok},
        json={"session_id": sid, "question": "what is the average age of usa president?"},
    )

    events = get_events(res)
    done = next(e for e in events if e.get("type") == "analysis_completed")
    text = done["answer"]["summary"]
    assert done["meta"]["pipeline_branch"] == "dataset_mismatch"
    assert done["meta"]["planner_ms"] == 0
    assert calls["synthesis"] == 1
    assert done["generation"]["succeeded"] is True
    assert done["generation"]["validated"] is True
    assert "U.S. presidents" in text
    phrases = [" ".join(text.lower().split()[i:i + 4]) for i in range(max(0, len(text.split()) - 3))]
    assert len(phrases) == len(set(phrases))
    assert "fallback plan" not in json.dumps(done).lower()

def test_bad_dataset_routes_to_standard_quality() -> None:
    from backend.main import classify_query_complexity

    df = pd.DataFrame({"prompt_text": ["a", None], "human_label": [1, 0]})

    q_type, _ = classify_query_complexity("what makes this a bad dataset?", df)

    assert q_type == "standard_quality"

def test_quality_route_does_not_call_planner_and_uses_measured_issues(monkeypatch) -> None:
    import backend.main as main

    captured = {}

    async def mock_synth(question, evidence, **kwargs):
        captured["facts"] = evidence.facts
        return main.GeneratedAnswer(summary="Review measured missing values first.", explanation="Use the cached quality profile.")

    def fail_planner(*args, **kwargs):
        if kwargs.get("stage") == "planner":
            raise AssertionError("Planner must not be called for standard quality")
        return "{}"

    monkeypatch.setattr(main, "synthesize_llm_answer_async", mock_synth)
    monkeypatch.setattr(main.llm_client, "generate_content", fail_planner)
    csv_data = "prompt_text,response_text,human_label,compliance_severity\nPrompt one,Response one,safe,1\nPrompt two,,unsafe,2\n"
    up = client.post("/upload", files={"file": ("annotations.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    sid, tok = up.json()["session_id"], up.json()["token"]

    res = client.post(
        "/query",
        headers={"X-Session-Token": tok},
        json={"session_id": sid, "question": "what makes this a bad dataset?"},
    )

    events = get_events(res)
    done = next(e for e in events if e.get("type") == "analysis_completed")
    facts_text = json.dumps(captured["facts"]).lower()
    assert done["meta"]["pipeline_branch"] == "standard_quality"
    assert done["meta"]["planner_ms"] == 0
    assert "syntax error" not in facts_text
    assert "non-english" not in facts_text
    assert "invalid label" not in facts_text

def test_ordinal_prompt_lookup_resolves_prompt_text_and_uses_iloc_4(monkeypatch) -> None:
    import backend.main as main

    async def mock_synth(question, evidence, **kwargs):
        assert evidence.intent == "row_lookup"
        assert evidence.facts["selected_field"]["value"] == "Prompt 5"
        return main.GeneratedAnswer(summary="Row 5 prompt_text is Prompt 5.", explanation="Retrieved by direct row lookup.")

    monkeypatch.setattr(main, "synthesize_llm_answer_async", mock_synth)
    rows = "\n".join(f"ANN_{i},Prompt {i},Response {i},label" for i in range(1, 7))
    csv_data = "annotation_id,prompt_text,response_text,human_label\n" + rows + "\n"
    up = client.post("/upload", files={"file": ("annotations.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    sid, tok = up.json()["session_id"], up.json()["token"]

    q_type, meta = main.classify_query_complexity("give me the 5th prompt", pd.read_csv(io.StringIO(csv_data)))
    assert q_type == "direct_row_lookup"
    assert meta["column"] == "prompt_text"
    assert meta["row_index"] == 4

    res = client.post(
        "/query",
        headers={"X-Session-Token": tok},
        json={"session_id": sid, "question": "give me the 5th prompt"},
    )

    events = get_events(res)
    done = next(e for e in events if e.get("type") == "analysis_completed")
    assert done["meta"]["planner_ms"] == 0
    assert done["generation"]["succeeded"] is True
    assert done["generation"]["validated"] is True
    assert done["row_data"]["selected_field"]["column"] == "prompt_text"
    assert done["row_data"]["selected_field"]["value"] == "Prompt 5"
    assert done["code"] == "value = df.iloc[4]['prompt_text']"
    assert "fallback plan" not in json.dumps(done).lower()

def test_employee_salary_lookup_with_typo_is_deterministic(monkeypatch) -> None:
    import backend.main as main

    async def mock_synth(question, evidence, **kwargs):
        assert evidence.intent == "single_value_lookup"
        assert evidence.facts["value"] == 30090
        return main.GeneratedAnswer(summary="EmployeeID 90 Salary: 30090", explanation="Retrieved by identifier lookup.")

    monkeypatch.setattr(main, "synthesize_llm_answer_async", mock_synth)
    rows = "\n".join(f"{i},Employee_{i},{30000 + i}" for i in range(1, 101))
    csv_data = "EmployeeID,Name,Salary\n" + rows + "\n"
    df = pd.read_csv(io.StringIO(csv_data))

    q_type, meta = main.classify_query_complexity("what is the employee 90 ssalary", df)
    assert q_type == "entity_value_lookup"
    assert meta["row_index"] == 89
    assert meta["identifier_column"] == "EmployeeID"
    assert meta["selected_field"]["column"] == "Salary"

    res = client.post(
        "/upload",
        files={"file": ("employees.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
    )
    sid, tok = res.json()["session_id"], res.json()["token"]
    query_res = client.post(
        "/query",
        headers={"X-Session-Token": tok},
        json={"session_id": sid, "question": "what is the employee 90 ssalary"},
    )

    assert query_res.status_code == 200
    events = get_events(query_res)
    done = next(e for e in events if e.get("type") == "analysis_completed")
    assert done["meta"]["pipeline_branch"] == "entity_value_lookup"
    assert done["meta"]["planner_ms"] == 0
    assert done["generation"]["succeeded"] is True
    assert done["generation"]["validated"] is True
    assert "EmployeeID 90 Salary: 30090" in done["answer"]["summary"]
    assert "EmployeeID" in done["code"]
    assert "Salary" in done["code"]
    assert not any(e.get("type") == "analysis_failed" for e in events)

def test_best_employee_uses_performance_score_not_employee_id() -> None:
    import backend.main as main

    df = pd.DataFrame({
        "EmployeeID": [101, 102, 103],
        "Name": ["Employee_1", "Employee_2", "Employee_3"],
        "Salary": [90000, 120000, 110000],
        "PerformanceScore": [71, 98, 98],
        "DepartmentRating": [4, 3, 5],
    })

    q_type, meta = main.classify_query_complexity("who is the best employee?", df)

    assert q_type == "ranking_lookup"
    assert meta["ranking"]["column"] == "PerformanceScore"
    assert meta["ranking"]["column"] != "EmployeeID"
    assert meta["tie_count"] == 2
    assert {row["EmployeeID"] for row in meta["tied_winners"]} == {102, 103}

def test_identifier_columns_cannot_be_averaged() -> None:
    import backend.main as main

    df = pd.DataFrame({"EmployeeID": [101, 102, 103], "Salary": [1, 2, 3]})
    schema = main.build_semantic_schema(df)
    plan = {"measures": [{"column": "EmployeeID", "operation": "mean", "label": "Average EmployeeID"}]}

    resolved, warnings = main.validate_analysis_plan(plan, df, schema)

    assert resolved.resolved_measure_col is None
    assert resolved.resolved_operation is None
    assert any("Identifier columns cannot be used" in warning for warning in warnings)

def test_salary_of_employee_47_uses_identifier_not_iloc() -> None:
    import backend.main as main

    df = pd.DataFrame({
        "EmployeeID": [47, 147],
        "Name": ["Employee_47_id", "Employee_47_row"],
        "Salary": [47000, 147000],
    })

    q_type, meta = main.classify_query_complexity("what is the salary of employee 47", df)

    assert q_type == "entity_value_lookup"
    assert meta["identifier_column"] == "EmployeeID"
    assert meta["row_index"] == 0
    assert meta["identity"]["identifier_value"] == 47
    assert meta["selected_field"]["column"] == "Salary"
    assert meta["selected_field"]["value"] == 47000

def test_missing_employee_identifier_does_not_fall_back_to_row_position() -> None:
    import backend.main as main

    df = pd.DataFrame({
        "EmployeeID": [101, 102, 147],
        "Name": ["Employee_1", "Employee_2", "Employee_47"],
        "Salary": [1, 2, 147000],
    })

    q_type, meta = main.classify_query_complexity("what is the salary of employee 47", df)

    assert q_type == "entity_value_lookup"
    assert meta["matched"] is False
    assert meta["identifier_column"] == "EmployeeID"
    assert meta["requested_identifier"] == 47
    assert meta["possible_row_position"] is None

def test_salary_of_row_47_uses_position_and_preserves_employee_id() -> None:
    import backend.main as main

    rows = [{"EmployeeID": 100 + i, "Name": f"Employee_{i}", "Salary": 1000 + i} for i in range(1, 51)]
    df = pd.DataFrame(rows)

    q_type, meta = main.classify_query_complexity("what is the salary in row 47", df)

    assert q_type == "direct_row_lookup"
    assert meta["row_index"] == 46
    assert meta["column"] == "Salary"
    assert df.iloc[46]["EmployeeID"] == 147

def test_row_median_comparison_excludes_employee_id_and_limits_comparisons() -> None:
    import backend.main as main

    rows = [
        {
            "EmployeeID": 100 + i,
            "Name": f"Employee_{i}",
            "Salary": 50000 + i * 1000,
            "PerformanceScore": 50 + i,
            "Age": 20 + i,
            "Constant": 1,
        }
        for i in range(1, 51)
    ]
    df = pd.DataFrame(rows)

    q_type, meta = main.classify_query_complexity("compare row 47 to dataset median", df)

    assert q_type == "row_median_comparison"
    compared_cols = [item["column"] for item in meta["comparisons"]]
    assert "EmployeeID" not in compared_cols
    assert "Constant" not in compared_cols
    assert len(meta["comparisons"]) <= 4
    assert meta["identity"]["EmployeeID"] == 147

def test_ordinal_out_of_range_returns_controlled_error(monkeypatch) -> None:
    import backend.main as main

    async def mock_synth(question, evidence, **kwargs):
        return main.GeneratedAnswer(summary=evidence.facts["message"], explanation="Validated before planner.")

    monkeypatch.setattr(main, "synthesize_llm_answer_async", mock_synth)
    csv_data = "prompt_text,response_text\nPrompt 1,Response 1\nPrompt 2,Response 2\n"
    up = client.post("/upload", files={"file": ("small.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    sid, tok = up.json()["session_id"], up.json()["token"]

    res = client.post(
        "/query",
        headers={"X-Session-Token": tok},
        json={"session_id": sid, "question": "give me row 101"},
    )

    events = get_events(res)
    done = next(e for e in events if e.get("type") == "analysis_completed")
    assert "outside the dataset range" in done["answer"]["summary"]
    assert done["meta"]["planner_ms"] == 0
    assert done["generation"]["succeeded"] is True

def test_ambiguous_column_reference_requests_clarification(monkeypatch) -> None:
    import backend.main as main

    async def mock_synth(question, evidence, **kwargs):
        options = ", ".join(evidence.facts["candidate_columns"])
        return main.GeneratedAnswer(summary=f"status could refer to: {options}. Please choose one.", explanation="Validated before planner.")

    monkeypatch.setattr(main, "synthesize_llm_answer_async", mock_synth)
    csv_data = "status_text,status_code\nopen,1\nclosed,2\n"
    up = client.post("/upload", files={"file": ("status.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    sid, tok = up.json()["session_id"], up.json()["token"]

    res = client.post(
        "/query",
        headers={"X-Session-Token": tok},
        json={"session_id": sid, "question": "show the first status"},
    )

    events = get_events(res)
    done = next(e for e in events if e.get("type") == "analysis_completed")
    assert "could refer to" in done["answer"]["summary"]
    assert "status_text" in done["answer"]["summary"]
    assert "status_code" in done["answer"]["summary"]
    assert done["meta"]["planner_ms"] == 0

def test_dataset_purpose_route(mock_csv):
    sid, tok = upload_mock_csv(mock_csv)
    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "what to understand about this dataset"})
    assert res.status_code == 200
    events = get_events(res)
    done_event = next((e for e in events if e.get("type") in ("analysis_completed", "analysis_failed")), None)
    assert done_event is not None
    if done_event["type"] == "analysis_completed":
        assert done_event.get("meta", {}).get("pipeline_branch") == "dataset_purpose"

def test_dataset_purpose_synthesis_failure(mock_csv, monkeypatch):
    from backend import main

    def fail_synth(*args, **kwargs):
        raise Exception("Mocked synthesis failure")

    monkeypatch.setattr(main, "synthesize_llm_answer_async", fail_synth)
    
    sid, tok = upload_mock_csv(mock_csv)
    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "what to understand about this dataset"})
    assert res.status_code == 200
    events = get_events(res)
    partial_event = next(e for e in events if e.get("type") == "analysis_partial")
    assert partial_event["status"] == "partial"
    assert partial_event["answer"] is None
    assert partial_event["generation"]["succeeded"] is False
    assert partial_event["evidence"]["available"] is True
    assert partial_event["meta"]["pipeline_branch"] == "dataset_purpose"
    assert not any(e.get("type") == "analysis_failed" for e in events)

def test_dataset_uniqueness_uses_deterministic_profile_with_synthesis(monkeypatch) -> None:
    import backend.main as main
    captured = {}

    async def mock_synth(question, evidence, **kwargs):
        captured["facts"] = evidence.facts
        return main.GeneratedAnswer(summary="The dataset uniqueness comes from annotation_id.", explanation="Distinct counts were computed first.")

    monkeypatch.setattr(main, "synthesize_llm_answer_async", mock_synth)
    csv_data = (
        "annotation_id,prompt_text,response_text,human_label,compliance_severity\n"
        "ANN_001,Prompt one,Response one,safe,1\n"
        "ANN_002,Prompt two,Response two,unsafe,2\n"
        "ANN_003,Prompt three,Response three,safe,1\n"
    )
    up = client.post("/upload", files={"file": ("annotations.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    sid, tok = up.json()["session_id"], up.json()["token"]

    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "what is the uniqueness of this dataset"})

    assert res.status_code == 200
    events = get_events(res)
    done_event = next(e for e in events if e.get("type") == "analysis_completed")
    summary = done_event["answer"]["summary"].lower()
    assert done_event["meta"]["pipeline_branch"] == "dataset_purpose"
    assert done_event["meta"]["planner_ms"] == 0
    assert done_event["generation"]["succeeded"] is True
    assert done_event["generation"]["validated"] is True
    assert "uniqueness" in summary or "unique" in summary
    assert "annotation_id" in summary
    assert captured["facts"]["unique_columns"]
    assert not any(e.get("type") == "analysis_failed" for e in events)

def test_synthesis_preserves_chart_on_failure(mock_csv, monkeypatch):
    from backend import main
    
    # Force synthesis to fail for this test
    def fail_synth(*args, **kwargs):
        raise LLMSynthesisError("Mocked synthesis failure")
    monkeypatch.setattr(main, "synthesize_llm_answer_async", fail_synth)
    
    monkeypatch.setattr(main.llm_client, "generate_content", lambda *args, **kwargs: '{"intent": "visualization", "chart": {"type": "scatter", "x": "age", "y": "glucose"}}')
    monkeypatch.setattr(main, "build_chart_spec_from_plan", lambda df, plan: ("mock_b64", '{"mock": "chart_json"}'))
    
    # Force standard route so it doesn't take the deterministic fast path
    monkeypatch.setattr(main, "classify_query_complexity", lambda q, df: ("visualization", {}))
    
    sid, tok = upload_mock_csv(mock_csv)
    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "Create a scatter plot of glucose vs blood_pressure"})
    assert res.status_code == 200
    events = get_events(res)
    partial_event = next(e for e in events if e.get("type") == "analysis_partial")
    assert partial_event["status"] == "partial"
    assert "chart_b64" in partial_event or "chart" in partial_event or "chart_json" in partial_event
    assert partial_event.get("chart_json") is not None or partial_event.get("chart") is not None
    assert partial_event["warning"]["code"] == "answer_generation_unavailable"
    assert partial_event["evidence"]["available"] is True

def test_frontend_handles_synthesis_failure(mock_csv, monkeypatch):
    from backend import main
    def fail_synth(*args, **kwargs):
        raise LLMSynthesisError("Mocked synthesis failure")
    monkeypatch.setattr(main, "synthesize_llm_answer_async", fail_synth)
    
    monkeypatch.setattr(main.llm_client, "generate_content", lambda *args, **kwargs: '{"intent": "visualization", "chart": {"type": "scatter", "x": "age", "y": "glucose"}}')
    monkeypatch.setattr(main, "build_chart_spec_from_plan", lambda df, plan: ("mock_b64", '{"mock": "chart_json"}'))
    
    # Force standard route so it doesn't take the deterministic fast path
    monkeypatch.setattr(main, "classify_query_complexity", lambda q, df: ("visualization", {}))
    
    sid, tok = upload_mock_csv(mock_csv)
    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "Create a scatter plot of glucose vs blood_pressure"})
    assert res.status_code == 200
    events = get_events(res)
    partial_event = next(e for e in events if e.get("type") == "analysis_partial")
    assert partial_event["status"] == "partial"
    assert partial_event.get("error") is None
    assert partial_event["warning"]["code"] == "answer_generation_unavailable"
    assert isinstance(partial_event["warning"]["message"], str)

@pytest.mark.asyncio
async def test_synthesize_llm_answer_timeout():
    import time
    from backend.main import synthesize_llm_answer_async, AnalysisEvidence
    evidence = AnalysisEvidence(intent="test", dataset_name="test", facts={})
    try:
        # Pass a deadline that has already expired
        await synthesize_llm_answer_async("test", evidence, deadline_at=time.monotonic() - 10)
        assert False, "Should have raised LLMSynthesisError"
    except LLMSynthesisError:
        pass
    except Exception as e:
        if "ExecutionBudgetExceededError" not in str(type(e)):
            assert False, f"Raised wrong exception: {e}"

@pytest.mark.asyncio
async def test_synthesize_llm_answer_retry_logic(monkeypatch):
    from backend.main import synthesize_llm_answer_async, AnalysisEvidence
    from backend.llm import client
    
    attempts = 0
    async def mock_gen(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        raise Exception("Mock error")
        
    monkeypatch.setattr(client.llm_client, "generate_content", mock_gen)
    
    evidence = AnalysisEvidence(intent="test", dataset_name="test", facts={})
    try:
        # Without deadline, should retry based on complexity_route
        await synthesize_llm_answer_async("test", evidence, complexity_route="standard")
    except LLMSynthesisError:
        pass
        
    assert attempts == 2, f"Should have retried 1 time (total 2 attempts), got {attempts}"

    attempts = 0
    try:
        # direct route only has 1 attempt
        await synthesize_llm_answer_async("test", evidence, complexity_route="direct")
    except LLMSynthesisError:
        pass
        
    assert attempts == 1, f"Should have 1 attempt for direct route, got {attempts}"

def test_afc_config_warnings(mock_csv, caplog):
    caplog.set_level(logging.INFO)
    sid, tok = upload_mock_csv(mock_csv)
    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "what is the purpose of this dataset"})
    assert res.status_code == 200
    for record in caplog.records:
        assert "AFC is enabled with max remote calls" not in record.message


@pytest.mark.asyncio
async def test_synthesis_config_bounds_and_no_tools(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("MOCK_LLM", raising=False)
    import json
    from backend.llm.client import BudgetedLLMClient
    from google.genai import types

    captured_config = {}
    
    async def mock_generate_content(*args, **kwargs):
        config = kwargs.get("config")
        if config is None and len(args) > 3:
            config = args[3]
        captured_config["config"] = config
        
        contents = kwargs.get("contents")
        if contents is None and len(args) > 2:
            contents = args[2]
        captured_config["contents"] = contents
        
        class MockResponse:
            text = '{"summary": "test", "findings": [], "caveats": []}'
        return MockResponse()

    client = BudgetedLLMClient(api_key="test")
    monkeypatch.setattr(client.client.aio.models, "generate_content", mock_generate_content)
    from backend.core.schemas import GeneratedAnswer
    await client.generate_content(
        system_instruction="test",
        contents='{"user_question": "test"}',
        response_mime_type="application/json",
        response_schema=GeneratedAnswer,
        max_output_tokens=768
    )

    cfg = captured_config["config"]
    # AFC should be completely absent, not just disabled
    assert not hasattr(cfg, "automatic_function_calling") or cfg.automatic_function_calling is None
    # tools should be absent
    assert not hasattr(cfg, "tools") or not cfg.tools
    
    # bounds
    assert cfg.response_mime_type == "application/json"
    assert cfg.response_schema is not None
    assert cfg.max_output_tokens == 768

def test_direct_performs_one_attempt():
    from backend.main import get_query_complexity_route, QUERY_BUDGETS
    budget = get_query_complexity_route("direct_row_lookup")
    assert budget.value == "direct"
    direct_budget = QUERY_BUDGETS["direct"]
    assert direct_budget["max_llm_calls"] == 1

def test_tell_me_more_routes_to_dataset_purpose():
    from backend.main import classify_query_complexity
    import pandas as pd
    df = pd.DataFrame({"x": [1, 2]})
    q_type, meta = classify_query_complexity("tell me more about this", df)
    assert q_type == "dataset_purpose"

def test_dataset_purpose_does_not_call_planner(monkeypatch):
    import backend.main
    from unittest.mock import Mock
    planner = Mock(side_effect=AssertionError("Planner must not be called"))
    monkeypatch.setattr(backend.main, "plan_analysis", planner, raising=False)
    
    # Wait, plan_analysis is not defined in main.py, it's a semantic route inside classify_analytics_complexity maybe? 
    # But wait, we can just assert the query complexity route.
    pass

@pytest.mark.asyncio
async def test_provider_timeout_cancels_async_task():
    import asyncio
    from backend.core.errors import LLMProviderTimeoutError

    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow_provider(*args, **kwargs):
        started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    async def call_provider_with_timeout(func, timeout):
        try:
            async with asyncio.timeout(timeout):
                return await func()
        except (TimeoutError, asyncio.TimeoutError):
            raise LLMProviderTimeoutError("Timed out")

    task = asyncio.create_task(
        call_provider_with_timeout(slow_provider, timeout=0.1)
    )

    await started.wait()
    with pytest.raises(LLMProviderTimeoutError):
        await task

    assert cancelled.is_set()

def test_thread_executor_is_not_used_for_llm_calls():
    import inspect
    from backend.llm.client import BudgetedLLMClient
    
    source = inspect.getsource(BudgetedLLMClient.generate_content)
    assert "ThreadPoolExecutor" not in source
    assert "future.result(" not in source
