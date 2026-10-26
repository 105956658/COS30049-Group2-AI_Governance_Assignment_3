"""
DoS demonstration - run against your OWN server on localhost only.

Test 1 (expensive request): sends one maximum-size request and, while it runs, keeps
pinging /api/health and sending a small /api/predict. Measures how long other users wait.

Test 2 (flood): fires many requests at once. Counts 200s vs 503s and checks the server
still answers /api/health during the flood.

Start the server with RATE_LIMIT_PER_MINUTE=0 for these runs, otherwise the rate
limiter answers the flood with 429s before the inference gate is ever reached.

    # before:  $env:DOS_PROTECTION="off"; $env:RATE_LIMIT_PER_MINUTE="0"; uvicorn main:app --port 8000
    python dos_demo.py --label before
    # after:   $env:DOS_PROTECTION="on";  $env:RATE_LIMIT_PER_MINUTE="0"; uvicorn main:app --port 8000
    python dos_demo.py --label after

Results append to results/dos_results.csv
"""
import argparse
import asyncio
import csv
import statistics
import time
from collections import Counter
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
MAX_CHARS = 10_000   # keep in sync with the server

SMALL_TEXT = (
    "The committee reviewed the proposal carefully and agreed to revisit it next month. "
    "Several members raised concerns about the budget and the timeline for delivery."
)


def heavy_text(n_chars: int) -> str:
    """Many short distinct sentences - the most work per character for a sentence-level model."""
    parts, total, i = [], 0, 0
    while True:
        sentence = f"Sentence {i} discusses an idea about topic {i % 37} in some detail. "
        if total + len(sentence) > n_chars:
            break
        parts.append(sentence)
        total += len(sentence)
        i += 1
    return "".join(parts)


async def timed(client, method, path, **kw):
    t0 = time.perf_counter()
    try:
        r = await client.request(method, BASE + path, **kw)
        status = r.status_code
    except httpx.HTTPError:
        status = "error"
    return status, (time.perf_counter() - t0) * 1000


async def test_expensive(client):
    heavy = asyncio.create_task(timed(client, "POST", "/api/predict", json={"text": heavy_text(MAX_CHARS)}))
    await asyncio.sleep(0.05)   # let the heavy request start first
    health_ms, small_ms = [], []
    while not heavy.done():
        (_, h), (_, s) = await asyncio.gather(
            timed(client, "GET", "/api/health"),
            timed(client, "POST", "/api/predict", json={"text": SMALL_TEXT}),
        )
        health_ms.append(h)
        small_ms.append(s)
        await asyncio.sleep(0.1)
    heavy_status, heavy_ms = heavy.result()
    med = lambda xs: round(statistics.median(xs)) if xs else None
    mx = lambda xs: round(max(xs)) if xs else None
    return {
        "heavy_status": heavy_status, "heavy_ms": round(heavy_ms),
        "health_median_ms": med(health_ms), "health_max_ms": mx(health_ms),
        "small_predict_median_ms": med(small_ms), "small_predict_max_ms": mx(small_ms),
    }


async def test_flood(client, n):
    text = heavy_text(5_000)
    t0 = time.perf_counter()
    flood = [asyncio.create_task(timed(client, "POST", "/api/predict", json={"text": text})) for _ in range(n)]
    await asyncio.sleep(0.3)   # let the flood land first, then see if a normal user still gets an answer
    _, health_ms = await timed(client, "GET", "/api/health")
    results = await asyncio.gather(*flood)
    codes = Counter(str(s) for s, _ in results)
    ok_times = [ms for s, ms in results if s == 200]
    rej_times = [ms for s, ms in results if s == 503]
    return {
        "flood_n": n,
        "flood_200": codes.get("200", 0),
        "flood_503": codes.get("503", 0),
        "flood_other": n - codes.get("200", 0) - codes.get("503", 0),
        "flood_total_s": round(time.perf_counter() - t0, 2),
        "flood_503_median_ms": round(statistics.median(rej_times)) if rej_times else None,
        "flood_200_max_ms": round(max(ok_times)) if ok_times else None,
        "health_during_flood_ms": round(health_ms),
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--flood", type=int, default=50)
    args = ap.parse_args()

    limits = httpx.Limits(max_connections=args.flood + 10)
    async with httpx.AsyncClient(timeout=120, limits=limits) as client:
        r1 = await test_expensive(client)
        print(f"[{args.label}] expensive request:", r1)
        await asyncio.sleep(2)
        r2 = await test_flood(client, args.flood)
        print(f"[{args.label}] flood:", r2)

    Path("results").mkdir(exist_ok=True)
    out = Path("results/dos_results.csv")
    row = {"label": args.label, **r1, **r2}
    new = not out.exists()
    with out.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if new:
            w.writeheader()
        w.writerow(row)


if __name__ == "__main__":
    asyncio.run(main())