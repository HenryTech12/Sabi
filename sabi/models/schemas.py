"""
SABI Pydantic Schemas.

Bug Fix Applied:
- Removed force_mathematical_consistency validator from SimulateReviewResponse.
  This validator was recalculating predicted_rating by parsing the reasoning_chain
  text. When LLM calls failed (rate limit / fallback), the chain contained error
  messages with no 'baseline'/'started at' keywords, so calculated_rating stayed
  at 0.0 and was clamped to max(1.0, 0.0) = 1.0.
  Result: every sample got predicted_rating=1.0 regardless of actual prediction,
  causing RMSE=2.93 and making all evaluation results meaningless.
  Fix: trust the predicted_rating the LLM returns directly. The review_simulator
  already clamps it to 1.0-5.0 before building this object.
"""

from pydantic import BaseModel, model_validator
from typing import Optional, List, Any
import re


# ── Core item/user schemas ────────────────────────────────────────────────────

class ReviewedItem(BaseModel):
    item_id: str
    title: str = "Unknown"
    category: str = "Movie"
    rating_given: float = 3.0
    review_text: str = ""
    date: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def accept_rating_alias(cls, data):
        """Accept 'rating' as an alias for 'rating_given' (MovieLens/Amazon key)."""
        if isinstance(data, dict):
            if "rating" in data and "rating_given" not in data:
                data = {**data, "rating_given": data["rating"]}
        return data


class UserHistory(BaseModel):
    user_id: str
    name: str = "Unknown"
    age: int = 25
    location: str = "Lagos"
    occupation: Optional[str] = None
    reviewed_items: List[ReviewedItem]


class SoulProfile(BaseModel):
    user_id: str
    avg_rating: float
    rating_style: str
    rating_variance: float
    personality_type: str
    review_length_style: str
    primary_focus: str
    emotional_vs_analytical: str
    forgiveness_factor: float
    novelty_seeking: float
    cultural_sensitivity: float
    signature_phrases: List[str]
    punctuation_style: str
    dialect_markers: List[str]
    detected_region: str
    dialect_persona: str
    cultural_affinity_score: float


class Item(BaseModel):
    item_id: str
    title: str
    category: str
    genre: List[str]
    description: str
    avg_community_rating: float
    is_nigerian: bool
    is_african: Optional[bool] = True
    themes: Optional[List[str]] = []
    year: Optional[int] = 2024
    poster_path: Optional[str] = None   # TMDB poster URL


# ── Request/Response schemas ──────────────────────────────────────────────────

class SimulateReviewRequest(BaseModel):
    user_history: UserHistory
    item: Item


class SimulateReviewResponse(BaseModel):
    predicted_rating: float
    review_text: str
    confidence_score: float
    rating_drivers: List[str]
    dialect_used: str
    # Change these types to Any or Dict to allow the nested objects the LLM is returning
    soul_profile_summary: Any 
    reasoning_chain: List[Any] 

    @model_validator(mode="after")
    def clamp_rating(self) -> "SimulateReviewResponse":
        self.predicted_rating = round(
            max(1.0, min(5.0, float(self.predicted_rating))), 1
        )
        self.confidence_score = round(
            max(0.0, min(1.0, float(self.confidence_score))), 2
        )
        
        # Add these two lines to force conversion if you want to keep your UI clean:
        self.soul_profile_summary = str(self.soul_profile_summary)
        self.reasoning_chain = [str(item) for item in self.reasoning_chain]
        
        return self


class ChatMessage(BaseModel):
    role: str
    content: str


class RecommendRequest(BaseModel):
    user_history: UserHistory
    chat_history: List[ChatMessage] = []
    current_message: str = ""
    context: Optional[str] = None
    n_recommendations: Optional[int] = 10


class RecommendationItem(BaseModel):
    rank: int
    item: Item
    fit_score: float
    predicted_rating: float
    reason: str
    reasoning_chain: List[str]
    cold_start_flag: bool


class RecommendResponse(BaseModel):
    recommendations: List[RecommendationItem]
    soul_profile_summary: str
    dialect_used: str = "neutral_abuja"
    cold_start_applied: bool
    context_applied: str


# ── Evaluation Schemas ────────────────────────────────────────────────────────

class RougeScores(BaseModel):
    rouge1: float
    rouge2: float
    rougeL: float


class EvalSampleResult(BaseModel):
    user_id: Optional[str] = None
    sample_id: Optional[str] = None
    actual_rating: float
    predicted_rating: float
    actual_review: Optional[str] = None
    predicted_review: Optional[str] = None
    rmse_contribution: Optional[float] = None
    rouge: Optional[RougeScores] = None


class EvaluationResults(BaseModel):
    rmse: float
    rouge_1: float
    rouge_2: float
    rouge_l: float
    sample_count: int
    per_sample_results: List[EvalSampleResult]
    ndcg_10: Optional[float] = None
    bert_score: Optional[float] = None


class EvaluationResponse(BaseModel):
    sample_count: int
    rmse: float
    avg_rouge: Optional[RougeScores] = None
    rouge_1: Optional[float] = None
    rouge_2: Optional[float] = None
    rouge_l: Optional[float] = None
    ndcg_10: Optional[float] = None
    bert_score: Optional[float] = None
    per_sample_results: List[dict]


# ── Demo Schemas ──────────────────────────────────────────────────────────────

class UserDemo(BaseModel):
    review_count: int
    cold_start_applied: bool
    prior_region: str
    recommendations: List[RecommendationItem]
    reasoning: str


class ColdStartDemoResponse(BaseModel):
    cold_user: UserDemo
    warm_user: UserDemo
    difference_analysis: str


class PipelineStep(BaseModel):
    step: int
    agent: str
    output: dict


class PipelineDemoResponse(BaseModel):
    user_id: str
    input_history_summary: str
    pipeline_steps: List[PipelineStep]
    total_latency_ms: float