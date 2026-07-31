from backend.test_main import *
from backend import main
from backend.main import LLMSynthesisError

def test_debug_events(mock_csv, monkeypatch):
    def fail_synth(*args, **kwargs):
        raise LLMSynthesisError("Mocked synthesis failure")
    monkeypatch.setattr(main, "synthesize_llm_answer", fail_synth)
    
    class MockResponse:
        @property
        def text(self):
            return """{
                "intent": "test_intent",
                "resolved_operation": "sum",
                "resolved_dimension_col": null,
                "resolved_measure_col": "Glucose",
                "chart": true,
                "resolved_chart_type": "bar",
                "reasoning_summary": "test reasoning"
            }"""

    def mock_llm(*args, **kwargs):
        return MockResponse()
    monkeypatch.setattr(main.llm_client, "generate_content", mock_llm)
    
    sid, tok = upload_mock_csv(mock_csv)
    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "plot the glucose"})
    
    events = get_events(res)
    print("\n--- EVENTS ---")
    for e in events:
        print(e.get("type"), e.get("step"), e.get("message"))
        if e.get("type") == "analysis_failed":
            print("CHART JSON:", e.get("chart_json"))
    
    assert False, "Check events"
