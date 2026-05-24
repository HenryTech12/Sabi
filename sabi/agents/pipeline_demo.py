import json
import os
import time
from sabi.models.schemas import UserHistory, PipelineDemoResponse, PipelineStep, Item
from sabi.agents.soul_reader import build_soul_profile
from sabi.agents.voice_mapper import get_voice_instruction
from sabi.agents.review_simulator import simulate_review
from sabi.agents.recommender import get_recommendations

async def run_full_pipeline_demo(user_id: str):
    start_time = time.time()
    
    # 0. Load User
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    samples_path = os.path.join(base_dir, "data", "sample_users.json")
    
    with open(samples_path, "r") as f:
        users = json.load(f)
    
    user_data = next((u for u in users if u["user_id"] == user_id), users[0])
    user_history = UserHistory(**user_data)
    
    # Step 1: Soul Profile
    t1 = time.time()
    soul_profile = await build_soul_profile(user_history)
    
    # Step 2: Voice Instruction
    voice_instruction = get_voice_instruction(soul_profile)
    
    # Step 3: Simulated Review
    # Construct a default item to review
    item = Item(
        item_id="demo_item_999",
        title="Brotherhood",
        category="movie",
        genre=["Action", "Thriller"],
        description="A high-stakes thriller set in the underbelly of Lagos.",
        avg_community_rating=4.5,
        is_nigerian=True,
        is_african=True,
        themes=["Loyalty", "Crime"],
        year=2022
    )
    sim_review = await simulate_review(user_history, item)
    
    # Step 4: Recommendations
    recs = await get_recommendations(user_history, n_recommendations=5)
    
    end_time = time.time()
    
    steps = [
        PipelineStep(step=1, agent="Soul Reader", output=soul_profile.model_dump()),
        PipelineStep(step=2, agent="Voice Mapper", output={"voice_instruction": voice_instruction}),
        PipelineStep(step=3, agent="Review Simulator", output=sim_review.model_dump()),
        PipelineStep(step=4, agent="Contextual Recommender", output=recs.model_dump())
    ]
    
    return PipelineDemoResponse(
        user_id=user_id,
        input_history_summary=f"User has {len(user_history.reviewed_items)} reviews.",
        pipeline_steps=steps,
        total_latency_ms=round((end_time - start_time) * 1000, 2)
    )
    
async def get_all_sample_user_ids():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    samples_path = os.path.join(base_dir, "data", "sample_users.json")
    with open(samples_path, "r") as f:
        users = json.load(f)
    return [u["user_id"] for u in users]
