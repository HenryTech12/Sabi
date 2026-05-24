import React from "react";
import { User, MapPin, Briefcase, Star } from "lucide-react";

const PersonaCard = ({ persona, selected, onClick }) => {
    const getRegionalIndicator = (location) => {
        switch (location) {
            case "Lagos":
                return "🇳🇬 Lagos Pidgin";
            case "Kano":
                return "🇳🇬 Hausa Formal";
            case "Enugu":
                return "🇳🇬 Igbo Expressive";
            case "Port Harcourt":
                return "🇳🇬 South-South Warm";
            case "Abuja":
                return "🇳🇬 Professional Neutral";
            default:
                return "🇳🇬 Nigerian";
        }
    };

    const getPersonalityBadge = (id) => {
        const badges = {
            usr_001: "Igbo Analyst | Critical Rater",
            usr_002: "Hausa Traditionalist | Measured",
            usr_003: "Lagos Hustler | Generous Rater",
            usr_004: "Abuja Cosmopolitan | Perfectionist",
            usr_005: "PH Urbanist | Enthusiastic",
        };
        return badges[id] || "Nigerian Soul";
    };

    return (
        <div
            className={`p-4 rounded-xl cursor-pointer transition-all border-2 mb-4 ${
                selected
                    ? "bg-green/10 border-green scale-[1.02] shadow-md"
                    : "bg-white border-transparent hover:border-green/30 hover:shadow-sm"
            }`}
            onClick={() => onClick(persona)}
        >
            <div className="flex justify-between items-start mb-2">
                <h4 className="font-bold text-navy flex items-center">
                    <User className="w-4 h-4 mr-2 text-green" />
                    {persona.name}
                </h4>
                <span className="bg-navy text-white text-[10px] px-2 py-0.5 rounded-full">
                    {persona.user_id}
                </span>
            </div>

            <div className="space-y-1 mb-3">
                <div className="flex items-center text-muted text-xs">
                    <MapPin className="w-3 h-3 mr-1" />
                    {persona.location}
                </div>
                <div className="flex items-center text-muted text-xs">
                    <Briefcase className="w-3 h-3 mr-1" />
                    {persona.occupation || "Student"} • {persona.age} years
                </div>
            </div>

            <div className="flex items-center justify-between">
                <div className="flex items-center bg-amber/10 text-amber text-[10px] font-bold px-2 py-1 rounded">
                    <Star className="w-3 h-3 mr-1 fill-amber" />
                    {persona.reviewed_items.reduce(
                        (acc, curr) => acc + curr.rating_given,
                        0
                    ) / persona.reviewed_items.length}{" "}
                    AVG
                </div>
                <div className="text-[10px] text-muted font-medium">
                    {persona.reviewed_items.length} Reviews
                </div>
            </div>

            <div className="mt-3 pt-3 border-t border-light text-[10px] text-navy/70 italic font-medium">
                {getPersonalityBadge(persona.user_id)}
            </div>
        </div>
    );
};

export default PersonaCard;
