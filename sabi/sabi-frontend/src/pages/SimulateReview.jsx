import React, { useState, useEffect } from "react";
import { getPersonas, getItems, simulateReview } from "../utils/api";
import PersonaCard from "../components/PersonaCard";
import ItemCard from "../components/ItemCard";
import LoadingSpinner from "../components/LoadingSpinner";
import SoulProfileCard from "../components/SoulProfileCard";
import ReasoningChain from "../components/ReasoningChain";
import {
    Star,
    MessageSquare,
    AlertCircle,
    RefreshCcw,
    Quote,
} from "lucide-react";

const SimulateReview = () => {
    const [personaList, setPersonaList] = useState([]);
    const [itemList, setItemList] = useState([]);
    const [selectedPersona, setSelectedPersona] = useState(null);
    const [selectedItem, setSelectedItem] = useState(null);
    const [loading, setLoading] = useState(false);
    const [initialLoading, setInitialLoading] = useState(true);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [pData, iData] = await Promise.all([
                    getPersonas(),
                    getItems(),
                ]);
                setPersonaList(pData);
                setItemList(iData);
            } catch (err) {
                console.error("Failed to fetch startup data:", err);
            } finally {
                setInitialLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleRunSabi = async () => {
        if (!selectedPersona || !selectedItem) return;

        setLoading(true);
        setResult(null);
        setError(null);

        try {
            const data = await simulateReview(selectedPersona, selectedItem);
            setResult(data);
        } catch (err) {
            console.error(err);
            setError(
                err.response?.data?.detail ||
                    "SABI encountered an error while simulating the review."
            );
        } finally {
            setLoading(false);
        }
    };

    const renderStars = (rating) => {
        return (
            <div className="flex items-center">
                {[1, 2, 3, 4, 5].map((s) => (
                    <Star
                        key={s}
                        className={`w-8 h-8 ${
                            s <= Math.round(rating)
                                ? "text-amber fill-amber"
                                : "text-light fill-light border-light"
                        }`}
                    />
                ))}
                <span className="ml-3 text-3xl font-black text-navy">
                    {rating}
                </span>
            </div>
        );
    };

    return (
        <div className="pt-24 pb-12 px-6 bg-light min-h-screen">
            <div className="max-w-7xl mx-auto grid lg:grid-cols-12 gap-8">
                {/* Left Column: Inputs */}
                <div className="lg:col-span-5 space-y-8">
                    <div>
                        <h2 className="text-2xl font-black text-navy mb-1 uppercase tracking-tighter italic">
                            Step 1: Select User Persona
                        </h2>
                        <p className="text-muted text-sm mb-6">
                            Choose a Nigerian profile with history.
                        </p>
                        <div className="max-h-[300px] overflow-y-auto pr-2 space-y-4 thin-scrollbar">
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
                            Step 2: Select Movie to Review
                        </h2>
                        <p className="text-muted text-sm mb-6">
                            What should this user experience?
                        </p>
                        <div className="grid grid-cols-2 gap-4 max-h-[400px] overflow-y-auto pr-2 thin-scrollbar">
                            {initialLoading ? (
                                <div className="col-span-2 flex justify-center p-8">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green"></div>
                                </div>
                            ) : (
                                itemList.map((i) => (
                                    <ItemCard
                                        key={i.item_id}
                                        item={i}
                                        selected={
                                            selectedItem?.item_id === i.item_id
                                        }
                                        onClick={setSelectedItem}
                                    />
                                ))
                            )}
                        </div>
                    </div>

                    <div className="pt-4">
                        <button
                            onClick={handleRunSabi}
                            disabled={
                                !selectedPersona || !selectedItem || loading
                            }
                            className={`w-full py-5 rounded-2xl font-black text-xl transition-all shadow-xl flex items-center justify-center ${
                                !selectedPersona || !selectedItem || loading
                                    ? "bg-muted/20 text-muted cursor-not-allowed"
                                    : "bg-green text-white hover:bg-teal hover:scale-[1.01]"
                            }`}
                        >
                            {loading
                                ? "SABI is Thinking..."
                                : "Simulate Review →"}
                        </button>
                    </div>
                </div>

                {/* Right Column: Results */}
                <div className="lg:col-span-7">
                    {!loading && !result && !error && (
                        <div className="h-full flex flex-col items-center justify-center text-center p-12 bg-white/50 border-2 border-dashed border-muted/30 rounded-3xl">
                            <MessageSquare className="w-16 h-16 text-muted/30 mb-4" />
                            <h3 className="text-xl font-bold text-navy/50">
                                Ready to simulate
                            </h3>
                            <p className="text-muted text-sm max-w-xs">
                                Select a persona and movie to see SABI in action
                            </p>
                        </div>
                    )}

                    {loading && (
                        <div className="h-full bg-navy rounded-3xl overflow-hidden shadow-2xl flex items-center justify-center">
                            <LoadingSpinner type="review" />
                        </div>
                    )}

                    {error && (
                        <div className="bg-red-50 border-2 border-red-200 rounded-3xl p-10 text-center">
                            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                            <h3 className="text-2xl font-bold text-red-700 mb-2">
                                SABI encountered an error
                            </h3>
                            <p className="text-red-600/80 mb-6">{error}</p>
                            <button
                                onClick={handleRunSabi}
                                className="bg-red-600 text-white px-8 py-3 rounded-full font-bold flex items-center mx-auto hover:bg-red-700 transition-colors"
                            >
                                <RefreshCcw className="w-4 h-4 mr-2" />
                                Try Again
                            </button>
                        </div>
                    )}

                    {result && !loading && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
                            <SoulProfileCard
                                profile={result}
                                userName={selectedPersona.name}
                            />

                            <div className="grid md:grid-cols-2 gap-6">
                                <div className="bg-white p-6 rounded-3xl shadow-sm border border-light flex flex-col justify-center">
                                    <p className="text-[10px] text-muted uppercase font-bold mb-4 tracking-widest">
                                        Predicted Rating
                                    </p>
                                    {renderStars(result.predicted_rating)}
                                    <div className="mt-6 flex items-center justify-between">
                                        <span className="text-xs text-muted font-bold uppercase">
                                            Confidence
                                        </span>
                                        <span className="text-xs text-green font-bold">
                                            {Math.round(
                                                result.confidence_score * 100
                                            )}
                                            %
                                        </span>
                                    </div>
                                    <div className="w-full bg-light h-1.5 rounded-full mt-2 overflow-hidden">
                                        <div
                                            className="bg-green h-full rounded-full transition-all duration-1000"
                                            style={{
                                                width: `${
                                                    result.confidence_score *
                                                    100
                                                }%`,
                                            }}
                                        ></div>
                                    </div>
                                </div>

                                <div className="bg-white p-6 rounded-3xl shadow-sm border border-light">
                                    <p className="text-[10px] text-muted uppercase font-bold mb-4 tracking-widest">
                                        Rating Drivers
                                    </p>
                                    <div className="flex flex-wrap gap-2">
                                        {result.rating_drivers.map((driver) => (
                                            <span
                                                key={driver}
                                                className="bg-green/10 text-green px-3 py-1.5 rounded-full text-xs font-bold border border-green/20"
                                            >
                                                {driver.replace("_", " ")}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white p-8 rounded-3xl shadow-lg border-l-8 border-green relative">
                                <div className="absolute top-0 right-0 p-8 text-light pointer-events-none">
                                    <Quote className="w-20 h-20 opacity-20 rotate-180" />
                                </div>
                                <div className="flex items-center space-x-2 mb-4">
                                    <div className="bg-green text-white text-[10px] font-black px-2 py-1 rounded-md uppercase">
                                        {result.dialect_used.replace("_", " ")}{" "}
                                        Voice
                                    </div>
                                </div>
                                <p className="text-xl md:text-2xl text-navy font-medium italic leading-relaxed relative z-10">
                                    "{result.review_text}"
                                </p>
                            </div>

                            <ReasoningChain chain={result.reasoning_chain} />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SimulateReview;
