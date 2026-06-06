"""
Cloud Data Service for SABI Backend.

This module provides high-level abstractions for fetching live data from 
external platforms with local JSON fallbacks for resilience.

Technical Design:
- Asynchronous fetching using httpx for TMDB API.
- Streaming datasets using HuggingFace 'datasets' for MovieLens AND Amazon Reviews.
- Thread-safe rotation for regional persona assignments.

Data Sources:
1. TMDB:              Live movies and Nollywood discovery (catalog)
2. Amazon Reviews:    Real written reviews from HuggingFace (primary user profiling)
3. MovieLens 100k:    Rating-only user histories (secondary user profiling)
4. Local Fallbacks:   JSON snapshots in /data directory (always available)

Amazon Reviews Integration:
- Dataset: mteb/amazon_reviews_multi (English, 200k rows)
- Used for: fetch_user_profiles() — builds rich user histories WITH real review text
- Advantage over MovieLens: real written text = meaningful Soul Reader input
- ROUGE/BERTScore evaluation is only meaningful with Amazon data (has text)
- MovieLens kept as secondary fallback (has no written review text)

Bug Fixes Applied (from audit):
- fetch_tmdb_movies:  'release_year' (str) → 'year' (int) to match Item schema
- fetch_nollywood_movies: same 'year' fix + added 'themes' field
- REGIONAL_GENRE_AFFINITY: 'PortHarcourt' → 'Port Harcourt' (space) to match
  soul_reader output and nigerian_priors.json keys
- REGION_ROTATION: 'PortHarcourt' → 'Port Harcourt' for consistency
- _fetch_movielens_user_profiles_sync: added 'title' field to reviewed_items
- _load_fallback_priors: added hard-coded 5-region fallback so recommender
  always has cultural context even if nigerian_priors.json fails
"""

import json
import os
import random
import asyncio
import httpx
from collections import defaultdict
from typing import Optional

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE    = "https://api.themoviedb.org/3"


# ─────────────────────────────────────────
# GENRE MAP (shared by all TMDB fetchers)
# ─────────────────────────────────────────

_GENRE_MAP = {
    28: "action",    12: "adventure", 16: "animation",
    35: "comedy",    80: "crime",     99: "documentary",
    18: "drama",  10751: "family",    14: "fantasy",
    36: "history",   27: "horror",  10402: "music",
  9648: "mystery", 10749: "romance",  878: "sci-fi",
 10770: "tv-movie",  53: "thriller", 10752: "war",
    37: "western"
}

# Amazon product category → SABI category label
_AMAZON_CATEGORY_MAP = {
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


def _map_genre_ids(genre_ids: list) -> list:
    """Maps TMDB numeric genre IDs to readable strings."""
    return [_GENRE_MAP.get(gid, str(gid)) for gid in genre_ids]


def _map_amazon_category(raw: str) -> str:
    """Maps Amazon product_category string to SABI category label."""
    return _AMAZON_CATEGORY_MAP.get(raw.lower(), raw.replace("_", " ").title())


def _safe_year(release_date: str) -> int:
    """
    Extracts a 4-digit year integer from a TMDB release_date string.
    Returns 2024 as default if missing or malformed.
    """
    try:
        return int((release_date or "2024")[:4])
    except (ValueError, TypeError):
        return 2024


def _safe_stars(stars) -> float:
    """Safely converts any value to a float rating in the 1.0–5.0 range."""
    try:
        return max(1.0, min(5.0, float(stars)))
    except (TypeError, ValueError):
        return 3.0


# ─────────────────────────────────────────
# NIGERIAN PERSONA ROTATION (shared)
# ─────────────────────────────────────────
# BUG FIX: 'PortHarcourt' → 'Port Harcourt' to match soul_reader output
# and nigerian_priors.json keys (confirmed with space in data file).

REGION_ROTATION = [
    {
        "detected_region": "Lagos",
        "dialect_persona": "pidgin_lagos",
        "location":        "Lagos",
        "name_pool":       ["Tunde", "Bola", "Seun", "Kemi", "Lara", "Dami", "Tobi"]
    },
    {
        "detected_region": "Kano",
        "dialect_persona": "hausa_kano",
        "location":        "Kano",
        "name_pool":       ["Musa", "Aisha", "Ibrahim", "Fatima", "Sani", "Hauwa", "Yusuf"]
    },
    {
        "detected_region": "Enugu",
        "dialect_persona": "igbo_east",
        "location":        "Enugu",
        "name_pool":       ["Chidi", "Ngozi", "Emeka", "Adaeze", "Obinna", "Chioma", "Nkem"]
    },
    {
        # BUG FIX: was "PortHarcourt" — now "Port Harcourt" for consistency
        "detected_region": "Port Harcourt",
        "dialect_persona": "southsouth",
        "location":        "Port Harcourt",
        "name_pool":       ["Ekene", "Tamara", "Tonye", "Ebere", "Zino", "Preye", "Doubra"]
    },
    {
        "detected_region": "Abuja",
        "dialect_persona": "neutral_abuja",
        "location":        "Abuja",
        "name_pool":       ["David", "Grace", "Victor", "Amaka", "Felix", "Ngozi", "Bello"]
    },
]


# ─────────────────────────────────────────
# ITEMS: Fetch from TMDB, fallback to items.json
# ─────────────────────────────────────────

async def fetch_tmdb_movies(
    page: int = 1,
    genre_id: Optional[int] = None,
    limit: int = 20
) -> list:
    """
    Fetches movie items from TMDB API.
    Maps TMDB fields to SABI Item schema.
    Falls back to data/items.json if TMDB is unavailable or key missing.

    BUG FIX: Returns 'year' (int) not 'release_year' (str) to match Item schema.
    """
    if not TMDB_API_KEY:
        print("[cloud_data] No TMDB_API_KEY. Using local items.json fallback.")
        return _load_fallback_items()

    try:
        params = {
            "api_key":   TMDB_API_KEY,
            "language":  "en-US",
            "page":      page,
            "sort_by":   "popularity.desc"
        }
        if genre_id:
            params["with_genres"] = genre_id

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{TMDB_BASE}/discover/movie", params=params)
            response.raise_for_status()
            data = response.json()

        movies = []
        for m in data.get("results", [])[:limit]:
            movies.append({
                "item_id":              f"tmdb_{m['id']}",
                "title":                m.get("title", "Unknown"),
                "category":             "Movie",
                "genre":                _map_genre_ids(m.get("genre_ids", [])),
                "avg_community_rating": round(m.get("vote_average", 3.0) / 2, 1),
                "description":          m.get("overview", ""),
                "is_nigerian":          False,
                "is_african":           False,
                "themes":               [],
                "year":                 _safe_year(m.get("release_date", "")),  # BUG FIX
                "popularity":           m.get("popularity", 0),
                "source":               "tmdb",
            })

        print(f"[cloud_data] Fetched {len(movies)} movies from TMDB.")
        return movies if movies else _load_fallback_items()

    except Exception as e:
        print(f"[cloud_data] TMDB fetch failed: {e}. Using local fallback.")
        return _load_fallback_items()


async def fetch_nollywood_movies(limit: int = 10) -> list:
    """
    Fetches Nollywood movies from TMDB using Nigerian production region filter.
    Merged into main catalog to boost Nigerian cultural relevance.

    BUG FIX: Returns 'year' (int) + includes 'themes' field for schema compliance.
    """
    if not TMDB_API_KEY:
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{TMDB_BASE}/discover/movie",
                params={
                    "api_key":             TMDB_API_KEY,
                    "with_origin_country": "NG",
                    "language":            "en-US",
                    "page":                1
                }
            )
            response.raise_for_status()
            data = response.json()

        nollywood = []
        for m in data.get("results", [])[:limit]:
            nollywood.append({
                "item_id":              f"nollywood_{m['id']}",
                "title":                m.get("title", "Unknown"),
                "category":             "Nollywood",
                "genre":                ["nigerian", "nollywood"] + _map_genre_ids(m.get("genre_ids", [])),
                "avg_community_rating": round(m.get("vote_average", 3.0) / 2, 1),
                "description":          m.get("overview", ""),
                "is_nigerian":          True,
                "is_african":           True,
                "themes":               ["nigerian", "nollywood"],  # BUG FIX: was missing
                "year":                 _safe_year(m.get("release_date", "")),  # BUG FIX
                "source":               "tmdb_nollywood",
            })

        print(f"[cloud_data] Fetched {len(nollywood)} Nollywood titles.")
        return nollywood

    except Exception as e:
        print(f"[cloud_data] Nollywood fetch failed: {e}")
        return []


async def fetch_full_catalog(limit: int = 30) -> list:
    """
    Master catalog builder. Combines Nollywood + popular TMDB movies.
    Nollywood titles listed first so they appear at top of candidate list
    for the recommender (Nigerian cultural bonus made structurally visible).
    Falls back to items.json if both cloud sources fail.
    """
    popular, nollywood = await asyncio.gather(
        fetch_tmdb_movies(limit=limit),
        fetch_nollywood_movies(limit=10)
    )

    seen = set()
    catalog = []
    for item in nollywood + popular:   # Nollywood first
        if item["item_id"] not in seen:
            seen.add(item["item_id"])
            catalog.append(item)

    if not catalog:
        print("[cloud_data] All cloud sources failed. Using full local fallback.")
        return _load_fallback_items()

    print(
        f"[cloud_data] Final catalog: {len(catalog)} items "
        f"({len(nollywood)} Nollywood + {len(popular)} popular)"
    )
    return catalog


# ─────────────────────────────────────────
# USER PROFILES: Amazon Reviews (PRIMARY) + MovieLens (SECONDARY)
# ─────────────────────────────────────────

def _load_amazon_profiles_sync(
    num_users: int = 25,
    min_reviews: int = 3,
    stream_depth: int = 10000,
    category_filter: Optional[str] = None,
) -> list:
    """
    Streams mteb/amazon_reviews_multi from HuggingFace (English subset).
    Groups rows by reviewer_id to build per-user review histories.
    Assigns Nigerian regional personas via rotation.

    Why Amazon over MovieLens:
    - Has REAL written review text → Soul Reader extracts richer profiles
    - ROUGE/BERTScore evaluation becomes meaningful (text vs text)
    - Cross-domain: books, movies, electronics, grocery, etc.
    - 200k rows → enough users with 3+ reviews

    Args:
        num_users:       Number of user profiles to return
        min_reviews:     Minimum reviews per user to qualify
        stream_depth:    How many rows to scan before stopping
        category_filter: Optional e.g. 'video_dvd_film' for movies only

    Returns list of dicts matching SABI UserHistory schema.
    """
    try:
        from datasets import load_dataset

        hf_token = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")

        print(
            f"[cloud_data] Streaming HenrF/Amazon-Reviews-2023-bucket "
            f"(depth={stream_depth}, users={num_users})..."
        )

        ds = load_dataset(
            "json",
            data_files={"train": "https://huggingface.co/buckets/HenrF/Amazon-Reviews-2023-bucket/raw/review_categories/Appliances.jsonl"},
            split="train",
            streaming=True
        )

        user_buckets: defaultdict = defaultdict(list)

        for i, record in enumerate(ds):
            if i >= stream_depth:
                break

            product_cat = record.get("product_category", "")
            if category_filter and category_filter.lower() not in product_cat.lower():
                continue

            review_text = str(record.get("text", "")).strip()
            if not review_text:
                continue   # skip blank reviews — Soul Reader needs text

            reviewer_id = str(record.get("reviewer_id", f"anon_{i}"))
            product_id  = str(record.get("product_id",  f"prod_{i}"))
            stars       = _safe_stars(record.get("rating", 3))
            title       = str(record.get("review_title", "")).strip() or f"Review of {product_id[:8]}"
            category    = _map_amazon_category(product_cat)

            user_buckets[reviewer_id].append({
                "item_id":      f"amz_{product_id}",
                "title":        title,
                "category":     category,
                "rating_given": stars,
                "review_text":  review_text,
                "date":         "2023-01-01",
            })

        qualified = [
            records for records in user_buckets.values()
            if len(records) >= min_reviews
        ]
        print(f"[cloud_data] Amazon: {len(qualified)} reviewers with {min_reviews}+ reviews.")

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

        print(f"[cloud_data] Amazon: built {len(profiles)} user profiles.")
        return profiles

    except Exception as e:
        print(f"[cloud_data] Amazon stream failed: {e}. Will fall back to MovieLens.")
        return []


def _fetch_movielens_user_profiles_sync(
    num_users: int = 10,
    min_reviews: int = 3,
    stream_depth: int = 3000
) -> list:
    """
    Secondary source: Streams DukeNLPGroup/movielens-100k from HuggingFace.
    Used only when Amazon Reviews streaming fails.
    Note: MovieLens has NO written review text — Soul Reader profiles are weaker.

    BUG FIX: Added 'title' field to reviewed_items so Soul Reader receives
    meaningful item names instead of silent empty strings.
    """
    try:
        from datasets import load_dataset

        print(f"[cloud_data] MovieLens fallback: streaming {num_users} profiles...")

        dataset = load_dataset(
            "DukeNLPGroup/movielens-100k",
            split="train",
            streaming=True
        )

        user_buckets: defaultdict = defaultdict(list)
        for i, record in enumerate(dataset):
            if i >= stream_depth:
                break
            uid      = str(record.get("user_id",     f"u_{i}"))
            movie_id = str(record.get("movie_id",    i))
            title    = str(record.get("title",       f"Movie {movie_id}"))
            rating   = float(record.get("user_rating", 3.0))

            user_buckets[uid].append({
                "movieId": movie_id,
                "title":   title,
                "rating":  rating,
                "userId":  uid,
            })

        qualified = [
            records for records in user_buckets.values()
            if len(records) >= min_reviews
        ]
        print(f"[cloud_data] MovieLens: {len(qualified)} qualified users.")

        profiles = []
        for idx, records in enumerate(qualified[:num_users]):
            region = REGION_ROTATION[idx % len(REGION_ROTATION)]
            name   = region["name_pool"][idx % len(region["name_pool"])]
            records_sorted = sorted(records, key=lambda r: r.get("timestamp", 0))

            reviewed_items = []
            for r in records_sorted:
                reviewed_items.append({
                    "item_id":      f"ml_{r.get('movieId', idx)}",
                    "title":        r.get("title", f"Movie {r.get('movieId', idx)}"),  # BUG FIX
                    "rating_given": float(r.get("rating", 3.0)),
                    "review_text":  "",      # MovieLens has no text
                    "category":     "Movie",
                })

            profiles.append({
                "user_id":         f"ml_user_{records[0].get('userId', idx)}",
                "name":            name,
                "age":             random.randint(22, 42),
                "location":        region["location"],
                "detected_region": region["detected_region"],
                "dialect_persona": region["dialect_persona"],
                "occupation":      "Professional",
                "reviewed_items":  reviewed_items,
            })

        return profiles if profiles else _load_fallback_users()

    except Exception as e:
        print(f"[cloud_data] MovieLens stream failed: {e}. Using local fallback.")
        return _load_fallback_users()


async def fetch_user_profiles(
    num_users: int = 10,
    min_reviews: int = 3,
    stream_depth: int = 10000,
    prefer_amazon: bool = True,
) -> list:
    """
    PRIMARY user profile fetcher used by all agents.

    Waterfall priority:
    1. Amazon Reviews Multi (HuggingFace) — real text, cross-domain, best for Soul Reader
    2. MovieLens 100k     (HuggingFace) — ratings only, no text, weaker profiles
    3. sample_users.json  (local)       — static fallback, always works

    Args:
        num_users:     How many profiles to return
        min_reviews:   Minimum reviews per user
        stream_depth:  Rows to scan from HuggingFace stream
        prefer_amazon: Set False to skip Amazon and go straight to MovieLens
    """
    # ── 1. Try Amazon Reviews (primary) ──────────────────────────────────────
    if prefer_amazon:
        profiles = await asyncio.to_thread(
            _load_amazon_profiles_sync,
            num_users,
            min_reviews,
            stream_depth,
            None,  # no category filter — all domains
        )
        if profiles:
            print(f"[cloud_data] Using Amazon Reviews profiles ({len(profiles)} users).")
            return profiles
        print("[cloud_data] Amazon Reviews unavailable. Trying MovieLens...")

    # ── 2. Try MovieLens (secondary) ─────────────────────────────────────────
    profiles = await asyncio.to_thread(
        _fetch_movielens_user_profiles_sync,
        num_users,
        min_reviews,
        3000,
    )
    if profiles:
        print(f"[cloud_data] Using MovieLens profiles ({len(profiles)} users).")
        return profiles

    # ── 3. Local fallback ─────────────────────────────────────────────────────
    print("[cloud_data] Both HuggingFace sources failed. Using local sample_users.json.")
    return _load_fallback_users()


async def fetch_movielens_user_profiles(
    num_users: int = 10,
    min_reviews: int = 3,
    stream_depth: int = 3000
) -> list:
    """
    Legacy wrapper kept for backward compatibility with existing routes in main.py.
    Internally now calls fetch_user_profiles() which tries Amazon first.
    """
    return await fetch_user_profiles(
        num_users=num_users,
        min_reviews=min_reviews,
        stream_depth=stream_depth,
        prefer_amazon=True,
    )


# ─────────────────────────────────────────
# NIGERIAN PRIORS: TMDB genre trends, fallback to nigerian_priors.json
# ─────────────────────────────────────────

async def fetch_regional_priors() -> dict:
    """
    Builds Nigerian regional priors from TMDB genre popularity data.
    Falls back to nigerian_priors.json if TMDB unavailable.

    BUG FIX: REGIONAL_GENRE_AFFINITY key changed from 'PortHarcourt'
    to 'Port Harcourt' (with space) to match soul_reader output and
    nigerian_priors.json keys (confirmed 'Port Harcourt' in data file).
    """
    if not TMDB_API_KEY:
        return _load_fallback_priors()

    try:
        # BUG FIX: "PortHarcourt" → "Port Harcourt"
        REGIONAL_GENRE_AFFINITY = {
            "Lagos":         [28, 35, 10749],   # Action, Comedy, Romance
            "Kano":          [18, 36, 10751],   # Drama, History, Family
            "Enugu":         [18, 53, 80],      # Drama, Thriller, Crime
            "Port Harcourt": [28, 12, 878],     # Action, Adventure, SciFi
            "Abuja":         [99, 18, 10752],   # Documentary, Drama, War
        }

        priors = {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for region, genre_ids in REGIONAL_GENRE_AFFINITY.items():
                top_items = []
                for gid in genre_ids[:2]:
                    resp = await client.get(
                        f"{TMDB_BASE}/discover/movie",
                        params={
                            "api_key":     TMDB_API_KEY,
                            "with_genres": gid,
                            "sort_by":     "popularity.desc",
                            "page":        1
                        }
                    )
                    if resp.status_code == 200:
                        results = resp.json().get("results", [])[:3]
                        top_items.extend([f"tmdb_{m['id']}" for m in results])

                priors[region] = {
                    "preferred_genres": genre_ids,
                    "top_items":        list(set(top_items)),
                    "source":           "tmdb_live",
                }

        print(f"[cloud_data] Built live regional priors for {len(priors)} regions.")
        return priors if priors else _load_fallback_priors()

    except Exception as e:
        print(f"[cloud_data] Regional priors fetch failed: {e}. Using local fallback.")
        return _load_fallback_priors()


# ─────────────────────────────────────────
# ABSOLUTE DATA PATH RESOLUTION
# ─────────────────────────────────────────

def _get_absolute_data_path(filename: str) -> str:
    """
    Resolves absolute path to data files regardless of working directory.
    Supports SABI_DATA_DIR env override for Docker / Render deployments.
    """
    if os.getenv("SABI_DATA_DIR"):
        return os.path.join(os.getenv("SABI_DATA_DIR"), filename)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", filename)


# ─────────────────────────────────────────
# FALLBACK LOADERS
# ─────────────────────────────────────────

def _load_fallback_items() -> list:
    try:
        with open(_get_absolute_data_path("items.json"), "r", encoding="utf-8") as f:
            items = json.load(f)
        print(f"[cloud_data] Loaded {len(items)} items from local fallback.")
        return items
    except Exception as e:
        print(f"[cloud_data] Local items.json failed: {e}")
        return []


def _load_fallback_users() -> list:
    try:
        with open(_get_absolute_data_path("sample_users.json"), "r", encoding="utf-8") as f:
            users = json.load(f)
        print(f"[cloud_data] Loaded {len(users)} users from local fallback.")
        return users
    except Exception as e:
        print(f"[cloud_data] Local sample_users.json failed: {e}")
        return []


def _load_fallback_priors() -> dict:
    try:
        with open(_get_absolute_data_path("nigerian_priors.json"), "r", encoding="utf-8") as f:
            priors = json.load(f)
        print("[cloud_data] Loaded nigerian_priors from local fallback.")
        return priors
    except Exception as e:
        print(f"[cloud_data] Local nigerian_priors.json failed: {e}")
        # Hard-coded last-resort fallback — recommender always has cultural context
        return {
            "Lagos":         {"top_genres": ["action", "comedy", "romance"],    "themes": ["hustle", "power", "urban"]},
            "Kano":          {"top_genres": ["drama", "history", "family"],     "themes": ["family", "honour", "faith"]},
            "Enugu":         {"top_genres": ["drama", "thriller", "crime"],     "themes": ["ambition", "excellence", "resilience"]},
            "Port Harcourt": {"top_genres": ["action", "adventure", "sci-fi"],  "themes": ["community", "brotherhood", "resilience"]},
            "Abuja":         {"top_genres": ["documentary", "drama", "war"],    "themes": ["power", "politics", "prestige"]},
        }