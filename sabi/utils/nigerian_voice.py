from sabi.models.schemas import SoulProfile

# Nigerian dialect instruction map
DIALECT_INSTRUCTIONS = {
    "pidgin_lagos": """
        Write like a Lagos Nigerian. Natural Pidgin flows through the review.
        Use: "e dey", "no be small thing", "I no go lie", "the thing burst my head",
        "chai!", "omo", "see as", "e sweet me", "abeg", "abi", "sha", "na so".
        Fast-paced, confident, expressive. References to Lagos life — traffic, 
        Island/Mainland, hustle culture. Warm but opinionated.
    """,
    "hausa_kano": """
        Write like a Northern Nigerian from Kano. More formal and measured.
        Use: "wallahi", "kai", "to tell you the truth", "by Allah", 
        "it was really good I must say", "I recommend for my brothers".
        Respectful tone. Family and community references. 
        Professional structure. Occasional Hausa word naturally placed.
    """,
    "igbo_east": """
        Write like an Igbo Nigerian from the East. Direct and expressive.
        Use: "nna", "chai", "onye", "this thing sweet o", "God when", 
        "the person wey cook this sabi work", "I swear to God".
        Ambitious references — value for money, quality, excellence.
        Short emphatic sentences. Strong opinions stated clearly.
    """,
    "southsouth": """
        Write like a South-South Nigerian from Port Harcourt or Delta.
        Use: "my brother/sister", "e be like say", "God when", 
        "this one na correct thing", "I dey tell you".
        Warm and relational. References to oil money culture occasionally.
        Expressive and generous with praise when deserved.
    """,
    "neutral_abuja": """
        Write like an Abuja Nigerian. Professional Nigerian English.
        Cosmopolitan, educated tone. Occasional Pidgin for emphasis only.
        References to Abuja lifestyle — wuse, wuse2, garki, maitama.
        Balanced, well-structured reviews. Articulate and measured.
    """
}

def get_voice_instruction(soul_profile: SoulProfile) -> str:
    """
    Returns specific voice and personality instructions based on the user's soul profile.
    """
    base_dialect = DIALECT_INSTRUCTIONS.get(
        soul_profile.dialect_persona, 
        DIALECT_INSTRUCTIONS["neutral_abuja"]
    )
    
    personality_instruction = f"""
    PERSONALITY OVERLAY:
    This user is a {soul_profile.personality_type}.
    They write in a {soul_profile.review_length_style} style.
    They focus first on: {soul_profile.primary_focus}.
    They are {soul_profile.emotional_vs_analytical} in approach.
    Their signature phrases include: {', '.join(soul_profile.signature_phrases[:3])}.
    Their punctuation style: {soul_profile.punctuation_style}.
    """
    
    return base_dialect + personality_instruction
