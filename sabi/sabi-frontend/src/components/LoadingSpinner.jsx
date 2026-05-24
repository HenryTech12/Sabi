import React, { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";

const LoadingSpinner = ({ type = "review" }) => {
    const [messageIndex, setMessageIndex] = useState(0);

    const reviewMessages = [
        "Reading soul profile...",
        "Detecting Nigerian voice...",
        "Simulating review...",
    ];

    const recommendMessages = [
        "Building soul profile...",
        "Reasoning across 50 items...",
        "Ranking by fit...",
    ];

    const messages = type === "review" ? reviewMessages : recommendMessages;

    useEffect(() => {
        const interval = setInterval(() => {
            setMessageIndex((prev) => (prev + 1) % messages.length);
        }, 2000);
        return () => clearInterval(interval);
    }, [messages.length]);

    return (
        <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
            <div className="relative mb-6">
                <Loader2 className="w-16 h-16 text-green animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-green font-bold text-xs">SABI</span>
                </div>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
                {messages[messageIndex]}
            </h3>
            <p className="text-muted text-sm max-w-xs">
                The LLM agents are thinking deeply — this can take up to 60
                seconds for complex profiles.
            </p>
        </div>
    );
};

export default LoadingSpinner;
