import React from "react";
import { Target, Users, Layout, ShieldCheck, Heart } from "lucide-react";

const About = () => {
    return (
        <div className="pt-24 pb-20 bg-light min-h-screen">
            <div className="max-w-4xl mx-auto px-6">
                <div className="bg-navy text-white rounded-[40px] p-12 mb-12 shadow-2xl relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-12 opacity-5 scale-150">
                        <Heart className="w-64 h-64 fill-white" />
                    </div>

                    <h1 className="text-6xl font-black mb-6 tracking-tighter italic">
                        About SABI<span className="text-green">.</span>
                    </h1>
                    <p className="text-xl text-light/80 leading-relaxed max-w-2xl mb-8">
                        In Nigerian Pidgin, <strong>SABI</strong> means "to know
                        deeply". Most recommendation systems only know your
                        clicks. We know your soul.
                    </p>

                    <div className="flex flex-wrap gap-6">
                        <div className="bg-white/10 px-6 py-3 rounded-2xl border border-white/20">
                            <p className="text-[10px] text-green font-black uppercase tracking-widest">
                                Hackathon
                            </p>
                            <p className="font-bold text-sm">
                                DSN x Bluechip 3.0
                            </p>
                        </div>
                        <div className="bg-white/10 px-6 py-3 rounded-2xl border border-white/20">
                            <p className="text-[10px] text-green font-black uppercase tracking-widest">
                                Built with
                            </p>
                            <p className="font-bold text-sm">
                                OpenAI GPT-4o Agentic Flow
                            </p>
                        </div>
                    </div>
                </div>

                <div className="space-y-16">
                    <section>
                        <h2 className="text-3xl font-black text-navy mb-8 flex items-center italic">
                            <Target className="mr-4 text-green" />
                            The Four-Agent Architecture
                        </h2>

                        <div className="space-y-4">
                            {[
                                {
                                    name: "Soul Reader",
                                    role: "Psychological Profiler",
                                    desc: "Analyzes review history to build a 22-point psychological trait profile of the user.",
                                },
                                {
                                    name: "Voice Mapper",
                                    role: "Dialect Contextualizer",
                                    desc: "Maps personality into region-specific Nigerian English and dialects for authentic expression.",
                                },
                                {
                                    name: "Review Simulator",
                                    role: "Behavioral Predictor",
                                    desc: "Calculates likely star ratings and simulated textual reviews for unseen content.",
                                },
                                {
                                    name: "Contextual Recommender",
                                    role: "Soul Matcher",
                                    desc: "Ranks database items based on the user's personality match rather than just simple genres.",
                                },
                            ].map((agent, i) => (
                                <div
                                    key={i}
                                    className="bg-white p-6 rounded-3xl border border-light flex items-center gap-6 group hover:border-green transition-colors"
                                >
                                    <div className="bg-navy h-12 w-12 rounded-2xl flex items-center justify-center font-black text-green shrink-0">
                                        {i + 1}
                                    </div>
                                    <div>
                                        <h4 className="font-bold text-navy">
                                            {agent.name}{" "}
                                            <span className="text-muted text-xs font-normal ml-2">
                                                ({agent.role})
                                            </span>
                                        </h4>
                                        <p className="text-muted text-sm mt-1">
                                            {agent.desc}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="bg-green rounded-[40px] p-12 text-white shadow-xl">
                        <h2 className="text-3xl font-black mb-6 italic">
                            Why Culture Matters
                        </h2>
                        <p className="text-lg text-white/90 leading-relaxed mb-6">
                            Recommendation systems serve global audiences but
                            experience is always local. A "good" film for a
                            Lagos critical rater is different from a "good" film
                            for a Kano traditionalist.
                        </p>
                        <p className="text-lg text-white/90 leading-relaxed">
                            By contextualizing ratings and reviews through
                            regional dialects and psychological forgiveness
                            factors, SABI creates a system that users actually
                            trust—because it sounds, thinks, and feels like
                            them.
                        </p>
                    </section>

                    <section className="text-center pt-10">
                        <ShieldCheck className="w-12 h-12 text-green mx-auto mb-4" />
                        <p className="text-muted text-sm italic">
                            SABI is a research project for the DSN x Bluechip
                            LLM Agent Challenge 2024.
                        </p>
                    </section>
                </div>
            </div>
        </div>
    );
};

export default About;
