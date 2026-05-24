import axios from "axios";

// Fallback for Vercel deployments
const getBaseUrl = () => {
    // 1. If an explicit environment variable is set, use it
    if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
    
    // 2. On Vercel, we use the /api proxy configured in vercel.json
    // This avoids CORS issues entirely as it becomes a Same-Origin request
    if (window.location.hostname.includes("vercel.app")) {
        return "/api";
    }
    
    // 3. Default for local development (Vite proxy)
    return "/api";
};

const api = axios.create({
    baseURL: getBaseUrl(),
    headers: { "Content-Type": "application/json" },
    timeout: 60000, // 60 seconds — LLM calls take time
});

export const simulateReview = async (userHistory, item) => {
    const response = await api.post("/simulate-review", {
        user_history: userHistory,
        item: item,
    });
    return response.data;
};

export const getRecommendations = async (
    userHistory,
    chatHistory = [],
    currentMessage = "",
    context = null
) => {
    // If chatHistory was passed as a string (legacy/single-context mode), move it to context
    const actualChatHistory = Array.isArray(chatHistory) ? chatHistory : [];
    const actualContext =
        typeof chatHistory === "string" ? chatHistory : context;

    const response = await api.post("/recommend", {
        user_history: userHistory,
        chat_history: actualChatHistory,
        current_message: currentMessage,
        context: actualContext,
        n_recommendations: 10,
    });
    return response.data;
};

export const getPersonas = async () => {
    const response = await api.get("/personas");
    return response.data;
};

export const getItems = async () => {
    const response = await api.get("/items");
    return response.data;
};

export const getEvalResults = async () => {
    const response = await api.get("/evaluation/results");
    return response.data;
};

export const runEvaluation = async () => {
    const response = await api.post("/evaluation/run");
    return response.data;
};

export const getPipelineDemo = async (userId) => {
    const response = await api.get(`/demo/pipeline?user_id=${userId}`);
    return response.data;
};

export const getColdStartDemo = async () => {
    const response = await api.get("/demo/cold-start");
    return response.data;
};

export default api;
