import json
import os
from sabi.models.schemas import UserHistory, ReviewedItem, ColdStartDemoResponse, UserDemo
from sabi.agents.recommender import get_recommendations

async def run_cold_start_demo():
    # 1. Define cold_user (1 review, Lagos)
    cold_user = UserHistory(
        user_id="cold_user_001",
        name="James Lagos",
        age=25,
        location="Lagos",
        occupation="Student",
        reviewed_items=[
            ReviewedItem(
                item_id="mov_001",
                title="The Wedding Party",
                category="movie",
                rating_given=4.0,
                review_text="Omo, this movie funny die. Standard Lagos wedding vibes.",
                date="2023-12-01"
            )
        ]
    )

    # 2. Define warm_user (8+ reviews, Lagos)
    warm_user = UserHistory(
        user_id="warm_user_001",
        name="Tunde Lagos",
        age=29,
        location="Lagos",
        occupation="Marketing Exec",
        reviewed_items=[
            ReviewedItem(item_id="mov_001", title="The Wedding Party", category="movie", rating_given=5.0, review_text="Classic Lagos comedy."),
            ReviewedItem(item_id="mov_002", title="King of Boys", category="movie", rating_given=5.0, review_text="Powerful performance by Sola Sobowale."),
            ReviewedItem(item_id="mov_003", title="Merry Men", category="movie", rating_given=3.0, review_text="A bit shallow but okay."),
            ReviewedItem(item_id="mov_004", title="Lionheart", category="movie", rating_given=4.0, review_text="Stellar direction by Genevieve."),
            ReviewedItem(item_id="mov_005", title="Chief Daddy", category="movie", rating_given=4.0, review_text="Funny ensemble cast."),
            ReviewedItem(item_id="mov_006", title="Up North", category="movie", rating_given=4.0, review_text="Beautiful scenery of Bauchi."),
            ReviewedItem(item_id="mov_007", title="Sugar Rush", category="movie", rating_given=5.0, review_text="Chaos and fun all the way!"),
            ReviewedItem(item_id="mov_008", title="Citation", category="movie", rating_given=4.0, review_text="Important message about power dynamics.")
        ]
    )

    # Call recommendations for both
    cold_res = await get_recommendations(cold_user, n_recommendations=5)
    warm_res = await get_recommendations(warm_user, n_recommendations=5)

    difference_analysis = (
        "The cold-start user recommendations heavily rely on Lagos regional priors "
        "(popular high-energy Nollywood comedies) since their single review lacks deep psychological depth. "
        "The warm user's list is more nuanced, surfacing titles that match their specific preference for "
        "prestige drama and power dynamics detected across their 8 reviews."
    )

    return ColdStartDemoResponse(
        cold_user=UserDemo(
            review_count=1,
            cold_start_applied=True,
            prior_region="Lagos",
            recommendations=cold_res.recommendations,
            reasoning="Based on Lagos popularity markers."
        ),
        warm_user=UserDemo(
            review_count=8,
            cold_start_applied=False,
            prior_region="Lagos",
            recommendations=warm_res.recommendations,
            reasoning="Based on deep behavioral patterns."
        ),
        difference_analysis=difference_analysis
    )
