"""
settings.py - every setting comes from environment variables (or backend/.env),
never hard-coded, so nothing secret or deployment-specific lives in source code.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:  # python-dotenv is optional; plain env vars still work
    pass

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent   # where pipeline.py, features.py and models/ live


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


# --- Model -----------------------------------------------------------------
MODEL_DIR = os.getenv("MODEL_DIR", str(PROJECT_ROOT / "models"))
MODEL_VERSION = os.getenv("MODEL_VERSION", "svc-gmm-rfr-1.0")
AI_THRESHOLD = 0.5   # same as config.js and the evaluation (acc@0.5)

# --- Input limits (must match frontend/src/config.js) ------------------------
MAX_CHARS = _env_int("MAX_CHARS", 10_000)
MIN_WORDS = _env_int("MIN_WORDS", 20)
# Worst case 4 bytes per character in UTF-8, plus room for the JSON wrapper.
MAX_BODY_BYTES = _env_int("MAX_BODY_BYTES", MAX_CHARS * 4 + 1024)

# --- CORS: only our own front end ---------------------------------------------
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

# --- Denial-of-service protection ----------------------------------------------
DOS_PROTECTION = os.getenv("DOS_PROTECTION", "on").lower() != "off"
INFERENCE_WORKERS = _env_int("INFERENCE_WORKERS", 2)     # processes running the model
INFERENCE_QUEUE = _env_int("INFERENCE_QUEUE", 4)         # requests allowed to wait on top of that
INFERENCE_TIMEOUT = _env_float("INFERENCE_TIMEOUT", 15)  # seconds before the client gets a 503
RATE_LIMIT_PER_MINUTE = _env_int("RATE_LIMIT_PER_MINUTE", 30)  # per client IP; 0 turns it off