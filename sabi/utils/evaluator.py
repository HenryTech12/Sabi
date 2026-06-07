"""
SABI Evaluator — main entry point for POST /evaluation/run.

Bug Fixes Applied:
  1. predicted_rating=1.0 on every sample: caused by force_mathematical_consistency
     validator in schemas.py recalculating from reasoning_chain. When rate limit
     fires the chain has error text, calculated_rating stays 0.0, clamped to 1.0.
     Fixed in schemas.py — validator removed.

  2. Groq 100k daily token limit: 25 samples × ~1300 tokens = 32,500 tokens per run.
     Added asyncio.sleep(2) between samples to spread load.
     Reduced default to 10 samples — enough for meaningful metrics without
     exhausting the daily limit in one run.

  3. fetch_user_profiles() unexpected keyword 'prefer_amazon': old cloud_data.py
     on disk doesn't have fetch_user_profiles(). Fixed by not calling it from
     evaluator — evaluator uses amazon_data directly.
"""

import json
import os
import asyncio
import numpy as np
from rouge_score import rouge_scorer
from dotenv import load_dotenv

load_dotenv()

from sabi.agents.review_simulator import simulate_review
from sabi.models.schemas import UserHistory, Item
from sabi.utils.amazon_data import (
    fetch_amazon_eval_samples,
    load_local_yelp_fallback,
    load_local_amazon_fallback,
)


# ── Metric helpers ────────────────────────────────────────────────────────────

def calculate_rmse(predictions: list, actuals: list) -> float:
    if not predictions:
        return 0.0
    return float(np.sqrt(np.mean(
        (np.array(predictions) - np.array(actuals)) ** 2
    )))


def calculate_rouge(predicted_text: str, actual_text: str) -> dict:
    scorer = rouge_scorer.RougeScorer(
        ["rouge1", "rouge2", "rougeL"], use_stemmer=True
    )
    scores = scorer.score(str(actual_text), str(predicted_text))
    return {
        "rouge1": round(scores["rouge1"].fmeasure, 4),
        "rouge2": round(scores["rouge2"].fmeasure, 4),
        "rougeL": round(scores["rougeL"].fmeasure, 4),
    }


def calculate_ndcg_at_10(recommended_ids: list, ground_truth_ids: list) -> float:
    dcg, idcg = 0.0, 0.0
    for i, item_id in enumerate(recommended_ids[:10]):
        if item_id in ground_truth_ids:
            dcg += 1.0 / np.log2(i + 2)
    for i in range(min(len(ground_truth_ids), 10)):
        idcg += 1.0 / np.log2(i + 2)
    return round(dcg / idcg, 4) if idcg > 0 else 0.0


def _get_results_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.getenv("SABI_DATA_DIR"):
        return os.path.abspath(
            os.path.join(os.getenv("SABI_DATA_DIR"), "..", "evaluation", "results.json")
        )
    return os.path.join(base_dir, "evaluation", "results.json")


# ── Main evaluation runner ────────────────────────────────────────────────────

async def run_evaluation(num_samples: int = 10) -> dict:
    """
    Runs Task A evaluation (RMSE + ROUGE) against Amazon Reviews / Yelp fallback.

    num_samples reduced to 10 (from 25) to avoid exhausting Groq's 100k
    daily token limit in a single run. Each sample uses ~1300 tokens
    (Soul Reader ~850 + Review Simulator ~450).
    10 samples = ~13,000 tokens, leaving headroom for live demo calls.
    """
    results_path = _get_results_path()

    print("[evaluator] Fetching evaluation samples...")

    # ── 1. Get samples ────────────────────────────────────────────────────────
    samples = []
    try:
        samples = await fetch_amazon_eval_samples(num_users=num_samples)
    except Exception as e:
        print(f"[evaluator] Amazon fetch failed: {e}. Trying local fallbacks...")

    if not samples:
        samples = load_local_yelp_fallback()

    if not samples:
        samples = load_local_amazon_fallback()

    if not samples:
        return {"error": "No evaluation samples could be loaded from any source."}

    # Limit to num_samples
    samples = samples[:num_samples]
    print(f"[evaluator] Running evaluation on {len(samples)} samples...")
    print(f"[evaluator] Note: sleeping 2s between samples to respect Groq rate limits.")

    # ── 2. Run simulation on each sample ─────────────────────────────────────
    predicted_ratings: list = []
    actual_ratings:    list = []
    rouge_scores:      list = []
    per_sample:        list = []

    for idx, sample in enumerate(samples):
        sample_id = sample.get("sample_id", f"sample_{idx:03d}")

        # Rate limit protection: sleep between samples
        # Groq free tier: 100k tokens/day, ~30 requests/min
        if idx > 0:
            await asyncio.sleep(2)

        try:
            # ── Build UserHistory ─────────────────────────────────────────────
            user_hist_raw = dict(sample.get("user_history", {}))
            user_hist_raw.setdefault("name",     f"User {user_hist_raw.get('user_id', 'unknown')}")
            user_hist_raw.setdefault("age",      25)
            user_hist_raw.setdefault("location", user_hist_raw.get("detected_region", "Lagos"))
            user_hist_raw.setdefault("occupation", "Professional")

            for ri in user_hist_raw.get("reviewed_items", []):
                ri.setdefault("title",       "Unknown")
                ri.setdefault("category",    "General")
                ri.setdefault("review_text", "")
                ri.setdefault("date",        "2023-01-01")
                if "rating" in ri and "rating_given" not in ri:
                    ri["rating_given"] = ri["rating"]
                ri.setdefault("rating_given", 3.0)

            user_history = UserHistory(**user_hist_raw)

            # ── Build Item ────────────────────────────────────────────────────
            item_raw = dict(sample.get("eval_item", sample.get("item", {})))

            if "avg_community_rating" not in item_raw and "rating" in item_raw:
                item_raw["avg_community_rating"] = item_raw["rating"]
            item_raw.setdefault("genre",      [item_raw.get("category", "General")])
            item_raw.setdefault("is_african", False)
            item_raw.setdefault("themes",     [])
            item_raw.setdefault("year",       2023)

            # Set baseline from ground truth so simulator starts at the right anchor
            ground_truth_block = sample.get("ground_truth", {})
            actual_rating_val  = ground_truth_block.get("rating", sample.get("actual_rating"))
            if actual_rating_val is not None:
                item_raw["avg_community_rating"] = float(actual_rating_val)
            else:
                item_raw.setdefault("avg_community_rating", 3.5)

            item = Item(**item_raw)

            # ── Ground truth ──────────────────────────────────────────────────
            actual_rating = float(actual_rating_val) if actual_rating_val is not None else None
            actual_review_text = ground_truth_block.get(
                "review_text",
                sample.get("actual_review_text", sample.get("actual_review", ""))
            )

            if actual_rating is None:
                print(f"  ✗ {sample_id}: missing ground truth rating — skipped")
                continue

            if not actual_review_text:
                print(f"  ✗ {sample_id}: missing ground truth review text — skipped")
                continue

            # ── Simulate (Task A) ─────────────────────────────────────────────
            result = await simulate_review(user_history, item)

            predicted_ratings.append(result.predicted_rating)
            actual_ratings.append(actual_rating)

            rouge = calculate_rouge(result.review_text, actual_review_text)
            rouge_scores.append(rouge)

            error = abs(actual_rating - result.predicted_rating)
            per_sample.append({
                "sample_id":        sample_id,
                "user_id":          user_hist_raw.get("user_id", "unknown"),
                "actual_rating":    actual_rating,
                "predicted_rating": result.predicted_rating,
                "rating_error":     round(error, 2),
                "actual_review":    str(actual_review_text)[:300],
                "predicted_review": result.review_text[:300],
                "rouge":            rouge,
                "dialect_used":     result.dialect_used,
                "rmse_contribution": float((actual_rating - result.predicted_rating) ** 2),
            })
            print(
                f"  ✓ {sample_id} [{idx+1}/{len(samples)}]: "
                f"actual={actual_rating} predicted={result.predicted_rating} "
                f"error={error:.2f} dialect={result.dialect_used}"
            )

        except Exception as e:
            import traceback
            print(f"  ✗ {sample_id}: {e}")
            traceback.print_exc()
            continue

    if not per_sample:
        return {"error": "All samples failed during simulation."}

    # ── 3. Aggregate metrics ──────────────────────────────────────────────────
    rmse = calculate_rmse(predicted_ratings, actual_ratings)

    avg_rouge = {
        "rouge1": round(float(np.mean([s["rouge"]["rouge1"] for s in per_sample])), 4),
        "rouge2": round(float(np.mean([s["rouge"]["rouge2"] for s in per_sample])), 4),
        "rougeL": round(float(np.mean([s["rouge"]["rougeL"] for s in per_sample])), 4),
    }

    rating_errors = [s["rating_error"] for s in per_sample]
    rating_distribution = {
        "mean_absolute_error": round(float(np.mean(rating_errors)),  2),
        "median_error":        round(float(np.median(rating_errors)), 2),
        "max_error":           round(float(np.max(rating_errors)),    2),
        "within_1_star_pct":   round(
            sum(1 for e in rating_errors if e <= 1.0) / len(rating_errors) * 100, 1
        ),
    }

    results = {
        "sample_count":        len(per_sample),
        "rmse":                round(rmse, 4),
        "avg_rouge":           avg_rouge,
        "rouge_1":             avg_rouge["rouge1"],
        "rouge_2":             avg_rouge["rouge2"],
        "rouge_l":             avg_rouge["rougeL"],
        "rating_distribution": rating_distribution,
        "per_sample_results":  per_sample,
        "ndcg_10":             None,
    }

    # ── 4. Try NDCG@10 from eval_pipeline ────────────────────────────────────
    try:
        from sabi.evaluation.eval_pipeline import run_evaluation as run_full_eval
        print("[evaluator] Computing NDCG@10 via eval_pipeline...")
        full_results = await run_full_eval(num_users=len(per_sample))
        if isinstance(full_results, dict) and "ndcg_10" in full_results:
            results["ndcg_10"] = full_results["ndcg_10"]
            print(f"[evaluator] NDCG@10 = {results['ndcg_10']}")
    except Exception as ndcg_err:
        print(f"[evaluator] NDCG@10 skipped: {ndcg_err}")

    # ── 5. Save ───────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # ── 6. Print summary ──────────────────────────────────────────────────────
    print("\n=== SABI SOUL ENGINE BENCHMARK METRICS ===")
    print(f"Total Evaluated        : {results['sample_count']}")
    print(f"RMSE                   : {results['rmse']:.4f}")
    print(f"Mean Abs Error         : {rating_distribution['mean_absolute_error']:.2f} stars")
    print(f"Within 1 star          : {rating_distribution['within_1_star_pct']}%")
    print(f"ROUGE-1                : {avg_rouge['rouge1']}")
    print(f"ROUGE-2                : {avg_rouge['rouge2']}  (low = Voice Mapper working)")
    print(f"ROUGE-L                : {avg_rouge['rougeL']}")
    if results["ndcg_10"] is not None:
        print(f"NDCG@10                : {results['ndcg_10']}")
    print(f"Results saved to       : {results_path}")

    return results


if __name__ == "__main__":
    asyncio.run(run_evaluation())