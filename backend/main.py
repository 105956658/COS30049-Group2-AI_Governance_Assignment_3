"""
main.py - TextTrace API (FastAPI).

    GET  /api/health   -> is the server up and the model loaded? (used by the header status dot)
    POST /api/predict  -> check a text for AI generation
    POST /api/predict-file -> check an uploaded .txt file (same response as /api/predict)

Descriptions and examples for every endpoint appear on http://127.0.0.1:8000/docs.

Run from the backend folder:
    uvicorn main:app --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, UploadFile
from upload_security import read_safe_text_file
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
    FILE_ERROR_RESPONSES,
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


app = FastAPI(
    title="TextTrace API",
    version=settings.MODEL_VERSION,
    lifespan=lifespan,
    description=(
        "Estimates how likely a piece of English writing is to be AI-generated.\n\n"
        "**Limits:** text 20 words to 10,000 characters; `.txt` uploads up to 32,000 bytes; "
        "request body up to 41,024 bytes; 30 predictions per minute per IP (429); "
        "at most 6 predictions in flight (503 when busy).\n\n"
        "**Every error** uses the same JSON shape: "
        '`{"error": {"code": "...", "message": "...", "details": [{"field": "...", "message": "..."}]}}`.\n\n'
        "Results are estimates and must not be used to judge real students."
    ),
    openapi_tags=[
        {"name": "Prediction", "description": "Score pasted text or a .txt file."},
        {"name": "System", "description": "Health check used by the front end's status badge."},
    ],
)

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


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check the server is up and the model is loaded",
    description=(
        "Returns `model_loaded: true` once the models have been loaded at start-up. "
        "The front end calls this to show **Model online** or **Service offline** in the header. "
        "It never touches the model, so it stays fast even while predictions are running.\n\n"
        "**Example request:** `GET /api/health` (no body)."
    ),
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", model_loaded=gate.ready, model_version=settings.MODEL_VERSION)


@app.post(
    "/api/predict",
    response_model=PredictResponse,
    responses=ERROR_RESPONSES,
    dependencies=[Depends(rate_limit)],
    tags=["Prediction"],
    summary="Check pasted text for AI generation",
    description=(
        "Send JSON `{\"text\": \"...\"}`. The text is split into sentences the same way as in training. "
        "The calibrated LinearSVC scores each sentence, the GMM adds style-cluster posteriors, and the "
        "random-forest regressor turns these into one document-level `ai_score` with a `score_range`. "
        "The text is processed in memory and never stored.\n\n"
        "Cheap checks run first: over 10,000 characters returns 413, and under 20 words returns 422, "
        "so bad input never reaches the model."
    ),
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

@app.post(
    "/api/predict-file",
    response_model=PredictResponse,
    responses=FILE_ERROR_RESPONSES,
    dependencies=[Depends(rate_limit)],
    tags=["Prediction"],
    summary="Check an uploaded .txt file for AI generation",
    description=(
        "Send one UTF-8 `.txt` file as multipart form data in the field `file` (max 32,000 bytes). "
        "`upload_security.py` checks the file name, size and actual bytes before the model runs; the "
        "declared MIME type is not trusted, and the file is never saved or executed. The text then goes "
        "through the same checks and model as `/api/predict`, and the response is identical.\n\n"
        "**Example request:**\n"
        "```\n"
        'curl -X POST http://127.0.0.1:8000/api/predict-file -F "file=@essay.txt;type=text/plain"\n'
        "```"
    ),
)
async def predict_file(
    file: UploadFile = File(..., description="A UTF-8 plain-text .txt file, up to 32,000 bytes."),
) -> PredictResponse:
    text = await read_safe_text_file(file)
    return await predict(PredictRequest(text=text))