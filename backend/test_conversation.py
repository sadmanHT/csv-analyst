import pytest
import pandas as pd
from backend.main import classify_query_complexity, QueryComplexity, get_query_complexity_route, SCHEMA_AWARE_PLANNER_SYSTEM, PLANNER_SYSTEM

def test_hello_routes_to_conversation():
    df = pd.DataFrame({"age": [10, 20]})
    q_type, _ = classify_query_complexity("hello", df)
    assert q_type == "conversation"
    assert get_query_complexity_route(q_type) == QueryComplexity.CONVERSATION

def test_helloo_routes_to_conversation():
    df = pd.DataFrame({"age": [10, 20]})
    q_type, _ = classify_query_complexity("hell0o", df)
    assert q_type == "conversation"

def test_kire_ki_khobor_routes_to_conversation():
    df = pd.DataFrame({"age": [10, 20]})
    q_type, _ = classify_query_complexity("kire ki khobor", df)
    assert q_type == "conversation"

def test_plot_glucose_does_not_route_to_conversation():
    df = pd.DataFrame({"glucose": [100, 200]})
    q_type, _ = classify_query_complexity("plot glucose", df)
    assert q_type != "conversation"
    
def test_average_glucose_does_not_route_to_conversation():
    df = pd.DataFrame({"glucose": [100, 200]})
    q_type, _ = classify_query_complexity("average glucose", df)
    assert q_type != "conversation"

def test_prompt_strings_are_valid_utf8_without_mojibake():
    # Ensure there are no 'Ã' or 'Â' or 'ƒ¢‚' characters which indicate mojibake
    for prompt in [SCHEMA_AWARE_PLANNER_SYSTEM, PLANNER_SYSTEM]:
        assert 'Ã' not in prompt
        assert 'Â' not in prompt
        assert 'ƒ' not in prompt
        assert '€' not in prompt
        assert '‚' not in prompt
