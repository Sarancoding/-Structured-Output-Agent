from agent.core import StructuredOutputAgent, get_agent
from agent.schemas import SCHEMA_REGISTRY
import pytest

def test_agent_initialization():
    agent = StructuredOutputAgent()
    assert len(agent.list_generators()) >= 3

def test_process_mock_success():
    agent = StructuredOutputAgent()
    result = agent.process(generator_name="mock_success", schema_name="TextAnalysis")
    assert result["success"] is True
    assert result["schema_used"] == "TextAnalysis"
    assert "data" in result
    assert result["data"]["summary"] != "[Fallback] Unable to generate valid structured output."

def test_process_mock_fail_once():
    agent = StructuredOutputAgent()
    result = agent.process(generator_name="mock_fail_once", schema_name="TextAnalysis")
    assert result["success"] is True
    assert result["retry_attempts"] == 1

def test_process_mock_always_fails():
    agent = StructuredOutputAgent()
    result = agent.process(generator_name="mock_always_fails", schema_name="TextAnalysis")
    assert result["success"] is False
    assert result["retry_attempts"] == 3
    assert result["data"]["summary"] == "[Fallback] Unable to generate valid structured output."

def test_validate_raw():
    agent = StructuredOutputAgent()
    raw_data = {
        "summary": "Valid summary",
        "entities": [{"name": "Valid", "type": "Test", "confidence": 0.8}],
        "key_points": [],
        "sentiment": {"sentiment": "neutral", "score": 0.0, "confidence": 1.0},
        "word_count": 2,
        "language": "en"
    }
    result = agent.validate_raw(raw_data=raw_data, schema_name="TextAnalysis")
    assert result["success"] is True

    invalid_data = {
        "summary": "Valid summary",
        "entities": [{"name": "Valid", "type": "Test", "confidence": 1.5}], # Invalid confidence
        "key_points": [],
        "sentiment": {"sentiment": "neutral", "score": 0.0, "confidence": 1.0},
        "word_count": 2,
        "language": "en"
    }
    result = agent.validate_raw(raw_data=invalid_data, schema_name="TextAnalysis")
    assert result["success"] is False

def test_stats_and_history():
    agent = StructuredOutputAgent()
    agent.process(generator_name="mock_success", schema_name="TextAnalysis")
    agent.process(generator_name="mock_always_fails", schema_name="TextAnalysis")

    stats = agent.get_stats()
    assert stats["total_requests"] == 2
    assert stats["successful_requests"] == 1
    assert stats["failed_requests"] == 1

    history = agent.get_history()
    assert len(history) == 2
