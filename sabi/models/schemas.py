from pydantic import BaseModel
from typing import Optional, List

class ReviewedItem(BaseModel):
    item_id: str
    title: str
    category: str  # movie, restaurant, book
    rating_given: float  # 1.0 to 5.0
    review_text: str
    date: Optional[str] = None

class UserHistory(BaseModel):
    user_id: str
    name: str
    age: int
    location: str  # Lagos, Kano, Enugu, Port Harcourt, Abuja
    occupation: Optional[str] = None
    reviewed_items: List[ReviewedItem]

class SoulProfile(BaseModel):
    user_id: str
    # Rating behaviour
    avg_rating: float
    rating_style: str        # generous, critical, balanced
    rating_variance: float   # how much their ratings vary
    # Personality dimensions
    personality_type: str    # optimist, contrarian, analyst, storyteller, minimalist
    review_length_style: str # verbose, terse, moderate
    primary_focus: str       # what they mention first — food/service/ambience/value/story
    emotional_vs_analytical: str  # emotional, analytical, mixed
    # Behavioural patterns
    forgiveness_factor: float     # 0-1: do they forgive flaws for strengths?
    novelty_seeking: float        # 0-1: do they prefer new or familiar?
    cultural_sensitivity: float   # 0-1: how much does cultural relevance affect rating?
    # Writing style
    signature_phrases: List[str]  # phrases they reuse
    punctuation_style: str        # heavy punctuation, minimal, emoji-user
    dialect_markers: List[str]    # Nigerian expressions they naturally use
    # Nigerian identity
    detected_region: str          # Lagos, Kano, Enugu, Port Harcourt, Abuja
    dialect_persona: str          # pidgin_lagos, hausa_kano, igbo_east, southsouth, neutral_abuja
    cultural_affinity_score: float  # 0-1: preference for Nigerian/African content

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
    role: str  # "user" or "assistant"
    content: str

class RecommendRequest(BaseModel):
    user_history: UserHistory
    chat_history: List[ChatMessage] = []  # defaults to empty for backwards compatibility
    current_message: str = ""
    context: Optional[str] = None  # keep old field so existing calls don't break
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

# Evaluation Pipeline Schemas
class RougeScores(BaseModel):
    rouge1: float
    rouge2: float
    rougeL: float

class EvaluationResponse(BaseModel):
    sample_count: int
    rmse: float
    avg_rouge: Optional[RougeScores] = None
    rouge_1: Optional[float] = None
    rouge_2: Optional[float] = None
    rouge_l: Optional[float] = None
    per_sample_results: List[dict]

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

# Cold Start Demo Schemas
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

# Pipeline Demo Schemas
class PipelineStep(BaseModel):
    step: int
    agent: str
    output: dict

class PipelineDemoResponse(BaseModel):
    user_id: str
    input_history_summary: str
    pipeline_steps: List[PipelineStep]
    total_latency_ms: float
