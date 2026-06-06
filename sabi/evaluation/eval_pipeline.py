"""
SABI Evaluation Pipeline — upgraded to use Amazon Reviews as primary source.

Data source priority:
  1. Amazon Reviews Multi (HuggingFace) — has REAL review text, best for ROUGE/BERTScore
  2. MovieLens (HuggingFace) — ratings only, used if Amazon unavailable
  3. yelp_samples.json (local) — final fallback, 25 Nigerian-specific samples

Metrics computed:
  - RMSE (Task A rating accuracy)
  - ROUGE-1, ROUGE-2, ROUGE-L (Task A review text quality)
  - NDCG@10 (Task B ranking quality) — the 30-point metric
  - BERTScore F1 (Task A behavioural fidelity)
"""

import json
import math
import os
import asyncio
import numpy as np
from rouge_score import rouge_scorer
from sklearn.metrics import mean_squared_error

from sabi.agents.review_simulator import simulate_review
from sabi.agents.recommender import get_recommendations
from sabi.models.schemas import UserHistory, Item, EvaluationResults, EvalSampleResult
from sabi.utils.cloud_data import fetch_movielens_user_profiles, fetch_full_catalog
from sabi.utils.amazon_data import fetch_amazon_eval_samples, load_local_amazon_fallback

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.json")


# ─────────────────────────────────────────
# NDCG@10 helper
# ─────────────────────────────────────────

def compute_ndcg_at_k(recommendations: list, relevant_item_id: str, k: int = 10) -> float:
    """
    Computes NDCG@K for a single recommendation list.
    A hit at rank i scores 1/log2(i+2). IDCG = 1.0 (best possible = hit at rank 1).
    Returns 0.0 if the relevant item is not in the top-k.
    """
    for i, rec in enumerate(recommendations[:k]):
        # rec is a RecommendationItem — item field is an Item object or dict
        item = rec.item if hasattr(rec, "item") else rec.get("item", {})
        item_id = item.item_id if hasattr(item, "item_id") else item.get("item_id", "")
        title = item.title if hasattr(item, "title") else item.get("title", "")

        # Match on item_id OR title (Amazon items won't be in TMDB catalog by id)
        if item_id == relevant_item_id or title == relevant_item_id:
            return 1.0 / math.log2(i + 2)

    return 0.0


# ─────────────────────────────────────────
# SAMPLE BUILDER — Amazon first, then MovieLens fallback
# ─────────────────────────────────────────

async def fetch_evaluation_samples(num_users: int = 25) -> list:
    """
    Tries Amazon Reviews first (real review text = better ROUGE/BERTScore).
    Falls back to MovieLens + TMDB if Amazon is unavailable.
    """
    print("[eval] Trying Amazon Reviews as primary eval source...")
    samples = await fetch_amazon_eval_samples(num_users=num_users)

    if samples:
        print(f"[eval] Using {len(samples)} Amazon Review samples.")
        return samples

    # Fallback 1: MovieLens + TMDB
    print("[eval] Amazon unavailable. Falling back to MovieLens...")
    catalog, user_profiles = await asyncio.gather(
        fetch_full_catalog(limit=50),
        asyncio.to_thread(fetch_movielens_user_profiles, num_users=num_users + 10)
    )
    item_lookup = {item["item_id"]: item for item in catalog}

    samples = []
    for idx, profile in enumerate(user_profiles):
        reviewed = profile.get("reviewed_items", [])
        if len(reviewed) < 3:
            continue

        history_items = reviewed[:-1]
        eval_item_ref = reviewed[-1]
        eval_item_data = item_lookup.get(
            eval_item_ref["item_id"],
            {
                "item_id": eval_item_ref["item_id"],
                "title": f"Movie {eval_item_ref['item_id']}",
                "category": "Movie",
                "genre": ["Movie"],
                "description": "",
                "avg_community_rating": eval_item_ref.get("rating", 3.0),
                "is_nigerian": False,
                "is_african": False,
                "themes": [],
                "year": 2023,
            }
        )

        samples.append({
            "sample_id": f"ml_{idx:03d}",
            "user_history": {
                **{k: v for k, v in profile.items() if k != "reviewed_items"},
                "reviewed_items": history_items,
            },
            "eval_item": eval_item_data,
            "ground_truth": {
                "rating": eval_item_ref.get("rating", eval_item_ref.get("rating_given", 3.0)),
                "review_text": eval_item_data.get("description", ""),
            }
        })

    if samples:
        print(f"[eval] Using {len(samples)} MovieLens samples.")
        return samples[:num_users]

    # Fallback 2: local yelp_samples.json
    print("[eval] MovieLens unavailable. Using local yelp fallback...")
    return load_local_amazon_fallback()


# ─────────────────────────────────────────
# MAIN EVALUATION RUNNER
# ─────────────────────────────────────────

async def run_evaluation(num_users: int = 25):
    samples = await fetch_evaluation_samples(num_users=num_users)

    if not samples:
        return {"error": "No evaluation samples available from any source."}

    per_sample_results = []
    actual_ratings, predicted_ratings = [], []
    rouge_scores = {"rouge1": [], "rouge2": [], "rougeL": []}
    bert_scores = []
    ndcg_scores = []

    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)

    # Try importing BERTScore (optional — graceful degradation if not installed)
    bert_available = False
    try:
        from bert_score import score as bert_score_fn
        bert_available = True
        print("[eval] BERTScore available.")
    except ImportError:
        print("[eval] BERTScore not installed. Skipping. Run: pip install bert-score")

    for sample in samples:
        try:
            # ── Build UserHistory ──────────────────────────────────────────
            user_history_data = sample["user_history"]

            # Ensure name and age have defaults (MovieLens profiles may lack them)
            user_history_data.setdefault("name", f"User {user_history_data.get('user_id', 'unknown')}")
            user_history_data.setdefault("age", 25)
            user_history_data.setdefault("location", user_history_data.get("detected_region", "Lagos"))
            user_history_data.setdefault("occupation", "Professional")

            # Normalise reviewed_items: accept both 'rating' and 'rating_given'
            for ri in user_history_data.get("reviewed_items", []):
                ri.setdefault("title", "Unknown")
                ri.setdefault("category", "Movie")
                ri.setdefault("review_text", "")
                ri.setdefault("date", "2023-01-01")
                if "rating" in ri and "rating_given" not in ri:
                    ri["rating_given"] = ri["rating"]
                ri.setdefault("rating_given", 3.0)

            user_history = UserHistory(**user_history_data)

            # ── Build Item ─────────────────────────────────────────────────
            eval_item_data = sample["eval_item"]
            item = Item(
                item_id=eval_item_data.get("item_id", "unknown"),
                title=eval_item_data.get("title", eval_item_data.get("name", "Untitled")),
                category=eval_item_data.get("category", "Movie"),
                genre=eval_item_data.get("genre", eval_item_data.get("tags", ["General"])),
                description=eval_item_data.get("description", ""),
                avg_community_rating=float(eval_item_data.get("avg_community_rating",
                                           eval_item_data.get("average_rating", 4.0))),
                is_nigerian=eval_item_data.get("is_nigerian", False),
                is_african=eval_item_data.get("is_african", False),
                themes=eval_item_data.get("themes", []),
                year=int(eval_item_data.get("year", eval_item_data.get("release_year", 2023))),
            )

            # ── Task A: Simulate Review ────────────────────────────────────
            prediction = await simulate_review(user_history, item)

            actual_rating = float(sample["ground_truth"]["rating"])
            predicted_rating = prediction.predicted_rating
            actual_review = sample["ground_truth"].get("review_text") or "No ground truth."
            predicted_review = prediction.review_text

            actual_ratings.append(actual_rating)
            predicted_ratings.append(predicted_rating)

            # ROUGE
            rouge = scorer.score(actual_review, predicted_review)
            rouge_scores["rouge1"].append(rouge["rouge1"].fmeasure)
            rouge_scores["rouge2"].append(rouge["rouge2"].fmeasure)
            rouge_scores["rougeL"].append(rouge["rougeL"].fmeasure)

            # BERTScore
            bert_f1 = None
            if bert_available and actual_review.strip():
                try:
                    _, _, F1 = bert_score_fn(
                        [predicted_review], [actual_review],
                        lang="en",
                        model_type="distilbert-base-uncased",
                        verbose=False
                    )
                    bert_f1 = float(F1[0])
                    bert_scores.append(bert_f1)
                except Exception as be:
                    print(f"[eval] BERTScore error: {be}")

            # ── Task B: NDCG@10 ───────────────────────────────────────────
            ndcg = 0.0
            try:
                recs = await get_recommendations(user_history, n_recommendations=10)
                # Use item title as match key (Amazon items won't be in TMDB by id)
                ndcg = compute_ndcg_at_k(
                    recs.recommendations,
                    relevant_item_id=item.item_id,
                    k=10
                )
                # If no id match, try title match
                if ndcg == 0.0:
                    ndcg = compute_ndcg_at_k(
                        recs.recommendations,
                        relevant_item_id=item.title,
                        k=10
                    )
                ndcg_scores.append(ndcg)
            except Exception as ne:
                print(f"[eval] NDCG computation error: {ne}")
                ndcg_scores.append(0.0)

            per_sample_results.append(EvalSampleResult(
                user_id=user_history.user_id,
                sample_id=sample.get("sample_id", user_history.user_id),
                actual_rating=actual_rating,
                predicted_rating=predicted_rating,
                actual_review=actual_review,
                predicted_review=predicted_review,
                rmse_contribution=float((actual_rating - predicted_rating) ** 2),
            ))

        except Exception as e:
            import traceback
            print(f"[eval] Error on sample {sample.get('sample_id', '?')}: {e}")
            traceback.print_exc()
            continue

    if not actual_ratings:
        return {"error": "No samples were successfully evaluated."}

    rmse = float(np.sqrt(mean_squared_error(actual_ratings, predicted_ratings)))
    avg_ndcg = float(np.mean(ndcg_scores)) if ndcg_scores else 0.0
    avg_bert = float(np.mean(bert_scores)) if bert_scores else None

    results = EvaluationResults(
        rmse=rmse,
        rouge_1=float(np.mean(rouge_scores["rouge1"])),
        rouge_2=float(np.mean(rouge_scores["rouge2"])),
        rouge_l=float(np.mean(rouge_scores["rougeL"])),
        sample_count=len(per_sample_results),
        per_sample_results=per_sample_results,
    )

    # Build full results dict with all metrics
    results_dict = results.model_dump()
    results_dict["ndcg_10"] = round(avg_ndcg, 4)
    if avg_bert is not None:
        results_dict["bert_score"] = round(avg_bert, 4)

    print(f"\n[eval] ══════════════════════════════════════")
    print(f"[eval] RMSE:       {rmse:.4f}")
    print(f"[eval] ROUGE-1:    {results_dict['rouge_1']:.4f}")
    print(f"[eval] ROUGE-L:    {results_dict['rouge_l']:.4f}")
    print(f"[eval] NDCG@10:    {avg_ndcg:.4f}")
    if avg_bert:
        print(f"[eval] BERTScore:  {avg_bert:.4f}")
    print(f"[eval] Samples:    {len(per_sample_results)}")
    print(f"[eval] ══════════════════════════════════════\n")

    with open(RESULTS_PATH, "w") as f:
        json.dump(results_dict, f, indent=2)

    return results_dict


def get_latest_results():
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH) as f:
            return json.load(f)
    return None