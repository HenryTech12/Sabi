import React, { useState, useEffect } from "react";
import { getPipelineDemo, getPersonas } from "../utils/api";
import {
    Scan,
    Mic2,
    PenTool,
    Compass,
    ChevronDown,
    ChevronUp,
    Activity,
    Clock,
    CheckCircle2,
    Quote,
} from "lucide-react";
import LoadingSpinner from "./LoadingSpinner";

const PipelineVisualizer = () => {
    const [trace, setTrace] = useState(null);
    const [personas, setPersonas] = useState([]);
    const [selectedUser, setSelectedUser] = useState("");
    const [loading, setLoading] = useState(false);
    const [activeStep, setActiveStep] = useState(null);

    useEffect(() => {
        loadPersonas();
    }, []);

    const loadPersonas = async () => {
        try {
            const data = await getPersonas();
            setPersonas(data);
            if (data.length > 0) {
                setSelectedUser(data[0].user_id);
            }
        } catch (err) {
            console.error("Failed to load personas");
        }
    };

    const runDemo = async () => {
        if (!selectedUser) return;
        setLoading(true);
        setActiveStep(null);
        try {
            const data = await getPipelineDemo(selectedUser);
            setTrace(data);
            // Sequentially animate steps
            for (let i = 0; i < 4; i++) {
                await new Promise((r) => setTimeout(r, 400));
                setActiveStep(i + 1);
            }
        } catch (err) {
            console.error("Demo failed");
        } finally {
            setLoading(false);
        }
    };

    const steps = [
        {
            id: 1,
            title: "Soul Reader",
            agent: "Core Profiler",
            icon: <Scan className="w-5 h-5" />,
        },
        {
            id: 2,
            title: "Voice Mapper",
            agent: "Linguistic Overlay",
            icon: <Mic2 className="w-5 h-5" />,
        },
        {
            id: 3,
            title: "Review Simulator",
            agent: "Behavioral Forecaster",
            icon: <PenTool className="w-5 h-5" />,
        },
        {
            id: 4,
            title: "Contextual Recommender",
            agent: "Fidelity Ranker",
            icon: <Compass className="w-5 h-5" />,
        },
    ];

    return (
        <div className="space-y-8">
            {/* Header Info */}
            <div className="flex flex-col md:flex-row justify-between items-end md:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
                <div className="space-y-4 w-full md:w-auto">
                    <div className="space-y-1">
                        <h3 className="text-xl font-bold text-slate-900">
                            End-to-End Pipeline
                        </h3>
                        <p className="text-slate-500 text-sm">
                            Trace a user through the full agent stack.
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <select
                            value={selectedUser}
                            onChange={(e) => setSelectedUser(e.target.value)}
                            className="bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block p-2.5"
                        >
                            <option value="">Select a User</option>
                            {personas.map((p) => (
                                <option key={p.user_id} value={p.user_id}>
                                    {p.name} ({p.location})
                                </option>
                            ))}
                        </select>
                        <button
                            onClick={runDemo}
                            disabled={loading}
                            className="px-6 py-2.5 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
                        >
                            {loading ? (
                                <Activity className="w-4 h-4 animate-spin" />
                            ) : (
                                <Activity className="w-4 h-4" />
                            )}
                            Run Demo
                        </button>
                    </div>
                </div>

                {trace && (
                    <div className="bg-indigo-50 p-4 rounded-xl border border-indigo-100 flex items-center gap-4">
                        <div className="p-3 bg-indigo-600 rounded-lg text-white">
                            <Clock className="w-6 h-6" />
                        </div>
                        <div>
                            <p className="text-indigo-600 text-xs font-bold uppercase tracking-wider">
                                Total Latency
                            </p>
                            <p className="text-2xl font-black text-indigo-900">
                                {trace.total_latency_ms}ms
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* Pipeline Stepper */}
            <div className="relative space-y-4">
                {/* Connecting Line */}
                <div className="absolute left-6 top-8 bottom-8 w-0.5 bg-slate-100 hidden md:block"></div>

                {steps.map((step) => {
                    const isEnabled =
                        activeStep !== null && activeStep >= step.id;
                    const isCurrent = activeStep === step.id;
                    const output = trace?.pipeline_steps.find(
                        (s) => s.step === step.id
                    )?.output;

                    return (
                        <div
                            key={step.id}
                            className={`relative flex gap-6 group transition-all ${
                                isEnabled ? "opacity-100" : "opacity-40"
                            }`}
                        >
                            <div
                                className={`hidden md:flex flex-shrink-0 w-12 h-12 rounded-full items-center justify-center z-10 transition-colors ${
                                    isEnabled
                                        ? "bg-indigo-600 text-white"
                                        : "bg-slate-100 text-slate-400"
                                }`}
                            >
                                {isEnabled ? (
                                    <CheckCircle2 className="w-6 h-6" />
                                ) : (
                                    step.id
                                )}
                            </div>

                            <div
                                className={`flex-1 bg-white rounded-2xl border transition-all ${
                                    isCurrent
                                        ? "border-indigo-500 shadow-lg ring-1 ring-indigo-500"
                                        : "border-slate-100 shadow-sm"
                                }`}
                            >
                                <div
                                    className="p-4 flex items-center justify-between cursor-pointer"
                                    onClick={() =>
                                        isEnabled &&
                                        setActiveStep(
                                            activeStep === step.id
                                                ? null
                                                : step.id
                                        )
                                    }
                                >
                                    <div className="flex items-center gap-4">
                                        <div
                                            className={`p-2 rounded-lg ${
                                                isEnabled
                                                    ? "bg-indigo-50 text-indigo-600"
                                                    : "bg-slate-50 text-slate-400"
                                            }`}
                                        >
                                            {step.icon}
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-slate-900">
                                                {step.title}
                                            </h4>
                                            <p className="text-xs text-slate-500">
                                                {step.agent}
                                            </p>
                                        </div>
                                    </div>
                                    {isEnabled &&
                                        (activeStep === step.id ? (
                                            <ChevronUp className="w-5 h-5 text-slate-400" />
                                        ) : (
                                            <ChevronDown className="w-5 h-5 text-slate-400" />
                                        ))}
                                </div>

                                {isEnabled && activeStep === step.id && (
                                    <div className="p-6 pt-0 border-t border-slate-50 animate-in fade-in slide-in-from-top-2 duration-300">
                                        <div className="mt-4 overflow-hidden rounded-xl bg-slate-50">
                                            {step.id === 1 &&
                                                renderStep1(output)}
                                            {step.id === 2 &&
                                                renderStep2(output)}
                                            {step.id === 3 &&
                                                renderStep3(output)}
                                            {step.id === 4 &&
                                                renderStep4(output)}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );

    function renderStep1(output) {
        return (
            <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatBox label="Personality" value={output.personality_type} />
                <StatBox label="Dialect" value={output.dialect_persona} />
                <StatBox label="Avg Rating" value={output.avg_rating} />
                <StatBox label="Variance" value={output.rating_variance} />
            </div>
        );
    }

    function renderStep2(output) {
        return (
            <div className="p-6 bg-slate-900 text-slate-50 rounded-xl m-4">
                <div className="flex items-center gap-2 mb-4">
                    <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                        Injection Instruction
                    </span>
                </div>
                <div className="font-mono text-sm leading-relaxed p-4 bg-slate-800 rounded-lg border border-slate-700">
                    {output.voice_instruction}
                </div>
            </div>
        );
    }

    function renderStep3(output) {
        return (
            <div className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                    <h5 className="font-bold">Simulated Review: Brotherhood</h5>
                    <div className="flex gap-1 text-amber-500">
                        {Array.from({ length: 5 }).map((_, i) => (
                            <span key={i}>
                                {i < Math.floor(output.predicted_rating)
                                    ? "★"
                                    : "☆"}
                            </span>
                        ))}
                    </div>
                </div>
                <div className="relative p-6 bg-indigo-50 rounded-2xl italic text-slate-700">
                    <Quote className="absolute -top-2 -left-2 w-8 h-8 text-indigo-200" />
                    {output.review_text}
                </div>
            </div>
        );
    }

    function renderStep4(output) {
        if (!output || !output.recommendations) {
            return <div className="p-6 text-slate-500 italic">No recommendations available</div>;
        }
        
        return (
            <div className="p-6 space-y-3">
                {output.recommendations.slice(0, 3).map((rec, i) => (
                    <div
                        key={i}
                        className="bg-white p-3 rounded-xl border border-slate-100 flex justify-between items-center shadow-sm"
                    >
                        <span className="font-bold text-slate-900">
                            {i + 1}. {rec?.item?.title || "Untitled Item"}
                        </span>
                        <span className="bg-green-100 text-green-700 text-xs font-bold px-2 py-1 rounded">
                            Score: {rec?.fit_score ? Math.round(rec.fit_score * 100) : 0}%
                        </span>
                    </div>
                ))}
            </div>
        );
    }

    function StatBox({ label, value }) {
        return (
            <div className="p-4 bg-white rounded-xl border border-slate-100 flex flex-col items-center justify-center text-center shadow-sm">
                <span className="text-[10px] font-bold text-slate-400 uppercase mb-1">
                    {label}
                </span>
                <span className="text-sm font-bold text-indigo-600 truncate w-full">
                    {value}
                </span>
            </div>
        );
    }
};

export default PipelineVisualizer;
