# SABI: Nigerian Behavioural Soul Engine - System Workflow

SABI is a four-agent LLM system that models users as living psychological personalities. It prioritizes cultural nuance and regional dialects to deliver recommendations that feel authentic to the Nigerian experience.

---

## 1. Data Ingestion & Enrichment

The foundation of SABI is a hybrid data layer that combines global metadata with local cultural context.

-   **Global Catalog**: Fetches live movie data from **TMDB API**.
-   **Cultural Layer**: Specifically harvests **Nollywood** titles using Nigerian production region filters.
-   **User Seeding**: Streams rating patterns from **MovieLens 100k** (via HuggingFace) and dynamically assigns them to one of five Nigerian regional personas (Lagos, Kano, Enugu, Port Harcourt, Abuja).
-   **Resilience**: Implements local JSON fallbacks ([data/items.json](sabi/data/items.json)) to ensure the system remains functional even if external APIs are throttled.

---

## 2. Agent 1: The Soul Reader

The [Soul Reader](sabi/agents/soul_reader.py) is the system's "psychologist." It processes a user's entire star-rating and review history to build a **Soul Profile**.

-   **Rating Behaviour**: Calculates `avg_rating` and `rating_variance` to determine if a user is _Generous_, _Critical_, or _Balanced_.
-   **Psychological Persona**: Categorizes the user into types like _Optimist_, _Analyst_, _Storyteller_, or _Minimalist_.
-   **Linguistic Detection**: Identifies the user's region and assigns a `dialect_persona` (e.g., `pidgin_lagos`, `hausa_kano`).

---

## 3. The Voice Mapper (Instruction Synthesis)

The [Voice Mapper](sabi/utils/nigerian_voice.py) acts as a translator between raw data and creative writing.

-   **Dialect Injection**: It maps the Soul Profile's region to a library of regional slang and sentence structures.
-   **Personality Overlay**: It modulates the tone. A "Lagos Storyteller" gets instructions to be verbose and use Pidgin, while an "Abuja Analyst" is instructed to be measured and professional.
-   **System Prompt Generation**: This agent outputs the instructions that guide all subsequent LLM completions.

---

## 4. Agent 2 & 3: Simulation & Orchestration

### Task A: Review Simulator

The [Review Simulator](sabi/agents/review_simulator.py) creates high-fidelity synthetic reviews.

1.  **Reasoning**: It applies a "Reasoning Chain" to adjust the community average based on the user's Soul Profile (e.g., +0.3 for a Nollywood movie, -0.2 for a critical rater).
2.  **Voice**: It writes the review text using the specific vocabulary provided by the Voice Mapper.

### Task B: Contextual Recommender

The [Recommender](sabi/agents/recommender.py) synthesizes history and live context.

1.  **Filtering**: Removes items the user has already seen.
2.  **Regional Priors**: Prioritizes movies that are currently "trending" in the user's specific region.
3.  **Dialect Justification**: Instead of "You may like this," it generates justifications like: _"Omo, you go love this one because the drama too much!"_

---

## 5. Deployment & Infrastructure

-   **Backend**: FastAPI handles asynchronous orchestration of agents.
-   **Singleton Client**: Uses a shared `AsyncOpenAI` client with a managed `httpx` connection pool to prevent resource leaks during large evaluations.
-   **Frontend**: A React/Tailwind application provides "Classic Mode" (Visual Dashboard) and "Chat Mode" (Conversational Interface).
-   **Evaluation**: An automated [eval_pipeline.py](sabi/evaluation/eval_pipeline.py) compares simulated reviews against ground-truth data using **RMSE** and **ROUGE** scores.

---

## 6. Request Lifecycle

1.  **Frontend**: User selects a persona or sends a chat message.
2.  **API**: `POST /recommend` or `POST /simulate-review` is triggered.
3.  **Soul Reader**: History is summarized into a Soul Profile JSON.
4.  **Voice Mapper**: Profile is converted into linguistic instructions.
5.  **Task Agent**: LLM generates the final response (JSON) containing reasoning and text.
6.  **Frontend**: Renders the **Soul Card**, **Reasoning Chain**, and **Ranked Items**.
