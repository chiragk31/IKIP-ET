"""
Standardized API Response Helpers

Every API endpoint must return responses using these helpers.
This ensures consistent response format across the entire platform.

Format:
    Success: {"status": "success", "message": "...", "data": {...}}
    Error:   {"status": "error",   "message": "...", "errors": {...}}
"""

from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
) -> JSONResponse:
    """
    Create a standardized success response.

    Args:
        data: Response payload
        message: Human-readable success message
        status_code: HTTP status code (default 200)

    Returns:
        JSONResponse with standard structure
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "success",
            "message": message,
            "data": data or {},
        },
    )


def error_response(
    message: str,
    errors: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
) -> JSONResponse:
    """
    Create a standardized error response.

    Never expose stack traces. Always return structured errors.

    Args:
        message: Human-readable error message
        errors: Optional detailed error dictionary
        status_code: HTTP status code (default 400)

    Returns:
        JSONResponse with standard error structure
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "message": message,
            "errors": errors or {},
        },
    )


def paginated_response(
    items: list,
    page: int,
    limit: int,
    total: int,
    message: str = "Success",
) -> JSONResponse:
    """
    Create a standardized paginated response.

    Args:
        items: List of items for the current page
        page: Current page number (1-indexed)
        limit: Items per page
        total: Total count of all items
        message: Human-readable message

    Returns:
        JSONResponse with pagination metadata
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": message,
            "data": {
                "items": items,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit if limit > 0 else 0,
                },
            },
        },
    )
