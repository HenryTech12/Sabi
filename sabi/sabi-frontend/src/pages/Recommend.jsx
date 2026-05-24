import React, { useState, useEffect } from "react";
import { getPersonas, getRecommendations } from "../utils/api";
import PersonaCard from "../components/PersonaCard";
import ItemCard from "../components/ItemCard";
import LoadingSpinner from "../components/LoadingSpinner";
import ConversationalRecommender from "../components/ConversationalRecommender";
import {
    Sparkles,
    Moon,
    PartyPopper,
    Zap,
    Calendar,
    Star,
    ChevronDown,
    ChevronUp,
    AlertCircle,
    RefreshCcw,
    MessageSquare,
    List,
} from "lucide-react";

const RecommendationItem = ({ item, rank }) => {
    const [expanded, setExpanded] = useState(false);

    const getRankColor = (rank) => {
        if (rank === 1) return "bg-amber text-white shadow-amber/30";
        if (rank === 2) return "bg-muted text-white shadow-muted/30";
        if (rank === 3) return "bg-amber/60 text-white shadow-amber/20";
        return "bg-light text-navy";
    };

    const scoreColor =
        item.fit_score >= 0.9
            ? "text-green"
            : item.fit_score >= 0.75
            ? "text-amber"
            : "text-muted";
    const progressBg =
        item.fit_score >= 0.9
            ? "bg-green"
            : item.fit_score >= 0.75
            ? "bg-amber"
            : "bg-muted";

    return (
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-light relative group hover:shadow-xl transition-all duration-300">
            <div className="flex flex-col md:flex-row md:items-center gap-6">
                <div
                    className={`w-12 h-12 rounded-2xl flex items-center justify-center font-black text-xl shrink-0 shadow-lg ${getRankColor(
                        rank
                    )}`}
                >
                    {rank}
                </div>

                <div className="grow">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                        <h3 className="text-xl font-black text-navy leading-none uppercase tracking-tight italic">
                            {item.item.title}
                        </h3>
                        <span className="text-xs text-muted font-bold mr-2">
                            ({item.item.year})
                        </span>
                        {item.item.is_nigerian && (
                            <span className="text-[9px] bg-amber text-white px-2 py-0.5 rounded-full font-bold uppercase">
                                Nollywood
                            </span>
                        )}
                        <div className="flex gap-1">
                            {item.item.genre.slice(0, 2).map((g) => (
                                <span
                                    key={g}
                                    className="text-[9px] bg-green/10 text-green px-2 py-0.5 rounded-full font-bold"
                                >
                                    {g}
                                </span>
                            ))}
                        </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <div>
                            <p className="text-[10px] text-muted font-bold uppercase tracking-wider mb-1">
                                Fit Score
                            </p>
                            <div className="flex items-center space-x-2">
                                <span
                                    className={`text-sm font-black ${scoreColor}`}
                                >
                                    {Math.round(item.fit_score * 100)}%
                                </span>
                                <div className="grow bg-light h-1 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full ${progressBg}`}
                                        style={{
                                            width: `${item.fit_score * 100}%`,
                                        }}
                                    ></div>
                                </div>
                            </div>
                        </div>
                        <div>
                            <p className="text-[10px] text-muted font-bold uppercase tracking-wider mb-1">
                                Predicted
                            </p>
                            <div className="flex items-center text-navy font-black text-sm">
                                <Star className="w-3.5 h-3.5 text-amber fill-amber mr-1" />
                                {item.predicted_rating}
                            </div>
                        </div>
                    </div>

                    <div className="bg-light/50 p-4 rounded-2xl border-l-4 border-green relative">
                        <p className="text-sm text-navy font-medium italic leading-relaxed">
                            "{item.reason}"
                        </p>
                    </div>
                </div>

                <button
                    onClick={() => setExpanded(!expanded)}
                    className="md:self-start bg-light hover:bg-light/80 p-2 rounded-xl transition-colors shrink-0"
                >
                    {expanded ? (
                        <ChevronUp className="w-5 h-5" />
                    ) : (
                        <ChevronDown className="w-5 h-5" />
                    )}
                </button>
            </div>

            {expanded && (
                <div className="mt-6 pt-6 border-t border-light animate-in fade-in slide-in-from-top-2 duration-300">
                    <p className="text-[10px] text-muted font-bold uppercase tracking-widest mb-3">
                        Reasoning Chain
                    </p>
                    <div className="flex flex-wrap gap-2 text-xs">
                        {item.reasoning_chain.map((r) => (
                            <div
                                key={r}
                                className="bg-navy/5 text-navy/70 px-3 py-1 rounded-lg border border-navy/10 font-medium"
                            >
                                {r.replace("_", " ")}
                            </div>
                        ))}
                        {item.cold_start_flag && (
                            <span className="bg-purple/10 text-purple px-3 py-1 rounded-lg border border-purple/10 font-bold">
                                Cold Start Handle
                            </span>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

const Recommend = () => {
    const [personaList, setPersonaList] = useState([]);
    const [selectedPersona, setSelectedPersona] = useState(null);
    const [context, setContext] = useState(null);
    const [loading, setLoading] = useState(false);
    const [initialLoading, setInitialLoading] = useState(true);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [viewMode, setViewMode] = useState("classic"); // "classic" or "chat"

    useEffect(() => {
        const fetchData = async () => {
            try {
                const data = await getPersonas();
                setPersonaList(data);
            } catch (err) {
                console.error("Failed to fetch personas:", err);
            } finally {
                setInitialLoading(false);
            }
        };
        fetchData();
    }, []);

    const contextOptions = [
        {
            id: "evening",
            label: "Evening Mood",
            icon: Moon,
            color: "hover:bg-indigo-500 hover:text-white",
        },
        {
            id: "celebratory",
            label: "Celebratory",
            icon: PartyPopper,
            color: "hover:bg-pink-500 hover:text-white",
        },
        {
            id: "stressed",
            label: "Stressed",
            icon: Zap,
            color: "hover:bg-amber-500 hover:text-white",
        },
        {
            id: "weekend",
            label: "Weekend",
            icon: Calendar,
            color: "hover:bg-green hover:text-white",
        },
    ];

    const handleGetRecommendations = async () => {
        if (!selectedPersona) return;

        setLoading(true);
        setResult(null);
        setError(null);

        try {
            const data = await getRecommendations(selectedPersona, context);
            setResult(data);
        } catch (err) {
            console.error(err);
            setError(
                err.response?.data?.detail ||
                    "SABI encountered an error while finding matches."
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="pt-24 pb-12 px-6 bg-light min-h-screen">
            <div className="max-w-7xl mx-auto flex flex-col gap-8">
                {/* View Mode Toggle */}
                <div className="flex justify-center mb-4">
                    <div className="bg-slate-200/50 p-1 rounded-2xl flex gap-1 border border-slate-200">
                        <button
                            onClick={() => setViewMode("classic")}
                            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-black text-sm transition-all ${
                                viewMode === "classic"
                                    ? "bg-white text-navy shadow-lg"
                                    : "text-slate-500 hover:text-slate-800"
                            }`}
                        >
                            <List className="w-4 h-4" />
                            Classic Mode
                        </button>
                        <button
                            onClick={() => setViewMode("chat")}
                            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-black text-sm transition-all ${
                                viewMode === "chat"
                                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-200"
                                    : "text-slate-500 hover:text-slate-800"
                            }`}
                        >
                            <MessageSquare className="w-4 h-4" />
                            Chat Mode
                        </button>
                    </div>
                </div>

                <div className="grid lg:grid-cols-12 gap-8">
                    {/* Left Column: Inputs */}
                    <div className="lg:col-span-4 space-y-8">
                        <div>
                            <h2 className="text-2xl font-black text-navy mb-1 uppercase tracking-tighter italic">
                                Step 1: Select User
                            </h2>
                            <p className="text-muted text-sm mb-6">
                                Whose soul should we recommend for?
                            </p>
                            <div className="max-h-[500px] overflow-y-auto pr-2 space-y-4 thin-scrollbar">
                                {initialLoading ? (
                                    <div className="flex justify-center p-8">
                                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green"></div>
                                    </div>
                                ) : (
                                    personaList.map((p) => (
                                        <PersonaCard
                                            key={p.user_id}
                                            persona={p}
                                            selected={
                                                selectedPersona?.user_id ===
                                                p.user_id
                                            }
                                            onClick={setSelectedPersona}
                                        />
                                    ))
                                )}
                            </div>
                        </div>

                        <div>
                            <h2 className="text-2xl font-black text-navy mb-1 uppercase tracking-tighter italic">
                                Step 2: Context
                            </h2>
                            <p className="text-muted text-sm mb-6">
                                How is {selectedPersona?.name || "the user"}{" "}
                                feeling today?
                            </p>
                            <div className="grid grid-cols-2 gap-3">
                                {contextOptions.map((opt) => (
                                    <button
                                        key={opt.id}
                                        onClick={() =>
                                            setContext(
                                                context === opt.id
                                                    ? null
                                                    : opt.id
                                            )
                                        }
                                        className={`flex items-center justify-center gap-2 p-3 rounded-2xl border-2 font-bold text-[11px] transition-all ${
                                            context === opt.id
                                                ? "bg-navy text-white border-navy shadow-lg"
                                                : `bg-white border-transparent ${opt.color} text-muted`
                                        }`}
                                    >
                                        <opt.icon
                                            className={`w-4 h-4 ${
                                                context === opt.id
                                                    ? "text-green"
                                                    : ""
                                            }`}
                                        />
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <button
                            onClick={handleGetRecommendations}
                            disabled={!selectedPersona || loading}
                            className={`w-full py-5 rounded-2xl font-black text-xl transition-all shadow-xl flex items-center justify-center ${
                                !selectedPersona || loading
                                    ? "bg-muted/20 text-muted cursor-not-allowed"
                                    : "bg-green text-white hover:bg-teal hover:scale-[1.01]"
                            }`}
                        >
                            {loading
                                ? "Finding Matches..."
                                : "Get Recommendations →"}
                        </button>
                    </div>

                    {/* Right Column: Dynamic Output */}
                    <div className="lg:col-span-8">
                        {viewMode === "chat" ? (
                            <div className="h-full min-h-[600px]">
                                {selectedPersona ? (
                                    <ConversationalRecommender
                                        userHistory={selectedPersona}
                                    />
                                ) : (
                                    <div className="bg-white rounded-3xl p-12 text-center border-2 border-dashed border-slate-200 flex flex-col items-center justify-center h-full">
                                        <MessageSquare className="w-16 h-16 text-slate-200 mb-4" />
                                        <h3 className="text-xl font-bold text-slate-400">
                                            Select a persona to start chatting
                                        </h3>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <>
                                {!loading && !result && !error && (
                                    <div className="h-full flex flex-col items-center justify-center text-center p-12 bg-white/50 border-2 border-dashed border-muted/30 rounded-3xl">
                                        <Sparkles className="w-16 h-16 text-muted/30 mb-4" />
                                        <h3 className="text-xl font-bold text-navy/50">
                                            Ready to rank
                                        </h3>
                                        <p className="text-muted text-sm max-w-xs">
                                            Select a persona to see personalized
                                            recommendations
                                        </p>
                                    </div>
                                )}

                                {loading && (
                                    <div className="h-full bg-navy rounded-3xl overflow-hidden shadow-2xl flex items-center justify-center">
                                        <LoadingSpinner type="recommend" />
                                    </div>
                                )}

                                {error && (
                                    <div className="bg-red-50 border-2 border-red-200 rounded-3xl p-10 text-center">
                                        <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                                        <h3 className="text-2xl font-bold text-red-700 mb-2">
                                            Recommendation System Error
                                        </h3>
                                        <p className="text-red-600/80 mb-6">
                                            {error}
                                        </p>
                                        <button
                                            onClick={handleGetRecommendations}
                                            className="bg-red-600 text-white px-8 py-3 rounded-full font-bold flex items-center mx-auto hover:bg-red-700 transition-colors"
                                        >
                                            <RefreshCcw className="w-4 h-4 mr-2" />
                                            Try Again
                                        </button>
                                    </div>
                                )}

                                {result && !loading && (
                                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
                                        <div className="bg-navy p-8 rounded-3xl shadow-xl border-b-8 border-green">
                                            <div className="flex items-center gap-3 mb-4">
                                                <Sparkles className="text-green w-8 h-8" />
                                                <h2 className="text-3xl font-black text-white italic lowercase tracking-tight">
                                                    Top Matches for{" "}
                                                    {selectedPersona.name}
                                                </h2>
                                            </div>
                                            <p className="text-light/90 text-lg font-medium italic mb-6 leading-relaxed">
                                                "{result.soul_profile_summary}"
                                            </p>
                                            <div className="flex flex-wrap gap-4 items-center">
                                                <span className="bg-green text-white text-[10px] font-black px-3 py-1 rounded-md uppercase">
                                                    {result.dialect_used.replace(
                                                        "_",
                                                        " "
                                                    )}{" "}
                                                    Applied
                                                </span>
                                                <span className="text-muted text-xs font-bold uppercase tracking-widest">
                                                    Context:{" "}
                                                    {result.context_applied ||
                                                        "General Taste"}
                                                </span>
                                                {result.cold_start_applied && (
                                                    <span className="bg-amber text-white text-[10px] font-black px-3 py-1 rounded-md uppercase">
                                                        Nigerian Priors Used
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        <div className="space-y-4">
                                            {result.recommendations.map(
                                                (item, idx) => (
                                                    <RecommendationItem
                                                        key={item.item.item_id}
                                                        item={item}
                                                        rank={item.rank}
                                                    />
                                                )
                                            )}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Recommend;
