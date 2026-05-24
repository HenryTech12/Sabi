import React, { useState, useEffect } from "react";
import { getColdStartDemo } from "../utils/api";
import { User, Flame, MapPin, Star, BadgeCheck } from "lucide-react";
import LoadingSpinner from "./LoadingSpinner";

const ColdStartDemo = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [viewMode, setViewMode] = useState("cold"); // 'cold' or 'warm'

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const res = await getColdStartDemo();
            setData(res);
            setError(null);
        } catch (err) {
            setError("Failed to fetch cold-start demo data.");
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <LoadingSpinner />;
    if (error)
        return (
            <div className="p-4 text-red-500 bg-red-100 rounded">{error}</div>
        );

    const currentUser = viewMode === "cold" ? data.cold_user : data.warm_user;

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                <div>
                    <h3 className="text-xl font-bold text-slate-900">
                        Cold-Start side-by-side
                    </h3>
                    <p className="text-slate-500 text-sm">
                        Comparing recommendation fidelity based on history
                        depth.
                    </p>
                </div>
                <div className="flex bg-slate-100 p-1 rounded-lg">
                    <button
                        onClick={() => setViewMode("cold")}
                        className={`px-4 py-2 rounded-md transition-all ${
                            viewMode === "cold"
                                ? "bg-white shadow-sm text-indigo-600 font-semibold"
                                : "text-slate-600"
                        }`}
                    >
                        Cold User (1 review)
                    </button>
                    <button
                        onClick={() => setViewMode("warm")}
                        className={`px-4 py-2 rounded-md transition-all ${
                            viewMode === "warm"
                                ? "bg-white shadow-sm text-indigo-600 font-semibold"
                                : "text-slate-600"
                        }`}
                    >
                        Warm User (8 reviews)
                    </button>
                </div>
            </div>

            {viewMode === "cold" && (
                <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl flex items-center gap-3 text-amber-800">
                    <Flame className="w-5 h-5 text-amber-600" />
                    <span className="font-medium text-sm">
                        Cold-start fallback active — using{" "}
                        {data.cold_user.prior_region} regional priors
                    </span>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* User Card */}
                <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-xl space-y-4 h-fit">
                    <div className="flex items-center gap-4">
                        <div
                            className={`p-3 rounded-full ${
                                viewMode === "cold"
                                    ? "bg-blue-100 text-blue-600"
                                    : "bg-orange-100 text-orange-600"
                            }`}
                        >
                            <User className="w-6 h-6" />
                        </div>
                        <div>
                            <h4 className="text-lg font-bold">
                                {viewMode === "cold"
                                    ? "James (Cold Start)"
                                    : "Tunde (Profiled User)"}
                            </h4>
                            <div className="flex items-center gap-2 text-slate-500 text-sm">
                                <MapPin className="w-3 h-3" />{" "}
                                {currentUser.prior_region} •{" "}
                                {currentUser.review_count} Reviews
                            </div>
                        </div>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-xl text-slate-700 text-sm italic border-l-4 border-indigo-400">
                        "{currentUser.reasoning}"
                    </div>
                    <div className="p-4 bg-indigo-50 rounded-xl text-indigo-900 text-sm">
                        <p className="font-bold mb-1">Difference Analysis:</p>
                        {data.difference_analysis}
                    </div>
                </div>

                {/* Recommendations List */}
                <div className="space-y-4">
                    <h4 className="font-bold text-slate-800 flex items-center gap-2">
                        Suggested for you
                        <span className="text-xs font-normal bg-slate-200 px-2 py-0.5 rounded-full">
                            {currentUser.recommendations.length} items
                        </span>
                    </h4>
                    <div className="space-y-3">
                        {currentUser.recommendations.map((rec, idx) => {
                            const isProfileUnlocked =
                                viewMode === "warm" &&
                                !data.cold_user.recommendations.some(
                                    (c) => c.item.item_id === rec.item.item_id
                                );

                            return (
                                <div
                                    key={rec.item.item_id}
                                    className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-all flex items-start gap-4"
                                >
                                    <div className="bg-slate-900 text-white w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm flex-shrink-0">
                                        #{idx + 1}
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center justify-between mb-1">
                                            <h5 className="font-bold text-slate-900">
                                                {rec.item.title}
                                            </h5>
                                            <div className="flex items-center gap-1 text-amber-500 font-bold text-sm">
                                                <Star className="w-3 h-3 fill-amber-500" />
                                                {rec.predicted_rating}
                                            </div>
                                        </div>
                                        <p className="text-slate-500 text-xs mb-2 line-clamp-1">
                                            {rec.reason}
                                        </p>
                                        <div className="flex flex-wrap gap-2">
                                            <span className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">
                                                Score:{" "}
                                                {Math.round(
                                                    rec.fit_score * 100
                                                )}
                                                %
                                            </span>
                                            {isProfileUnlocked && (
                                                <span className="text-[10px] px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full font-bold flex items-center gap-1 border border-yellow-200">
                                                    <BadgeCheck className="w-2.5 h-2.5" />{" "}
                                                    Profile-Unlocked
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ColdStartDemo;
