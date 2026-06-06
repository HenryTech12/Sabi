# Run with: python -m utils.evaluator
# Requires OPENAI_API_KEY env variable set
# Output saved to evaluation/results.json

import json
import os
import numpy as np
import asyncio
from dotenv import load_dotenv
from rouge_score import rouge_scorer

load_dotenv()

from sabi.agents.review_simulator import simulate_review
from sabi.models.schemas import UserHistory, Item
from sabi.utils.amazon_data import fetch_amazon_eval_samples, load_local_yelp_fallback

def calculate_rmse(predictions: list, actuals: list) -> float:
    if not predictions: 
        return 0.0
    return float(np.sqrt(np.mean((np.array(predictions) - np.array(actuals)) ** 2)))

def calculate_rouge(predicted_text: str, actual_text: str) -> dict:
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = scorer.score(str(actual_text), str(predicted_text))
    return {
        "rouge1": round(scores['rouge1'].fmeasure, 4),
        "rouge2": round(scores['rouge2'].fmeasure, 4),
        "rougeL": round(scores['rougeL'].fmeasure, 4)
    }

def calculate_ndcg_at_10(recommended_ids: list, ground_truth_ids: list) -> float:
    dcg, idcg = 0.0, 0.0
    for i, item_id in enumerate(recommended_ids[:10]):
        if item_id in ground_truth_ids:
            dcg += 1.0 / np.log2(i + 2)
    for i in range(min(len(ground_truth_ids), 10)):
        idcg += 1.0 / np.log2(i + 2)
    return round(dcg / idcg, 4) if idcg > 0 else 0.0

async def run_evaluation() -> dict:
    # Handle absolute environment paths or workspace fallback parameters
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_path = os.path.join(base_dir, "evaluation", "results.json")
    
    if os.getenv("SABI_DATA_DIR"):
        results_path = os.path.join(os.getenv("SABI_DATA_DIR"), "..", "evaluation", "results.json")
        results_path = os.path.abspath(results_path)

    print("[evaluator] Aggregating multi-domain validation evaluation samples...")
    
    # 1. Attempt high-fidelity live streaming via HuggingFace Amazon Reviews Multi
    try:
        samples = await fetch_amazon_eval_samples(num_users=25)
    except Exception as e:
        print(f"[evaluator] Live streaming connection bypassed: {e}. Slipping to fallbacks.")
        samples = []

    # 2. Fall back to absolute local data snapshots if streaming is offline or threshold is breached
    if not samples:
        print("[evaluator] Utilizing absolute local fallback data matrix.")
        samples = load_local_yelp_fallback()

    if not samples:
        print("[evaluator] CRITICAL: No validation samples could be loaded.")
        return {"error": "Evaluation matrices empty."}

    predicted_ratings, actual_ratings = [], []
    rouge_scores = []
    per_sample = []

    print(f"[evaluator] Commencing simulation sequence across {len(samples)} profiles...")

    for sample in samples:
        sample_id = sample.get("sample_id", "unknown_sample")
        try:
            user_hist_raw = sample.get("user_history", {})
            item_raw = sample.get("eval_item", sample.get("item", {}))
            
            # Defensive field mapping normalization for strict Pydantic model alignment
            # Ensures cross-domain and legacy datasets share identical internal signatures
            reviewed_items = user_hist_raw.get("reviewed_items", [])
            for item_entry in reviewed_items:
                if "rating_given" not in item_entry and "rating" in item_entry:
                    item_entry["rating_given"] = item_entry["rating"]
            
            if "avg_community_rating" not in item_raw and "rating" in item_raw:
                item_raw["avg_community_rating"] = item_raw["rating"]
            if "genre" not in item_raw:
                item_raw["genre"] = [item_raw.get("category", "General")]

            # Instantiate standard Pydantic validation boundaries
            user_history = UserHistory(**user_hist_raw)
            item = Item(**item_raw)
            
            # Map flexible target values safely across ground_truth dictionaries or flat files
            ground_truth_block = sample.get("ground_truth", {})
            actual_rating = ground_truth_block.get("rating", sample.get("actual_rating"))
            actual_review_text = ground_truth_block.get("review_text", sample.get("actual_review_text", sample.get("actual_review")))
            
            if actual_rating is None or actual_review_text is None:
                print(f"✗ Sample {sample_id} skipped: Missing ground truth target variables.")
                continue

            # Route execution to Agent 3 (Review Simulator)
            result = await simulate_review(user_history, item)
            
            predicted_ratings.append(result.predicted_rating)
            actual_ratings.append(float(actual_rating))
            
            rouge = calculate_rouge(result.review_text, actual_review_text)
            rouge_scores.append(rouge)
            
            per_sample.append({
                "sample_id": sample_id,
                "user_id": user_hist_raw.get("user_id", "unknown_user"),
                "actual_rating": float(actual_rating),
                "predicted_rating": result.predicted_rating,
                "actual_review": str(actual_review_text),
                "predicted_review": result.review_text,
                "rouge": rouge,
                "rmse_contribution": float((float(actual_rating) - result.predicted_rating) ** 2)
            })
            print(f"✓ Sample {sample_id} safely quantified.")
            
        except Exception as e:
            print(f"✗ Sample {sample_id} experienced runtime parsing exception: {e}")
            continue

    if not per_sample:
        return {"error": "All execution nodes failed schema parsing constraints."}

    avg_rouge = {
        "rouge1": round(np.mean([s["rouge"]["rouge1"] for s in per_sample]), 4),
        "rouge2": round(np.mean([s["rouge"]["rouge2"] for s in per_sample]), 4),
        "rougeL": round(np.mean([s["rouge"]["rougeL"] for s in per_sample]), 4)
    }

    results = {
        "sample_count": len(per_sample),
        "rmse": calculate_rmse(predicted_ratings, actual_ratings),
        "avg_rouge": avg_rouge,
        "rouge_1": avg_rouge["rouge1"],
        "rouge_2": avg_rouge["rouge2"],
        "rouge_l": avg_rouge["rougeL"],
        "per_sample_results": per_sample
    }

    # Atomically write results file back to evaluation log directory
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n=== SABI SOUL ENGINE BENCHMARK METRICS ===")
    print(f"Total Evaluated Run Cohort: {results['sample_count']}")
    print(f"Task A Behavioral Consistency — RMSE: {results['rmse']:.4f}")
    print(f"Task A Semantic Similarity    — ROUGE-1: {avg_rouge['rouge1']} | ROUGE-2: {avg_rouge['rouge2']} | ROUGE-L: {avg_rouge['rougeL']}")
    print(f"[evaluator] Absolute metrics written cleanly to: {results_path}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_evaluation())