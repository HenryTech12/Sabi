import React, { useState, useEffect } from "react";
import { getEvalResults, runEvaluation } from "../utils/api";
import { Play, Target, BarChart3, Database } from "lucide-react";
import LoadingSpinner from "../components/LoadingSpinner";
import ColdStartDemo from "../components/ColdStartDemo";
import PipelineVisualizer from "../components/PipelineVisualizer";
import EvaluationDashboard from "../components/EvaluationDashboard";

const EvaluationPage = () => {
    const [activeTab, setActiveTab] = useState("eval");
    const [evalResults, setEvalResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (activeTab === "eval") {
            loadEvaluation();
        }
    }, [activeTab]);

    const loadEvaluation = async () => {
        setLoading(true);
        try {
            const data = await getEvalResults();
            setEvalResults(data);
            setError(null);
        } catch (err) {
            setError(
                "No evaluation results found. Click 'Run Evaluation' to generate them."
            );
        } finally {
            setLoading(false);
        }
    };

    const handleRunEval = async () => {
        setLoading(true);
        try {
            const data = await runEvaluation();
            setEvalResults(data);
            setError(null);
        } catch (err) {
            setError("Evaluation failed. Check backend logs.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto px-4 py-12">
            <div className="mb-12">
                <h1 className="text-4xl font-black text-slate-900 mb-2">
                    Live Demo & Evaluation
                </h1>
                <p className="text-slate-500 text-lg">
                    Hacking the Nigerian Behavioural Soul Engine 🇳🇬
                </p>
            </div>

            {/* Navigation Tabs */}
            <div className="flex flex-wrap gap-2 mb-8 bg-slate-100 p-1.5 rounded-2xl w-fit">
                <TabButton
                    active={activeTab === "eval"}
                    onClick={() => setActiveTab("eval")}
                    icon={<Target className="w-4 h-4" />}
                    label="Evaluation Suite"
                />
                <TabButton
                    active={activeTab === "pipeline"}
                    onClick={() => setActiveTab("pipeline")}
                    icon={<Play className="w-4 h-4" />}
                    label="End-to-End Pipeline"
                />
                <TabButton
                    active={activeTab === "cold"}
                    onClick={() => setActiveTab("cold")}
                    icon={<Database className="w-4 h-4" />}
                    label="Cold-Start Test"
                />
            </div>

            {/* Tab Content */}
            <div className="min-h-[600px]">
                {activeTab === "eval" && (
                    <div className="space-y-8 animate-in fade-in duration-500">
                        {/* Summary Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                            <MetricCard
                                label="RMSE"
                                value={evalResults?.rmse?.toFixed(3) || "0.000"}
                                color="text-indigo-600"
                                desc="Lower is Better"
                            />
                            <MetricCard
                                label="ROUGE-1"
                                value={
                                    evalResults?.rouge_1?.toFixed(3) || "0.000"
                                }
                                color="text-emerald-600"
                                desc="Lexical Match"
                            />
                            <MetricCard
                                label="ROUGE-L"
                                value={
                                    evalResults?.rouge_l?.toFixed(3) || "0.000"
                                }
                                color="text-amber-600"
                                desc="Sequence Flow"
                            />
                            <MetricCard
                                label="Samples"
                                value={evalResults?.sample_count || "0"}
                                color="text-slate-900"
                                desc="Validated users"
                            />
                        </div>

                        {/* Action Header */}
                        <div className="flex items-center justify-between p-6 bg-white rounded-2xl border border-slate-100 shadow-xl">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-slate-900 rounded-xl text-white">
                                    <BarChart3 className="w-6 h-6" />
                                </div>
                                <div>
                                    <h2 className="text-xl font-bold">
                                        Accuracy Diagnostics
                                    </h2>
                                    <p className="text-slate-500 text-sm">
                                        Validating simulation against real-world
                                        human reviews.
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={handleRunEval}
                                disabled={loading}
                                className="px-6 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-all flex items-center gap-2 disabled:opacity-50"
                            >
                                <Play className="w-4 h-4" />
                                {loading ? "Evaluating..." : "Run Evaluation"}
                            </button>
                        </div>

                        {error && (
                            <div className="p-4 bg-amber-50 text-amber-700 rounded-xl border border-amber-200">
                                {error}
                            </div>
                        )}

                        {/* Results Table */}
                        {evalResults && (
                            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead className="bg-slate-50 border-b border-slate-100">
                                        <tr>
                                            <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">
                                                User ID
                                            </th>
                                            <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">
                                                Actual
                                            </th>
                                            <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">
                                                Predicted
                                            </th>
                                            <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">
                                                Variance
                                            </th>
                                            <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase">
                                                Review Snippet
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-50">
                                        {evalResults.per_sample_results.map(
                                            (res, i) => (
                                                <tr
                                                    key={i}
                                                    className="hover:bg-slate-50 transition-colors"
                                                >
                                                    <td className="px-6 py-4 font-mono text-xs text-indigo-600">
                                                        {res.user_id}
                                                    </td>
                                                    <td className="px-6 py-4 font-bold">
                                                        {res.actual_rating} ★
                                                    </td>
                                                    <td className="px-6 py-4 font-bold text-slate-900">
                                                        {res.predicted_rating} ★
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span
                                                            className={`px-2 py-1 rounded-full text-xs font-bold ${
                                                                Math.abs(
                                                                    res.actual_rating -
                                                                        res.predicted_rating
                                                                ) < 0.5
                                                                    ? "bg-emerald-100 text-emerald-700"
                                                                    : "bg-amber-100 text-amber-700"
                                                            }`}
                                                        >
                                                            ±
                                                            {Math.abs(
                                                                res.actual_rating -
                                                                    res.predicted_rating
                                                            ).toFixed(1)}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 text-slate-500 text-sm italic truncate max-w-xs">
                                                        "{res.predicted_review}"
                                                    </td>
                                                </tr>
                                            )
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === "pipeline" && <PipelineVisualizer />}
                {activeTab === "cold" && <ColdStartDemo />}
            </div>
        </div>
    );
};

const TabButton = ({ active, onClick, icon, label }) => (
    <button
        onClick={onClick}
        className={`flex items-center gap-2 px-6 py-3 rounded-xl transition-all font-bold text-sm ${
            active
                ? "bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200"
                : "text-slate-500 hover:text-slate-800"
        }`}
    >
        {icon}
        {label}
    </button>
);

const MetricCard = ({ label, value, color, desc }) => (
    <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-2">
        <p className="text-slate-400 text-xs font-bold uppercase tracking-wider leading-none">
            {label}
        </p>
        <p className={`text-3xl font-black ${color}`}>{value}</p>
        <p className="text-slate-400 text-[10px] font-medium">{desc}</p>
    </div>
);

export default EvaluationPage;
