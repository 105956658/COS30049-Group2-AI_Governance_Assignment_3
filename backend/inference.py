"""
inference.py - loads the models once and runs predictions with DoS protection.

Why: model inference is CPU-heavy. Running it inside an `async def` endpoint blocks
the event loop, so one slow request freezes the server for every other user. And
with no cap on concurrent work, a flood of requests piles up until the server falls over.

Defence:
  1. Predictions run in a separate process pool, never on the event loop, so the
     server keeps answering other requests (e.g. /api/health) while the model works.
  2. A fixed number of slots (workers + small queue). When all are taken, new
     requests are rejected immediately with 503 + Retry-After instead of queueing forever.
  3. A timeout: a prediction that runs too long returns 503 to the client. The slot
     stays held until the worker really finishes, so we never over-commit the CPU.

DOS_PROTECTION=off switches to the naive version (model called directly inside the
async endpoint) - used only for the "before" measurement.
"""
import asyncio
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import settings
from errors import ApiError

# pipeline.py / features.py live in the project root, one level above backend/
if str(settings.PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(settings.PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Runs inside each worker process. Models are loaded ONCE per process at startup.
# ---------------------------------------------------------------------------
_models = None


def _init_worker(model_dir: str) -> None:
    global _models
    if str(settings.PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(settings.PROJECT_ROOT))
    from pipeline import load_models
    _models = load_models(model_dir)
    _models["rfr"]["model"].n_jobs = 1   # one core per worker; parallelism comes from the pool


def _clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


def _predict(text: str):
    """Runs pipeline.analyze() - the same code path the models were evaluated with:
    LinearSVC per-sentence P(AI) -> GMM posteriors -> RandomForestRegressor document
    score, with the 5th-95th percentile spread across the forest's trees as the range."""
    from pipeline import analyze

    result = analyze(text, _models)
    if result is None:
        return None   # no sentence with >= 4 words -> endpoint returns 422

    score = _clip01(result["overall"])
    low, high = sorted((_clip01(result["low"]), _clip01(result["high"])))
    # The score is the MEAN of the trees, the band is percentiles, so a few outlier
    # trees can leave the mean just outside the band. Widen it so it always contains the score.
    low, high = min(low, score), max(high, score)
    return {
        "ai_score": score,
        "score_range": {"low": low, "high": high},
        "sentences": [
            {"text": s["text"], "p_ai": None if s["p_ai"] is None else _clip01(s["p_ai"])}
            for s in result["sentences"]
        ],
    }


def _warmup(_):
    return _models is not None


# ---------------------------------------------------------------------------
# Runs in the server process: the gate every prediction goes through.
# ---------------------------------------------------------------------------
class InferenceGate:
    def __init__(self):
        self.pool = None
        self.ready = False
        self.capacity = settings.INFERENCE_WORKERS + settings.INFERENCE_QUEUE
        self.in_flight = 0

    def start(self) -> None:
        if settings.DOS_PROTECTION:
            self.pool = ProcessPoolExecutor(
                max_workers=settings.INFERENCE_WORKERS,
                initializer=_init_worker,
                initargs=(settings.MODEL_DIR,),
            )
            # Start the workers and load the models now, not on the first user request
            if not all(self.pool.map(_warmup, range(settings.INFERENCE_WORKERS))):
                raise RuntimeError("Model failed to load in a worker process.")
        else:
            _init_worker(settings.MODEL_DIR)
        self.ready = True

    def stop(self) -> None:
        self.ready = False
        if self.pool:
            self.pool.shutdown(cancel_futures=True)

    def _release(self, _future) -> None:
        self.in_flight -= 1

    async def run(self, text: str):
        if not settings.DOS_PROTECTION:
            # Naive "before" version: blocks the whole event loop for the prediction
            return _predict(text)

        # Load shedding. No await between the check and the increment, so this is
        # race-free on the single event-loop thread.
        if self.in_flight >= self.capacity:
            raise ApiError(
                503, "server_busy",
                "The service is busy right now. Please try again in a few seconds.",
                headers={"Retry-After": "5"},
            )
        self.in_flight += 1

        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(self.pool, _predict, text)
        # The slot is freed only when the worker actually finishes - even if the
        # client times out or disconnects first.
        future.add_done_callback(self._release)

        try:
            return await asyncio.wait_for(asyncio.shield(future), settings.INFERENCE_TIMEOUT)
        except asyncio.TimeoutError:
            raise ApiError(
                503, "processing_timeout",
                "The check took too long. Please try again with a shorter text.",
                headers={"Retry-After": "5"},
            )


gate = InferenceGate()