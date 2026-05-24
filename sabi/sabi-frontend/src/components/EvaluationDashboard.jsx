import React, { useState, useEffect } from "react";
import { getEvaluationResults, runFullEvaluation } from "../utils/api";
import {
    Play,
    BarChart3,
    Activity,
    Layers,
    CheckCircle2,
    AlertCircle,
    Clock,
} from "lucide-react";

const EvaluationDashboard = () => {
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchResults = async () => {
        try {
            const data = await getEvaluationResults();
            setResults(data);
        } catch (err) {
            if (err.response && err.response.status === 404) {
                // Not run yet
                setError(
                    "Evaluation not run yet. Click 'Run Evaluation' to start."
                );
            } else {
                setError("Failed to load previous results.");
            }
        }
    };

    useEffect(() => {
        fetchResults();
    }, []);

    const runEvaluation = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await runFullEvaluation();
            setResults(data);
        } catch (err) {
            setError(
                "Evaluation failed: " +
                    (err.response?.data?.detail || err.message)
            );
        } finally {
            setLoading(false);
        }
    };

    const getRatingColor = (actual, predicted) => {
        const diff = Math.abs(actual - predicted);
        if (diff <= 0.5) return "bg-emerald-100 text-emerald-700 font-bold";
        if (diff <= 1.0) return "bg-amber-100 text-amber-700";
        return "bg-red-100 text-red-700";
    };

    return (
        <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                        <Activity className="text-emerald-600" />
                        Evaluation Dashboard
                    </h2>
                    <p className="text-sm text-slate-500">
                        Benchmark SABI agents against a golden dataset of Yelp
                        samples.
                    </p>
                </div>
                <button
                    onClick={runEvaluation}
                    disabled={loading}
                    className="flex items-center gap-2 bg-emerald-600 text-white px-6 py-2.5 rounded-lg font-bold hover:bg-emerald-700 disabled:opacity-50 transition-all shadow-md active:scale-95"
                >
                    {loading ? (
                        <>
                            <Clock className="w-5 h-5 animate-spin" />
                            Running evaluation...
                        </>
                    ) : (
                        <>
                            <Play className="w-5 h-5" />
                            Run Evaluation
                        </>
                    )}
                </button>
            </div>

            {loading && (
                <div className="bg-emerald-50 border border-emerald-200 p-8 rounded-xl flex flex-col items-center justify-center animate-pulse">
                    <div className="flex gap-2 mb-4">
                        <div className="w-4 h-4 bg-emerald-600 rounded-full animate-bounce"></div>
                        <div className="w-4 h-4 bg-emerald-600 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                        <div className="w-4 h-4 bg-emerald-600 rounded-full animate-bounce [animation-delay:0.4s]"></div>
                    </div>
                    <p className="font-bold text-emerald-800">
                        Running SABI against 25 Yelp samples...
                    </p>
                    <p className="text-sm text-emerald-600 mt-1">
                        This takes ~30 seconds as agents simulate reviews for
                        each entry.
                    </p>
                </div>
            )}

            {error && !loading && !results && (
                <div className="bg-slate-50 border border-slate-200 p-12 rounded-xl text-center">
                    <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-600">{error}</p>
                </div>
            )}

            {results && (
                <>
                    {/* Metrics Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-2 bg-blue-50 rounded-lg">
                                    <BarChart3 className="text-blue-600 w-6 h-6" />
                                </div>
                                <span className="text-xs font-bold text-slate-400 uppercase">
                                    Task A
                                </span>
                            </div>
                            <h3 className="text-3xl font-black text-slate-800">
                                {results.rmse.toFixed(4)}
                            </h3>
                            <p className="text-sm text-slate-500 mt-1">
                                Rating RMSE{" "}
                                <span className="text-xs font-normal">
                                    (lower is better)
                                </span>
                            </p>
                        </div>

                        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-2 bg-emerald-50 rounded-lg">
                                    <CheckCircle2 className="text-emerald-600 w-6 h-6" />
                                </div>
                                <span className="text-xs font-bold text-slate-400 uppercase">
                                    Textuality
                                </span>
                            </div>
                            <div className="space-y-1">
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-500">
                                        ROUGE-1:
                                    </span>
                                    <span className="text-slate-800 font-bold">
                                        {results.avg_rouge.rouge1}
                                    </span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-500">
                                        ROUGE-2:
                                    </span>
                                    <span className="text-slate-800 font-bold">
                                        {results.avg_rouge.rouge2}
                                    </span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-500">
                                        ROUGE-L:
                                    </span>
                                    <span className="text-slate-800 font-bold">
                                        {results.avg_rouge.rougeL}
                                    </span>
                                </div>
                            </div>
                            <p className="text-xs text-slate-400 mt-3 italic">
                                Measures dialect & style overlap
                            </p>
                        </div>

                        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-2 bg-amber-50 rounded-lg">
                                    <Layers className="text-amber-600 w-6 h-6" />
                                </div>
                            </div>
                            <h3 className="text-3xl font-black text-slate-800">
                                {results.sample_count}
                            </h3>
                            <p className="text-sm text-slate-500 mt-1">
                                Golden Samples Benchmarked
                            </p>
                        </div>
                    </div>

                    {/* Detailed Table */}
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                        <div className="p-4 border-b border-slate-200 bg-slate-50">
                            <h4 className="font-bold text-slate-700">
                                Per-Sample Results
                            </h4>
                        </div>
                        <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                            <table className="w-full text-left border-collapse">
                                <thead className="sticky top-0 bg-slate-100 z-10">
                                    <tr className="text-xs uppercase text-slate-500 font-bold tracking-wider">
                                        <th className="px-6 py-3">Sample ID</th>
                                        <th className="px-6 py-3 text-center">
                                            Actual Rating
                                        </th>
                                        <th className="px-6 py-3 text-center">
                                            Predicted Rating
                                        </th>
                                        <th className="px-6 py-3 text-center">
                                            ROUGE-1
                                        </th>
                                        <th className="px-6 py-3 text-center">
                                            ROUGE-2
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {results.per_sample_results.map(
                                        (sample, idx) => (
                                            <tr
                                                key={idx}
                                                className="hover:bg-slate-50 transition-colors"
                                            >
                                                <td className="px-6 py-4 text-sm font-mono text-slate-600">
                                                    {sample.sample_id}
                                                </td>
                                                <td className="px-6 py-4 text-center font-bold text-slate-400">
                                                    {sample.actual_rating.toFixed(
                                                        1
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 text-center">
                                                    <span
                                                        className={`px-2 py-1 rounded text-xs ${getRatingColor(
                                                            sample.actual_rating,
                                                            sample.predicted_rating
                                                        )}`}
                                                    >
                                                        {sample.predicted_rating.toFixed(
                                                            1
                                                        )}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-center text-sm text-slate-600">
                                                    {sample.rouge.rouge1}
                                                </td>
                                                <td className="px-6 py-4 text-center text-sm text-slate-600">
                                                    {sample.rouge.rouge2}
                                                </td>
                                            </tr>
                                        )
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default EvaluationDashboard;
