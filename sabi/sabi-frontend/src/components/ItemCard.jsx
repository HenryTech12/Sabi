import React from "react";
import { Calendar, Monitor, Globe, Star } from "lucide-react";

const ItemCard = ({ item, selected, onClick }) => {
    return (
        <div
            className={`p-4 rounded-xl cursor-pointer transition-all border-2 ${
                selected
                    ? "bg-green/10 border-green scale-[1.02] shadow-md"
                    : "bg-white border-transparent hover:border-green/30 hover:shadow-sm"
            }`}
            onClick={() => onClick && onClick(item)}
        >
            <div className="flex justify-between items-start mb-2">
                <h4 className="font-bold text-navy leading-tight line-clamp-1">
                    {item.title}
                </h4>
                {item.is_nigerian && (
                    <span className="bg-amber text-white text-[9px] font-bold px-1.5 py-0.5 rounded leading-none shrink-0 ml-2">
                        NOLLYWOOD
                    </span>
                )}
            </div>

            <div className="flex items-center text-muted text-[11px] mb-3 space-x-3">
                <span className="flex items-center">
                    <Calendar className="w-3 h-3 mr-1" /> {item.year}
                </span>
                <span className="flex items-center flex-wrap">
                    {item.genre.slice(0, 2).map((g) => (
                        <span
                            key={g}
                            className="bg-green/10 text-green px-1.5 py-0.5 rounded mr-1 mb-1"
                        >
                            {g}
                        </span>
                    ))}
                </span>
            </div>

            <p className="text-muted text-[11px] line-clamp-2 mb-3 h-8">
                {item.description}
            </p>

            <div className="flex items-center justify-between pt-1 border-t border-light mt-auto">
                <div className="flex items-center text-[11px] font-bold text-navy">
                    <Star className="w-3 h-3 text-amber fill-amber mr-1" />
                    {item.avg_community_rating}
                </div>
                <div className="flex items-center text-[10px] text-muted">
                    {item.is_african ? (
                        <Globe className="w-2.5 h-2.5 mr-1" />
                    ) : (
                        <Monitor className="w-2.5 h-2.5 mr-1" />
                    )}
                    {item.is_african ? "African" : "Global"}
                </div>
            </div>
        </div>
    );
};

export default ItemCard;
