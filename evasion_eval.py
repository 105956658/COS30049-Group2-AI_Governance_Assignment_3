"""
evasion_eval.py - compare original vs AI-only vs balanced retrained detectors.

Evaluates three detectors on the frozen test and holdout_2026 samples under clean
and attacked (strip_case_and_punct) input, reporting detection rate, FPR, F1 and
evasion success rate (ESR) - with the ATTACKED FPR always shown beside ESR, since
a defence that beats the attack by flagging everything as AI is not a real win.

It also:
  * runs the balanced retrain with 3 TRAINING seeds (the frozen evaluation sample
    is unchanged) and reports mean and min-max of the balanced numbers;
  * runs one EXTRA attack against the balanced model - strip punctuation but keep
    capitals (strip_punct_keep_caps), a variant it was not trained on verbatim;
  * measures training time, training-data size, and inference latency per document.

Missing balanced models are trained on demand (slow). Results -> results/evasion/.

Run (ai_detect_proj env, project root):
    python evasion_eval.py
"""
import argparse
import time

import numpy as np
import pandas as pd

import evasion_lib as el
from evasion_retrain import retrain

ORIG = el.ROOT / "models"
AI_ONLY = el.ROOT / "models_adv"
SEEDS = [1, 2, 3]
BAL = {1: el.ROOT / "models_adv_balanced" / "seed1",
       2: el.ROOT / "models_adv_balanced" / "seed2",
       3: el.ROOT / "models_adv_balanced" / "seed3"}

_models, _scores = {}, {}


def get_model(dirp):
    k = str(dirp)
    if k not in _models:
        _models[k] = el.load_detector(dirp)
    return _models[k]


def get_scores(dirp, dataset, df, variant):
    k = (str(dirp), dataset, variant)
    if k not in _scores:
        texts = df["text"].tolist()
        tx = texts if variant == "clean" else [el.ATTACKS[variant](t) for t in texts]
        _scores[k] = el.score_texts(tx, get_model(dirp))
    return _scores[k]


def row(detector, variant, y, scores, base):
    m = el.summarize(y, scores)
    esr, n_caught, n_flipped = el.evasion_success_rate(y, base, scores)
    return {"detector": detector, "input": variant,
            "detection_rate": round(m["detection_rate"], 4),
            "attacked_fpr" if variant != "clean" else "fpr": round(m["false_positive_rate"], 4),
            "f1": round(m["f1"], 4),
            "evasion_success_rate": round(esr, 4) if variant != "clean" else np.nan}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+", default=["test", "holdout_2026"])
    a = ap.parse_args()

    # ---- 1. ensure 3 balanced models (train missing ones) ----
    timing = []
    for s in SEEDS:
        d = BAL[s]
        if (d / "regressor.joblib").exists():
            print(f"[retrain] balanced seed {s}: already present at {d}")
            timing.append({"mode": "balanced", "seed": s, "train_time_s": np.nan,
                           "n_train_sentences": np.nan, "out_dir": str(d)})
        else:
            timing.append(retrain(mode="balanced", seed=s, out_dir=d))

    samples = {ds: el.freeze_sample(ds) for ds in a.datasets}

    # ---- 2. three-way comparison (clean + strip_case_and_punct) ----
    for ds in a.datasets:
        df = samples[ds]; y = df["is_ai"].to_numpy()
        rows = []
        for name, dirp in [("original", ORIG), ("ai_only", AI_ONLY), ("balanced_s1", BAL[1])]:
            base = get_scores(dirp, ds, df, "clean")
            rows.append(row(name, "clean", y, base, base))
            att = get_scores(dirp, ds, df, "strip_case_and_punct")
            rows.append(row(name, "strip_case_and_punct", y, att, base))
        el.save_csv(f"eval_three_way_{ds}.csv", pd.DataFrame(rows))
        print(f"\n=== three-way ({ds}) ===")
        print(pd.DataFrame(rows).to_string(index=False))

    # ---- 3. extra attack vs balanced: strip punct, KEEP caps ----
    extra = []
    for ds in a.datasets:
        df = samples[ds]; y = df["is_ai"].to_numpy()
        base = get_scores(BAL[1], ds, df, "clean")
        att = get_scores(BAL[1], ds, df, "strip_punct_keep_caps")
        r = row("balanced_s1", "strip_punct_keep_caps", y, att, base); r["dataset"] = ds
        extra.append(r)
    el.save_csv("eval_extra_attack.csv", pd.DataFrame(extra))
    print("\n=== extra attack (strip_punct_keep_caps vs balanced) ===")
    print(pd.DataFrame(extra).to_string(index=False))

    # ---- 4. multi-seed balanced (strip_case_and_punct): mean + min-max ----
    for ds in a.datasets:
        df = samples[ds]; y = df["is_ai"].to_numpy()
        per = []
        for s in SEEDS:
            base = get_scores(BAL[s], ds, df, "clean")
            att = get_scores(BAL[s], ds, df, "strip_case_and_punct")
            mc, ma = el.summarize(y, base), el.summarize(y, att)
            esr, _, _ = el.evasion_success_rate(y, base, att)
            per.append({"seed": s, "clean_fpr": mc["false_positive_rate"],
                        "clean_f1": mc["f1"], "attacked_fpr": ma["false_positive_rate"],
                        "attack_f1": ma["f1"], "evasion_success_rate": esr})
        pdf = pd.DataFrame(per)
        agg = {"seed": "mean/min-max"}
        for c in ["clean_fpr", "clean_f1", "attacked_fpr", "attack_f1", "evasion_success_rate"]:
            agg[c] = f"{pdf[c].mean():.4f} [{pdf[c].min():.4f}, {pdf[c].max():.4f}]"
        out = pd.concat([pdf.round(4), pd.DataFrame([agg])], ignore_index=True)
        el.save_csv(f"eval_balanced_seeds_{ds}.csv", out)
        print(f"\n=== balanced multi-seed ({ds}) ===")
        print(out.to_string(index=False))

    # ---- 5. timing: train time, data size, inference latency/doc ----
    hd = samples[a.datasets[-1]]
    t0 = time.perf_counter()
    _ = el.score_texts(hd["text"].tolist(), get_model(ORIG))
    lat_ms = (time.perf_counter() - t0) / len(hd) * 1000.0
    tdf = pd.DataFrame(timing)
    tdf["inference_ms_per_doc"] = round(lat_ms, 3)
    el.save_csv("eval_timing.csv", tdf)
    print("\n=== timing ===")
    print(tdf.to_string(index=False))
    print(f"inference latency: {lat_ms:.2f} ms/doc (original detector, {a.datasets[-1]})")


if __name__ == "__main__":
    main()
