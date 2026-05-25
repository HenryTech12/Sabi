import json
import os
from sabi.models.schemas import UserHistory, SoulProfile
from sabi.agents.voice_mapper import get_openai_client

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
"""

async def build_soul_profile(user_history: UserHistory) -> SoulProfile:
    """
    Builds a psychological soul profile from a user's review history.
    """
    history_text = json.dumps(user_history.model_dump(), indent=2)
    client = get_openai_client()
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.2,  # low temperature — we want consistent profiling
            max_tokens=1500,
            messages=[
                {"role": "system", "content": SOUL_READER_SYSTEM_PROMPT},
                {"role": "user", "content": f"""
                Analyse this Nigerian user's review history and build their complete 
                psychological soul profile.
                
                USER DATA:
                {history_text}
                
                Return ONLY a valid JSON object matching the SoulProfile schema.
                Be specific and detailed in every field.
                """}
            ]
        )
        
        raw = response.choices[0].message.content.strip()
        # Clean JSON if wrapped in markdown
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        
        # Log for debugging
        print(f"DEBUG: RAW LLM RESPONSE: {raw}")
        
        profile_data = json.loads(raw.strip())
        
        def normalize_profile(data):
            """Robustly maps LLM hallucinations back to the schema."""
            flat = {}
            
            # 1. Deep unwrap common parent keys
            if "SoulProfile" in data: data = data["SoulProfile"]
            if "profile" in data: data = data["profile"]
            
            # Helper to safely extract float from string or number
            def to_float(val, default=0.5):
                if isinstance(val, (int, float)): return float(val)
                if isinstance(val, str):
                    if "high" in val.lower(): return 0.8
                    if "low" in val.lower(): return 0.3
                    if "mid" in val.lower() or "moderate" in val.lower(): return 0.5
                    try: 
                        import re
                        match = re.search(r"(\d+\.?\d*)", val)
                        if match: return float(match.group(1))
                    except: pass
                return default

            # 2. Extract with common naming variations
            # Ratings
            flat["avg_rating"] = to_float(data.get("avg_rating") or data.get("rating_behaviour_analysis", {}).get("average_rating") or data.get("average_rating"), 4.0)
            flat["rating_style"] = data.get("rating_style") or data.get("rating_behaviour_analysis", {}).get("generosity") or "balanced"
            flat["rating_variance"] = to_float(data.get("rating_variance") or data.get("rating_behaviour_analysis", {}).get("variance") or 0.5)
            
            # Personality
            flat["personality_type"] = data.get("personality_type") or "storyteller"
            flat["review_length_style"] = data.get("review_length_style") or "moderate"
            flat["primary_focus"] = data.get("primary_focus") or "quality"
            flat["emotional_vs_analytical"] = data.get("emotional_vs_analytical") or "mixed"
            
            # Behavioural
            behav = data.get("behavioural_patterns", {})
            flat["forgiveness_factor"] = to_float(data.get("forgiveness_factor") or behav.get("forgiveness_factor"), 0.7)
            flat["novelty_seeking"] = to_float(data.get("novelty_seeking") or behav.get("novelty_seeking"), 0.5)
            flat["cultural_sensitivity"] = to_float(data.get("cultural_sensitivity") or behav.get("cultural_sensitivity"), 0.8)
            
            # Writing
            dna = data.get("writing_style_dna", {})
            flat["signature_phrases"] = data.get("signature_phrases") or dna.get("signature_phrases") or []
            flat["punctuation_style"] = data.get("punctuation_style") or dna.get("emphasis_style") or "standard"
            flat["dialect_markers"] = data.get("dialect_markers") or dna.get("nigerian_expressions") or dna.get("common_expressions") or []
            
            # identity
            iden = data.get("nigerian_identity_detection", {})
            flat["detected_region"] = data.get("detected_region") or iden.get("cultural_region") or "Lagos"
            flat["dialect_persona"] = data.get("dialect_persona") or iden.get("cultural_tone") or "pidgin_lagos"
            flat["cultural_affinity_score"] = to_float(data.get("cultural_affinity_score") or 0.8)
            
            # Cleanup list types
            if isinstance(flat.get("signature_phrases"), str): flat["signature_phrases"] = [flat["signature_phrases"]]
            if not flat.get("signature_phrases"): flat["signature_phrases"] = []
            
            if isinstance(flat.get("dialect_markers"), str): flat["dialect_markers"] = [flat["dialect_markers"]]
            if not flat.get("dialect_markers"): flat["dialect_markers"] = []
            
            # Ensure float types
            for field in ["avg_rating", "rating_variance", "forgiveness_factor", "novelty_seeking", "cultural_sensitivity", "cultural_affinity_score"]:
                if field in flat:
                    flat[field] = to_float(flat[field])
            
            # Enum mapping for dialect_persona if LLM used descriptive terms
            persona_map = {
                "Enugu/Igbo": "igbo_east",
                "Lagos/Yoruba": "pidgin_lagos",
                "Kano/Hausa": "hausa_kano",
                "Port Harcourt": "southsouth",
                "Abuja": "neutral_abuja"
            }
            for k, v in persona_map.items():
                if k.lower() in str(flat["dialect_persona"]).lower():
                    flat["dialect_persona"] = v
                    break
            
            # Final validation of dialect enum
            valid_personas = ["pidgin_lagos", "hausa_kano", "igbo_east", "southsouth", "neutral_abuja"]
            if flat["dialect_persona"] not in valid_personas:
                flat["dialect_persona"] = "neutral_abuja"
                
            return flat

        profile_data = normalize_profile(profile_data)
        profile_data["user_id"] = user_history.user_id
        return SoulProfile(**profile_data)
    except Exception as e:
        print(f"DEBUG: Soul Reader Error: {str(e)}")
        # Retry once with stricter prompt if JSON fails
        response = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.1,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": SOUL_READER_SYSTEM_PROMPT + "\nOUTPUT MUST BE ONLY JSON. NO MARKDOWN. NO CODE BLOCKS."},
                {"role": "user", "content": f"Analyze: {history_text}"}
            ]
        )
        raw = response.choices[0].message.content.strip()
        profile_data = json.loads(raw)
        
        # Use the same normalization logic defined above (I should have made it a helper function)
        # For the sake of the edit, I'll repeat the core normalization or just wrap it.
        # Let's refactor normalize_profile to a local function within build_soul_profile scope
        # Wait, I already added it inside build_soul_profile.
        
        # I'll just use the same logic again.
        def normalize_profile_retry(data):
            flat = {}
            if "SoulProfile" in data: data = data["SoulProfile"]
            if "profile" in data: data = data["profile"]
            
            def to_float(val, default=0.5):
                if isinstance(val, (int, float)): return float(val)
                if isinstance(val, str):
                    if "high" in val.lower(): return 0.8
                    if "low" in val.lower(): return 0.3
                    if "mid" in val.lower() or "moderate" in val.lower(): return 0.5
                    try: 
                        import re
                        match = re.search(r"(\d+\.?\d*)", val)
                        if match: return float(match.group(1))
                    except: pass
                return default

            flat["avg_rating"] = to_float(data.get("avg_rating") or data.get("rating_behaviour_analysis", {}).get("average_rating") or data.get("average_rating"), 4.0)
            flat["rating_style"] = data.get("rating_style") or data.get("rating_behaviour_analysis", {}).get("generosity") or "balanced"
            flat["rating_variance"] = to_float(data.get("rating_variance") or data.get("rating_behaviour_analysis", {}).get("variance") or 0.5)
            flat["personality_type"] = data.get("personality_type") or "storyteller"
            flat["review_length_style"] = data.get("review_length_style") or "moderate"
            flat["primary_focus"] = data.get("primary_focus") or "quality"
            flat["emotional_vs_analytical"] = data.get("emotional_vs_analytical") or "mixed"
            
            behav = data.get("behavioural_patterns", {})
            flat["forgiveness_factor"] = to_float(data.get("forgiveness_factor") or behav.get("forgiveness_factor"), 0.7)
            flat["novelty_seeking"] = to_float(data.get("novelty_seeking") or behav.get("novelty_seeking"), 0.5)
            flat["cultural_sensitivity"] = to_float(data.get("cultural_sensitivity") or behav.get("cultural_sensitivity"), 0.8)
            
            dna = data.get("writing_style_dna", {})
            flat["signature_phrases"] = data.get("signature_phrases") or dna.get("signature_phrases") or []
            flat["punctuation_style"] = data.get("punctuation_style") or dna.get("emphasis_style") or "standard"
            flat["dialect_markers"] = data.get("dialect_markers") or dna.get("nigerian_expressions") or dna.get("common_expressions") or []
            
            iden = data.get("nigerian_identity_detection", {})
            flat["detected_region"] = data.get("detected_region") or iden.get("cultural_region") or "Lagos"
            flat["dialect_persona"] = data.get("dialect_persona") or iden.get("cultural_tone") or "pidgin_lagos"
            flat["cultural_affinity_score"] = to_float(data.get("cultural_affinity_score") or 0.8)
            
            if isinstance(flat.get("signature_phrases"), str): flat["signature_phrases"] = [flat["signature_phrases"]]
            if not flat.get("signature_phrases"): flat["signature_phrases"] = []
            
            if isinstance(flat.get("dialect_markers"), str): flat["dialect_markers"] = [flat["dialect_markers"]]
            if not flat.get("dialect_markers"): flat["dialect_markers"] = []

            # Ensure float types
            for field in ["avg_rating", "rating_variance", "forgiveness_factor", "novelty_seeking", "cultural_sensitivity", "cultural_affinity_score"]:
                if field in flat:
                    flat[field] = to_float(flat[field])
            
            valid_personas = ["pidgin_lagos", "hausa_kano", "igbo_east", "southsouth", "neutral_abuja"]
            if flat["dialect_persona"] not in valid_personas:
                flat["dialect_persona"] = "neutral_abuja"
                
            return flat

        profile_data = normalize_profile_retry(profile_data)
        profile_data["user_id"] = user_history.user_id
        return SoulProfile(**profile_data)
