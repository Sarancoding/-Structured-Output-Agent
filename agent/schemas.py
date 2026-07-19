"""
Pydantic schema definitions for structured output enforcement.

Defines base models, domain-specific schemas, nested data structures,
and utility schemas for validation and error reporting.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Type Variables ───────────────────────────────────────────────────────────

T = TypeVar("T", bound=BaseModel)


# ─── Enums ────────────────────────────────────────────────────────────────────

class Sentiment(str, Enum):
    """Sentiment classification for text analysis."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class IntentCategory(str, Enum):
    """Categories of user intent for routing."""
    INFORMATION = "information"
    ACTION = "action"
    NAVIGATION = "navigation"
    CONFIRMATION = "confirmation"
    CUSTOM = "custom"


class ValidationStatus(str, Enum):
    """Status of a validation check."""
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
    RETRYING = "retrying"
    FALLBACK = "fallback"


# ─── Base Schema ──────────────────────────────────────────────────────────────

class BaseAgentSchema(BaseModel):
    """Base model for all agent output schemas with common fields."""
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the request/response pair",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO 8601 timestamp of when the response was generated",
    )
    version: str = Field(
        default="1.0",
        description="Schema version for backward compatibility",
    )

    class Config:
        extra = "forbid"  # Reject unknown fields


# ─── Nested / Domain Schemas ──────────────────────────────────────────────────

class Entity(BaseModel):
    """A named entity extracted from text."""
    name: str = Field(..., description="Entity name or label")
    type: str = Field(..., description="Entity type (person, org, location, etc.)")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0 and 1"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)


class KeyPoint(BaseModel):
    """A key point or bullet extracted from content."""
    summary: str = Field(..., min_length=1, description="Brief summary of the point")
    relevance: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score between 0 and 1"
    )

    @field_validator("relevance")
    @classmethod
    def validate_relevance(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("Relevance must be between 0.0 and 1.0")
        return round(v, 4)


class ActionItem(BaseModel):
    """An actionable item extracted from a request."""
    description: str = Field(..., min_length=1, description="Description of the action")
    priority: str = Field(
        default="medium", pattern=r"^(low|medium|high|critical)$",
        description="Priority level: low, medium, high, or critical",
    )
    deadline: Optional[str] = Field(
        None, description="Optional deadline for the action (ISO 8601)"
    )
    assigned_to: Optional[str] = Field(
        None, description="Person or system responsible"
    )


# ─── Analysis Schemas ─────────────────────────────────────────────────────────

class SentimentAnalysis(BaseModel):
    """Sentiment analysis result for a piece of text."""
    sentiment: Sentiment = Field(..., description="Overall sentiment classification")
    score: float = Field(
        ..., ge=-1.0, le=1.0, description="Sentiment score from -1 (negative) to 1 (positive)"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the sentiment analysis"
    )

    @model_validator(mode="after")
    def validate_score_sentiment_consistency(self) -> "SentimentAnalysis":
        if self.sentiment == Sentiment.POSITIVE and self.score < 0:
            raise ValueError("Positive sentiment requires a non-negative score")
        if self.sentiment == Sentiment.NEGATIVE and self.score > 0:
            raise ValueError("Negative sentiment requires a non-positive score")
        return self


class TextAnalysis(BaseModel):
    """Full text analysis result with entities, key points, and sentiment."""
    summary: str = Field(..., min_length=1, description="Concise summary of the text")
    entities: List[Entity] = Field(
        default_factory=list, description="Named entities extracted from text"
    )
    key_points: List[KeyPoint] = Field(
        default_factory=list, description="Key points extracted from text"
    )
    sentiment: Optional[SentimentAnalysis] = Field(
        None, description="Sentiment analysis of the text"
    )
    word_count: int = Field(..., ge=0, description="Total word count of the input text")
    language: str = Field(
        default="en", description="Detected language code (ISO 639-1)"
    )


# ─── Response Schemas ─────────────────────────────────────────────────────────

class StructuredResponse(BaseModel, Generic[T]):
    """
    Generic wrapper for all structured agent responses.

    Wraps typed data payloads with metadata about validation and processing.
    """
    success: bool = Field(..., description="Whether the operation succeeded")
    data: Optional[T] = Field(None, description="The structured response payload")
    error: Optional[str] = Field(None, description="Error message if failed")
    validation_status: ValidationStatus = Field(
        ValidationStatus.SUCCESS,
        description="Status of the validation pipeline",
    )
    retry_attempts: int = Field(
        0, ge=0, description="Number of retry attempts made"
    )
    processing_time_ms: float = Field(
        0.0, ge=0.0, description="Total processing time in milliseconds"
    )


class ValidationErrorDetail(BaseModel):
    """Detailed information about a validation failure."""
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When the validation failure occurred",
    )
    expected_schema: str = Field(
        ..., description="Name of the expected Pydantic schema"
    )
    actual_response: Dict[str, Any] = Field(
        ..., description="The raw response that failed validation"
    )
    validation_errors: List[Dict[str, Any]] = Field(
        ..., description="Specific validation error details"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the request/response",
    )
    request_id: str = Field(
        ..., description="Request ID for traceability"
    )


# ─── Configuration Schema ─────────────────────────────────────────────────────

class AgentConfig(BaseModel):
    """Configuration for the Structured Output Agent."""
    max_retries: int = Field(
        default=3, ge=0, le=10,
        description="Maximum number of retry attempts for validation failures",
    )
    base_delay_seconds: float = Field(
        default=1.0, gt=0, le=60,
        description="Base delay in seconds for exponential backoff",
    )
    backoff_multiplier: float = Field(
        default=2.0, gt=1.0, le=10.0,
        description="Multiplier for exponential backoff calculation",
    )
    log_level: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level for the agent",
    )
    log_file: Optional[str] = Field(
        default="logs/agent.log",
        description="Path to the log file (null for console only)",
    )
    enable_structured_logging: bool = Field(
        default=True,
        description="Whether to use structured JSON logging",
    )


# ─── Schema Registry ──────────────────────────────────────────────────────────

# Map of schema names to their Pydantic model classes for dynamic lookup
SCHEMA_REGISTRY: Dict[str, type[BaseModel]] = {
    "TextAnalysis": TextAnalysis,
    "SentimentAnalysis": SentimentAnalysis,
    "Entity": Entity,
    "KeyPoint": KeyPoint,
    "ActionItem": ActionItem,
    "StructuredResponse": StructuredResponse,
    "ValidationErrorDetail": ValidationErrorDetail,
}


def get_schema_by_name(name: str) -> Optional[type[BaseModel]]:
    """Look up a schema class by its string name."""
    return SCHEMA_REGISTRY.get(name)


def list_available_schemas() -> List[Dict[str, str]]:
    """List all registered schemas with their docstrings."""
    return [
        {
            "name": name,
            "description": (model.__doc__ or "").strip(),
            "fields": list(model.model_fields.keys()),
        }
        for name, model in SCHEMA_REGISTRY.items()
    ]
