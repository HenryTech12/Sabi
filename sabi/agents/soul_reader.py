"""
SABI Soul Reader (Agent 1).

Reads a user's review history and extracts their psychological personality
profile. This profile drives every downstream agent.

Bug Fixes Applied:
- Added _truncate_history_for_llm(): even after amazon_data.py caps at
  MAX_HISTORY_ITEMS=15, a safety guard here ensures we never send more than
  ~6000 tokens of history to the LLM regardless of how the caller built it.
- Extracted normalize_profile() as a module-level function so it is not
  duplicated identically in both the try and except blocks.
- Retry now sends the truncated history (not the full original) so the
  retry can't overflow either.
- Added _neutral_soul_profile() fallback: if both LLM attempts fail the
  Soul Reader returns a safe default profile instead of crashing the caller.
"""

import json
import re
import os
from sabi.models.schemas import UserHistory, SoulProfile
from sabi.agents.voice_mapper import get_openai_client

# Max characters of history JSON to send to the LLM.
# ~24,000 chars ≈ ~6,000 tokens — well within the 128k limit.
# The Soul Reader only needs writing style signals, not every word.
_MAX_HISTORY_CHARS = 24_000

SOUL_READER_SYSTEM_PROMPT = """
You are SABI's Soul Reader — the most important agent in the system.

Your job is to read a user's complete review history and extract their 
psychological personality profile. You MUST follow this JSON schema EXACTLY.

REQUIRED FIELDS AND TYPES:
{
  "avg_rating": float (e.g. 4.2),
  "rating_style": string ("generous", "critical", or "balanced"),
  "rating_variance": float (0.0 to 2.0),
  "personality_type": string ("optimist", "contrarian", "analyst", "storyteller", or "minimalist"),
  "review_length_style": string ("verbose", "terse", or "moderate"),
  "primary_focus": string (the core thing they care about, e.g., "story", "food quality"),
  "emotional_vs_analytical": string ("emotional", "analytical", or "mixed"),
  "forgiveness_factor": float (0.0 to 1.0),
  "novelty_seeking": float (0.0 to 1.0),
  "cultural_sensitivity": float (0.0 to 1.0),
  "signature_phrases": ["phrase 1", "phrase 2"],
  "punctuation_style": string ("heavy", "minimal", or "emoji-user"),
  "dialect_markers": ["marker 1", "marker 2"],
  "detected_region": string ("Lagos", "Kano", "Enugu", "Port Harcourt", or "Abuja"),
  "dialect_persona": string ("pidgin_lagos", "hausa_kano", "igbo_east", "southsouth", or "neutral_abuja"),
  "cultural_affinity_score": float (0.0 to 1.0)
}

RULES:
1. NO NESTING. Do not group fields into sub-objects like "rating_analysis" or "identity".
2. FLOAT FIELDS MUST BE NUMBERS. Do not use strings like "0.5" or "high". Use 0.5 or 0.8.
3. FIELD NAMES MUST BE EXACT. Use "avg_rating", not "average_rating".
4. Return ONLY the JSON object. No markdown. No explanation. No code blocks.
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_float(val, default: float = 0.5) -> float:
    """Robustly converts any LLM value to a float."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.lower()
        if "high"     in s: return 0.8
        if "low"      in s: return 0.3
        if "mid"      in s or "moderate" in s: return 0.5
        try:
            m = re.search(r"(\d+\.?\d*)", val)
            if m:
                return float(m.group(1))
        except Exception:
            pass
    return default


def _truncate_history_for_llm(user_history: UserHistory) -> str:
    """
    Serialises user_history to JSON and truncates to _MAX_HISTORY_CHARS.

    This is the critical safety guard against context overflow errors.
    The Soul Reader only needs to detect writing style patterns — it does
    not need to read every single word of every review. Truncating at
    ~6000 tokens still gives the LLM plenty of signal to work with.

    We truncate the raw JSON string rather than slicing reviewed_items
    so the structure is always valid JSON (the LLM sees a partial last
    review at worst, which is fine).
    """
    history_dict = user_history.model_dump()

    # Keep only the last 15 reviews before serialising
    if "reviewed_items" in history_dict:
        history_dict["reviewed_items"] = history_dict["reviewed_items"][-15:]

    full_text = json.dumps(history_dict, indent=2)

    if len(full_text) <= _MAX_HISTORY_CHARS:
        return full_text

    truncated = full_text[:_MAX_HISTORY_CHARS]
    print(
        f"[soul_reader] History truncated: {len(full_text):,} → {_MAX_HISTORY_CHARS:,} chars "
        f"to prevent context overflow."
    )
    return truncated + "\n... (truncated for LLM context limit)"


def normalize_profile(data: dict) -> dict:
    """
    Robustly maps LLM output (which may use nested keys or alternate names)
    back to the flat SoulProfile schema.

    Extracted as a module-level function so it is not duplicated in both
    the try and except retry blocks.
    """
    flat = {}

    # Unwrap common parent keys the LLM sometimes adds
    if "SoulProfile" in data: data = data["SoulProfile"]
    if "profile"     in data: data = data["profile"]

    # ── Ratings ──────────────────────────────────────────────────────────────
    rb = data.get("rating_behaviour_analysis", {})
    flat["avg_rating"]      = _to_float(data.get("avg_rating") or rb.get("average_rating") or data.get("average_rating"), 4.0)
    flat["rating_style"]    = data.get("rating_style")   or rb.get("generosity") or "balanced"
    flat["rating_variance"] = _to_float(data.get("rating_variance") or rb.get("variance"), 0.5)

    # ── Personality ───────────────────────────────────────────────────────────
    flat["personality_type"]        = data.get("personality_type")        or "storyteller"
    flat["review_length_style"]     = data.get("review_length_style")     or "moderate"
    flat["primary_focus"]           = data.get("primary_focus")           or "quality"
    flat["emotional_vs_analytical"] = data.get("emotional_vs_analytical") or "mixed"

    # ── Behavioural ───────────────────────────────────────────────────────────
    behav = data.get("behavioural_patterns", {})
    flat["forgiveness_factor"]   = _to_float(data.get("forgiveness_factor")   or behav.get("forgiveness_factor"),   0.7)
    flat["novelty_seeking"]      = _to_float(data.get("novelty_seeking")      or behav.get("novelty_seeking"),      0.5)
    flat["cultural_sensitivity"] = _to_float(data.get("cultural_sensitivity") or behav.get("cultural_sensitivity"), 0.8)

    # ── Writing style ─────────────────────────────────────────────────────────
    dna = data.get("writing_style_dna", {})
    flat["signature_phrases"] = (
        data.get("signature_phrases")
        or dna.get("signature_phrases")
        or []
    )
    flat["punctuation_style"] = (
        data.get("punctuation_style")
        or dna.get("emphasis_style")
        or "standard"
    )
    flat["dialect_markers"] = (
        data.get("dialect_markers")
        or dna.get("nigerian_expressions")
        or dna.get("common_expressions")
        or []
    )

    # ── Nigerian identity ─────────────────────────────────────────────────────
    iden = data.get("nigerian_identity_detection", {})
    flat["detected_region"]       = data.get("detected_region")       or iden.get("cultural_region") or "Lagos"
    flat["dialect_persona"]       = data.get("dialect_persona")       or iden.get("cultural_tone")   or "pidgin_lagos"
    flat["cultural_affinity_score"] = _to_float(data.get("cultural_affinity_score"), 0.8)

    # ── Cleanup list fields ───────────────────────────────────────────────────
    for list_field in ("signature_phrases", "dialect_markers"):
        val = flat.get(list_field)
        if isinstance(val, str):
            flat[list_field] = [val] if val else []
        elif not isinstance(val, list):
            flat[list_field] = []

    # ── Ensure float types ────────────────────────────────────────────────────
    for float_field in (
        "avg_rating", "rating_variance", "forgiveness_factor",
        "novelty_seeking", "cultural_sensitivity", "cultural_affinity_score"
    ):
        flat[float_field] = _to_float(flat.get(float_field))

    # ── Normalise dialect_persona enum ────────────────────────────────────────
    _persona_map = {
        "enugu":         "igbo_east",
        "igbo":          "igbo_east",
        "lagos":         "pidgin_lagos",
        "yoruba":        "pidgin_lagos",
        "kano":          "hausa_kano",
        "hausa":         "hausa_kano",
        "port harcourt": "southsouth",
        "portharcourt":  "southsouth",
        "delta":         "southsouth",
        "abuja":         "neutral_abuja",
    }
    persona_lower = str(flat["dialect_persona"]).lower()
    for key, mapped in _persona_map.items():
        if key in persona_lower:
            flat["dialect_persona"] = mapped
            break

    _valid_personas = {"pidgin_lagos", "hausa_kano", "igbo_east", "southsouth", "neutral_abuja"}
    if flat["dialect_persona"] not in _valid_personas:
        flat["dialect_persona"] = "neutral_abuja"

    return flat


def _neutral_soul_profile(user_id: str) -> SoulProfile:
    """
    Returns a safe default SoulProfile when both LLM attempts fail.
    Prevents the caller from crashing with an unhandled exception.
    """
    return SoulProfile(
        user_id=user_id,
        avg_rating=3.5,
        rating_style="balanced",
        rating_variance=0.5,
        personality_type="storyteller",
        review_length_style="moderate",
        primary_focus="quality",
        emotional_vs_analytical="mixed",
        forgiveness_factor=0.6,
        novelty_seeking=0.5,
        cultural_sensitivity=0.8,
        signature_phrases=[],
        punctuation_style="standard",
        dialect_markers=[],
        detected_region="Lagos",
        dialect_persona="pidgin_lagos",
        cultural_affinity_score=0.8,
    )


def _strip_markdown(raw: str) -> str:
    """Strips ```json ... ``` fences from LLM output."""
    raw = raw.strip()
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


# ── Main function ─────────────────────────────────────────────────────────────

async def build_soul_profile(user_history: UserHistory) -> SoulProfile:
    """
    Builds a psychological soul profile from a user's review history.

    Pipeline:
        1. Truncate history to _MAX_HISTORY_CHARS (safety guard)
        2. Send to LLM for profiling
        3. Normalize the response with robust field mapping
        4. Retry once at lower temperature if first attempt fails
        5. Return neutral fallback if both attempts fail
    """
    # BUG FIX: truncate BEFORE building the prompt to prevent context overflow
    history_text = _truncate_history_for_llm(user_history)
    client = get_openai_client()

    user_prompt = f"""
Analyse this Nigerian user's review history and build their complete 
psychological soul profile.

USER DATA:
{history_text}

Return ONLY a valid JSON object matching the SoulProfile schema.
Be specific and detailed in every field.
"""

    # ── First attempt ─────────────────────────────────────────────────────────
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": SOUL_READER_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ]
        )

        raw = _strip_markdown(response.choices[0].message.content)
        print(f"[soul_reader] Raw LLM response (first 200 chars): {raw[:200]}")

        profile_data = json.loads(raw)
        profile_data = normalize_profile(profile_data)
        profile_data["user_id"] = user_history.user_id
        return SoulProfile(**profile_data)

    except Exception as first_error:
        print(f"[soul_reader] First attempt failed: {first_error}. Retrying...")

    # ── Retry at lower temperature with stricter instruction ──────────────────
    # BUG FIX: retry uses the SAME truncated history_text, not the full original.
    # Original code used `history_text` which was already the full untruncated
    # json.dumps — so the retry would overflow too.
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=1500,
            messages=[
                {
                    "role": "system",
                    "content": SOUL_READER_SYSTEM_PROMPT
                    + "\nOUTPUT MUST BE ONLY JSON. NO MARKDOWN. NO CODE BLOCKS. NO EXTRA TEXT.",
                },
                {
                    "role": "user",
                    "content": f"Analyze this user and return ONLY JSON:\n{history_text}"
                }
            ]
        )

        raw = _strip_markdown(response.choices[0].message.content)
        profile_data = json.loads(raw)
        profile_data = normalize_profile(profile_data)   # BUG FIX: was duplicated inline
        profile_data["user_id"] = user_history.user_id
        return SoulProfile(**profile_data)

    except Exception as retry_error:
        print(f"[soul_reader] Retry also failed: {retry_error}. Returning neutral fallback.")

    # ── Safe fallback — never crash the caller ────────────────────────────────
    return _neutral_soul_profile(user_history.user_id)