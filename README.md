# SABI: Nigerian Behavioural Soul Engine 🧠🇳🇬

SABI (meaning "to know deeply" in Nigerian Pidgin) is a sophisticated multi-agent AI system designed to understand, simulate, and recommend content through the lens of Nigerian psychological and cultural personas.

---

## 📖 Non-Technical Overview

### What is SABI?

Most recommendation systems (like Netflix or Amazon) treat you like a list of numbers—a "user vector." They suggest things because "people like you also liked this."

**SABI is different.** It treats users as living personalities with:

-   **A Soul**: Understands your deep motivations (Are you a "Contrarian" who likes hidden gems? Or a "Minimalist" who hates clutter?).
-   **A Voice**: Speaks to you in your own dialect, whether it's Lagos Pidgin, Northern-style English, or Eastern-inflected prose.
-   **A Culture**: Respects the nuances of Nigerian life, from the hustle of Lagos to the family-centric values of Kano.

### How it Works

When you interact with SABI, four specialized agents work together to serve you:

1.  **The Soul Reader**: Analyzes your history to build a psychological profile.
2.  **The Voice Mapper**: Decides how to speak to you based on your region and personality.
3.  **The Review Simulator**: Predicts exactly what you would say about a movie before you even see it.
4.  **The Contextual Recommender**: Finds matches that fit your current mood, time of day, and cultural background.

---

## 🛠 Technical Architecture

### System Components

SABI is built on a high-performance **FastAPI** backend and a **React/Vite** frontend, leveraging the power of **GPT-4o**.

#### 1. The Agent Stack

-   **SoulReader Agent**: (`sabi/agents/soul_reader.py`)
    -   _Input_: `UserHistory` (List of ratings/reviews).
    -   _Logic_: Uses few-shot prompting to derive `personality_type` and `cultural_affinity`.
-   **VoiceMapper Agent**: (`sabi/agents/voice_mapper.py`)
    -   _Logic_: Translates system instructions into linguistic overlays (e.g., `pidgin_lagos`, `hausa_kano`).
-   **ReviewSimulator Agent**: (`sabi/agents/review_simulator.py`)
    -   _Logic_: Generates high-fidelity synthetic reviews and star ratings. Use cases include cold-start enrichment and synthetic data generation.
-   **Recommender Agent**: (`sabi/agents/recommender.py`)
    -   _Logic_: Implements "Contextual Personalized Ranking." It weights recommendations by psychological fit, cultural relevance, and temporal context.

#### 2. Data Infrastructure (`sabi/utils/cloud_data.py`)

SABI uses a "Hybrid Cloud" data approach:

-   **Live Catalog**: Real-time fetching from **TMDB API** (with a specialized Nollywood boost layer).
-   **Live User Profiles**: Streaming of real-world rating patterns from **MovieLens (HuggingFace Datasets)**.
-   **Resilient Fallback**: If APIs are down, the system seamlessly reverts to local `data/*.json` files to ensure zero downtime.

### API Specifications

-   `POST /simulate-review`: Predicts a user's reaction to a specific item.
-   `POST /recommend`: Context-aware recommendation engine (supports conversational chat).
-   `GET /demo/pipeline`: Returns a full step-by-step trace of the agent reasoning process.
-   `GET /health`: Checks connectivity to OpenAI, TMDB, and HuggingFace.

---

## 🚀 Getting Started

### Prerequisites

-   Python 3.9+
-   Node.js 18+
-   OpenAI API Key
-   TMDB API Key (Optional, for live data)

### Installation

1.  **Environment Setup**:
    ```bash
    cp .env.example .env
    # Add your keys to .env
    ```
2.  **Backend**:
    ```bash
    pip install -r requirements.txt
    uvicorn sabi.main:app --reload
    ```
3.  **Frontend**:
    ```bash
    cd sabi-frontend
    npm install
    npm run dev
    ```

---

## 🏆 Hackathon Context

SABI was developed for the **DSN x Bluechip LLM Agent Challenge Hackathon 3.0**.

-   **Task A (Reviews)**: Solved via `ReviewSimulator` with dialect-specific linguistic layers.
-   **Task B (Recommendations)**: Solved via `Recommender` using multi-dimensional soul-profiling.
-   **Bonus**: Implemented live Nollywood discovery and regional Nigerian priors.
