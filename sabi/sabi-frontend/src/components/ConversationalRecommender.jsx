import React, { useState, useEffect, useRef } from "react";
import { getRecommendations } from "../utils/api";
import { Send, User, Bot, Trash2, Sparkles, Star } from "lucide-react";
import ItemCard from "./ItemCard";

const ConversationalRecommender = ({ userHistory }) => {
    const [chatHistory, setChatHistory] = useState([]);
    const [currentMessage, setCurrentMessage] = useState("");
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [chatHistory]);

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!currentMessage.trim() || loading) return;

        const newMessage = { role: "user", content: currentMessage };
        const updatedHistory = [...chatHistory, newMessage];

        setChatHistory(updatedHistory);
        setCurrentMessage("");
        setLoading(true);

        try {
        // TRUNCATE: Only send the last 4 messages (2 turns) to keep token count low
            const limitedHistory = updatedHistory.slice(-4); 

            const data = await getRecommendations(
                userHistory,
                limitedHistory, // <--- Use the sliced history here
                currentMessage
            );

            console.log("Full API Response:", data); // Add this line

            const assistantMessage = {
                role: "assistant",
                content: data.soul_profile_summary || data.reasoning || "Here are some matches for you:",
                recommendations: data.recommendations,
            };

            setChatHistory([...updatedHistory, assistantMessage]);
        } catch (error) {
            console.error("Chat error:", error);
            setChatHistory([
                ...updatedHistory,
                {
                    role: "assistant",
                    content:
                        "Omo, something went wrong with the connection. Abeg try again.",
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const clearChat = () => {
        setChatHistory([]);
    };

    return (
        <div className="flex flex-col h-[600px] bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-emerald-600 to-teal-600 p-4 flex justify-between items-center text-white">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5" />
                    <h3 className="font-bold">
                        SABI Conversational Recommender
                    </h3>
                </div>
                <button
                    onClick={clearChat}
                    className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                    title="Clear conversation"
                >
                    <Trash2 className="w-5 h-5" />
                </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
                {chatHistory.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
                        <Bot className="w-12 h-12 opacity-20" />
                        <p className="text-sm">
                            What would you like recommendations for today?
                        </p>
                    </div>
                )}

                {chatHistory.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex ${
                            msg.role === "user"
                                ? "justify-end"
                                : "justify-start"
                        }`}
                    >
                        <div
                            className={`flex gap-3 max-w-[85%] ${
                                msg.role === "user"
                                    ? "flex-row-reverse"
                                    : "flex-row"
                            }`}
                        >
                            <div
                                className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                                    msg.role === "user"
                                        ? "bg-emerald-100 text-emerald-600"
                                        : "bg-teal-600 text-white"
                                }`}
                            >
                                {msg.role === "user" ? (
                                    <User className="w-5 h-5" />
                                ) : (
                                    <Bot className="w-5 h-5" />
                                )}
                            </div>

                            <div
                                className={`p-3 rounded-2xl ${
                                    msg.role === "user"
                                        ? "bg-emerald-600 text-white rounded-tr-none"
                                        : "bg-white border border-slate-200 text-slate-800 rounded-tl-none shadow-sm"
                                }`}
                            >
                                <p className="text-sm whitespace-pre-wrap">
                                    {msg.content}
                                </p>

                                {msg.recommendations && (
                                    <div className="mt-4 grid grid-cols-1 gap-3">
                                        <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1 flex items-center gap-1">
                                            <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                                            Top Picks for you
                                        </p>
                                        {msg.recommendations.map(
                                            (rec, rIdx) => (
                                                <div
                                                    key={rIdx}
                                                    className="scale-90 origin-top-left -mb-4"
                                                >
                                                    <ItemCard
                                                        recommendation={rec}
                                                    />
                                                </div>
                                            )
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="flex justify-start">
                        <div className="flex gap-3">
                            <div className="w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center shrink-0">
                                <Bot className="w-5 h-5" />
                            </div>
                            <div className="p-4 bg-white border border-slate-200 rounded-2xl rounded-tl-none shadow-sm flex gap-1">
                                <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce"></div>
                                <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                                <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce [animation-delay:0.4s]"></div>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form
                onSubmit={handleSendMessage}
                className="p-4 bg-white border-t border-slate-200 flex gap-2"
            >
                <input
                    type="text"
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    placeholder="Ask for recommendations..."
                    className="flex-1 px-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 text-sm"
                />
                <button
                    type="submit"
                    disabled={loading || !currentMessage.trim()}
                    className="bg-emerald-600 text-white p-2 rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                >
                    <Send className="w-5 h-5" />
                </button>
            </form>
        </div>
    );
};

export default ConversationalRecommender;
