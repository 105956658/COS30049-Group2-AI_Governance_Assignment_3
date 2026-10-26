"""
errors.py - every error leaves the API in ONE JSON shape (matches frontend/src/api/client.js):

    { "error": { "code": "text_too_long",
                 "message": "Text must be at most 10,000 characters.",
                 "details": [{ "field": "text", "message": "..." }] } }

Unexpected errors are logged in full on the server but the client only ever sees a
generic message - never a stack trace, file path or exception text.
"""
import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("texttrace")

DEFAULT_MESSAGES = {
    400: "The request could not be understood.",
    404: "This API endpoint does not exist.",
    405: "This method is not allowed on this endpoint.",
    413: "The request is larger than the server accepts.",
    422: "The server could not accept this input.",
    429: "Too many checks in a short time. Please wait a moment and try again.",
    500: "The server hit an unexpected problem. Please try again.",
    503: "The service is busy right now. Please try again in a few seconds.",
}


class ApiError(HTTPException):
    """Raise this anywhere to send a specific code + message in the shared format.
    Subclasses HTTPException so FastAPI passes it through untouched, even when it is
    raised while the request body is being read."""

    def __init__(self, status_code: int, code: str, message: str, details=None, headers=None):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.details = details or []


def error_response(status: int, code: str, message: str, details=None, headers=None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or []}},
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc, ApiError):
        return error_response(exc.status_code, exc.code, exc.detail, exc.details, exc.headers)
    # Framework errors (unknown route, wrong method...) get a friendly message instead of "Not Found"
    message = DEFAULT_MESSAGES.get(exc.status_code, "The request failed.")
    return error_response(exc.status_code, f"http_{exc.status_code}", message, headers=getattr(exc, "headers", None))


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    for err in exc.errors():
        if err.get("type") == "json_invalid":
            details.append({"field": "body", "message": "Request body is not valid JSON."})
            continue
        loc = [str(part) for part in err.get("loc", ()) if part != "body"]
        field = loc[-1] if loc else "body"
        # Only the field name and pydantic's message - never echo the user's input back
        details.append({"field": field, "message": err.get("msg", "Invalid value.")})
    message = f"{details[0]['field']}: {details[0]['message']}" if details else DEFAULT_MESSAGES[422]
    return error_response(422, "validation_error", message, details)


async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)  # full trace in server log only
    return error_response(500, "internal_error", DEFAULT_MESSAGES[500])