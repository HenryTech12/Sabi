import React from "react";
import { Brain, Map, Star, MessageCircle, Heart, Zap } from "lucide-react";

const SoulProfileCard = ({ profile, userName }) => {
    if (!profile) return null;

    // Since response might be a simulated response object or a raw profile, handle both
    const isSimulatedResponse = profile.soul_profile_summary !== undefined;

    return (
        <div className="bg-navy text-white rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
                <Brain className="w-20 h-20" />
            </div>

            <div className="relative z-10">
                <div className="flex items-center space-x-2 mb-6">
                    <div className="bg-green p-2 rounded-lg">
                        <Brain className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <p className="text-[10px] text-green font-bold uppercase tracking-wider">
                            Soul Analysis
                        </p>
                        <h3 className="text-lg font-bold">
                            SABI read {userName}'s soul
                        </h3>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-white/10 p-3 rounded-xl">
                        <p className="text-muted text-[10px] uppercase font-bold mb-1">
                            Personality
                        </p>
                        <div className="flex items-center">
                            <Zap className="w-4 h-4 text-amber mr-2" />
                            <span className="font-bold text-sm tracking-tight">
                                {profile.personality_type?.toUpperCase() ||
                                    "ANALYST"}
                            </span>
                        </div>
                    </div>

                    <div className="bg-white/10 p-3 rounded-xl">
                        <p className="text-muted text-[10px] uppercase font-bold mb-1">
                            Nigerian Voice
                        </p>
                        <div className="flex items-center">
                            <Map className="w-4 h-4 text-green mr-2" />
                            <span className="font-bold text-sm tracking-tight">
                                {profile.detected_region || "Enugu"} •{" "}
                                {profile.dialect_persona?.replace("_", " ") ||
                                    "Igbo East"}
                            </span>
                        </div>
                    </div>

                    <div className="bg-white/10 p-3 rounded-xl">
                        <p className="text-muted text-[10px] uppercase font-bold mb-1">
                            Rating Style
                        </p>
                        <div className="flex items-center">
                            <Star className="w-4 h-4 text-amber mr-2" />
                            <span className="font-bold text-sm tracking-tight">
                                {profile.rating_style || "Balanced"} (
                                {profile.avg_rating || "3.8"})
                            </span>
                        </div>
                    </div>

                    <div className="bg-white/10 p-3 rounded-xl">
                        <p className="text-muted text-[10px] uppercase font-bold mb-1">
                            Primary Focus
                        </p>
                        <div className="flex items-center">
                            <MessageCircle className="w-4 h-4 text-teal mr-2" />
                            <span className="font-bold text-sm tracking-tight">
                                {profile.primary_focus || "Story/Plot"}
                            </span>
                        </div>
                    </div>
                </div>

                <div className="mt-6 flex flex-wrap gap-2">
                    {(profile.signature_phrases || ["nna", "chai", "God when"])
                        .slice(0, 3)
                        .map((phrase) => (
                            <span
                                key={phrase}
                                className="bg-white/5 border border-white/10 text-[10px] px-2 py-1 rounded-md text-light/80"
                            >
                                "{phrase}"
                            </span>
                        ))}
                </div>
            </div>
        </div>
    );
};

export default SoulProfileCard;
