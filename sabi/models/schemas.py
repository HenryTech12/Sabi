from pydantic import BaseModel, model_validator
from typing import Optional, List

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

class SimulateReviewRequest(BaseModel):
    user_history: UserHistory
    item: Item

class SimulateReviewResponse(BaseModel):
    predicted_rating: float
    review_text: str
    confidence_score: float
    rating_drivers: List[str]
    dialect_used: str
    soul_profile_summary: str
    reasoning_chain: List[str]

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
    dialect_used: str
    cold_start_applied: bool
    context_applied: str

# ── Evaluation Schemas ─────────────────────────────────────────────────────────

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
    ndcg_10: Optional[float] = None     # Task B: 30 pts
    bert_score: Optional[float] = None  # Task A: behavioural fidelity

class EvaluationResponse(BaseModel):
    sample_count: int
    rmse: float
    avg_rouge: Optional[RougeScores] = None
    rouge_1: Optional[float] = None
    rouge_2: Optional[float] = None
    rouge_l: Optional[float] = None
    ndcg_10: Optional[float] = None     # Task B: 30 pts
    bert_score: Optional[float] = None  # Task A: fidelity
    per_sample_results: List[dict]

# ── Demo Schemas ───────────────────────────────────────────────────────────────

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