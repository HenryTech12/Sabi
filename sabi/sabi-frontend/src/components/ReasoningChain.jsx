import React from "react";
import { ListChecks } from "lucide-react";

const ReasoningChain = ({
    chain,
    title = "How SABI calculated this rating",
}) => {
    if (!chain || chain.length === 0) return null;

    return (
        <div className="bg-light/50 border border-light rounded-2xl p-6">
            <div className="flex items-center space-x-2 mb-6">
                <ListChecks className="w-5 h-5 text-green" />
                <h3 className="font-bold text-navy">{title}</h3>
            </div>

            <div className="space-y-6 relative before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-green/20">
                {chain.map((step, index) => (
                    <div key={index} className="relative pl-8">
                        <div className="absolute left-0 top-1 w-6 h-6 rounded-full bg-white border-2 border-green flex items-center justify-center z-10">
                            <span className="text-[10px] font-bold text-green">
                                {index + 1}
                            </span>
                        </div>
                        <p className="text-sm text-navy/80 font-medium leading-relaxed">
                            {step}
                        </p>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ReasoningChain;
