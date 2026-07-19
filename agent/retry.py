"""
Retry mechanism with exponential backoff for validation failures.

Handles retry logic when LLM outputs fail schema validation,
with configurable retry limits, backoff timing, and detailed logging.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel

from agent.logger import get_logger
from agent.schemas import AgentConfig, ValidationStatus
from agent.validator import ValidationResult, validate_output

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class RetryAttempt:
    """Record of a single retry attempt."""
    attempt_number: int
    timestamp: str
    error_summary: str
    delay_seconds: float
    success: bool


@dataclass
class RetryResult:
    """Result of the full retry process."""
    success: bool
    final_data: Optional[BaseModel] = None
    attempts: List[RetryAttempt] = field(default_factory=list)
    total_time_ms: float = 0.0
    final_status: ValidationStatus = ValidationStatus.SUCCESS
    error_detail: Optional[Dict[str, Any]] = None


class RetryHandler:
    """
    Handles retry logic for validation failures with exponential backoff.

    Usage:
        handler = RetryHandler(config=AgentConfig())
        result = handler.execute_with_retry(
            generator_fn=my_llm_generate,
            schema_class=MySchema,
            context={"query": "hello"},
        )
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the retry handler.

        Args:
            config: Agent configuration. Uses defaults if not provided.
        """
        self.config = config or AgentConfig()
        self._stats: Dict[str, Any] = {
            "total_attempts": 0,
            "total_retries": 0,
            "total_successes": 0,
            "total_failures": 0,
        }

    def execute_with_retry(
        self,
        generator_fn: Callable[..., Dict[str, Any]],
        schema_class: Type[T],
        context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        fn_kwargs: Optional[Dict[str, Any]] = None,
    ) -> RetryResult:
        """
        Execute a generator function with retry on validation failure.

        Args:
            generator_fn: Function that generates raw output (e.g., LLM call).
            schema_class: Pydantic schema to validate against.
            context: Metadata for validation error details.
            request_id: Request ID for traceability.
            fn_kwargs: Additional keyword arguments for the generator function.

        Returns:
            RetryResult with final data and attempt history.
        """
        start_time = time.time()
        request_id = request_id or str(uuid.uuid4())
        fn_kwargs = fn_kwargs or {}
        context = context or {}

        result = RetryResult(final_status=ValidationStatus.FAILURE)
        raw_generation_context = context.copy()

        for attempt in range(self.config.max_retries + 1):
            attempt_start = time.time()
            is_retry = attempt > 0

            try:
                if is_retry:
                    logger.info(
                        f"Retry attempt {attempt}/{self.config.max_retries}",
                        extra={
                            "request_id": request_id,
                            "attempt": attempt,
                            "max_retries": self.config.max_retries,
                        },
                    )
                    # Add retry context to help the generator adjust
                    enriched_kwargs = {
                        **fn_kwargs,
                        "retry_context": {
                            "attempt": attempt,
                            "max_retries": self.config.max_retries,
                            "previous_errors": [
                                a.error_summary for a in result.attempts
                            ],
                        },
                    }
                else:
                    enriched_kwargs = fn_kwargs

                # Generate raw output
                raw_output = generator_fn(**enriched_kwargs)

                if not isinstance(raw_output, dict):
                    raise ValueError(
                        f"Generator returned {type(raw_output).__name__}, expected dict"
                    )

                # Validate against schema
                validation_result = validate_output(
                    raw_output=raw_output,
                    schema_class=schema_class,
                    context=raw_generation_context,
                    request_id=request_id,
                )

                attempt_duration = (time.time() - attempt_start) * 1000

                if validation_result.success:
                    self._stats["total_successes"] += 1
                    result.success = True
                    result.final_data = validation_result.validated_data
                    result.final_status = ValidationStatus.SUCCESS
                    result.attempts.append(RetryAttempt(
                        attempt_number=attempt,
                        timestamp=datetime.utcnow().isoformat(),
                        error_summary="",
                        delay_seconds=0.0,
                        success=True,
                    ))
                    break
                else:
                    # Validation failed
                    error_summary = (
                        validation_result.error_detail.validation_errors[0]["msg"]
                        if validation_result.error_detail
                        and validation_result.error_detail.validation_errors
                        else "Unknown validation error"
                    )

                    result.attempts.append(RetryAttempt(
                        attempt_number=attempt,
                        timestamp=datetime.utcnow().isoformat(),
                        error_summary=error_summary,
                        delay_seconds=0.0,
                        success=False,
                    ))

                    if attempt < self.config.max_retries:
                        # Calculate backoff delay
                        delay = self._calculate_backoff(attempt)
                        logger.warning(
                            f"Validation failed, retrying in {delay:.2f}s: {error_summary}",
                            extra={
                                "request_id": request_id,
                                "attempt": attempt,
                                "next_delay": delay,
                                "attempt_duration_ms": round(attempt_duration, 2),
                            },
                        )
                        time.sleep(delay)
                        result.attempts[-1].delay_seconds = delay
                    else:
                        # Max retries exhausted
                        logger.error(
                            "Max retries exhausted, returning fallback",
                            extra={
                                "request_id": request_id,
                                "max_retries": self.config.max_retries,
                                "total_attempts": attempt + 1,
                            },
                        )
                        result.final_status = ValidationStatus.FALLBACK
                        result.error_detail = (
                            validation_result.error_detail.model_dump()
                            if validation_result.error_detail
                            else None
                        )

                self._stats["total_retries"] += 1 if is_retry else 0
                self._stats["total_attempts"] += 1

            except Exception as e:
                logger.error(
                    f"Error during generation attempt {attempt}: {e}",
                    extra={
                        "request_id": request_id,
                        "attempt": attempt,
                        "traceback": __import__("traceback").format_exc(),
                    },
                )
                result.attempts.append(RetryAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.utcnow().isoformat(),
                    error_summary=str(e),
                    delay_seconds=0.0,
                    success=False,
                ))

                if attempt >= self.config.max_retries:
                    result.final_status = ValidationStatus.FALLBACK
                    result.error_detail = {"error": str(e)}
                else:
                    delay = self._calculate_backoff(attempt)
                    time.sleep(delay)
                    result.attempts[-1].delay_seconds = delay

                self._stats["total_attempts"] += 1

        result.total_time_ms = (time.time() - start_time) * 1000
        self._stats["total_failures"] += 0 if result.success else 1

        logger.info(
            "Retry handler completed",
            extra={
                "request_id": request_id,
                "success": result.success,
                "attempts": len(result.attempts),
                "total_time_ms": round(result.total_time_ms, 2),
                "final_status": result.final_status.value,
            },
        )

        return result

    async def execute_with_retry_async(
        self,
        generator_fn: Callable[..., Any],
        schema_class: Type[T],
        context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        fn_kwargs: Optional[Dict[str, Any]] = None,
    ) -> RetryResult:
        """
        Async version of execute_with_retry.

        Supports async generator functions and uses asyncio.sleep
        for non-blocking backoff delays.
        """
        start_time = time.time()
        request_id = request_id or str(uuid.uuid4())
        fn_kwargs = fn_kwargs or {}
        context = context or {}

        result = RetryResult(final_status=ValidationStatus.FAILURE)

        for attempt in range(self.config.max_retries + 1):
            is_retry = attempt > 0

            try:
                if is_retry:
                    enriched_kwargs = {
                        **fn_kwargs,
                        "retry_context": {
                            "attempt": attempt,
                            "max_retries": self.config.max_retries,
                            "previous_errors": [
                                a.error_summary for a in result.attempts
                            ],
                        },
                    }
                else:
                    enriched_kwargs = fn_kwargs

                # Support both async and sync generators
                raw_output = generator_fn(**enriched_kwargs)
                if hasattr(raw_output, "__await__"):
                    raw_output = await raw_output

                validation_result = validate_output(
                    raw_output=raw_output,
                    schema_class=schema_class,
                    context=context,
                    request_id=request_id,
                )

                if validation_result.success:
                    result.success = True
                    result.final_data = validation_result.validated_data
                    result.final_status = ValidationStatus.SUCCESS
                    result.attempts.append(RetryAttempt(
                        attempt_number=attempt,
                        timestamp=datetime.utcnow().isoformat(),
                        error_summary="",
                        delay_seconds=0.0,
                        success=True,
                    ))
                    break
                else:
                    error_summary = (
                        validation_result.error_detail.validation_errors[0]["msg"]
                        if validation_result.error_detail
                        and validation_result.error_detail.validation_errors
                        else "Unknown error"
                    )
                    result.attempts.append(RetryAttempt(
                        attempt_number=attempt,
                        timestamp=datetime.utcnow().isoformat(),
                        error_summary=error_summary,
                        delay_seconds=0.0,
                        success=False,
                    ))

                    if attempt < self.config.max_retries:
                        delay = self._calculate_backoff(attempt)
                        logger.warning(f"Async retry in {delay:.2f}s: {error_summary}")
                        await asyncio.sleep(delay)
                        result.attempts[-1].delay_seconds = delay
                    else:
                        result.final_status = ValidationStatus.FALLBACK
                        result.error_detail = (
                            validation_result.error_detail.model_dump()
                            if validation_result.error_detail
                            else None
                        )

            except Exception as e:
                logger.error(f"Async attempt {attempt} failed: {e}")
                result.attempts.append(RetryAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.utcnow().isoformat(),
                    error_summary=str(e),
                    delay_seconds=0.0,
                    success=False,
                ))

                if attempt >= self.config.max_retries:
                    result.final_status = ValidationStatus.FALLBACK
                    result.error_detail = {"error": str(e)}
                else:
                    delay = self._calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                    result.attempts[-1].delay_seconds = delay

        result.total_time_ms = (time.time() - start_time) * 1000
        return result

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        delay = base_delay * (backoff_multiplier ^ attempt)

        Args:
            attempt: The current attempt number (0-based).

        Returns:
            Delay in seconds.
        """
        delay = self.config.base_delay_seconds * (
            self.config.backoff_multiplier ** attempt
        )
        return min(delay, 60.0)  # Cap at 60 seconds

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate retry handler statistics."""
        return {
            **self._stats,
            "config": self.config.model_dump(),
        }

    def reset_stats(self) -> None:
        """Reset aggregate statistics."""
        self._stats = {
            "total_attempts": 0,
            "total_retries": 0,
            "total_successes": 0,
            "total_failures": 0,
        }
