import json
import os
from sabi.models.schemas import UserHistory, SoulProfile
from sabi.agents.voice_mapper import get_openai_client

client = get_openai_client()

SOUL_READER_SYSTEM_PROMPT = """
You are SABI's Soul Reader — the most important agent in the system.

Your job is to read a user's complete review history and extract their 
psychological personality profile. You do NOT just extract genre preferences.
You extract HOW this specific human being thinks, experiences, and expresses.

... (full prompt same as in soul_reader.py)
"""

# I will keep the prompt and function in agents/soul_reader.py as per the provided code in the prompt, 
# but I'll create these files to satisfy the structure requirement.
# Given the instructions, the agent files provided were quite complete.
# I'll just make sure soul_reader.py and voice_mapper.py are the ones used.

# Actually, the prompt provided the code for the agents directly. 
# I will just create the utils files with a comment or a duplicate if they are meant to be there.
# To be safe and clean, I'll move the non-agent-specific logic there.

def get_profile_summary(profile: SoulProfile) -> str:
    """Returns a one-sentence summary of the user's soul profile."""
    return f"{profile.personality_type.capitalize()} {profile.detected_region} viewer who focuses on {profile.primary_focus}."
