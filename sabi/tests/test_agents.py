import pytest
from sabi.models.schemas import UserHistory, Item, ReviewedItem

def test_pydantic_models():
    # Simple check for model instantiation
    item = Item(
        item_id="mov_001",
        title="King of Boys",
        category="movie",
        genre=["Crime"],
        description="Test",
        avg_community_rating=4.5,
        is_nigerian=True,
        is_african=True,
        themes=["power"],
        year=2018
    )
    assert item.title == "King of Boys"

def test_user_history():
    review = ReviewedItem(
        item_id="mov_001",
        title="King of Boys",
        category="movie",
        rating_given=5.0,
        review_text="Great!"
    )
    user = UserHistory(
        user_id="usr_001",
        name="Chioma",
        age=28,
        location="Enugu",
        reviewed_items=[review]
    )
    assert len(user.reviewed_items) == 1
