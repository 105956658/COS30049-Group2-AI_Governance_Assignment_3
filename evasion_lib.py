"""
evasion_lib.py - shared helpers for the detection-evasion experiment.

One place for everything the experiment scripts need: loading the detector,
freezing a fixed sample, scoring text, metrics, the evasion-success-rate, the
attack transforms, and the normalization defence. Local-only: it reads models/
and data/splits/ from disk and makes no network calls.

The detector under test is the shipped document chain:
    per-sentence classifier -> GMM posteriors -> RandomForest document score
reached through pipeline.build_doc_matrix, thresholded (default 0.5).
"""
import os
import json
import re
import string
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix)

from pipeline import load_models, build_doc_matrix
from features import split_sentences, is_scorable

ROOT = Path(__file__).resolve().parent
DATA_SPLITS = ROOT / "data" / "splits"
# EVASION_OUT lets a run redirect output elsewhere (used for safe verification
# so we never overwrite saved results in results/evasion/).
OUT = Path(os.getenv("EVASION_OUT", str(ROOT / "results" / "evasion")))
OUT.mkdir(parents=True, exist_ok=True)

THRESHOLD = float(os.getenv("EVASION_THRESHOLD", "0.5"))
DEFAULT_SEED = 5          # frozen-sample seed (matches robustness_eval.py)
DEFAULT_N = 10_000
BATCH_SIZE = 100


def set_threshold(t):
    global THRESHOLD
    THRESHOLD = float(t)
    return THRESHOLD


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def calculate_metrics(y_true, scores, threshold=None):
    """Metrics for one scored set. Predicts AI when score > threshold."""
    threshold = THRESHOLD if threshold is None else threshold
    y_true = np.asarray(y_true, dtype=int)
    scores = np.asarray(scores, dtype=float)
    pred = (scores > threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    both = len(np.unique(y_true)) == 2
    return {
        "n": len(y_true), "human_n": int((y_true == 0).sum()),
        "ai_n": int((y_true == 1).sum()),
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, scores) if both else float("nan"),
        "false_positive_rate": fp / (fp + tn) if fp + tn else float("nan"),
        "false_negative_rate": fn / (fn + tp) if fn + tp else float("nan"),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def summarize(y, scores):
    """Flat metric dict over the scorable subset. detection_rate = recall on AI;
    false_positive_rate = humans wrongly flagged as AI."""
    y = np.asarray(y, dtype=int)
    scores = np.asarray(scores, dtype=float)
    finite = np.isfinite(scores)
    n_total = len(scores)
    if int(finite.sum()) == 0:
        return {"n_total": n_total, "n_scored": 0, "n_unscorable": n_total}
    m = calculate_metrics(y[finite], scores[finite])
    m["detection_rate"] = m["recall"]
    m["n_total"] = n_total
    m["n_scored"] = int(finite.sum())
    m["n_unscorable"] = n_total - int(finite.sum())
    return m


def evasion_success_rate(y, base_scores, attacked_scores):
    """ESR: of AI docs CAUGHT at baseline, the fraction that flip to human after
    the attack. Returns (esr, n_caught_baseline, n_flipped)."""
    y = np.asarray(y, dtype=int)
    base = np.asarray(base_scores, dtype=float)
    att = np.asarray(attacked_scores, dtype=float)
    paired = np.isfinite(base) & np.isfinite(att)
    caught = paired & (y == 1) & (base > THRESHOLD)
    n_caught = int(caught.sum())
    if n_caught == 0:
        return float("nan"), 0, 0
    flipped = caught & (att <= THRESHOLD)
    return int(flipped.sum()) / n_caught, n_caught, int(flipped.sum())


# --------------------------------------------------------------------------- #
# Detector + scoring
# --------------------------------------------------------------------------- #
def load_detector(model_dir=None):
    """Load a detector once (default: shipped models/). n_jobs=1 for determinism."""
    models = load_models(str(model_dir or (ROOT / "models")))
    models["rfr"]["model"].n_jobs = 1
    return models


def eligible(text):
    return any(is_scorable(s) for s in split_sentences(text))


def score_texts(texts, models, batch_size=BATCH_SIZE, progress=False):
    """Document AI-score in [0,1] per text, aligned to input order; NaN if the
    text has no scorable sentence. Mirrors robustness_eval.predict_batches."""
    texts = list(texts)
    scores = np.full(len(texts), np.nan)
    valid = [i for i, t in enumerate(texts) if eligible(t)]
    for off in range(0, len(valid), batch_size):
        idx = valid[off:off + batch_size]
        batch = [texts[i] for i in idx]
        X, kept = build_doc_matrix(batch, models["clf"], models["gmm"], n_jobs=1)
        preds = models["rfr"]["model"].predict(X)
        for local, s in zip(kept, preds):
            scores[idx[int(local)]] = float(s)
        if progress:
            print(f"  scored {min(off + batch_size, len(valid)):,}/{len(valid):,}", flush=True)
    finite = scores[np.isfinite(scores)]
    if finite.size and ((finite < 0) | (finite > 1)).any():
        raise ValueError("Predicted scores must be between 0 and 1.")
    return scores


# --------------------------------------------------------------------------- #
# Frozen sample
# --------------------------------------------------------------------------- #
def freeze_sample(dataset, n=DEFAULT_N, seed=DEFAULT_SEED, force=False):
    """Fixed evaluation sample for `dataset`. Saved to OUT/sample_<dataset>.parquet
    on first use and reloaded afterwards, so every run sees identical documents."""
    frozen = OUT / f"sample_{dataset}.parquet"
    if frozen.exists() and not force:
        return pd.read_parquet(frozen)
    src = DATA_SPLITS / f"{dataset}.parquet"
    if not src.exists():
        raise FileNotFoundError(f"Missing {src}. Place the Kaggle split there first.")
    df = pd.read_parquet(src, columns=["text", "is_ai"])
    if (df.empty or df["text"].isna().any()
            or not df["text"].map(lambda v: isinstance(v, str)).all()
            or not df["is_ai"].isin([0, 1]).all()):
        raise ValueError(f"{src.name}: invalid text or labels.")
    df["text"] = df["text"].str.strip()
    if df.groupby("text")["is_ai"].nunique().gt(1).any():
        raise ValueError(f"{src.name}: conflicting labels for identical text.")
    df = df.drop_duplicates("text").reset_index(drop=True)
    if len(df) > n:
        df = df.sample(n, random_state=seed).reset_index(drop=True)
    df.to_parquet(frozen)
    print(f"froze {len(df):,} docs -> {frozen}")
    return df


# --------------------------------------------------------------------------- #
# IO
# --------------------------------------------------------------------------- #
def save_json(name, payload):
    (OUT / name).write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")
    print(f"wrote {OUT / name}")


def save_csv(name, df):
    df.to_csv(OUT / name, index=False)
    print(f"wrote {OUT / name}")


def record_metric(row):
    """Append one row to OUT/metrics.csv, replacing any row with the same
    (dataset, stage, condition)."""
    path = OUT / "metrics.csv"
    new = pd.DataFrame([row])
    if path.exists():
        old = pd.read_csv(path)
        key = ["dataset", "stage", "condition"]
        if all(c in old.columns for c in key):
            mask = ~(old[key] == new[key].iloc[0]).all(axis=1)
            new = pd.concat([old[mask], new], ignore_index=True)
    new.to_csv(path, index=False)
    print(f"updated {path}")


def save_scores(name, df_sample, scores):
    out = pd.DataFrame({"is_ai": df_sample["is_ai"].to_numpy(),
                        "score": np.asarray(scores, dtype=float)})
    out.to_parquet(OUT / name)
    return out


# --------------------------------------------------------------------------- #
# Attacks (text -> text, deterministic)
# --------------------------------------------------------------------------- #
_PUNCT_TABLE = str.maketrans({c: " " for c in string.punctuation})
_FILLERS = ["i think", "honestly", "in my opinion", "you know", "i mean", "to me"]
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def lowercase(text):
    """Zeroes uppercase_ratio."""
    return text.lower()


def remove_punctuation(text):
    """Strips punctuation (keeps capitals). Also the 'strip punct, keep caps' attack."""
    return text.translate(_PUNCT_TABLE)


def strip_case_and_punct(text):
    """Headline everyday attack: lower case AND no punctuation."""
    return remove_punctuation(text.lower())


def strip_punct_keep_caps(text):
    """Variant attack used to probe a defence trained on strip_case_and_punct:
    remove punctuation but KEEP capitalisation (a case the balanced model did not
    see verbatim)."""
    return remove_punctuation(text)


def filler_injection(text):
    """Adapted attack that survives normalization: inject first-person/stopword
    fillers to shift first_person_ratio and stopword_ratio."""
    sentences = _SENT_SPLIT.split(text)
    out, f = [], 0
    for i, s in enumerate(sentences):
        if s and i % 3 == 0:
            s = f"{_FILLERS[f % len(_FILLERS)]}, {s[0].lower()}{s[1:]}" if len(s) > 1 else s
            f += 1
        out.append(s)
    return " ".join(out)


ATTACKS = {
    "lowercase": lowercase,
    "remove_punctuation": remove_punctuation,
    "strip_case_and_punct": strip_case_and_punct,
    "strip_punct_keep_caps": strip_punct_keep_caps,
    "filler_injection": filler_injection,
}


# --------------------------------------------------------------------------- #
# Defense: serve-time input normalization
# --------------------------------------------------------------------------- #
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)
_SMART = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'",
                        "–": "-", "—": "-", "…": "..."})


def normalize_text(text):
    """Canonicalize before scoring: NFKC, strip zero-width, standardize smart
    quotes/dashes, lower-case, collapse whitespace (sentence punctuation kept)."""
    t = unicodedata.normalize("NFKC", text)
    t = t.translate(_ZERO_WIDTH)
    t = t.translate(_SMART)
    t = t.lower()
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()
