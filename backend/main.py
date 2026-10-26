"""
main.py - TextTrace API (FastAPI).

    GET  /api/health   -> is the server up and the model loaded? (used by the header status dot)
    POST /api/predict  -> check a text for AI generation

Run from the backend folder:
    uvicorn main:app --port 8000
(no --reload during the DoS demo - it doesn't mix well with the process pool on Windows)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

import settings
from errors import (
    ApiError,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from inference import gate
from limits import BodySizeLimitMiddleware, RateLimiter
from schemas import (
    ERROR_RESPONSES,
    HealthResponse,
    PredictRequest,
    PredictResponse,
    ScoreRange,
    SentenceScore,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    gate.start()   # the model is loaded once here, not per request
    yield
    gate.stop()


app = FastAPI(title="TextTrace API", version=settings.MODEL_VERSION, lifespan=lifespan)

# Middleware: the last one added runs first, so CORS wraps everything (errors included).
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.MAX_BODY_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,   # only our front end, never "*"
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
    allow_credentials=False,
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

rate_limit = RateLimiter(settings.RATE_LIMIT_PER_MINUTE)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", model_loaded=gate.ready, model_version=settings.MODEL_VERSION)


@app.post(
    "/api/predict",
    response_model=PredictResponse,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(rate_limit)],
)
async def predict(req: PredictRequest) -> PredictResponse:
    text = req.text

    # Cheap checks first, so bad input never reaches the expensive model
    if len(text) > settings.MAX_CHARS:
        message = f"Text must be at most {settings.MAX_CHARS:,} characters."
        raise ApiError(413, "text_too_long", message, [{"field": "text", "message": message}])

    word_count = len(text.split())
    if word_count < settings.MIN_WORDS:
        message = f"Text must contain at least {settings.MIN_WORDS} words."
        raise ApiError(422, "text_too_short", message, [{"field": "text", "message": message}])

    result = await gate.run(text)
    if result is None:
        message = "The text has no sentences the model can score. Use full sentences of at least 4 words."
        raise ApiError(422, "no_scorable_sentences", message, [{"field": "text", "message": message}])

    ai_score = result["ai_score"]
    label = "ai" if ai_score >= settings.AI_THRESHOLD else "human"
    return PredictResponse(
        label=label,
        confidence=ai_score if label == "ai" else 1 - ai_score,
        ai_score=ai_score,
        score_range=ScoreRange(**result["score_range"]),
        sentences=[SentenceScore(**s) for s in result["sentences"]],
        word_count=word_count,
        model_version=settings.MODEL_VERSION,
    )