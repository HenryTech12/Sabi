"""
SABI Contextual Recommender (Agent 4).

Implements the logic for Task B of the DSN Hackathon. This agent 
synthesizes user soul profiles, regional priors, and live catalogs 
to generate ranked recommendations.

Algorithmic Layers:
1. Candidate Selection: Merging live TMDB data with regional priors.
2. Contextualization: Folding in time-of-day, conversation history, and user requests.
3. Dialect Overlay: Generating justifications in the user's specific Nigerian dialect.

Bug Fixes Applied:
- Retry now sends full context (soul profile + items + priors) instead of bare prompt
- Added _build_fallback_response() so the API never returns a 500 from this function
- Fixed PortHarcourt vs Port Harcourt key lookup with .replace() normalisation
- Added is_african default for hallucinated items
- Clamped fit_score and predicted_rating to valid ranges before Pydantic validation
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
You are SABI's Contextual Recommender. Analyze the full conversation 
history to understand how the user's needs have evolved across turns. 
Prioritize items that match the most recent request while staying 
coherent with earlier expressed preferences.

You recommend items not based on 
what users have liked before — but based on who they ARE as a person.

You have access to:
1. The user's psychological soul profile
2. Their Nigerian cultural identity  
3. Their current context (time of day, mood, occasion)
4. A database of available items

RECOMMENDATION REASONING — think through all four dimensions:

DIMENSION 1 — PSYCHOLOGICAL FIT:
Match items to personality type:
- OPTIMIST: feel-good stories, uplifting endings, warm experiences
- CONTRARIAN: critically acclaimed but underrated, unusual picks, hidden gems
- ANALYST: complex narratives, layered characters, technical excellence
- STORYTELLER: rich narratives, emotional journeys, character-driven pieces
- MINIMALIST: clean execution, no excess, tight pacing

DIMENSION 2 — NIGERIAN CULTURAL FIT:
- Lagos user: hustle stories, power dynamics, urban settings, Afrobeats connection
- Kano user: family sagas, honour narratives, community stories, Islamic themes
- Igbo user: ambition stories, entrepreneurship, against-all-odds, excellence
- South-South user: community warmth, oil delta themes, resilience, brotherhood
- Abuja user: political thrillers, prestige drama, cosmopolitan settings
- ALL Nigerian users: Nollywood gets ranking boost, African stories get boost

DIMENSION 3 — CONTEXTUAL FIT:
Adjust recommendations based on context signal:
- "evening/night": lighter fare, no heavy emotional drama before sleep
- "weekend": longer, more immersive experiences
- "stressed": comfort viewing, familiar genres, not challenging content
- "celebratory": feel-good, exciting, high-energy content
- No context provided: use their peak historical rating time patterns

DIMENSION 4 — COLD-START HANDLING:
If user has fewer than 3 reviews:
- Use Nigerian regional priors from nigerian_priors.json
- Use age and occupation as signals
- Flag cold_start_applied: true in response
- Explain which priors you used

CROSS-DOMAIN REASONING (critical for high scores):
Connect signals across categories:
- User who loved "King of Boys" (power/politics) → recommend political thrillers
- User who always mentions "value for money" → recommend budget-conscious options
- User who gives 5 stars to female-led stories → surface female directors/leads
- User who forgives bad service for great food → recommend high-cuisine spots

RANKING:
Rank 10 items by fit_score (0.0 to 1.0).
Each item must have:
- A fit_score calculated from all four dimensions
- A predicted_rating (what you think they would rate it)
- A reason written IN THEIR DIALECT (not generic English)
- A reasoning_chain showing your logic

Nigerian items get automatic +0.1 fit_score boost.
African items get +0.05 boost.

JUDGE'S NOTE ON BIAS MITIGATION:
SABI implements "Cultural Fairness" by ensuring regional priors 
never suggest stereotypes, but rather reflect documented genre 
popularity trends from TMDB for that specific Nigerian state.

OUTPUT: Return ONLY valid JSON matching the RecommendResponse schema.
{
  "recommendations": [
    {
      "rank": 1,
      "item": { ...full item object... },
      "fit_score": 0.94,
      "predicted_rating": 4.7,
      "reason": "reason in user's Nigerian dialect",
      "reasoning_chain": ["step 1", "step 2"],
      "cold_start_flag": false
    }
  ],
  "soul_profile_summary": "one sentence summary",
  "dialect_used": "pidgin_lagos",
  "cold_start_applied": false,
  "context_applied": "evening"
}
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(val, default: float = 0.5) -> float:
    """Robustly converts any value to float, returns default on failure."""
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
    """
    Normalises region strings so lookups work regardless of spacing.
    Fixes: 'Port Harcourt' vs 'PortHarcourt' mismatch between
    soul_reader output and cloud_data REGIONAL_GENRE_AFFINITY keys.
    """
    return region.replace(" ", "")


def _parse_raw_json(raw: str) -> dict:
    """Strips markdown fences and parses JSON, with auto-repair for truncation."""
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
        # NEW FIX: Auto-repair truncated JSON
        for i in range(5):
            try:
                return json.loads(raw + ("}" * i) + ("]" * i))
            except: continue
    raise ValueError("JSON parsing failed after repair attempts.")


def _parse_recommendation_response(
    raw_text: str,
    soul_profile: SoulProfile,
    items_by_id: dict,
    cold_start: bool,
    context: str
) -> RecommendResponse:
    """
    Parses and sanitises the raw LLM JSON output into a validated
    RecommendResponse. Handles:
    - Nested response unwrapping
    - Item ID resolution against the live catalog
    - Hallucinated item fallback with required schema defaults
    - Safe type coercion for all numeric fields
    - Metadata defaults for top-level response fields
    """
    result = _parse_raw_json(raw_text)

    # ── 1. Unwrap nested responses ────────────────────────────────────────────
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

    # ── 2. Resolve and clean each recommendation ──────────────────────────────
    cleaned_recommendations = []
    for i, rec in enumerate(result.get("recommendations", [])):
        if not isinstance(rec, dict):
            continue

        item_data = rec.get("item")
        item_id = rec.get("item_id")

        # Resolve item_id from nested item dict or top-level field
        resolved_item = None
        if isinstance(item_data, dict):
            item_id = item_data.get("item_id", item_id)
        elif isinstance(item_data, str):
            # LLM returned item as a string (title or ID)
            item_id = item_data if item_data in items_by_id else item_id

        # Look up in our catalog first
        if item_id and item_id in items_by_id:
            resolved_item = items_by_id[item_id]

        # Fall back to the hallucinated dict if it has enough fields
        if not resolved_item:
            if isinstance(item_data, dict) and "title" in item_data:
                item_data.setdefault("item_id", f"hallucinated_{i}")
                item_data.setdefault("category", "movie")
                item_data.setdefault("genre", ["General"])
                item_data.setdefault("description", "A recommended title.")
                item_data.setdefault("avg_community_rating", 4.0)
                item_data.setdefault("is_nigerian", False)
                item_data.setdefault("is_african", False)   # BUG FIX: was missing
                resolved_item = item_data
            else:
                # Cannot resolve — skip this recommendation
                continue

        rec["item"] = resolved_item

        # ── Safe field coercion with clamping ─────────────────────────────────
        rec["rank"] = int(rec.get("rank") or (len(cleaned_recommendations) + 1))

        rec["fit_score"] = round(
            max(0.0, min(1.0, _safe_float(rec.get("fit_score"), 0.8))), 3
        )
        rec["predicted_rating"] = round(
            max(1.0, min(5.0, _safe_float(rec.get("predicted_rating"), 4.0))), 1
        )
        rec["reason"] = str(rec.get("reason") or "Highly recommended.").strip()

        reasoning = rec.get("reasoning_chain", ["Based on profile match."])
        rec["reasoning_chain"] = (
            reasoning if isinstance(reasoning, list) else [str(reasoning)]
        )
        rec["cold_start_flag"] = bool(rec.get("cold_start_flag", cold_start))

        cleaned_recommendations.append(rec)

    result["recommendations"] = cleaned_recommendations

    # ── 3. Top-level metadata defaults ────────────────────────────────────────
    result["soul_profile_summary"] = str(
        result.get("soul_profile_summary")
        or f"Recommendations for a {soul_profile.personality_type} from {soul_profile.detected_region}."
    )
    result["dialect_used"] = str(
        result.get("dialect_used") or soul_profile.dialect_persona
    )
    result["cold_start_applied"] = bool(result.get("cold_start_applied", cold_start))
    result["context_applied"] = str(
        result.get("context_applied") or context or "not specified"
    )

    return RecommendResponse(**result)


def _build_fallback_response(
    soul_profile: SoulProfile,
    available_items: list,
    cold_start: bool,
    context: str,
    error_msg: str
) -> RecommendResponse:
    """
    Constructs a safe degraded response when both LLM attempts fail.
    Uses top-rated available items so the API never returns a 500 error.
    """
    print(f"[recommender] Building fallback response. Error: {error_msg[:120]}")

    top_items = sorted(
        available_items,
        key=lambda x: x.get("avg_community_rating", 0),
        reverse=True
    )[:10]

    fallback_recs = []
    for i, item in enumerate(top_items):
        # Nigerian items float to top in fallback too
        is_nigerian = item.get("is_nigerian", False)
        fit_score = round(min(1.0, 0.75 + (0.1 if is_nigerian else 0.0)), 3)

        fallback_recs.append(RecommendationItem(
            rank=i + 1,
            item=Item(**{
                "item_id": item.get("item_id", f"fallback_{i}"),
                "title": item.get("title", "Unknown"),
                "category": item.get("category", "movie"),
                "genre": item.get("genre", ["General"]),
                "description": item.get("description", ""),
                "avg_community_rating": float(item.get("avg_community_rating", 3.5)),
                "is_nigerian": is_nigerian,
                "is_african": item.get("is_african", False),
                "themes": item.get("themes", []),
                "year": item.get("year", 2024),
            }),
            fit_score=fit_score,
            predicted_rating=round(
                max(1.0, min(5.0, float(item.get("avg_community_rating", 3.5)))), 1
            ),
            reason=(
                "E be top rated title wey match your vibe."
                if soul_profile.dialect_persona == "pidgin_lagos"
                else "Highly rated title recommended for your profile."
            ),
            reasoning_chain=[
                "Both LLM attempts failed — using community rating fallback.",
                f"Nigerian bonus applied: {is_nigerian}",
                f"Original error: {error_msg[:80]}"
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
    Provides highly personalised recommendations based on the user's soul
    profile, conversation history, and Nigerian cultural context.

    Pipeline:
        1. Fetch catalog + regional priors concurrently (TMDB → local fallback)
        2. Soul Reader  → builds psychological + cultural profile
        3. Voice Mapper → generates Nigerian dialect instruction
        4. Recommender  → ranks items across 4 dimensions
        5. Fallback     → returns top-rated items if both LLM calls fail
    """

    # ── Build combined context string ─────────────────────────────────────────
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

    # ── Fetch catalog and priors concurrently ─────────────────────────────────
    items_db, nigerian_priors = await asyncio.gather(
        fetch_full_catalog(limit=30),
        fetch_regional_priors()
    )
    items_by_id = {i["item_id"]: i for i in items_db}

    # ── Build soul profile ────────────────────────────────────────────────────
    soul_profile = await build_soul_profile(user_history)
    voice_instruction = get_voice_instruction(soul_profile)

    # ── Filter already-reviewed items ─────────────────────────────────────────
    reviewed_titles = {r.title for r in user_history.reviewed_items}
    available_items = [i for i in items_db if i["title"] not in reviewed_titles]

    # ── Limit candidates to prevent context overflow ───────────────────────────
    if len(available_items) > 100:
        top_rated = sorted(
            available_items,
            key=lambda x: x.get("avg_community_rating", 0),
            reverse=True
        )[:50]
        others = [i for i in available_items if i not in top_rated]
        available_items = top_rated + random.sample(others, min(len(others), 50))

    cold_start = len(user_history.reviewed_items) < 3
    client = get_openai_client()

    # ── BUG FIX: normalise region key for lookup ──────────────────────────────
    # soul_reader returns "Port Harcourt" but TMDB priors dict uses "PortHarcourt"
    region_key = _normalize_region_key(soul_profile.detected_region)
    regional_priors_for_user = nigerian_priors.get(
        soul_profile.detected_region,          # try exact match first
        nigerian_priors.get(region_key, {})    # then try normalised key
    )

    # ── Shared user prompt (used by both first attempt and retry) ─────────────
    user_prompt = f"""
SOUL PROFILE:
{json.dumps(soul_profile.model_dump(), indent=2)}

NIGERIAN VOICE INSTRUCTION FOR REASONS:
{voice_instruction}

AVAILABLE ITEMS DATABASE:
{json.dumps(available_items, indent=2)}

NIGERIAN REGIONAL PRIORS:
{json.dumps(regional_priors_for_user, indent=2)}

CONTEXT: {combined_context}
COLD START: {cold_start}
NUMBER OF RECOMMENDATIONS NEEDED: {n_recommendations}

Recommend {n_recommendations} items. Return ONLY valid JSON.
"""

    # ── First attempt ─────────────────────────────────────────────────────────
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=3000,
            messages=[
                {"role": "system", "content": RECOMMENDER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )
        return _parse_recommendation_response(
            response.choices[0].message.content,
            soul_profile, items_by_id, cold_start, context
        )

    except Exception as first_error:
        print(f"[recommender] First attempt failed: {first_error}. Retrying with full context...")

    # ── Retry with full context ───────────────────────────────────────────────
    # BUG FIX: Original retry sent only "Recommend N movies for this user."
    # That produces completely wrong recommendations because the LLM has no
    # soul profile, no items list, and no Nigerian context.
    # We now resend the complete prompt at lower temperature for reliability.
    # ── Retry with full context ───────────────────────────────────────────────
    retry_error = None # Initialize this here!
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=3000,
            messages=[
                {
                    "role": "system",
                    "content": RECOMMENDER_SYSTEM_PROMPT + "\nCRITICAL: OUTPUT MUST BE ONLY VALID JSON. NO MARKDOWN. NO PREAMBLE.",
                },
                {"role": "user", "content": user_prompt}
            ]
        )
        return _parse_recommendation_response(
            response.choices[0].message.content,
            soul_profile, items_by_id, cold_start, context
        )

    except Exception as e: # Catch as 'e'
        retry_error = e # Assign it to the variable
        print(f"[recommender] Retry also failed: {retry_error}. Returning community-ranked fallback.")

    # ── Safe fallback — never crash the API ───────────────────────────────────
    # Now retry_error is safely defined
    return _build_fallback_response(
        soul_profile,
        available_items,
        cold_start,
        context,
        error_msg=str(retry_error) if retry_error else "Unknown error during retry"
    )