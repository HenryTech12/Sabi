import os
from openai import AsyncOpenAI
from sabi.utils.nigerian_voice import get_voice_instruction, DIALECT_INSTRUCTIONS

def get_openai_client():
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
