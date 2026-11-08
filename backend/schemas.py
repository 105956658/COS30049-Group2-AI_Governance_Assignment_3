"""
schemas.py - Pydantic request/response models. These match the contract the front end
uses (frontend/src/api/detector.js and mock.js), so the UI works unchanged.

Descriptions and examples here are what the /docs page shows.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

EXAMPLE_TEXT = (
    "Climate change is one of the most pressing issues of our time. "
    "It affects ecosystems, economies and communities around the world. "
    "Moreover, it is crucial to ensure that various stakeholders work together "
    "to develop sustainable solutions for future generations."
)


# --- Requests ------------------------------------------------------------------
class PredictRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",   # unknown fields are rejected, not ignored
        json_schema_extra={"examples": [{"text": EXAMPLE_TEXT}]},
    )

    # min_length=1 rejects an empty string straight away. The 20-word minimum and the
    # 10,000-character maximum are checked in main.py so they return our own error
    # codes (text_too_short 422, text_too_long 413) with a clear message.
    text: str = Field(
        ...,
        min_length=1,
        description="The text to check: English prose, at least 20 words and at most 10,000 characters.",
    )


# --- Responses -----------------------------------------------------------------
class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"status": "ok", "model_loaded": True, "model_version": "svc-gmm-rfr-1.0"}]}
    )

    status: Literal["ok"] = Field(..., description='Always "ok" when the server answers.')
    model_loaded: bool = Field(..., description="True once the models have been loaded at start-up.")
    model_version: str = Field(..., description="Version of the deployed model.")


class ScoreRange(BaseModel):
    low: float = Field(..., ge=0, le=1, description="Lower end of the model range.")
    high: float = Field(..., ge=0, le=1, description="Upper end of the model range.")


class SentenceScore(BaseModel):
    text: str = Field(..., description="One sentence of the input, in reading order.")
    p_ai: Optional[float] = Field(None, ge=0, le=1, description="P(AI) for this sentence; null when the sentence is too short to score")


class PredictResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "label": "ai",
                    "confidence": 0.87,
                    "ai_score": 0.87,
                    "score_range": {"low": 0.72, "high": 0.94},
                    "sentences": [
                        {"text": "Climate change is one of the most pressing issues of our time.", "p_ai": 0.91},
                        {"text": "It affects ecosystems, economies and communities around the world.", "p_ai": 0.79},
                        {"text": "Moreover, it is crucial to ensure that various stakeholders work together "
                                 "to develop sustainable solutions for future generations.", "p_ai": 0.95},
                    ],
                    "word_count": 38,
                    "model_version": "svc-gmm-rfr-1.0",
                }
            ]
        }
    )

    label: Literal["ai", "human"] = Field(..., description='"ai" when ai_score >= 0.5, otherwise "human".')
    confidence: float = Field(..., ge=0, le=1, description="Probability of the predicted label")
    ai_score: float = Field(..., ge=0, le=1, description="Document-level P(AI) from the regressor")
    score_range: ScoreRange = Field(..., description="5th-95th percentile of the random forest's trees")
    sentences: list[SentenceScore]
    word_count: int = Field(..., ge=0, description="Number of words in the submitted text.")
    model_version: str = Field(..., description="Version of the model that produced this result.")


# --- Errors (for the /docs page) ------------------------------------------------
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorBody(BaseModel):
    code: str = Field(..., description="Machine-readable error code, e.g. text_too_long.")
    message: str = Field(..., description="Human-readable message the front end shows.")
    details: list[ErrorDetail] = []


class ErrorResponse(BaseModel):
    error: ErrorBody


def _error(description: str, code: str, message: str, field: Optional[str] = None) -> dict:
    """One documented error response: the shared JSON shape plus a concrete example."""
    details = [{"field": field, "message": message}] if field else []
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {"application/json": {"example": {"error": {"code": code, "message": message, "details": details}}}},
    }


ERROR_RESPONSES = {
    413: _error("Text or request body too large", "text_too_long", "Text must be at most 10,000 characters.", "text"),
    422: _error("Invalid input (too short, wrong fields, nothing scorable)", "text_too_short",
                "Text must contain at least 20 words.", "text"),
    429: _error("Rate limit exceeded (30 per minute per IP). Sent with a Retry-After header.", "rate_limited",
                "Too many checks in a short time. Please wait a moment and try again."),
    500: _error("Unexpected server error. No stack trace or internal detail is returned.", "internal_error",
                "The server hit an unexpected problem. Please try again."),
    503: _error("Server busy (all inference slots taken) or prediction timed out. Sent with Retry-After: 5.",
                "server_busy", "The service is busy right now. Please try again in a few seconds."),
}

FILE_ERROR_RESPONSES = {
    **ERROR_RESPONSES,
    413: _error("File larger than 32,000 bytes (file_too_large), its text over 10,000 characters "
                "(text_too_long), or request body too large", "file_too_large",
                "File must be at most 32,000 bytes."),
    415: _error("Not a .txt file or unsafe file name (unsupported_file_type), not valid UTF-8 "
                "(invalid_encoding), or binary/control characters (invalid_file_content)",
                "unsupported_file_type", "Upload a .txt file with a valid filename."),
}