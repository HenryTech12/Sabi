import asyncio
from sabi.agents.soul_reader import build_soul_profile
from sabi.models.schemas import UserHistory

# Create a dummy UserHistory object based on your Amazon data
test_history = UserHistory(
    user_id="amz_user_000",
    name="Tunde",
    reviewed_items=[{
        "item_id": "amz_prod_001",
        "title": "Broken Laptop",
        "category": "Tech",
        "rating_given": 1,
        "review_text": "Customer service was terrible, they froze my account for no reason!",
        "date": "2023-01-01"
    }]
)

async def test():
    profile = await build_soul_profile(test_history)
    print(f"Profile Generated: {profile.personality_type} | Dialect: {profile.dialect_persona}")

asyncio.run(test())