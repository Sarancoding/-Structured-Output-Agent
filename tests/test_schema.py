from agent.schemas import get_schema_by_name, TextAnalysis

def test_schema_exists():
    assert get_schema_by_name("TextAnalysis") is not None
