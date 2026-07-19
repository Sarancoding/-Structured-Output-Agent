"""
Response validation pipeline.

Validates raw LLM/tool outputs against defined Pydantic schemas,
catches and categorizes validation errors, and produces detailed
error reports for downstream retry logic.
"""

from __future__ import annotations

import traceback
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel, ValidationError

from agent.logger import get_logger
from agent.schemas import ValidationErrorDetail, ValidationStatus

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class ValidationResult(BaseModel):
    """Result of a validation operation."""
    success: bool
    validated_data: Optional[BaseModel] = None
    raw_data: Dict[str, Any]
    status: ValidationStatus
    error_detail: Optional[ValidationErrorDetail] = None
    warning: Optional[str] = None


def validate_output(
    raw_output: Dict[str, Any],
    schema_class: Type[T],
    context: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> ValidationResult:
    """
    Validate raw output against a Pydantic schema.

    Args:
        raw_output: The raw dictionary output to validate.
        schema_class: The Pydantic model class to validate against.
        context: Optional metadata about the request/response.
        request_id: Optional request ID for traceability.

    Returns:
        ValidationResult indicating success or failure with details.

    Raises:
        No exceptions; all validation errors are captured in the result.
    """
    if not isinstance(raw_output, dict):
        return ValidationResult(
            success=False,
            raw_data={"raw_input": str(raw_output)},
            status=ValidationStatus.FAILURE,
            error_detail=ValidationErrorDetail(
                expected_schema=schema_class.__name__,
                actual_response={"raw_input": str(raw_output)},
                validation_errors=[{
                    "type": "type_error",
                    "msg": f"Expected dict, got {type(raw_output).__name__}",
                    "input": str(raw_output)[:500],
                }],
                context=context or {},
                request_id=request_id or "unknown",
            ),
        )

    try:
        validated = schema_class.model_validate(raw_output)
        logger.info(
            "Validation successful",
            extra={
                "schema": schema_class.__name__,
                "request_id": request_id,
                "fields_validated": list(raw_output.keys()),
            },
        )
        return ValidationResult(
            success=True,
            validated_data=validated,
            raw_data=raw_output,
            status=ValidationStatus.SUCCESS,
        )

    except ValidationError as e:
        errors = _format_validation_errors(e)
        logger.warning(
            "Validation failed",
            extra={
                "schema": schema_class.__name__,
                "request_id": request_id,
                "error_count": len(errors),
                "errors": errors,
            },
        )
        return ValidationResult(
            success=False,
            raw_data=raw_output,
            status=ValidationStatus.FAILURE,
            error_detail=ValidationErrorDetail(
                expected_schema=schema_class.__name__,
                actual_response=raw_output,
                validation_errors=errors,
                context=context or {},
                request_id=request_id or "unknown",
            ),
        )

    except Exception as e:
        logger.error(
            f"Unexpected validation error: {e}",
            extra={
                "schema": schema_class.__name__,
                "request_id": request_id,
                "traceback": traceback.format_exc(),
            },
        )
        return ValidationResult(
            success=False,
            raw_data=raw_output,
            status=ValidationStatus.FAILURE,
            error_detail=ValidationErrorDetail(
                expected_schema=schema_class.__name__,
                actual_response=raw_output,
                validation_errors=[{
                    "type": "unexpected_error",
                    "msg": str(e),
                    "traceback": traceback.format_exc(),
                }],
                context=context or {},
                request_id=request_id or "unknown",
            ),
        )


def validate_multiple(
    outputs: List[Tuple[Dict[str, Any], Type[T]]],
    request_id: Optional[str] = None,
) -> List[ValidationResult]:
    """
    Validate multiple outputs against their respective schemas.

    Args:
        outputs: List of (raw_output, schema_class) tuples.
        request_id: Optional request ID for traceability.

    Returns:
        List of ValidationResults in the same order as inputs.
    """
    results = []
    for i, (raw_output, schema_class) in enumerate(outputs):
        result = validate_output(
            raw_output=raw_output,
            schema_class=schema_class,
            context={"batch_index": i},
            request_id=request_id,
        )
        results.append(result)
    return results


def is_valid_json_like(data: Any) -> bool:
    """Check if data looks like valid JSON (dict or list)."""
    return isinstance(data, (dict, list))


def partial_validate(
    raw_output: Dict[str, Any],
    schema_class: Type[T],
) -> Tuple[bool, Optional[BaseModel], List[str]]:
    """
    Attempt partial validation, returning warnings for non-critical issues.

    Useful for lenient mode where missing optional fields are tolerated
    but structural issues are still flagged.

    Returns:
        Tuple of (is_valid, partial_model, warnings_list).
    """
    warnings: List[str] = []
    try:
        validated = schema_class.model_validate(raw_output, strict=False)
        return True, validated, warnings
    except ValidationError as e:
        partial_data = {}
        for field_name, field_info in schema_class.model_fields.items():
            if field_name in raw_output:
                try:
                    field_type = field_info.annotation
                    if field_type and hasattr(field_type, "model_validate"):
                        partial_data[field_name] = field_type.model_validate(
                            raw_output[field_name]
                        )
                    else:
                        partial_data[field_name] = raw_output[field_name]
                except Exception:
                    warnings.append(f"Field '{field_name}' failed partial validation")

        warnings.extend(
            f"Field '{err['loc']}': {err['msg']}"
            for err in _format_validation_errors(e)
        )

        try:
            partial_model = schema_class.model_validate(partial_data)
            return True, partial_model, warnings
        except Exception:
            return False, None, warnings


def _format_validation_errors(error: ValidationError) -> List[Dict[str, Any]]:
    """Format Pydantic validation errors into serializable dicts."""
    formatted = []
    for err in error.errors():
        formatted.append({
            "type": err.get("type", "unknown"),
            "loc": [str(l) for l in err.get("loc", [])],
            "msg": err.get("msg", ""),
            "input": _truncate_value(err.get("input")),
            "ctx": {k: str(v) for k, v in err.get("ctx", {}).items()}
            if err.get("ctx") else None,
        })
    return formatted


def _truncate_value(value: Any, max_len: int = 500) -> Any:
    """Truncate long string values for readability in logs."""
    if isinstance(value, str) and len(value) > max_len:
        return value[:max_len] + "..."
    if isinstance(value, dict):
        return {k: _truncate_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate_value(v) for v in value[:10]] + (
            ["..."] if len(value) > 10 else []
        )
    return value
