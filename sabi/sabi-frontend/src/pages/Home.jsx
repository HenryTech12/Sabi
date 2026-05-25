import React from "react";
import { useNavigate } from "react-router-dom";
import { Brain, Mic, TrendingUp, ChevronRight, Play } from "lucide-react";

const Home = () => {
    const navigate = useNavigate();

    return (
        <div className="flex flex-col min-h-screen">
            {/* Hero Section */}
            <section className="bg-navy text-white pt-32 pb-20 px-6 overflow-hidden relative">
                <div className="absolute top-0 right-0 p-20 opacity-10 blur-2xl">
                    <div className="w-96 h-96 bg-green rounded-full"></div>
                </div>

                <div className="max-w-6xl mx-auto flex flex-col items-center text-center relative z-10">
                    <div className="bg-green/10 text-green px-4 py-1 rounded-full text-sm font-bold border border-green/30 mb-6 uppercase tracking-widest flex items-center gap-2">
                        <span className="w-2 h-2 bg-green rounded-full animate-pulse"></span>
                        SABI Engine v1.1 - Live Cloud Integrated
                    </div>
                    <h1 className="text-7xl md:text-8xl font-black mb-4 tracking-tighter">
                        SABI<span className="text-green">.</span>
                    </h1>
                    <h2 className="text-2xl md:text-3xl font-bold text-light/90 mb-6 uppercase tracking-tight">
                        To Know Deeply
                    </h2>
                    <p className="text-lg md:text-xl text-muted max-w-2xl mb-10 leading-relaxed">
                        The first AI that models Nigerian users as living
                        psychological personalities. Now streaming live from
                        TMDB and MovieLens for real-world cultural deep-dives.
                    </p>

                    <div className="flex flex-wrap justify-center gap-4">
                        <button
                            onClick={() => navigate("/simulate-review")}
                            className="bg-green hover:bg-teal text-white px-8 py-4 rounded-full font-bold transition-all shadow-lg flex items-center group"
                        >
                            Simulate Review
                            <ChevronRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </button>
                        <button
                            onClick={() => navigate("/recommend")}
                            className="bg-white/10 hover:bg-white/20 text-white border border-white/20 px-8 py-4 rounded-full font-bold transition-all backdrop-blur-sm"
                        >
                            Get Recommendations
                        </button>
                        <a
                            href="https://drive.google.com/file/d/1_C7NTmJpUzDJrfIHHKeFWz2Uwk9CXfrt/view?usp=sharing"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 text-white/70 hover:text-green px-6 py-4 transition-colors font-bold group"
                        >
                            <div className="w-10 h-10 rounded-full border border-white/20 flex items-center justify-center group-hover:bg-green group-hover:border-green transition-all">
                                <Play className="w-4 h-4 fill-current" />
                            </div>
                            Watch Demo Video
                        </a>
                    </div>

                    <div className="mt-12 flex items-center gap-6 opacity-60">
                        <span className="text-xs font-bold uppercase tracking-widest">
                            Powered By
                        </span>
                        <div className="flex gap-4 grayscale brightness-200">
                            {/* Small text labels instead of full logos for simplicity */}
                            <span className="text-[10px] font-black border border-white/30 px-2 py-1 rounded">
                                TMDB
                            </span>
                            <span className="text-[10px] font-black border border-white/30 px-2 py-1 rounded">
                                HuggingFace
                            </span>
                            <span className="text-[10px] font-black border border-white/30 px-2 py-1 rounded">
                                OpenAI
                            </span>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Grid */}
            <section className="py-20 px-6 bg-light">
                <div className="max-w-6xl mx-auto">
                    <div className="grid md:grid-cols-3 gap-8">
                        <div className="bg-white p-8 rounded-3xl shadow-sm border border-light relative overflow-hidden group">
                            <div className="bg-navy/5 p-4 rounded-2xl w-fit mb-6 text-navy">
                                <Brain className="w-8 h-8" />
                            </div>
                            <h3 className="text-xl font-bold text-navy mb-3 italic">
                                Psychological Profiling
                            </h3>
                            <p className="text-muted text-sm leading-relaxed">
                                Our Soul Reader agent reads your total review
                                history and extracts your internal world —
                                whether you are an optimist, storyteller, or
                                contrarian analyst.
                            </p>
                        </div>

                        <div className="bg-white p-8 rounded-3xl shadow-sm border border-light relative overflow-hidden group">
                            <div className="bg-green/5 p-4 rounded-2xl w-fit mb-6 text-green">
                                <Mic className="w-8 h-8" />
                            </div>
                            <h3 className="text-xl font-bold text-navy mb-3 italic">
                                Nigerian Voice Engine
                            </h3>
                            <p className="text-muted text-sm leading-relaxed">
                                The Voice Mapper detects your region and maps
                                your soul and personality to your local dialect
                                — Lagos Pidgin, Hausa-English, or Igbo-English.
                            </p>
                        </div>

                        <div className="bg-white p-8 rounded-3xl shadow-sm border border-light relative overflow-hidden group">
                            <div className="bg-amber/5 p-4 rounded-2xl w-fit mb-6 text-amber">
                                <TrendingUp className="w-8 h-8" />
                            </div>
                            <h3 className="text-xl font-bold text-navy mb-3 italic">
                                Behavioural Intelligence
                            </h3>
                            <p className="text-muted text-sm leading-relaxed">
                                SABI recommends based on who you ARE. If you
                                love female-led stories or high-stakes hustle,
                                SABI finds it across any category.
                            </p>
                        </div>
                    </div>

                    {/* Stats Bar */}
                    <div className="mt-20 bg-navy rounded-3xl p-8 flex flex-wrap justify-around items-center gap-8 shadow-2xl">
                        <div className="text-center">
                            <p className="text-4xl font-black text-green">
                                400+
                            </p>
                            <p className="text-[10px] text-muted uppercase font-bold tracking-widest mt-1">
                                Personas
                            </p>
                        </div>
                        <div className="text-center border-l border-white/10 pl-8">
                            <p className="text-4xl font-black text-white">
                                LIVE
                            </p>
                            <p className="text-[10px] text-muted uppercase font-bold tracking-widest mt-1">
                                TMDB Catalog
                            </p>
                        </div>
                        <div className="text-center border-l border-white/10 pl-8">
                            <p className="text-4xl font-black text-white">4</p>
                            <p className="text-[10px] text-muted uppercase font-bold tracking-widest mt-1">
                                AI Agents
                            </p>
                        </div>
                        <div className="text-center border-l border-white/10 pl-8">
                            <p className="text-4xl font-black text-green">6</p>
                            <p className="text-[10px] text-muted uppercase font-bold tracking-widest mt-1">
                                Dialects
                            </p>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default Home;
