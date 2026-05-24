import React from "react";
import { Link, useLocation } from "react-router-dom";

const Navbar = () => {
    const location = useLocation();

    const navLinks = [
        { name: "Home", path: "/" },
        { name: "Simulate Review", path: "/simulate-review" },
        { name: "Recommend", path: "/recommend" },
        { name: "Live Demo & Evaluation", path: "/evaluation" },
        { name: "About", path: "/about" },
    ];

    return (
        <nav className="bg-navy text-white py-4 px-6 fixed top-0 w-full z-50 shadow-lg flex items-center justify-between">
            <div className="flex items-center space-x-2">
                <Link to="/" className="text-2xl font-bold flex items-center">
                    SABI<span className="text-green text-3xl">.</span>
                </Link>
                <span className="text-muted text-xs hidden sm:inline-block ml-2 border-l border-muted/30 pl-2">
                    Nigerian Behavioural Soul Engine
                </span>
            </div>

            <div className="hidden md:flex items-center space-x-8">
                {navLinks.map((link) => (
                    <Link
                        key={link.path}
                        to={link.path}
                        className={`hover:text-green transition-colors ${
                            location.pathname === link.path
                                ? "text-green font-semibold"
                                : "text-light/80"
                        }`}
                    >
                        {link.name}
                    </Link>
                ))}
            </div>

            <div className="bg-green/20 text-green px-3 py-1 rounded-full text-xs font-semibold border border-green/30">
                DSN x BCT Hackathon 3.0
            </div>
        </nav>
    );
};

export default Navbar;
