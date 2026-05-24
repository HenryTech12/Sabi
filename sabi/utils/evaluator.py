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

def calculate_rmse(predictions: list, actuals: list) -> float:
    if not predictions: return 0.0
    return float(np.sqrt(np.mean((np.array(predictions) - np.array(actuals)) ** 2)))

def calculate_rouge(predicted_text: str, actual_text: str) -> dict:
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = scorer.score(actual_text, predicted_text)
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
    # Use absolute paths or relative to workspace root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    samples_path = os.path.join(base_dir, "data", "yelp_samples.json")
    results_path = os.path.join(base_dir, "evaluation", "results.json")
    
    if not os.path.exists(samples_path):
        return {"error": f"Samples not found at {samples_path}"}

    with open(samples_path) as f:
        samples = json.load(f)

    predicted_ratings, actual_ratings = [], []
    rouge_scores = []
    per_sample = []

    print(f"Starting SABI evaluation on {len(samples)} samples...")

    for sample in samples:
        try:
            user_history = UserHistory(**sample["user_history"])
            item = Item(**sample["item"])
            
            result = await simulate_review(user_history, item)
            
            predicted_ratings.append(result.predicted_rating)
            actual_ratings.append(sample["actual_rating"])
            
            rouge = calculate_rouge(result.review_text, sample["actual_review_text"])
            rouge_scores.append(rouge)
            
            per_sample.append({
                "sample_id": sample["sample_id"],
                "user_id": sample["user_id"],
                "actual_rating": sample["actual_rating"],
                "predicted_rating": result.predicted_rating,
                "actual_review": sample["actual_review_text"],
                "predicted_review": result.review_text,
                "rouge": rouge,
                "rmse_contribution": float((sample["actual_rating"] - result.predicted_rating) ** 2)
            })
            print(f"✓ {sample['sample_id']} processed")
            
        except Exception as e:
            print(f"✗ Sample {sample['sample_id']} failed: {e}")
            continue

    if not per_sample:
        return {"error": "No samples were successfully evaluated"}

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

    # Ensure evaluation directory exists
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== SABI EVALUATION RESULTS ===")
    print(f"Samples evaluated: {results['sample_count']}")
    print(f"Task A — RMSE: {results['rmse']:.4f}")
    print(f"Task A — ROUGE-1: {avg_rouge['rouge1']} | ROUGE-2: {avg_rouge['rouge2']} | ROUGE-L: {avg_rouge['rougeL']}")
    print(f"Results saved to {results_path}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_evaluation())
