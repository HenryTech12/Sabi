/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    theme: {
        extend: {
            colors: {
                navy: "#0C2340",
                green: "#1D9E75",
                amber: "#D97706",
                light: "#F0F4F8",
                dark: "#1E293B",
                muted: "#64748B",
                teal: "#0F766E",
                purple: "#4B3F8C",
            },
        },
    },
    plugins: [],
};
