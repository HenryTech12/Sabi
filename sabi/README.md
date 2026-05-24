# SABI — Nigerian Behavioural Soul Engine

SABI (meaning "to know deeply" in Nigerian Pidgin) is a four-agent LLM system that models users as living psychological personalities — not static preference vectors. Built for the DSN x Bluechip LLM Agent Challenge Hackathon 3.0.

## Overview

Sabi moves beyond simple genre matching. It reads a user's review history, builds their psychological soul profile, maps them to a Nigerian cultural identity, simulates authentic reviews in their exact voice, and recommends items through contextual behavioural reasoning.

## Architecture

```text
[ User History ] ──> [ Agent 1: Soul Reader ] ──> [ Soul Profile ]
                                                          │
                                                          ├──> [ Agent 2: Voice Mapper ] ──> [ Voice Instruction ]
                                                          │                                          │
    [ New Item ] ──> [ Agent 3: Review Simulator ] <──────┘ <────────────────────────────────────────┘
                               │
                               └──> [ Predicted Rating & Simulated Review ]

[ All Items ] ──> [ Agent 4: Contextual Recommender ] <── [ Soul Profile ]
                               │
                               └──> [ Ranked Recommendations with Dialect Reasons ]
```

## Features

-   **Soul Profiling**: Analyzes rating behavior, personality type, and narrative focus.
-   **Cultural Identity**: Detects regional Nigerian backgrounds (Lagos, Kano, Enugu, etc.).
-   **Voice Mapping**: Translates profiles into authentic Nigerian dialects (Pidgin, Hausa-English, etc.).
-   **Contextual Awareness**: Adjusts recommendations based on mood, time, and occasion.
-   **Cross-Domain Reasoning**: Connects abstract signals (e.g., love for power stories) across categories.

## Getting Started

### Prerequisites

-   Python 3.11+
-   OpenAI API Key (GPT-4o access required)
-   Docker (optional)

### Installation

1. Clone the repository.
2. Create a `.env` file from `.env.example` and add your `OPENAI_API_KEY`.
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running Locally

```bash
python -m uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

### Running with Docker

```bash
docker-compose up --build
```

## API Documentation

### 1. Simulate Review

**POST** `/simulate-review`

Simulates how a specific user would rate and review a movie.

**Sample Request:**

```bash
curl -X POST http://localhost:8000/simulate-review \
-H "Content-Type: application/json" \
-d '{
  "user_history": {
    "user_id": "usr_001",
    "name": "Chioma Okafor",
    "age": 28,
    "location": "Enugu",
    "reviewed_items": [
      {
        "item_id": "mov_001",
        "title": "King of Boys",
        "category": "movie",
        "rating_given": 5.0,
        "review_text": "Nna this film is not a joke o..."
      }
    ]
  },
  "item": {
    "item_id": "mov_002",
    "title": "Brotherhood",
    "category": "movie",
    "genre": ["Action", "Crime"],
    "description": "Two brothers on opposite sides of the law.",
    "avg_community_rating": 4.5,
    "is_nigerian": true,
    "is_african": true,
    "themes": ["family", "crime"],
    "year": 2022
  }
}'
```

### 2. Recommend

**POST** `/recommend`

Provides personalized recommendations based on the user's soul profile and current context.

**Sample Request:**

```bash
curl -X POST http://localhost:8000/recommend \
-H "Content-Type: application/json" \
-d '{
  "user_history": {
    "user_id": "usr_001",
    "name": "Chioma Okafor",
    "age": 28,
    "location": "Enugu",
    "reviewed_items": [
      {
        "item_id": "mov_001",
        "title": "King of Boys",
        "category": "movie",
        "rating_given": 5.0,
        "review_text": "Nna this film is not a joke o..."
      }
    ]
  },
  "context": "weekend",
  "n_recommendations": 5
}'
```

## Architecture Decisions

-   **Soul Reader First**: We profile the user once and pass the `SoulProfile` to other agents to ensure behavioral consistency.
-   **Async Implementation**: Every LLM call is awaited to allow the FastAPI server to handle multiple requests efficiently.
-   **JSON Strictness**: We use a retry mechanism and markdown stripping to ensure the LLM responses always conform to our Pydantic schemas.
-   **Lifespan Loading**: Data files are loaded once at startup to minimize disk I/O during request processing.

## Future Improvements

-   **Vector Search**: Use embedding-based retrieval before the Recommender agent for larger datasets.
-   **Multimodal Reviews**: Support for voice-to-text reviews for more natural Nigerian expressions.
-   **Dynamic Priors**: Feedback loop to update `nigerian_priors.json` based on actual user interactions.
