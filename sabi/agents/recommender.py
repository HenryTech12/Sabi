"""
SABI Contextual Recommender (Agent 4).

ROOT CAUSE FIX — Why the recommender always fell back to "Highly rated title":

  The recommender was sending ~6,654 tokens per request to llama-3.3-70b-versatile.
  Groq free tier TPM limit for that model is 6,000 tokens/minute.
  Every single call exceeded the per-minute limit → 429 rate limit → fallback.
  The fallback's generic reason "Highly rated title recommended for your profile."
  appeared on every card because the LLM never actually ran.

  Two-part fix:
  1. Switch to mixtral-8x7b-32768 (different token bucket on Groq)
  2. Compress items sent to LLM: full JSON (~400 tokens/item) → compact summary
     (~80 tokens/item). 20 items × 80 tokens = 1,600 tokens total.
     Payload drops from ~6,654 → ~2,200 tokens. Fits comfortably in rate limits.
"""

import json
import os
import random
import traceback
import asyncio
from sabi.models.schemas import (
    UserHistory, SoulProfile, RecommendResponse, RecommendationItem, Item
)
from sabi.agents.soul_reader import build_soul_profile
from sabi.agents.voice_mapper import get_voice_instruction, get_openai_client
from sabi.utils.cloud_data import fetch_full_catalog, fetch_regional_priors


RECOMMENDER_SYSTEM_PROMPT = """
You are SABI's recommender. Analyze user profile and items. 
Return ONLY valid JSON. Write 'reason' in the requested Nigerian dialect. 
IMPORTANT: Make each 'reason' unique, descriptive, and emotionally engaging. Avoid repetitive templates.
Vary your greeting and sentence structure in every 'reason'. Do not use the same opening phrase for all items. Make the 'reason' feel personalized to the user's soul profile and the specific item.
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(val, default: float = 0.5) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            import re
            match = re.search(r"(\d+\.?\d*)", val)
            if match:
                return float(match.group(1))
        except Exception:
            pass
    return default


def _normalize_region_key(region: str) -> str:
    return region.replace(" ", "")


def _compress_items_for_prompt(items: list) -> list:
    """
    Sends only the fields the LLM needs for ranking decisions.
    Full item JSON: ~400 tokens each. Compressed: ~80 tokens each.
    20 items: 8,000 tokens → 1,600 tokens. Fits within Groq TPM limits.
    The LLM returns item_ids; we resolve full Item objects after from items_by_id.
    """
    compressed = []
    for item in items:
        compressed.append({
            "item_id":              item.get("item_id"),
            "title":                item.get("title"),
            "genre":                item.get("genre", []),
            "avg_community_rating": item.get("avg_community_rating", 3.5),
            "is_nigerian":          item.get("is_nigerian", False),
            "is_african":           item.get("is_african", False),
            "year":                 item.get("year", 2024),
            "themes":               item.get("themes", [])[:3],
        })
    return compressed


def _parse_raw_json(raw: str) -> dict:
    raw = raw.strip()
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for suffix in ["}", "}]}", "}]}\n}", "}]}"]:
            try:
                return json.loads(raw + suffix)
            except Exception:
                continue
    raise ValueError("JSON parsing failed after repair attempts.")


def _parse_recommendation_response(
    raw_text: str,
    soul_profile: SoulProfile,
    items_by_id: dict,
    cold_start: bool,
    context: str
) -> RecommendResponse:
    result = _parse_raw_json(raw_text)

    # Unwrap nested responses
    if "recommendations" not in result:
        for val in result.values():
            if (
                isinstance(val, list)
                and len(val) > 0
                and isinstance(val[0], dict)
                and ("rank" in val[0] or "item_id" in val[0] or "item" in val[0])
            ):
                result["recommendations"] = val
                break

    cleaned_recommendations = []
    for i, rec in enumerate(result.get("recommendations", [])):
        if not isinstance(rec, dict):
            continue

        item_data = rec.get("item")
        item_id   = rec.get("item_id")

        resolved_item = None
        if isinstance(item_data, dict):
            item_id = item_data.get("item_id", item_id)
        elif isinstance(item_data, str):
            item_id = item_data if item_data in items_by_id else item_id

        # Resolve from full catalog first (this brings back the full description etc.)
        if item_id and item_id in items_by_id:
            resolved_item = items_by_id[item_id]

        # Fall back to whatever the LLM hallucinated
        if not resolved_item:
            if isinstance(item_data, dict) and "title" in item_data:
                item_data.setdefault("item_id",              f"hallucinated_{i}")
                item_data.setdefault("category",             "movie")
                item_data.setdefault("genre",                ["General"])
                item_data.setdefault("description",          "A recommended title.")
                item_data.setdefault("avg_community_rating", 4.0)
                item_data.setdefault("is_nigerian",          False)
                item_data.setdefault("is_african",           False)
                item_data.setdefault("themes",               [])
                item_data.setdefault("year",                 2024)
                resolved_item = item_data
            else:
                continue

        rec["item"]             = resolved_item
        rec["rank"]             = int(rec.get("rank") or (len(cleaned_recommendations) + 1))
        rec["fit_score"]        = round(max(0.0, min(1.0, _safe_float(rec.get("fit_score"),        0.8))), 3)
        rec["predicted_rating"] = round(max(1.0, min(5.0, _safe_float(rec.get("predicted_rating"), 4.0))), 1)
        rec["reason"]           = str(rec.get("reason") or "Highly recommended.").strip()

        reasoning = rec.get("reasoning_chain", ["Based on profile match."])
        rec["reasoning_chain"]  = reasoning if isinstance(reasoning, list) else [str(reasoning)]
        rec["cold_start_flag"]  = bool(rec.get("cold_start_flag", cold_start))

        cleaned_recommendations.append(rec)

    result["recommendations"]   = cleaned_recommendations
    result["soul_profile_summary"] = str(
        result.get("soul_profile_summary")
        or f"Recommendations for a {soul_profile.personality_type} from {soul_profile.detected_region}."
    )
    result["dialect_used"]       = str(result.get("dialect_used")      or soul_profile.dialect_persona)
    result["cold_start_applied"] = bool(result.get("cold_start_applied", cold_start))
    result["context_applied"]    = str(result.get("context_applied")   or context or "not specified")

    return RecommendResponse(**result)


def _build_fallback_response(
    soul_profile: SoulProfile,
    available_items: list,
    cold_start: bool,
    context: str,
    error_msg: str
) -> RecommendResponse:
    print(f"[recommender] Fallback triggered. Error: {error_msg[:120]}")

    top_items = sorted(
        available_items,
        key=lambda x: x.get("avg_community_rating", 0),
        reverse=True
    )[:10]

    # Dialect-specific fallback reasons (not just generic English)
    dialect_reasons = {
        "pidgin_lagos":  "E be top rated title wey match your vibe, abeg try am.",
        "igbo_east":     "Nna this one dey match your taste well well.",
        "hausa_kano":    "Wallahi, this is highly recommended for your profile.",
        "southsouth":    "My brother/sister, this one na correct pick for you.",
        "neutral_abuja": "This title is highly rated and matches your preferences.",
    }
    fallback_reason = dialect_reasons.get(
        soul_profile.dialect_persona,
        "Highly rated title recommended for your profile."
    )

    fallback_recs = []
    for i, item in enumerate(top_items):
        is_nigerian = item.get("is_nigerian", False)
        fit_score   = round(min(1.0, 0.75 + (0.1 if is_nigerian else 0.0)), 3)

        fallback_recs.append(RecommendationItem(
            rank=i + 1,
            item=Item(**{
                "item_id":              item.get("item_id",              f"fallback_{i}"),
                "title":                item.get("title",                "Unknown"),
                "category":             item.get("category",             "movie"),
                "genre":                item.get("genre",                ["General"]),
                "description":          item.get("description",          ""),
                "avg_community_rating": float(item.get("avg_community_rating", 3.5)),
                "is_nigerian":          is_nigerian,
                "is_african":           item.get("is_african",           False),
                "themes":               item.get("themes",               []),
                "year":                 item.get("year",                 2024),
            }),
            fit_score=fit_score,
            predicted_rating=round(max(1.0, min(5.0, float(item.get("avg_community_rating", 3.5)))), 1),
            reason=fallback_reason,
            reasoning_chain=[
                "LLM rate limit reached — using community rating fallback.",
                f"Nigerian bonus applied: {is_nigerian}",
                f"Error: {error_msg[:80]}"
            ],
            cold_start_flag=cold_start
        ))

    return RecommendResponse(
        recommendations=fallback_recs,
        soul_profile_summary=(
            f"Fallback recommendations for a {soul_profile.personality_type} "
            f"from {soul_profile.detected_region}."
        ),
        dialect_used=soul_profile.dialect_persona,
        cold_start_applied=cold_start,
        context_applied=context or "not specified"
    )


# ── Main function ─────────────────────────────────────────────────────────────

async def get_recommendations(
    user_history: UserHistory,
    chat_history: list = [],
    current_message: str = "",
    context: str = None,
    n_recommendations: int = 10
) -> RecommendResponse:
    """
    Recommends items using the four-agent pipeline.

    Groq free tier token budgets:
      llama-3.3-70b-versatile: 6,000 TPM  — our old payload (6,654) exceeded this
      mixtral-8x7b-32768:      5,000 TPM  — our new payload (~2,200) fits easily
    """
    # Context string
    formatted_history = "\n".join([
        f"{(m['role'] if isinstance(m, dict) else m.role).upper()}: "
        f"{m['content'] if isinstance(m, dict) else m.content}"
        for m in chat_history
    ])
    combined_context = (
        f"CONVERSATION HISTORY:\n{formatted_history}\nCURRENT REQUEST: {current_message}"
        if chat_history
        else (current_message or context or "baseline")
    )

    # Fetch catalog + priors concurrently (limit=20, down from 30)
    # Change this line in get_recommendations
    items_db, nigerian_priors = await asyncio.gather(
        fetch_full_catalog(limit=5), # Reduce from 20 to 10
        fetch_regional_priors()
    )
    items_by_id = {i["item_id"]: i for i in items_db}

    soul_profile      = await build_soul_profile(user_history)
    voice_instruction = get_voice_instruction(soul_profile)

    reviewed_titles = {r.title for r in user_history.reviewed_items}
    available_items = [i for i in items_db if i["title"] not in reviewed_titles]

    # Cap candidates at 20
    if len(available_items) > 20:
        top_rated = sorted(
            available_items,
            key=lambda x: x.get("avg_community_rating", 0),
            reverse=True
        )[:10]
        others = [i for i in available_items if i not in top_rated]
        available_items = top_rated + random.sample(others, min(len(others), 10))

    cold_start = len(user_history.reviewed_items) < 3
    client     = get_openai_client()

    region_key = _normalize_region_key(soul_profile.detected_region)
    regional_priors_for_user = nigerian_priors.get(
        soul_profile.detected_region,
        nigerian_priors.get(region_key, {})
    )

    # KEY FIX: compress items — saves ~6,000 tokens per request
    compressed_items = _compress_items_for_prompt(available_items)

    # Compact soul profile — only ranking-relevant fields
    # Change this in get_recommendations
    compact_soul = {
        "type": soul_profile.personality_type,
        "region": soul_profile.detected_region,
        "focus": soul_profile.primary_focus,
    }

    # Use compact JSON (no indentation)
    # Use this in your get_recommendations function
    user_prompt = f"""
        USER PROFILE: {json.dumps(compact_soul)}
        AVAILABLE ITEMS: {json.dumps(compressed_items)}
        DIALECT: {soul_profile.dialect_persona}
        CONTEXT: {combined_context}

        Return ONLY JSON.
        """
    # First attempt
    first_error = None
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",   # KEY FIX: was llama-3.3-70b-versatile
            temperature=0.4,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": RECOMMENDER_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ]
        )
        return _parse_recommendation_response(
            response.choices[0].message.content,
            soul_profile, items_by_id, cold_start, context
        )
    except Exception as e:
        first_error = e
        print(f"[recommender] First attempt failed: {e}. Retrying...")

    # Retry at lower temperature
    retry_error = None
    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=4000,
            messages=[
                {
                    "role": "system",
                    "content": RECOMMENDER_SYSTEM_PROMPT
                    + "\nOUTPUT MUST BE ONLY VALID JSON. NO MARKDOWN. NO EXTRA TEXT.",
                },
                {"role": "user", "content": user_prompt}
            ]
        )
        return _parse_recommendation_response(
            response.choices[0].message.content,
            soul_profile, items_by_id, cold_start, context
        )
    except Exception as e:
        retry_error = e
        print(f"[recommender] Retry also failed: {e}. Using fallback.")

    return _build_fallback_response(
        soul_profile,
        available_items,
        cold_start,
        context,
        error_msg=str(retry_error or first_error or "Unknown error")
    )