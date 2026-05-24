import json
import os
import time
import asyncio
from rouge_score import rouge_scorer
from sklearn.metrics import mean_squared_error
import numpy as np
from sabi.agents.review_simulator import simulate_review
from sabi.models.schemas import UserHistory, Item, EvaluationResults, EvalSampleResult

EVAL_SAMPLES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "yelp_samples.json")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.json")

async def run_evaluation():
    if not os.path.exists(EVAL_SAMPLES_PATH):
        return {"error": "Evaluation samples not found"}

    with open(EVAL_SAMPLES_PATH, "r") as f:
        samples = json.load(f)

    per_sample_results = []
    actual_ratings = []
    predicted_ratings = []
    
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    rouge_scores = {'rouge1': [], 'rouge2': [], 'rougeL': []}

    for sample in samples:
        user_history = UserHistory(**sample["user_history"])
        
        # We need an Item object for simulate_review
        # We'll construct a dummy item based on the item_id
        item = Item(
            item_id=sample["item_id"],
            title="Sample Item",
            category="general",
            genre=["general"],
            description="Sample item for evaluation",
            avg_community_rating=4.0,
            is_nigerian=True,
            is_african=True,
            themes=[],
            year=2024
        )
        
        try:
            prediction = await simulate_review(user_history, item)
            
            actual_rating = sample["actual_rating"]
            predicted_rating = prediction.predicted_rating
            actual_review = sample["actual_review_text"]
            predicted_review = prediction.review_text
            
            # RMSE metrics
            actual_ratings.append(actual_rating)
            predicted_ratings.append(predicted_rating)
            
            # ROUGE metrics
            scores = scorer.score(actual_review, predicted_review)
            rouge_scores['rouge1'].append(scores['rouge1'].fmeasure)
            rouge_scores['rouge2'].append(scores['rouge2'].fmeasure)
            rouge_scores['rougeL'].append(scores['rougeL'].fmeasure)
            
            per_sample_results.append(EvalSampleResult(
                user_id=sample["user_id"],
                actual_rating=actual_rating,
                predicted_rating=predicted_rating,
                actual_review=actual_review,
                predicted_review=predicted_review,
                rmse_contribution=float((actual_rating - predicted_rating)**2)
            ))
        except Exception as e:
            print(f"Error evaluating sample {sample['user_id']}: {e}")
            continue

    if not actual_ratings:
        return {"error": "No samples were successfully evaluated"}

    rmse = float(np.sqrt(mean_squared_error(actual_ratings, predicted_ratings)))
    
    results = EvaluationResults(
        rmse=rmse,
        rouge_1=float(np.mean(rouge_scores['rouge1'])),
        rouge_2=float(np.mean(rouge_scores['rouge2'])),
        rouge_l=float(np.mean(rouge_scores['rougeL'])),
        sample_count=len(per_sample_results),
        per_sample_results=per_sample_results
    )

    with open(RESULTS_PATH, "w") as f:
        f.write(results.model_dump_json(indent=2))

    return results.model_dump()

def get_latest_results():
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, "r") as f:
            return json.load(f)
    return None
