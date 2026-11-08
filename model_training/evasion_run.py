"""
evasion_run.py - baseline, attack, and the normalization-defense comparison.

One command does the first three steps of the experiment on a frozen sample:
  * baseline   : score the untouched detector (the "before" numbers)
  * attack     : apply strip_case_and_punct, measure the evasion success rate
  * compare    : 5-condition normalization-defense table + latency

Local-only; attacks our own detector in-process. Optional --sweep prints a
threshold sweep from the baseline scores.

Run (ai_detect_proj env, project root):
    python evasion_run.py --dataset holdout_2026
    python evasion_run.py --dataset test
    python evasion_run.py --dataset holdout_2026 --sweep
Outputs (results/evasion/): baseline_<ds>.json, attack_strip_case_and_punct_<ds>.json,
    comparison_<ds>.csv/json, scores_*, metrics.csv row(s).
"""
import argparse
import time

import numpy as np
import pandas as pd

import evasion_lib as el


def _cond(tag, y, scores, base):
    m = el.summarize(y, scores)
    esr, n_caught, n_flipped = el.evasion_success_rate(y, base, scores)
    return {"condition": tag, "detection_rate": m["detection_rate"],
            "false_positive_rate": m["false_positive_rate"], "f1": m["f1"],
            "evasion_success_rate": esr, "n_flipped": n_flipped,
            "n_caught_baseline": n_caught, "n_scored": m["n_scored"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="holdout_2026")
    ap.add_argument("--threshold", type=float, default=el.THRESHOLD)
    ap.add_argument("--sweep", action="store_true", help="also print a threshold sweep")
    a = ap.parse_args()
    el.set_threshold(a.threshold)

    models = el.load_detector()
    df = el.freeze_sample(a.dataset)
    y = df["is_ai"].to_numpy()
    texts = df["text"].tolist()
    print(f"[run] {a.dataset}: {len(texts):,} docs, threshold {a.threshold}")

    # ---- baseline ----
    s_clean = el.score_texts(texts, models, progress=True)
    el.save_scores(f"scores_baseline_{a.dataset}.parquet", df, s_clean)
    mb = el.summarize(y, s_clean)
    base_row = {"dataset": a.dataset, "stage": "baseline", "condition": "clean",
                "threshold": a.threshold, **mb}
    el.save_json(f"baseline_{a.dataset}.json", base_row)
    el.record_metric(base_row)
    print(f"[baseline] detection={mb['detection_rate']:.3f} FPR={mb['false_positive_rate']:.3f} "
          f"F1={mb['f1']:.3f} AUC={mb['roc_auc']:.3f}")

    if a.sweep:
        print("[sweep] threshold  detection  FPR  f1")
        for t in [0.5, 0.6, 0.7, 0.8, 0.9]:
            m = el.calculate_metrics(y[np.isfinite(s_clean)], s_clean[np.isfinite(s_clean)], t)
            print(f"        {t:.2f}       {m['recall']:.3f}    {m['false_positive_rate']:.3f} {m['f1']:.3f}")

    # ---- attack ----
    attacked = [el.strip_case_and_punct(t) for t in texts]
    s_attack = el.score_texts(attacked, models)
    el.save_scores(f"scores_attack_strip_case_and_punct_{a.dataset}.parquet", df, s_attack)
    ma = el.summarize(y, s_attack)
    esr, n_caught, n_flipped = el.evasion_success_rate(y, s_clean, s_attack)
    atk_row = {"dataset": a.dataset, "stage": "attack", "condition": "strip_case_and_punct",
               "evasion_success_rate": esr, "n_caught_baseline": n_caught,
               "n_flipped": n_flipped, **ma}
    el.save_json(f"attack_strip_case_and_punct_{a.dataset}.json", atk_row)
    el.record_metric(atk_row)
    print(f"[attack] detection={ma['detection_rate']:.3f} FPR={ma['false_positive_rate']:.3f} "
          f"F1={ma['f1']:.3f}  ESR={esr:.3f} ({n_flipped}/{n_caught})")

    # ---- normalization-defense comparison (5 conditions) ----
    adapted = [el.filler_injection(t) for t in texts]
    t0 = time.perf_counter()
    normed_clean = [el.normalize_text(t) for t in texts]
    norm_ms = (time.perf_counter() - t0) / len(texts) * 1000.0
    normed_attacked = [el.normalize_text(t) for t in attacked]
    normed_adapted = [el.normalize_text(t) for t in adapted]

    s_clean_def = el.score_texts(normed_clean, models)
    s_attack_def = el.score_texts(normed_attacked, models)
    s_adapt_def = el.score_texts(normed_adapted, models)

    rows = [
        _cond("1_clean_no_defense", y, s_clean, s_clean),
        _cond("2_attack_no_defense", y, s_attack, s_clean),
        _cond("3_clean_defense", y, s_clean_def, s_clean),
        _cond("4_attack_defense", y, s_attack_def, s_clean),
        _cond("5_adapted_defense", y, s_adapt_def, s_clean),
    ]
    table = pd.DataFrame(rows)
    table["dataset"] = a.dataset
    table["norm_latency_ms_per_doc"] = round(norm_ms, 4)
    el.save_csv(f"comparison_{a.dataset}.csv", table)
    el.save_json(f"comparison_{a.dataset}.json", rows)

    print(f"\n=== Before/after comparison ({a.dataset}) ===")
    print(table[["condition", "detection_rate", "false_positive_rate", "f1",
                 "evasion_success_rate"]].round(4).to_string(index=False))
    print(f"\nNormalization latency: {norm_ms:.3f} ms/doc")


if __name__ == "__main__":
    main()
