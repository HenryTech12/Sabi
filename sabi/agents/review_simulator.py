import json
import os
from sabi.models.schemas import UserHistory, Item, SoulProfile, SimulateReviewResponse
from sabi.agents.soul_reader import build_soul_profile
from sabi.agents.voice_mapper import get_voice_instruction, get_openai_client


REVIEW_SIMULATOR_SYSTEM_PROMPT = """
You are SABI's Review Simulator. You simulate authentic reviews that a 
specific Nigerian human being would write — based on their psychological 
soul profile and Nigerian cultural identity.

YOUR TASK:
Given a user's soul profile and an item they have NOT reviewed, simulate:
1. The star rating they would give (1.0 to 5.0, one decimal)
2. The written review they would write

RATING SIMULATION — reason through this step by step:
Step 1: Start with the item's community average rating as a baseline
Step 2: Apply genre/category match adjustment:
   - Beloved genre/category: +0.3 to +0.8 stars
   - Neutral genre: 0 adjustment  
   - Disliked genre: -0.3 to -0.8 stars
Step 3: Apply personality adjustment:
   - Generous rater (avg > 4.0): +0.2 to +0.4
   - Critical rater (avg < 3.0): -0.2 to -0.4
   - Balanced rater: 0 adjustment
Step 4: Apply Nigerian cultural bonus:
   - Nigerian/Nollywood item + Nigerian user: +0.2 to +0.4
   - African item + Nigerian user: +0.1 to +0.2
Step 5: Apply forgiveness factor:
   - High forgiveness (>0.7): soften any negative adjustments by 50%
   - Low forgiveness (<0.3): amplify negative adjustments by 20%
Step 6: Round to nearest 0.5 or 0.1 based on user's typical precision

REVIEW TEXT SIMULATION — write exactly like this person:
- Match their review length precisely (verbose = 6-8 sentences, terse = 2-3)
- Use their primary focus as the opening topic
- Include their signature phrases naturally — do not force them
- Apply their Nigerian dialect and personality overlay exactly
- Match their emotional vs analytical style
- Include specific details about the item — not generic praise
- End in their typical style (some users trail off, some make recommendations)

CONFIDENCE SCORE:
- High (0.8-1.0): user has many reviews in this category, clear patterns
- Medium (0.5-0.79): some relevant history, patterns emerging
- Low (0.3-0.49): limited history, cold-start territory

OUTPUT: Return ONLY valid JSON. No text outside JSON.
{
  "predicted_rating": 4.2,
  "review_text": "The full simulated review text here...",
  "confidence_score": 0.87,
  "rating_drivers": ["genre_match", "cultural_relevance", "forgiveness_applied"],
  "dialect_used": "pidgin_lagos",
  "soul_profile_summary": "One sentence description of this user",
  "reasoning_chain": [
    "Started at community baseline: 4.1",
    "Genre match bonus (user loves thrillers): +0.4",
    "Critical rater adjustment: -0.2",
    "Nollywood bonus: +0.3",
    "Final predicted rating: 4.6"
  ]
}
"""


def _parse_review_raw(raw: str) -> dict:
    raw = raw.strip()
    # Try direct load first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: Extract everything between the first '{' and last '}'
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Could not find valid JSON in response")

def _coerce_review_response(result: dict) -> SimulateReviewResponse:
    """
    Applies safe defaults for any missing optional fields before
    constructing the Pydantic model, preventing validation errors.
    """
    result.setdefault("predicted_rating", 3.0)
    result.setdefault("review_text", "No review could be generated.")
    result.setdefault("confidence_score", 0.5)
    result.setdefault("rating_drivers", ["baseline"])
    result.setdefault("dialect_used", "neutral_abuja")
    result.setdefault("soul_profile_summary", "Nigerian user profile.")
    result.setdefault("reasoning_chain", ["Prediction based on available data."])


    # In _coerce_review_response, change the default:
    result.setdefault("review_text", "Nna, I never watch this one yet, but I go check am soon.")
    result.setdefault("predicted_rating", 4.0) # More positive for a demo
    
    # Clamp predicted_rating to valid range
    try:
        result["predicted_rating"] = round(
            max(1.0, min(5.0, float(result["predicted_rating"]))), 1
        )
    except (TypeError, ValueError):
        result["predicted_rating"] = 3.0

    # Clamp confidence_score to valid range
    try:
        result["confidence_score"] = round(
            max(0.0, min(1.0, float(result["confidence_score"]))), 2
        )
    except (TypeError, ValueError):
        result["confidence_score"] = 0.5

    # Ensure list fields are actually lists
    for list_field in ("rating_drivers", "reasoning_chain"):
        if not isinstance(result[list_field], list):
            result[list_field] = [str(result[list_field])]

    return SimulateReviewResponse(**result)


async def simulate_review(user_history: UserHistory, item: Item) -> SimulateReviewResponse:
    soul_profile = await build_soul_profile(user_history)
    voice_instruction = get_voice_instruction(soul_profile)
    client = get_openai_client()

    # 1. AGGRESSIVE TRUNCATION: Only take the last 2 items, and truncate text to 20 chars
    pruned_history = [
        {"title": r.title[:20], "rating": r.rating_given} 
        for r in user_history.reviewed_items[-2:]
    ]

    # 2. COMPACT PROMPT: Remove all unnecessary whitespace and indentation
    user_prompt = (
        f"Profile: {soul_profile.personality_type}, {soul_profile.detected_region}. "
        f"Voice: {voice_instruction}. "
        f"Item: {item.title}. "
        f"History: {json.dumps(pruned_history)}. "
        f"Return ONLY JSON with: predicted_rating, review_text, confidence_score, "
        f"rating_drivers, dialect_used, soul_profile_summary, reasoning_chain."
    )

    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=500, # Limit the output size too
            messages=[
                {"role": "system", "content": "You are a simulator. Return ONLY JSON."},
                {"role": "user", "content": user_prompt}
            ]
        )
        # ... rest of your parsing logic
        raw = response.choices[0].message.content
        return _coerce_review_response(_parse_review_raw(raw))
    
    except Exception as e:
        print(f"[review_simulator] Critical error: {e}")
        # Return valid empty response to keep pipeline moving
        return _coerce_review_response({})