import os
import httpx
from openai import AsyncOpenAI
from sabi.utils.nigerian_voice import get_voice_instruction, DIALECT_INSTRUCTIONS

_client = None

def get_openai_client():
    global _client
    if _client is None:
        # Explicitly create an httpx client to avoid proxy-related init errors in some environments
        # and reuse it via a singleton to prevent 'aclose' attribute errors during GC.
        http_client = httpx.AsyncClient()
        _client = AsyncOpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
    return _client
