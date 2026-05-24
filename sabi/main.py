from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import os
from dotenv import load_dotenv

from sabi.models.schemas import (
    SimulateReviewRequest, SimulateReviewResponse, 
    RecommendRequest, RecommendResponse,
    EvaluationResponse, ColdStartDemoResponse, PipelineDemoResponse
)
from sabi.agents.review_simulator import simulate_review
from sabi.agents.recommender import get_recommendations
from sabi.utils.evaluator import run_evaluation
from sabi.agents.cold_start_demo import run_cold_start_demo
from sabi.agents.pipeline_demo import run_full_pipeline_demo

# Get the directory where main.py is located
base_dir = os.path.dirname(os.path.abspath(__file__))
# Load .env from the same directory as main.py
load_dotenv(os.path.join(base_dir, ".env"))

# Global state for pre-loaded data
app_data = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load items.json and nigerian_priors.json at startup
    try:
        # Use base_dir calculated above
        with open(os.path.join(base_dir, "data", "items.json")) as f:
            app_data["items"] = json.load(f)
        with open(os.path.join(base_dir, "data", "nigerian_priors.json")) as f:
            app_data["priors"] = json.load(f)
        with open(os.path.join(base_dir, "data", "sample_users.json")) as f:
            app_data["personas"] = json.load(f)
    except Exception as e:
        print(f"Error loading startup data: {e}")
    yield
    # Clean up on shutdown if needed
    app_data.clear()

app = FastAPI(
    title="SABI — Nigerian Behavioural Soul Engine",
    description="""
    SABI (meaning 'to know deeply' in Nigerian Pidgin) is a four-agent LLM system 
    that models users as living psychological personalities — not static preference 
    vectors. Built for the DSN x Bluechip LLM Agent Challenge Hackathon 3.0.
    
    Task A: Simulate authentic Nigerian user reviews and star ratings
    Task B: Deliver contextual personalised recommendations
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Improved CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # Must be False if allow_origins is ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "name": "SABI",
        "tagline": "To know deeply — Nigerian Behavioural Soul Engine",
        "version": "1.0.0",
        "hackathon": "DSN x BCT LLM Agent Challenge Hackathon 3.0",
        "tasks": {
            "task_a_simulate_review": "POST /simulate-review",
            "task_b_recommend": "POST /recommend"
        },
        "sample_data": {
            "personas": "GET /personas",
            "items": "GET /items"
        }
    }

@app.post("/simulate-review", response_model=SimulateReviewResponse)
async def simulate_review_endpoint(request: SimulateReviewRequest):
    try:
        result = await simulate_review(request.user_history, request.item)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review Simulation Failed: {str(e)}")

@app.post("/recommend", response_model=RecommendResponse)
async def recommend_endpoint(payload: RecommendRequest):
    try:
        return await get_recommendations(
            payload.user_history,
            payload.chat_history,
            payload.current_message,
            payload.context,
            payload.n_recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation Task Failed: {str(e)}")

@app.get("/personas")
def get_sample_personas():
    if "personas" not in app_data:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, "data", "sample_users.json")) as f:
            return json.load(f)
    return app_data["personas"]

@app.get("/items")
def get_items():
    if "items" not in app_data:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, "data", "items.json")) as f:
            return json.load(f)
    return app_data["items"]

@app.get("/health")
def health():
    return {
        "status": "alive", 
        "agent": "SABI",
        "data_loaded": "items" in app_data and "priors" in app_data
    }

# Evaluation Endpoints
@app.get("/evaluation/results", response_model=EvaluationResponse)
async def get_evaluation_results():
    results_path = os.path.join(os.path.dirname(__file__), "evaluation", "results.json")
    if not os.path.exists(results_path):
        raise HTTPException(status_code=404, detail="No evaluation results found. Run POST /evaluation/run first")
    
    with open(results_path, "r") as f:
        return json.load(f)

@app.post("/evaluation/run", response_model=EvaluationResponse)
async def trigger_evaluation():
    try:
        results = await run_evaluation()
        if isinstance(results, dict) and "error" in results:
            raise HTTPException(status_code=500, detail=results["error"])
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

# Demo Endpoints
@app.get("/demo/cold-start", response_model=ColdStartDemoResponse)
async def get_cold_start_demo():
    try:
        return await run_cold_start_demo()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cold start demo failed: {str(e)}")

@app.get("/demo/pipeline", response_model=PipelineDemoResponse)
async def get_pipeline_demo(user_id: str):
    try:
        return await run_full_pipeline_demo(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline demo failed: {str(e)}")
