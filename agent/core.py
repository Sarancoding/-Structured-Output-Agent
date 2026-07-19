"""
Core agent orchestrator.

Ties together schema definitions, the validation pipeline, retry logic,
and structured logging into a unified, extensible processing pipeline
for structured outputs from language models.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel

from agent.logger import configure_logging, get_logger
from agent.retry import RetryHandler, RetryResult
from agent.schemas import (
    AgentConfig,
    BaseAgentSchema,
    SCHEMA_REGISTRY,
    ValidationErrorDetail,
    ValidationStatus,
)
from agent.validator import ValidationResult, validate_output

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


# ─── Mock LLM Generators (for demo/testing) ───────────────────────────────────

def mock_llm_generator_success(**kwargs) -> Dict[str, Any]:
    """Mock generator that produces valid structured output."""
    return {
        "summary": "This is a sample analysis of the provided text. The main topics include technology trends and their impact on society.",
        "entities": [
            {"name": "Artificial Intelligence", "type": "technology", "confidence": 0.95},
            {"name": "Machine Learning", "type": "technology", "confidence": 0.92},
        ],
        "key_points": [
            {"summary": "AI is transforming industries", "relevance": 0.98},
            {"summary": "Ethical considerations are important", "relevance": 0.85},
        ],
        "sentiment": {
            "sentiment": "positive",
            "score": 0.75,
            "confidence": 0.88,
        },
        "word_count": 150,
        "language": "en",
    }


def mock_llm_generator_fail_once(**kwargs) -> Dict[str, Any]:
    """Mock generator that fails validation on first attempt, then succeeds."""
    retry_context = kwargs.get("retry_context", {})
    attempt = retry_context.get("attempt", 0)

    if attempt == 0:
        return {
            "summary": "Test analysis",
            "entities": [
                {"name": "AI", "type": "technology", "confidence": 1.5},  # Invalid: > 1.0
            ],
            "key_points": [
                {"summary": "Point 1", "relevance": 1.2},  # Invalid: > 1.0
            ],
            "sentiment": {
                "sentiment": "positive",
                "score": 0.5,
                "confidence": 0.9,
            },
            "word_count": 100,
            "language": "en",
        }
    return mock_llm_generator_success(**kwargs)


def mock_llm_generator_always_fails(**kwargs) -> Dict[str, Any]:
    """Mock generator that always produces invalid output."""
    return {
        "summary": "",
        "entities": [
            {"name": "Test", "type": "invalid", "confidence": 2.0},
        ],
        "key_points": [
            {"summary": "", "relevance": -0.5},
        ],
        "sentiment": {
            "sentiment": "positive",
            "score": -0.5,  # Mismatch: positive + negative score
            "confidence": 0.9,
        },
        "word_count": -5,
        "language": "",
    }


# ─── Structured Output Agent ──────────────────────────────────────────────────

class StructuredOutputAgent:
    """
    Main agent class that orchestrates structured output generation and validation.

    Provides a clean interface for:
    - Processing queries through the validation pipeline
    - Registering custom schemas and generators
    - Inspecting validation history and agent statistics
    - Configurable retry and logging behavior

    Usage:
        agent = StructuredOutputAgent()
        result = agent.process(
            generator_fn=my_llm_function,
            schema_name="TextAnalysis",
            context={"query": "Analyze this text"},
        )
    """

    def __init__(self, config: Optional[Union[AgentConfig, Dict[str, Any]]] = None):
        """
        Initialize the agent.

        Args:
            config: Agent configuration. Can be an AgentConfig instance
                   or a dict of config overrides.
        """
        if isinstance(config, dict):
            self.config = AgentConfig(**config)
        elif isinstance(config, AgentConfig):
            self.config = config
        else:
            self.config = AgentConfig()

        # Configure logging
        configure_logging(
            level=self.config.log_level,
            log_file=self.config.log_file,
            enable_structured=self.config.enable_structured_logging,
        )

        self.retry_handler = RetryHandler(config=self.config)
        self.processing_history: List[Dict[str, Any]] = []

        # Register built-in mock generators
        self._generators: Dict[str, Callable[..., Dict[str, Any]]] = {
            "mock_success": mock_llm_generator_success,
            "mock_fail_once": mock_llm_generator_fail_once,
            "mock_always_fails": mock_llm_generator_always_fails,
        }

        logger.info(
            "Agent initialized",
            extra={
                "max_retries": self.config.max_retries,
                "log_file": self.config.log_file,
                "schemas_available": list(SCHEMA_REGISTRY.keys()),
            },
        )

    def process(
        self,
        generator_fn: Optional[Callable[..., Dict[str, Any]]] = None,
        generator_name: Optional[str] = None,
        schema_class: Optional[Type[T]] = None,
        schema_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        fn_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a query through the structured output pipeline.

        Args:
            generator_fn: Function that generates raw output. If not provided,
                         uses a registered generator by name.
            generator_name: Name of a registered generator function.
            schema_class: Pydantic schema class to validate against.
            schema_name: Name of a registered schema.
            context: Metadata for the processing request.
            fn_kwargs: Additional keyword arguments for the generator.

        Returns:
            Dict with processing results including status, data, and metadata.
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        context = context or {}

        # Resolve generator
        if generator_fn is None and generator_name:
            if generator_name not in self._generators:
                raise ValueError(
                    f"Unknown generator '{generator_name}'. "
                    f"Available: {list(self._generators.keys())}"
                )
            generator_fn = self._generators[generator_name]

        if generator_fn is None:
            raise ValueError("Either generator_fn or generator_name is required")

        # Resolve schema
        if schema_class is None and schema_name:
            resolved = SCHEMA_REGISTRY.get(schema_name)
            if resolved is None:
                raise ValueError(
                    f"Unknown schema '{schema_name}'. "
                    f"Available: {list(SCHEMA_REGISTRY.keys())}"
                )
            schema_class = resolved  # type: ignore

        if schema_class is None:
            # Default to TextAnalysis schema
            from agent.schemas import TextAnalysis as DefaultSchema
            schema_class = DefaultSchema  # type: ignore

        logger.info(
            "Processing request",
            extra={
                "request_id": request_id,
                "schema": schema_class.__name__,
                "generator": generator_fn.__name__,
                "context_keys": list(context.keys()),
            },
        )

        # Execute with retry logic
        retry_result: RetryResult = self.retry_handler.execute_with_retry(
            generator_fn=generator_fn,
            schema_class=schema_class,  # type: ignore
            context=context,
            request_id=request_id,
            fn_kwargs=fn_kwargs,
        )

        # Build the processing record
        processing_time = (time.time() - start_time) * 1000
        result: Dict[str, Any] = {
            "request_id": request_id,
            "success": retry_result.success,
            "data": None,
            "error": None,
            "validation_status": retry_result.final_status.value,
            "retry_attempts": len(retry_result.attempts),
            "attempt_details": [
                {
                    "attempt": a.attempt_number,
                    "timestamp": a.timestamp,
                    "error": a.error_summary,
                    "success": a.success,
                }
                for a in retry_result.attempts
            ],
            "processing_time_ms": round(processing_time, 2),
            "schema_used": schema_class.__name__,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if retry_result.success and retry_result.final_data:
            result["data"] = retry_result.final_data.model_dump(mode="json")
        else:
            result["error"] = retry_result.error_detail
            # Provide fallback data
            result["data"] = self._generate_fallback(schema_class)  # type: ignore

        # Record processing history
        self.processing_history.append({
            "request_id": request_id,
            "timestamp": result["timestamp"],
            "schema": schema_class.__name__,
            "success": retry_result.success,
            "status": retry_result.final_status.value,
            "attempts": len(retry_result.attempts),
            "processing_time_ms": result["processing_time_ms"],
        })

        logger.info(
            "Request processed",
            extra={
                "request_id": request_id,
                "success": retry_result.success,
                "status": retry_result.final_status.value,
                "processing_time_ms": result["processing_time_ms"],
                "attempts": len(retry_result.attempts),
            },
        )

        return result

    def register_generator(
        self, name: str, fn: Callable[..., Dict[str, Any]]
    ) -> None:
        """
        Register a custom generator function.

        Args:
            name: Name to register the generator under.
            fn: The generator function.
        """
        self._generators[name] = fn
        logger.info(f"Generator '{name}' registered", extra={"generator": name})

    def list_generators(self) -> List[Dict[str, str]]:
        """List all registered generators with their names."""
        return [
            {
                "name": name,
                "module": fn.__module__,
                "type": "mock" if name.startswith("mock") else "custom",
            }
            for name, fn in self._generators.items()
        ]

    def get_history(
        self,
        limit: int = 10,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get processing history with optional filtering.

        Args:
            limit: Maximum number of history entries.
            status_filter: Optional filter by status (e.g., "success", "fallback").

        Returns:
            List of processing history entries.
        """
        history = self.processing_history
        if status_filter:
            history = [h for h in history if h["status"] == status_filter]
        return history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics including retry and validation metrics."""
        total = len(self.processing_history)
        successes = sum(1 for h in self.processing_history if h["success"])
        failures = total - successes

        return {
            "total_requests": total,
            "successful_requests": successes,
            "failed_requests": failures,
            "success_rate": round(successes / total * 100, 2) if total > 0 else 0.0,
            "avg_processing_time_ms": round(
                sum(h["processing_time_ms"] for h in self.processing_history) / total,
                2,
            ) if total > 0 else 0.0,
            "retry_handler_stats": self.retry_handler.get_stats(),
            "available_schemas": list(SCHEMA_REGISTRY.keys()),
            "available_generators": list(self._generators.keys()),
        }

    def reset(self) -> None:
        """Reset processing history and retry statistics."""
        self.processing_history.clear()
        self.retry_handler.reset_stats()
        logger.info("Agent state reset")

    def validate_raw(
        self,
        raw_data: Dict[str, Any],
        schema_name: str,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate raw data directly against a schema without generation.

        Useful for testing or pre-validation of external data.

        Args:
            raw_data: The raw dictionary data to validate.
            schema_name: Name of the schema to validate against.
            request_id: Optional request ID.

        Returns:
            Validation result dict.
        """
        schema_class = SCHEMA_REGISTRY.get(schema_name)
        if not schema_class:
            return {
                "success": False,
                "error": f"Unknown schema: {schema_name}",
            }

        result = validate_output(
            raw_output=raw_data,
            schema_class=schema_class,
            request_id=request_id or str(uuid.uuid4()),
        )

        return {
            "success": result.success,
            "data": (
                result.validated_data.model_dump(mode="json")
                if result.validated_data
                else None
            ),
            "status": result.status.value,
            "error_detail": (
                result.error_detail.model_dump(mode="json")
                if result.error_detail
                else None
            ),
        }

    def _generate_fallback(self, schema_class: Type[T]) -> Dict[str, Any]:
        """Generate a safe fallback response when all retries fail."""
        fallback: Dict[str, Any] = {
            "summary": "[Fallback] Unable to generate valid structured output.",
            "entities": [],
            "key_points": [],
            "sentiment": {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
            },
            "word_count": 0,
            "language": "en",
            "warning": "This is a fallback response due to validation failures.",
        }

        try:
            validated = schema_class.model_validate(fallback)
            return validated.model_dump(mode="json")
        except Exception:
            return {"error": "Fallback generation failed", "success": False}


# ─── Global Agent Instance ────────────────────────────────────────────────────

_global_agent: Optional[StructuredOutputAgent] = None


def get_agent(config: Optional[Dict[str, Any]] = None) -> StructuredOutputAgent:
    """Get or create the global agent instance."""
    global _global_agent
    if _global_agent is None:
        _global_agent = StructuredOutputAgent(config=config)
    return _global_agent


def reset_agent() -> None:
    """Reset the global agent instance."""
    global _global_agent
    _global_agent = None
