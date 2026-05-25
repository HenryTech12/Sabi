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

async def simulate_review(
    user_history: UserHistory, 
    item: Item
) -> SimulateReviewResponse:
    """
    Simulates a review and rating for a specific item based on user history.
    """
    # Step 1: Build soul profile
    soul_profile = await build_soul_profile(user_history)
    
    # Step 2: Get Nigerian voice instruction
    voice_instruction = get_voice_instruction(soul_profile)
    
    # Step 3: Simulate the review
    client = get_openai_client()
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.75,
            max_tokens=1200,
            messages=[
                {"role": "system", "content": REVIEW_SIMULATOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"""
                SOUL PROFILE:
                {json.dumps(soul_profile.model_dump(), indent=2)}
                
                NIGERIAN VOICE INSTRUCTION:
                {voice_instruction}
                
                ITEM TO REVIEW:
                {json.dumps(item.model_dump(), indent=2)}
                
                USER'S PAST REVIEWS FOR CONTEXT:
                {json.dumps([r.model_dump() for r in user_history.reviewed_items[-5:]], indent=2)}
                
                Simulate exactly how this specific Nigerian person would rate and 
                review this item. Show your reasoning chain for the rating.
                Return ONLY valid JSON.
                """}
            ]
        )
        
        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        
        result = json.loads(raw.strip())
        
        # Heuristic to handle nested responses in simulation
        if "predicted_rating" not in result:
            for val in result.values():
                if isinstance(val, dict) and "predicted_rating" in val:
                    result = val
                    break
                    
        return SimulateReviewResponse(**result)
    except Exception as e:
        # Retry once
        response = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.5,
            max_tokens=1200,
            messages=[
                {"role": "system", "content": REVIEW_SIMULATOR_SYSTEM_PROMPT + "\nRETURN ONLY JSON. MATCH SCHEMA EXACTLY."},
                {"role": "user", "content": f"Simulate review for item: {item.title}"}
            ]
        )
        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        
        if "predicted_rating" not in result:
            for val in result.values():
                if isinstance(val, dict) and "predicted_rating" in val:
                    result = val
                    break
        return SimulateReviewResponse(**result)
