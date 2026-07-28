"""
Performance Baseline & Benchmark Suite
Runs 11 query types against the backend router & query engine, recording timings, route classification, LLM call counts, and stage-level latency breakdowns.
"""

import io
import json
import time
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))
from main import app, dataframes, session_meta
from fastapi.testclient import TestClient

SAMPLE_CSV = "Department,EmployeeID,Salary,PerformanceScore\nEngineering,E01,95000,4.2\nEngineering,E02,105000,4.5\nSales,E03,75000,3.8\nSales,E04,82000,4.0\nHR,E05,65000,3.5\n"

BENCHMARK_QUERIES = [
    {"type": "model_recommendation", "question": "What model algorithm should I train for this dataset?", "expected_route": "DIRECT"},
    {"type": "unclear_query", "question": "gg", "expected_route": "DIRECT"},
    {"type": "dataset_purpose", "question": "What is this dataset about?", "expected_route": "DIRECT"},
    {"type": "direct_row_lookup", "question": "Show me row 5", "expected_route": "DIRECT"},
    {"type": "deterministic", "question": "How many rows are in this dataset?", "expected_route": "DIRECT"},
    {"type": "data_quality_guidance", "question": "How can I improve this dataset?", "expected_route": "STANDARD"},
    {"type": "lookup", "question": "Find employee with highest PerformanceScore", "expected_route": "STANDARD"},
    {"type": "aggregation", "question": "What is the average Salary by Department?", "expected_route": "STANDARD"},
    {"type": "comparison", "question": "Compare Salary across Department", "expected_route": "STANDARD"},
    {"type": "visualization", "question": "Do a pie chart of employees by Department", "expected_route": "STANDARD"},
    {"type": "modeling", "question": "Predict PerformanceScore based on Salary", "expected_route": "DEEP"},
]

def run_benchmark():
    client = TestClient(app)
    print("Starting Performance Benchmark Run...")
    
    # 1. Upload dataset
    t0 = time.time()
    res = client.post("/upload", files={"file": ("employees.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")})
    upload_time = time.time() - t0
    assert res.status_code == 200, f"Upload failed: {res.text}"
    session_data = res.json()
    session_id = session_data["session_id"]
    token = session_data.get("token", "")
    print(f"Dataset uploaded successfully in {upload_time*1000:.1f}ms. Session ID: {session_id}")

    results = []
    headers = {"X-Session-Token": token}

    for item in BENCHMARK_QUERIES:
        q_type = item["type"]
        question = item["question"]
        t_start = time.time()
        
        resp = client.post("/query", headers=headers, json={"session_id": session_id, "question": question, "category": "hr"})
        t_duration = time.time() - t_start
        
        success = resp.status_code == 200
        events = []
        if success:
            for block in resp.text.strip().split("\n\n"):
                line = next((ln for ln in block.splitlines() if ln.startswith("data: ")), None)
                if line:
                    try:
                        events.append(json.loads(line[6:]))
                    except Exception:
                        pass

        # Extract route details from events
        route_selected_event = next((e for e in events if e.get("type") == "route_selected"), {})
        complexity_route = route_selected_event.get("complexity_route", "DIRECT").upper()
        
        terminal_event = events[-1] if events else {}
        terminal_meta = terminal_event.get("meta", {})
        pipeline_branch = terminal_meta.get("pipeline_branch", terminal_meta.get("route", q_type))
        
        llm_calls = terminal_meta.get("llm_calls", 0)
        duration_ms = round(t_duration * 1000, 1)
        planner_ms = terminal_meta.get("planner_ms", terminal_meta.get("plan_ms", 0))
        execution_ms = terminal_meta.get("execution_ms", 0)
        synthesis_ms = terminal_meta.get("synthesis_ms", terminal_meta.get("reporter_ms", 0))
        unaccounted_ms = terminal_meta.get("unaccounted_ms", max(0, duration_ms - (planner_ms + execution_ms + synthesis_ms)))
        
        deadline_map = {"DIRECT": 15000, "STANDARD": 30000, "DEEP": 60000}
        route_deadline_ms = deadline_map.get(complexity_route, 30000)
        deadline_exceeded = duration_ms > (route_deadline_ms + 3000)

        res_entry = {
            "type": q_type,
            "question": question,
            "success": success,
            "duration_ms": duration_ms,
            "deadline_ms": route_deadline_ms,
            "deadline_exceeded": deadline_exceeded,
            "events_count": len(events),
            "complexity_route": complexity_route,
            "pipeline_branch": pipeline_branch,
            "llm_calls": llm_calls,
            "planner_ms": planner_ms,
            "execution_ms": execution_ms,
            "synthesis_ms": synthesis_ms,
            "unaccounted_ms": unaccounted_ms,
        }
        results.append(res_entry)

        # Correctness assertions
        if success:
            assert duration_ms <= (route_deadline_ms + 4000), f"Request '{question}' ({complexity_route}) took {duration_ms}ms, exceeding budget {route_deadline_ms}ms"
            if planner_ms > 0:
                assert llm_calls >= 1, f"Planner ran ({planner_ms}ms) but llm_calls is {llm_calls}"
            if synthesis_ms > 0:
                assert llm_calls >= 1, f"Synthesis ran ({synthesis_ms}ms) but llm_calls is {llm_calls}"

        print(f"[{q_type}] '{question}' -> {duration_ms:.1f}ms (Route: {complexity_route}, Deadline: {route_deadline_ms}ms, Exceeded: {deadline_exceeded}, LLM calls: {llm_calls}, Unaccounted: {unaccounted_ms:.0f}ms)")

    out_file = "backend/performance_baseline.json"
    with open(out_file, "w") as f:
        json.dump({"upload_time_ms": round(upload_time * 1000, 1), "benchmark_results": results}, f, indent=2)
    print(f"\nBenchmark completed. Results written to {out_file}.")

if __name__ == "__main__":
    run_benchmark()
