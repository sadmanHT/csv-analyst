import os
import ast

def main():
    test_code = """
def test_synthesis_config_and_fallback(monkeypatch):
    import main
    import json
    import io
    from backend.core.schemas import GeneratedAnswer

    # Mock llm_client.generate_content to assert kwargs
    original_generate = main.llm_client.generate_content
    
    call_kwargs = {}
    
    def mock_generate(*args, **kwargs):
        call_kwargs.update(kwargs)
        if kwargs.get("stage") == "synthesis":
            raise main.LLMSynthesisError("Mock timeout or failure")
        return original_generate(*args, **kwargs)

    monkeypatch.setattr(main.llm_client, "generate_content", mock_generate)
    monkeypatch.setattr(main, "PLANNER_MODEL", "gemma-4-26b-a4b-it")
    monkeypatch.setattr(main, "SYNTHESIS_MODEL", "gemma-4-26b-a4b-it")

    csv_data = "col1,col2\\n1,2\\n3,4\\n"
    up = client.post("/upload", files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up.status_code == 200
    data = up.json()
    sid = data["session_id"]
    tok = data["token"]
    
    # Query that triggers dataset_purpose
    res = client.post("/query", headers={"X-Session-Token": tok}, json={"session_id": sid, "question": "what is this dataset about?"})
    assert res.status_code == 200
    
    # Check the kwargs passed to generate_content
    assert call_kwargs.get("model") == "gemma-4-26b-a4b-it"
    assert call_kwargs.get("max_output_tokens") == 384
    assert call_kwargs.get("response_mime_type") == "application/json"
    assert call_kwargs.get("response_schema") == GeneratedAnswer
    assert call_kwargs.get("thinking_config") == {"thinking_level": "minimal"}
    assert call_kwargs.get("request_id") is not None
    assert call_kwargs.get("total_deadline_s") is not None
    assert "tools" not in call_kwargs
    assert "automatic_function_calling" not in call_kwargs
    
    # Check fallback preserves verified evidence
    events = [json.loads(line[6:]) for line in res.text.split("\\n") if line.startswith("data: ")]
    failed_event = next(e for e in events if e.get("type") == "analysis_failed")
    assert failed_event["error"]["code"] == "answer_generation_failed"
    assert failed_event["evidence"]["available"] is True
    assert len(failed_event["evidence"]["facts"]) >= 5
    labels = [f["label"] for f in failed_event["evidence"]["facts"]]
    assert "Rows" in labels
    assert "Columns" in labels
    assert "Missing values" in labels
    
"""
    with open("backend/test_main.py", "a", encoding="utf-8") as f:
        f.write(test_code)

if __name__ == "__main__":
    main()
