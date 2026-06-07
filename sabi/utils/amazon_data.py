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

Bug Fixes Applied:
  - _load_amazon_profiles_sync: was grouping by product_category instead of
    reviewer_id. This created buckets with thousands of reviews per category,
    causing context overflow (180k+ tokens) when soul_reader serialised the
    entire history. Fixed: group by reviewer_id as originally intended.
  - Added MAX_HISTORY_ITEMS=15 cap: even with correct grouping a prolific
    reviewer could have 50+ items. We cap at 15 most recent for the soul reader.
  - Added MAX_REVIEW_TEXT_CHARS=300 truncation: long review texts blow up the
    prompt. Truncated to 300 chars which is enough for style detection.
  - fetch_amazon_eval_samples: increased stream_depth to 50000 to find enough
    users with min_reviews=4 now that we group correctly by reviewer_id.

Requires: HUGGINGFACE_TOKEN env var (set in your backend .env)
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
        # Fixed: was "PortHarcourt" — now "Port Harcourt" to match soul_reader output
        "detected_region": "Port Harcourt",
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

# ── Safety caps to prevent context overflow ───────────────────────────────────
# Soul Reader serialises the full user history to JSON and sends it to the LLM.
# Without these caps a prolific reviewer can produce 100k+ token payloads.
MAX_HISTORY_ITEMS    = 15   # max reviewed_items sent to Soul Reader
MAX_REVIEW_TEXT_CHARS = 300  # truncate individual review texts


def _map_category(raw: str) -> str:
    return CATEGORY_MAP.get(raw.lower(), raw.replace("_", " ").title())


def _parse_stars(stars) -> float:
    """Safely convert stars field to float 1.0-5.0."""
    try:
        val = float(stars)
        return max(1.0, min(5.0, val))
    except (TypeError, ValueError):
        return 3.0


def _truncate_review(text: str) -> str:
    """
    Truncates review text to MAX_REVIEW_TEXT_CHARS.
    300 chars is enough for the Soul Reader to detect writing style.
    """
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= MAX_REVIEW_TEXT_CHARS:
        return text
    return text[:MAX_REVIEW_TEXT_CHARS] + "..."


# ── Core sync loader (runs in asyncio.to_thread) ────────────────────────────

def _load_amazon_profiles_sync(
    num_users: int = 25,
    min_reviews: int = 1,
    stream_depth: int = 50000,
    category_filter: Optional[str] = None,
) -> list:
    """
    Streams mteb/amazon_reviews_multi from HuggingFace.
    Groups rows by reviewer_id to build per-user review histories.
    Assigns Nigerian regional personas via rotation.

    BUG FIX: Previously grouped by product_category which created buckets
    with thousands of reviews (e.g. all 'electronics' reviews in one bucket).
    When serialised to JSON for the Soul Reader this exceeded the 128k token
    LLM context limit, causing: 'Please reduce the length of the messages'.
    Now groups correctly by reviewer_id as the docstring always said.

    Args:
        num_users:       How many user profiles to return
        min_reviews:     Minimum reviews per user to qualify
        stream_depth:    How many rows to scan (increased to 50k for reviewer_id grouping)
        category_filter: Optional category e.g. 'video_dvd_film' for movies only

    Returns list of dicts matching SABI UserHistory schema.
    """
    try:
        from datasets import load_dataset

        # Try local file first, fall back to HuggingFace streaming
        local_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "amazon_reviews_processed.jsonl"
        )

        if os.path.exists(local_path):
            print(f"[amazon] Loading local data from {local_path}...")
            ds = load_dataset("json", data_files=local_path, split="train", streaming=True)
        else:
            hf_token = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")
            print(f"[amazon] Streaming mteb/amazon_reviews_multi (depth={stream_depth})...")
            ds = load_dataset(
                "mteb/amazon_reviews_multi",
                "en",
                split="train",
                streaming=True,
                token=hf_token,
            )

        # ── BUG FIX: group by reviewer_id, NOT product_category ──────────────
        # Old code: user_buckets[category].append(...)  ← WRONG — thousands per bucket
        # New code: user_buckets[reviewer_id].append(...) ← CORRECT — one user per bucket
        user_buckets: defaultdict = defaultdict(list)

        for i, record in enumerate(ds):
            if i >= stream_depth:
                break

            product_cat = record.get("product_category", "General")

            if category_filter and category_filter.lower() not in product_cat.lower():
                continue

            review_text = str(record.get("review_body", "") or record.get("text", "")).strip()
            if not review_text:
                continue   # skip blank reviews — Soul Reader needs text

            # BUG FIX: key is now reviewer_id, not category
            reviewer_id = str(record.get("reviewer_id", f"anon_{i}"))
            product_id  = str(record.get("product_id",  f"prod_{i}"))
            stars       = _parse_stars(record.get("stars", record.get("rating", 3)))
            title       = str(record.get("review_title", "")).strip() or f"Review of {product_id[:8]}"
            category    = _map_category(product_cat)

            user_buckets[reviewer_id].append({
                "item_id":      f"amz_{product_id}",
                "title":        title,
                "category":     category,
                "rating_given": stars,
                # BUG FIX: truncate review text to prevent context overflow
                "review_text":  _truncate_review(review_text),
                "date":         "2023-01-01",
            })

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

            # BUG FIX: cap history to MAX_HISTORY_ITEMS most recent reviews
            # A prolific user with 50+ reviews would still overflow the context
            capped_records = records[-MAX_HISTORY_ITEMS:]

            profiles.append({
                "user_id":         f"amz_user_{idx:03d}",
                "name":            name,
                "age":             random.randint(22, 42),
                "location":        region["location"],
                "detected_region": region["detected_region"],
                "dialect_persona": region["dialect_persona"],
                "occupation":      "Professional",
                "reviewed_items":  capped_records,
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
    stream_depth: int = 50000,
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
      - All reviews except the last  →  Soul Reader history  (capped at 14)
      - Last review                  →  ground truth (rating + review_text)

    This is better than MovieLens because ground_truth has REAL review text,
    making ROUGE and BERTScore scores genuinely meaningful.
    """
    profiles = await fetch_amazon_user_profiles(
        num_users=num_users + 15,   # fetch extra — some won't qualify
        min_reviews=4,              # need 3 for history + 1 for eval target
        stream_depth=50000,         # increased from 12000 — needed for reviewer_id grouping
        category_filter=None,       # all categories = cross-domain coverage
    )

    samples = []
    for idx, profile in enumerate(profiles):
        reviewed = profile.get("reviewed_items", [])
        if len(reviewed) < 4:
            continue

        history_items = reviewed[:-1]   # everything except last (already capped at 14)
        eval_item     = reviewed[-1]    # last item = ground truth

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
                # use truncated review as proxy description
                "description":          eval_item["review_text"][:200],
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


# ── Local fallbacks ───────────────────────────────────────────────────────────

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
        print(f"[amazon] Local yelp fallback failed: {e}")
        return []


def load_local_amazon_fallback() -> list:
    """Returns a minimal hardcoded list of samples when all other sources fail."""
    return [
        {
            "sample_id": "fallback_001",
            "user_history": {
                "user_id":        "user_1",
                "name":           "Tunde",
                "age":            28,
                "location":       "Lagos",
                "reviewed_items": [
                    {
                        "item_id":      "nollywood_1432605",
                        "title":        "King of Boys",
                        "category":     "Movie",
                        "rating_given": 4.0,
                        "review_text":  "Very powerful film. The acting was top notch.",
                    }
                ]
            },
            "eval_item": {
                "item_id":              "nollywood_1172009",
                "title":                "The Black Book",
                "category":             "Movie",
                "genre":                ["Movie"],
                "description":          "A Nigerian thriller.",
                "avg_community_rating": 3.3,
                "is_nigerian":          True,
                "is_african":           True,
                "themes":               ["nigerian"],
                "year":                 2023,
            },
            "ground_truth": {
                "rating":      4.0,
                "review_text": "This movie was great and very intense.",
            }
        }
    ]