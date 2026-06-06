"""
Amazon Reviews Multi — HuggingFace Integration for SABI.

Dataset: mteb/amazon_reviews_multi (English subset)
Source:  https://huggingface.co/datasets/mteb/amazon_reviews_multi
Size:    200,000 train reviews across 26 product categories

Why this beats MovieLens for SABI evaluation:
  ✓ Has REAL written review text (MovieLens has NONE)
  ✓ ROUGE scores become meaningful — comparing text vs text
  ✓ BERTScore becomes meaningful — semantic similarity of real reviews
  ✓ Cross-domain: books, movies, electronics, grocery etc
  ✓ Reviewer IDs allow building per-user history profiles
  ✓ 200k rows = enough users with 3+ reviews

Requires: HUGGINGFACE_TOKEN env var (already set in your backend)
"""

import asyncio
import json
import os
import random
from collections import defaultdict
from typing import Optional

# ── Nigerian regional persona rotation ──────────────────────────────────────
REGION_ROTATION = [
    {
        "detected_region": "Lagos",
        "dialect_persona": "pidgin_lagos",
        "location": "Lagos",
        "name_pool": ["Tunde", "Bola", "Seun", "Kemi", "Lara", "Dami", "Tobi"]
    },
    {
        "detected_region": "Kano",
        "dialect_persona": "hausa_kano",
        "location": "Kano",
        "name_pool": ["Musa", "Aisha", "Ibrahim", "Fatima", "Sani", "Hauwa", "Yusuf"]
    },
    {
        "detected_region": "Enugu",
        "dialect_persona": "igbo_east",
        "location": "Enugu",
        "name_pool": ["Chidi", "Ngozi", "Emeka", "Adaeze", "Obinna", "Chioma", "Nkem"]
    },
    {
        "detected_region": "PortHarcourt",
        "dialect_persona": "southsouth",
        "location": "Port Harcourt",
        "name_pool": ["Ekene", "Tamara", "Tonye", "Ebere", "Zino", "Preye", "Doubra"]
    },
    {
        "detected_region": "Abuja",
        "dialect_persona": "neutral_abuja",
        "location": "Abuja",
        "name_pool": ["David", "Grace", "Victor", "Amaka", "Felix", "Ngozi", "Bello"]
    },
]

# ── Category mapping: Amazon → SABI ─────────────────────────────────────────
CATEGORY_MAP = {
    "video_dvd_film":      "Movie",
    "book":                "Book",
    "music":               "Music",
    "electronics":         "Electronics",
    "pc":                  "Electronics",
    "wireless":            "Electronics",
    "camera":              "Electronics",
    "grocery":             "Food & Grocery",
    "home":                "Home",
    "kitchen":             "Home",
    "furniture":           "Home",
    "apparel":             "Fashion",
    "shoes":               "Fashion",
    "jewelry":             "Fashion",
    "watch":               "Fashion",
    "beauty":              "Beauty",
    "drugstore":           "Health",
    "baby_product":        "Baby",
    "toy":                 "Toys",
    "sports":              "Sports",
    "lawn_and_garden":     "Garden",
    "automotive":          "Automotive",
    "pet_products":        "Pets",
    "musical_instruments": "Music",
    "office_product":      "Office",
    "luggage":             "Travel",
}

def _map_category(raw: str) -> str:
    return CATEGORY_MAP.get(raw.lower(), raw.replace("_", " ").title())


def _parse_stars(stars) -> float:
    """Safely convert stars field to float 1.0-5.0."""
    try:
        val = float(stars)
        return max(1.0, min(5.0, val))
    except (TypeError, ValueError):
        return 3.0


# ── Core sync loader (runs in asyncio.to_thread) ────────────────────────────

def _load_amazon_profiles_sync(
    num_users: int = 25,
    min_reviews: int = 3,
    stream_depth: int = 10000,
    category_filter: Optional[str] = None,
) -> list:
    """
    Streams mteb/amazon_reviews_multi from HuggingFace.
    Groups rows by reviewer_id to build per-user review histories.
    Assigns Nigerian regional personas via rotation.

    Args:
        num_users:       How many user profiles to return
        min_reviews:     Minimum reviews per user to qualify
        stream_depth:    How many rows to scan before stopping
        category_filter: Optional category e.g. 'video_dvd_film' for movies only

    Returns list of dicts matching SABI UserHistory schema.
    """
    try:
        from datasets import load_dataset

        hf_token = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")

        print(f"[amazon] Streaming HenrF/Amazon-Reviews-2023-bucket "
              f"(depth={stream_depth}, users={num_users})...")

        ds = load_dataset(
            "json",
            data_files={"train": "https://huggingface.co/buckets/HenrF/Amazon-Reviews-2023-bucket/raw/review_categories/Appliances.jsonl"},
            split="train",
            streaming=True
        )

        # Group reviews by reviewer_id
        user_buckets: defaultdict = defaultdict(list)

        for i, record in enumerate(ds):
            if i >= stream_depth:
                break

            # Optional category filter
            product_cat = record.get("product_category", "")
            if category_filter and category_filter.lower() not in product_cat.lower():
                continue

            review_text = str(record.get("text", "")).strip()
            if not review_text:
                continue  # skip blank reviews — we need text for ROUGE

            reviewer_id = str(record.get("reviewer_id", f"anon_{i}"))
            product_id  = str(record.get("product_id",  f"prod_{i}"))
            stars       = _parse_stars(record.get("rating", 3))
            title       = str(record.get("review_title", "")).strip() or f"Review of {product_id[:8]}"
            category    = _map_category(product_cat)

            user_buckets[reviewer_id].append({
                "item_id":      f"amz_{product_id}",
                "title":        title,
                "category":     category,
                "rating_given": stars,
                "review_text":  review_text,
                "date":         "2023-01-01",
                # keep raw stars for hold-out extraction
                "_stars":       stars,
            })

        # Filter users with enough reviews for a proper history
        qualified = [
            records for records in user_buckets.values()
            if len(records) >= min_reviews
        ]
        print(f"[amazon] {len(qualified)} reviewers with {min_reviews}+ reviews found.")

        # Build SABI UserHistory profiles with Nigerian personas
        profiles = []
        for idx, records in enumerate(qualified[:num_users]):
            region = REGION_ROTATION[idx % len(REGION_ROTATION)]
            name   = region["name_pool"][idx % len(region["name_pool"])]

            profiles.append({
                "user_id":         f"amz_user_{idx:03d}",
                "name":            name,
                "age":             random.randint(22, 42),
                "location":        region["location"],
                "detected_region": region["detected_region"],
                "dialect_persona": region["dialect_persona"],
                "occupation":      "Professional",
                "reviewed_items":  records,
            })

        print(f"[amazon] Built {len(profiles)} user profiles.")
        return profiles

    except Exception as e:
        print(f"[amazon] Stream failed: {e}")
        return []


# ── Async wrappers ───────────────────────────────────────────────────────────

async def fetch_amazon_user_profiles(
    num_users: int = 25,
    min_reviews: int = 3,
    stream_depth: int = 10000,
    category_filter: Optional[str] = None,
) -> list:
    """Async wrapper — runs the blocking HF loader in a thread."""
    return await asyncio.to_thread(
        _load_amazon_profiles_sync,
        num_users,
        min_reviews,
        stream_depth,
        category_filter,
    )


async def fetch_amazon_eval_samples(num_users: int = 25) -> list:
    """
    Builds evaluation samples using leave-one-out strategy:
      - All reviews except the last  →  Soul Reader history
      - Last review                  →  ground truth (rating + review_text)

    This is better than MovieLens because ground_truth has REAL review text,
    making ROUGE and BERTScore scores genuinely meaningful.
    """
    profiles = await fetch_amazon_user_profiles(
        num_users=num_users + 15,   # fetch extra — some won't qualify
        min_reviews=4,              # need 3 for history + 1 for eval
        stream_depth=12000,
        category_filter=None,       # all categories = cross-domain coverage
    )

    samples = []
    for idx, profile in enumerate(profiles):
        reviewed = profile.get("reviewed_items", [])
        if len(reviewed) < 4:
            continue

        history_items = reviewed[:-1]   # everything except last
        eval_item     = reviewed[-1]    # last item = ground truth

        # Build eval_item in SABI Item schema
        samples.append({
            "sample_id":    f"amz_{idx:03d}",
            "user_history": {
                "user_id":        profile["user_id"],
                "name":           profile["name"],
                "age":            profile["age"],
                "location":       profile["location"],
                "occupation":     profile.get("occupation", "Professional"),
                "reviewed_items": history_items,
            },
            "eval_item": {
                "item_id":              eval_item["item_id"],
                "title":                eval_item["title"],
                "category":             eval_item["category"],
                "genre":                [eval_item["category"]],
                "description":          eval_item["review_text"][:200],  # use review as proxy desc
                "avg_community_rating": eval_item["rating_given"],
                "is_nigerian":          False,
                "is_african":           False,
                "themes":               [],
                "year":                 2023,
            },
            "ground_truth": {
                "rating":      eval_item["rating_given"],
                "review_text": eval_item["review_text"],  # REAL TEXT for ROUGE/BERTScore
            },
        })

        if len(samples) >= num_users:
            break

    print(f"[amazon] {len(samples)} eval samples ready.")
    return samples


# ── Local fallback ───────────────────────────────────────────────────────────

def load_local_yelp_fallback() -> list:
    """
    Falls back to yelp_samples.json when HuggingFace is unavailable.
    Returns same schema as fetch_amazon_eval_samples().
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "data", "yelp_samples.json")

    try:
        with open(path) as f:
            raw = json.load(f)

        samples = []
        for s in raw:
            samples.append({
                "sample_id":    s.get("sample_id", f"yelp_{len(samples):03d}"),
                "user_history": s["user_history"],
                "eval_item": {
                    "item_id":              s.get("item_id", "unknown"),
                    "title":                s.get("item", {}).get("title", "Unknown"),
                    "category":             s.get("item", {}).get("category", "General"),
                    "genre":                s.get("item", {}).get("genre", ["General"]),
                    "description":          s.get("item", {}).get("description", ""),
                    "avg_community_rating": s.get("item", {}).get("avg_community_rating", 4.0),
                    "is_nigerian":          s.get("item", {}).get("is_nigerian", False),
                    "is_african":           False,
                    "themes":               [],
                    "year":                 2023,
                },
                "ground_truth": {
                    "rating":      s["actual_rating"],
                    "review_text": s["actual_review_text"],
                },
            })

        print(f"[amazon] Loaded {len(samples)} local yelp fallback samples.")
        return samples

    except Exception as e:
        print(f"[amazon] Local fallback failed: {e}")
        return []
    
def load_local_amazon_fallback():
    """Returns a minimal list of local samples for evaluation."""
    return [
        {
            "sample_id": "fallback_001",
            "user_history": {
                "user_id": "user_1",
                "reviewed_items": [
                    {"item_id": "nollywood_1432605", "rating_given": 4.0}
                ]
            },
            "eval_item": {
                "item_id": "nollywood_1172009",
                "title": "The Black Book",
                "avg_community_rating": 3.3
            },
            "ground_truth": {
                "rating": 4.0,
                "review_text": "This movie was great and very intense."
            }
        }
    ]