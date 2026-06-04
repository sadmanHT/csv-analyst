#!/usr/bin/env python
"""
CSV Analyst AI — Benchmark Evaluation CLI

Runs the full benchmark suite against a CSV file using the FastAPI TestClient
and prints a summary table + per-question breakdown.

Usage:
    python benchmark.py --csv ../sample_data/ecommerce_sales.csv
    python benchmark.py --csv data.csv --n 30 --out results.json
    python benchmark.py --csv data.csv --category retail
"""
import argparse
import io
import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient
from main import app, BENCHMARK_QUESTIONS

client = TestClient(app)


def upload_csv(path: str) -> str:
    with open(path, "rb") as f:
        content = f.read()
    res = client.post(
        "/upload",
        files={"file": (Path(path).name, io.BytesIO(content), "text/csv")},
    )
    if res.status_code != 200:
        print(f"[ERROR] Upload failed: {res.text}")
        sys.exit(1)
    return res.json()["session_id"]


def run_benchmark(session_id: str, n: int) -> dict:
    print(f"\nRunning {n} benchmark questions…\n")
    res = client.get(f"/benchmark/{session_id}?n={n}")
    if res.status_code != 200:
        print(f"[ERROR] Benchmark endpoint failed: {res.text}")
        sys.exit(1)
    return res.json()


def print_table(data: dict) -> None:
    sep = "─" * 78
    print(f"\n{'CSV Analyst AI — Benchmark Results':^78}")
    print(sep)
    print(f"  Total questions    : {data['total']}")
    print(f"  Success rate       : {data['success_rate']:.1%}")
    print(f"  Chart rate         : {data['chart_rate']:.1%}  (questions expecting a chart)")
    print(f"  SQL routing acc.   : {data['sql_routing_accuracy']:.1%}  (SQL questions routed to SQL)")
    print(f"  Repair rate        : {data['repair_rate']:.1%}  (questions that needed repair)")
    print(f"  Repair success     : {data['repair_success_rate']:.1%}  (of those repaired, % succeeded)")
    print(f"  Avg response time  : {data['avg_time_s']}s")
    print(sep)

    # Per-question table
    print(f"\n{'#':<4} {'Category':<12} {'SQL':<5} {'Chart':<7} {'OK':<5} {'Time':>6}  Question")
    print("─" * 78)
    for i, r in enumerate(data["results"], 1):
        ok       = "✓" if r["success"] else "✗"
        sql_mark = "SQL" if r["query_type"] == "sql" else "py"
        chart    = "✓" if r["has_chart"] else ("·" if r["expects_chart"] else " ")
        q        = r["question"][:52] + ("…" if len(r["question"]) > 52 else "")
        repair   = " (repaired)" if r["used_repair"] else ""
        print(f"{i:<4} {r['category']:<12} {sql_mark:<5} {chart:<7} {ok:<5} {r['time_s']:>5.1f}s  {q}{repair}")
    print(sep)


def main():
    parser = argparse.ArgumentParser(description="CSV Analyst AI benchmark runner")
    parser.add_argument("--csv",      required=True,  help="Path to the CSV file to benchmark against")
    parser.add_argument("--n",        type=int, default=20, help="Number of questions to run (default 20, max 50)")
    parser.add_argument("--out",      default=None,   help="Save full results to this JSON file")
    parser.add_argument("--category", default=None,   help="Filter questions to a specific category")
    args = parser.parse_args()

    n = min(args.n, len(BENCHMARK_QUESTIONS))

    print(f"Uploading {args.csv}…")
    session_id = upload_csv(args.csv)
    print(f"Session: {session_id}")

    data = run_benchmark(session_id, n)
    print_table(data)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nFull results saved to {args.out}")


if __name__ == "__main__":
    main()
