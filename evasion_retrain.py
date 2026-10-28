"""
evasion_retrain.py - adversarial-augmentation defence (retrain the detector).

The attack works because the detector leans on surface cues (case, punctuation)
a student can strip in seconds. This defence adds attacked COPIES of training
essays to the data so the model learns signal that survives the attack.

Two modes:
  ai_only  : augment only the AI essays with strip_case_and_punct copies
             (clean copies kept). Teaches "attacked text -> AI", which also makes
             attacked HUMAN text look AI. Saved to models_adv/.
  balanced : augment BOTH human and AI essays with the SAME transform, same
             proportion for both classes, original labels and clean copies kept.
             The attack becomes label-neutral, so the model should stop using
             "looks stripped" as an AI cue. Saved to models_adv_balanced/seed<seed>/.

Only the TRAINING split is augmented; GMM is copied unchanged and the regressor
is refit through the new classifier. Reads data/splits/*.parquet (the original
training scripts read .csv, which is no longer on disk; they are untouched).

Run (ai_detect_proj env, project root):
    python evasion_retrain.py --mode balanced --seed 1
    python evasion_retrain.py --mode ai_only            # reproduces models_adv/
"""
import argparse
import shutil
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor

from features import sentence_dataset, doc_feature_names
from pipeline import build_doc_matrix
from evasion_lib import strip_case_and_punct

ROOT = Path(__file__).resolve().parent
SPLITS = ROOT / "data" / "splits"
SRC_MODELS = ROOT / "models"
DEFAULT_DIR = {"ai_only": ROOT / "models_adv", "balanced": ROOT / "models_adv_balanced" / "seed1"}


def retrain(mode="balanced", seed=1, out_dir=None, n_docs=40000, n_es_docs=5000,
            n_fit_docs=20000, max_sent_per_doc=12, verbose=True):
    """Retrain the detector with augmentation. Returns a dict with timing and
    training-data size. `seed` is the TRAINING seed (sampling of docs); the frozen
    evaluation sample is independent of it."""
    assert mode in ("ai_only", "balanced")
    out_dir = Path(out_dir) if out_dir else DEFAULT_DIR[mode]
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()

    train = pd.read_parquet(SPLITS / "train.parquet", columns=["text", "is_ai"])
    # original (clean) training sentences
    X, y = sentence_dataset(train, n_docs, max_sent_per_doc, seed=seed)

    # augmented copies: AI only, or BOTH classes (same proportion = all sampled docs)
    used = train.sample(min(n_docs, len(train)), random_state=seed)
    aug = used[used["is_ai"] == 1].copy() if mode == "ai_only" else used.copy()
    aug["text"] = aug["text"].map(strip_case_and_punct)
    Xa, ya = sentence_dataset(aug, len(aug), max_sent_per_doc, seed=seed)
    X_aug = np.vstack([X, Xa])
    y_aug = np.concatenate([y, ya])
    if verbose:
        print(f"[{mode} seed={seed}] original {len(y):,} + augmented {len(ya):,} "
              f"= {len(y_aug):,} sentences (AI share {y_aug.mean():.2f})")

    # early-stopping docs: held-out TRAIN docs, never augmented
    es_pool = train.drop(index=used.index)
    Xes, yes = sentence_dataset(es_pool, n_es_docs, max_sent_per_doc, seed=seed + 7)

    clf = lgb.LGBMClassifier(
        n_estimators=1000, learning_rate=0.05, num_leaves=63, min_child_samples=50,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.8, class_weight="balanced",
        random_state=0, n_jobs=-1, verbose=-1)
    clf.fit(X_aug, y_aug, eval_set=[(Xes, yes)], eval_metric="auc",
            callbacks=[lgb.early_stopping(50, verbose=False)])
    joblib.dump(clf, out_dir / "classifier.joblib")

    shutil.copy(SRC_MODELS / "gmm.joblib", out_dir / "gmm.joblib")
    gmm = joblib.load(out_dir / "gmm.joblib")
    k = gmm["k"]

    val = pd.read_parquet(SPLITS / "val.parquet", columns=["text", "is_ai"])
    d = val.sample(min(n_fit_docs, len(val)), random_state=4).reset_index(drop=True)
    Xd, keep = build_doc_matrix(d["text"], clf, gmm)
    yv = d["is_ai"].to_numpy()[keep].astype(float)
    rfr = RandomForestRegressor(n_estimators=300, min_samples_leaf=3, max_features=0.5,
                                n_jobs=-1, random_state=0).fit(Xd, yv)
    joblib.dump({"model": rfr, "k": k, "feature_names": doc_feature_names(k)},
                out_dir / "regressor.joblib")

    train_time = time.perf_counter() - t_start
    if verbose:
        print(f"[{mode} seed={seed}] trained in {train_time:.1f}s -> {out_dir}")
    return {"mode": mode, "seed": seed, "out_dir": str(out_dir),
            "train_time_s": train_time, "n_train_sentences": int(len(y_aug))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["ai_only", "balanced"], default="balanced")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--n-docs", type=int, default=40000)
    ap.add_argument("--n-fit-docs", type=int, default=20000)
    a = ap.parse_args()
    info = retrain(mode=a.mode, seed=a.seed, out_dir=a.out_dir,
                   n_docs=a.n_docs, n_fit_docs=a.n_fit_docs)
    print(info)
    print("evaluate with: python evasion_eval.py")


if __name__ == "__main__":
    main()
