"""
schemas.py - Pydantic request/response models. These match the contract the front end
uses (frontend/src/api/detector.js and mock.js), so the UI works unchanged.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Requests ------------------------------------------------------------------
class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")   # unknown fields are rejected, not ignored

    text: str = Field(..., description="The text to check (20 words to 10,000 characters).")


# --- Responses -----------------------------------------------------------------
class HealthResponse(BaseModel):
    status: Literal["ok"]
    model_loaded: bool
    model_version: str


class ScoreRange(BaseModel):
    low: float = Field(..., ge=0, le=1)
    high: float = Field(..., ge=0, le=1)


class SentenceScore(BaseModel):
    text: str
    p_ai: Optional[float] = Field(None, ge=0, le=1, description="null when the sentence is too short to score")


class PredictResponse(BaseModel):
    label: Literal["ai", "human"]
    confidence: float = Field(..., ge=0, le=1, description="Probability of the predicted label")
    ai_score: float = Field(..., ge=0, le=1, description="Document-level P(AI) from the regressor")
    score_range: ScoreRange = Field(..., description="5th-95th percentile of the random forest's trees")
    sentences: list[SentenceScore]
    word_count: int
    model_version: str


# --- Errors (for the /docs page) ------------------------------------------------
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []


class ErrorResponse(BaseModel):
    error: ErrorBody


ERROR_RESPONSES = {
    413: {"model": ErrorResponse, "description": "Text or request body too large"},
    422: {"model": ErrorResponse, "description": "Invalid input (too short, wrong fields, nothing scorable)"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    500: {"model": ErrorResponse, "description": "Unexpected server error"},
    503: {"model": ErrorResponse, "description": "Server busy or prediction timed out"},
}