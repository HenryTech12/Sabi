import json
import os
from openai import AsyncOpenAI
from sabi.models.schemas import UserHistory, SoulProfile, RecommendResponse
from sabi.agents.soul_reader import build_soul_profile
from sabi.agents.voice_mapper import get_voice_instruction, get_openai_client



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

OUTPUT: Return ONLY valid JSON matching the RecommendResponse schema.
"""

async def get_recommendations(
    user_history: UserHistory,
    chat_history: list = [],
    current_message: str = "",
    context: str = None,
    n_recommendations: int = 10
) -> RecommendResponse:
    """
    Provides highly personalized recommendations based on the user's soul profile, conversation history, and context.
    """
    # Format chat_history into a readable thread
    formatted_history = "\n".join([f"{m['role'].upper() if isinstance(m, dict) else m.role.upper()}: {m['content'] if isinstance(m, dict) else m.content}" for m in chat_history])

    # Build a richer context string that combines chat history + current message
    combined_context = f"CONVERSATION HISTORY:\n{formatted_history}\nCURRENT REQUEST: {current_message}" \
        if chat_history else (current_message or context or "baseline")

    # Load items database
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base_dir, "data", "items.json")) as f:
        items_db = json.load(f)
    
    # Load Nigerian priors
    with open(os.path.join(base_dir, "data", "nigerian_priors.json")) as f:
        nigerian_priors = json.load(f)
    
    items_by_id = {i["item_id"]: i for i in items_db}
    
    # Build soul profile
    soul_profile = await build_soul_profile(user_history)
    voice_instruction = get_voice_instruction(soul_profile)
    
    # Filter out already reviewed items
    reviewed_titles = {r.title for r in user_history.reviewed_items}
    available_items = [i for i in items_db if i["title"] not in reviewed_titles]
    
    cold_start = len(user_history.reviewed_items) < 3
    client = get_openai_client()

    def parse_recommendation_response(raw_text, soul_profile, cold_start, context):
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        result = json.loads(raw_text.strip())
        
        # 1. Heuristic to handle nested responses
        if "recommendations" not in result:
            for val in result.values():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    if "rank" in val[0] or "item_id" in val[0] or "item" in val[0]:
                        result["recommendations"] = val
                        break
        
        # 2. Fix items - map IDs back to full items
        cleaned_recommendations = []
        if "recommendations" in result and isinstance(result["recommendations"], list):
            for rec in result["recommendations"]:
                item_data = rec.get("item")
                item_id = None
                
                if isinstance(item_data, dict):
                    item_id = item_data.get("item_id")
                elif "item_id" in rec:
                    item_id = rec["item_id"]
                elif isinstance(item_data, str):
                    item_id = item_data
                
                if item_id and item_id in items_by_id:
                    rec["item"] = items_by_id[item_id]
                elif not item_data:
                    continue
                
                # Defaults
                if "fit_score" not in rec: rec["fit_score"] = 0.5
                if "predicted_rating" not in rec: rec["predicted_rating"] = 4.0
                if "reason" not in rec: rec["reason"] = "Highly recommended for you."
                if "reasoning_chain" not in rec: rec["reasoning_chain"] = ["Standard match."]
                if "rank" not in rec: rec["rank"] = len(cleaned_recommendations) + 1
                if "cold_start_flag" not in rec: rec["cold_start_flag"] = cold_start
                
                cleaned_recommendations.append(rec)
        
        result["recommendations"] = cleaned_recommendations
        
        # 3. Metadata Defaults
        if "soul_profile_summary" not in result:
            result["soul_profile_summary"] = f"Recommendations for a {soul_profile.personality_type} from {soul_profile.detected_region}."
        if "dialect_used" not in result:
            result["dialect_used"] = soul_profile.dialect_persona
        if "cold_start_applied" not in result:
            result["cold_start_applied"] = cold_start
        if "context_applied" not in result:
            result["context_applied"] = context or "not specified"
            
        return RecommendResponse(**result)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            max_tokens=3000,
            messages=[
                {"role": "system", "content": RECOMMENDER_SYSTEM_PROMPT},
                {"role": "user", "content": f"""
                SOUL PROFILE:
                {json.dumps(soul_profile.model_dump(), indent=2)}
                
                NIGERIAN VOICE INSTRUCTION FOR REASONS:
                {voice_instruction}
                
                AVAILABLE ITEMS DATABASE:
                {json.dumps(available_items, indent=2)}
                
                NIGERIAN REGIONAL PRIORS:
                {json.dumps(nigerian_priors.get(soul_profile.detected_region, {}), indent=2)}
                
                CONTEXT: {combined_context}
                COLD START: {cold_start}
                NUMBER OF RECOMMENDATIONS NEEDED: {n_recommendations}
                
                Recommend {n_recommendations} items. Return ONLY valid JSON.
                """}
            ]
        )
        return parse_recommendation_response(
            response.choices[0].message.content, 
            soul_profile, cold_start, context
        )
    except Exception as e:
        # Retry once with stricter prompt
        response = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.1,
            max_tokens=3000,
            messages=[
                {"role": "system", "content": RECOMMENDER_SYSTEM_PROMPT + "\nOUTPUT MUST BE ONLY JSON."},
                {"role": "user", "content": f"Recommend {n_recommendations} movies for this user."}
            ]
        )
        return parse_recommendation_response(
            response.choices[0].message.content, 
            soul_profile, cold_start, context
        )
