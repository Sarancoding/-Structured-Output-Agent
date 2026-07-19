"""
FastAPI API layer for the Structured Output Agent.

Provides RESTful endpoints for:
- Processing queries through the agent pipeline
- Validating raw data against schemas
- Accessing agent statistics and history
- Managing schemas and generators
- Reading logs
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agent.core import StructuredOutputAgent, get_agent, reset_agent
from agent.logger import get_logger, read_logs, get_validation_stats
from agent.schemas import (
    AgentConfig,
    SCHEMA_REGISTRY,
    list_available_schemas,
)

logger = get_logger(__name__)

# ─── App Creation ─────────────────────────────────────────────────────────────

def create_app(agent: Optional[StructuredOutputAgent] = None) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        agent: Pre-configured agent instance. Creates default if not provided.

    Returns:
        Configured FastAPI app.
    """
    app = FastAPI(
        title="Structured Output Agent API",
        description="API for generating, validating, and managing structured outputs from AI agents",
        version="1.0.0",
    )

    # CORS
    origins = os.environ.get("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    agent_instance = agent or get_agent()

    # ─── Request/Response Models ───────────────────────────────────────────

    class ProcessRequest(BaseModel):
        query: Optional[str] = Field(None, description="The user query text")
        generator: str = Field(
            default="mock_success",
            description="Generator to use (mock_success, mock_fail_once, mock_always_fails)",
        )
        schema: str = Field(
            default="TextAnalysis",
            description="Schema name to validate against",
        )
        context: Dict[str, Any] = Field(
            default_factory=dict,
            description="Additional context/metadata",
        )

    class ValidateRequest(BaseModel):
        raw_data: Dict[str, Any] = Field(
            ..., description="Raw data to validate against the schema"
        )
        schema: str = Field(
            ..., description="Schema name to validate against"
        )

    class ConfigUpdateRequest(BaseModel):
        max_retries: Optional[int] = Field(None, ge=0, le=10)
        base_delay_seconds: Optional[float] = Field(None, gt=0, le=60)
        backoff_multiplier: Optional[float] = Field(None, gt=1.0, le=10.0)
        log_level: Optional[str] = Field(None, pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # ─── Endpoints ─────────────────────────────────────────────────────────

    # Try to serve static files from frontend/dist if they exist
    frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

    if os.path.exists(frontend_dist_path):
        app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")

        @app.get("/")
        async def root():
            """Serve the frontend React application."""
            return FileResponse(os.path.join(frontend_dist_path, "index.html"))
    else:
        @app.get("/")
        async def root():
            """Root endpoint with API information (fallback when frontend not built)."""
            return {
                "name": "Structured Output Agent API",
                "version": "1.0.0",
                "status": "running",
                "docs": "/docs",
                "openapi": "/openapi.json",
                "warning": "Frontend dist directory not found. Please build the frontend."
            }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.post("/process", summary="Process a query through the agent pipeline")
    async def process_request(request: ProcessRequest):
        """
        Process a query through the structured output pipeline.

        Generates output using the specified generator, validates it against
        the specified schema, with automatic retry on validation failures.
        """
        try:
            result = agent_instance.process(
                generator_name=request.generator,
                schema_name=request.schema,
                context={
                    "query": request.query or "",
                    **request.context,
                },
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Processing error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/validate", summary="Validate raw data against a schema")
    async def validate_data(request: ValidateRequest):
        """
        Validate raw data directly against a named schema without generation.

        Useful for testing data or pre-validating external inputs.
        """
        try:
            result = agent_instance.validate_raw(
                raw_data=request.raw_data,
                schema_name=request.schema,
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/schemas", summary="List all available schemas")
    async def list_schemas():
        """List all registered Pydantic schemas with their fields."""
        return {
            "schemas": list_available_schemas(),
            "count": len(SCHEMA_REGISTRY),
        }

    @app.get("/schemas/{schema_name}", summary="Get schema details")
    async def get_schema(schema_name: str):
        """
        Get detailed information about a specific schema.

        Returns field definitions, types, and descriptions.
        """
        schema_class = SCHEMA_REGISTRY.get(schema_name)
        if not schema_class:
            raise HTTPException(
                status_code=404,
                detail=f"Schema '{schema_name}' not found",
            )

        fields = {}
        for name, field_info in schema_class.model_fields.items():
            fields[name] = {
                "type": str(field_info.annotation),
                "required": field_info.is_required(),
                "default": (
                    str(field_info.default) if field_info.default is not None
                    else None
                ),
                "description": field_info.description or "",
            }

        return {
            "name": schema_name,
            "description": (schema_class.__doc__ or "").strip(),
            "fields": fields,
            "field_count": len(fields),
        }

    @app.get("/generators", summary="List available generators")
    async def list_generators():
        """List all registered generators."""
        return {
            "generators": agent_instance.list_generators(),
            "count": len(agent_instance.list_generators()),
        }

    @app.get("/history", summary="Get processing history")
    async def get_history(
        limit: int = 10,
        status: Optional[str] = None,
    ):
        """
        Get the agent's processing history.

        Args:
            limit: Maximum number of entries (default: 10).
            status: Optional filter by status.
        """
        return {
            "history": agent_instance.get_history(limit=limit, status_filter=status),
            "total": len(agent_instance.processing_history),
        }

    @app.get("/stats", summary="Get agent statistics")
    async def get_stats():
        """Get aggregate agent statistics and performance metrics."""
        return agent_instance.get_stats()

    @app.post("/reset", summary="Reset agent state")
    async def reset():
        """Reset processing history and retry statistics."""
        agent_instance.reset()
        return {"status": "reset"}

    @app.post("/config", summary="Update agent configuration")
    async def update_config(config: ConfigUpdateRequest):
        """
        Update agent configuration parameters.

        Only provided fields are updated.
        """
        updates = config.model_dump(exclude_none=True)
        if updates:
            for key, value in updates.items():
                if hasattr(agent_instance.config, key):
                    setattr(agent_instance.config, key, value)
            return {
                "status": "updated",
                "config": agent_instance.config.model_dump(),
            }
        return {
            "status": "no_changes",
            "config": agent_instance.config.model_dump(),
        }

    @app.get("/logs", summary="Read structured logs")
    async def get_logs(
        level: Optional[str] = None,
        limit: int = 100,
        request_id: Optional[str] = None,
    ):
        """
        Read agent log entries with optional filtering.

        Args:
            level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            limit: Maximum entries to return.
            request_id: Filter by specific request ID.
        """
        log_file = agent_instance.config.log_file or "logs/agent.log"
        entries = read_logs(
            log_file=log_file,
            level=level,
            limit=limit,
            request_id=request_id,
        )
        return {
            "entries": entries,
            "count": len(entries),
            "stats": get_validation_stats(log_file=log_file),
        }

    @app.post("/enrich", summary="Enrich context with retry feedback")
    async def enrich_with_retry_context(
        generator: str,
        schema: str,
        query: Optional[str] = None,
    ):
        """
        Simulate enriched generation with retry feedback context.

        This is useful for demonstrating how retry context is passed
        to generators for improved subsequent attempts.
        """
        try:
            result = agent_instance.process(
                generator_name=generator,
                schema_name=schema,
                context={"query": query or "Demo query", "enriched": True},
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return app
