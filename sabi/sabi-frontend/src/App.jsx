import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import SimulateReview from "./pages/SimulateReview";
import Recommend from "./pages/Recommend";
import Evaluation from "./pages/Evaluation";
import About from "./pages/About";

function App() {
    return (
        <Router
            future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true,
            }}
        >
            <div className="min-h-screen bg-light">
                <Navbar />
                <main>
                    <Routes>
                        <Route path="/" element={<Home />} />
                        <Route
                            path="/simulate-review"
                            element={<SimulateReview />}
                        />
                        <Route path="/recommend" element={<Recommend />} />
                        <Route path="/evaluation" element={<Evaluation />} />
                        <Route path="/about" element={<About />} />
                    </Routes>
                </main>
            </div>
        </Router>
    );
}

export default App;
